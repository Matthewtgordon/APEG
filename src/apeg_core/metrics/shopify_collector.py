"""Shopify orders collector with attribution.

Fetches orders for a date window and applies waterfall attribution logic.
"""
import json
import logging
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

import aiohttp

from .attribution import choose_attribution, match_strategy_tag


logger = logging.getLogger(__name__)


def _redact(text: str, token: str) -> str:
    if not text:
        return text
    return text.replace(token, "[REDACTED]")


class ShopifyOrdersCollector:
    """Async collector for Shopify orders with attribution."""

    def __init__(
        self,
        shop_domain: str,
        access_token: str,
        api_version: str,
        session: aiohttp.ClientSession,
        raw_dir: Path,
        strategy_catalog: list[str],
    ) -> None:
        """Initialize Shopify orders collector.

        Args:
            shop_domain: Shopify store domain
            access_token: Admin API access token
            api_version: API version (e.g., '2024-10')
            session: aiohttp session
            raw_dir: Directory for raw JSONL audit logs
            strategy_catalog: List of strategy tags for matching
        """
        self.shop_domain = shop_domain
        self._access_token = access_token
        self.api_version = api_version
        self.session = session
        self.raw_dir = Path(raw_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.strategy_catalog = strategy_catalog

    async def fetch_orders(self, target_date: date) -> list[dict]:
        """Fetch orders created on target date.

        Uses GraphQL to fetch orders with customerJourneySummary.

        Args:
            target_date: Date to fetch orders for

        Returns:
            List of Order nodes
        """
        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = datetime.combine(target_date, datetime.max.time())

        start_iso = start_dt.replace(tzinfo=timezone.utc).isoformat()
        end_iso = end_dt.replace(tzinfo=timezone.utc).isoformat()

        query = """
        query($query: String!, $cursor: String) {
          orders(first: 250, query: $query, after: $cursor) {
            pageInfo {
              hasNextPage
              endCursor
            }
            nodes {
              id
              name
              createdAt
              totalPriceSet {
                shopMoney {
                  amount
                  currencyCode
                }
              }
              customerJourneySummary {
                firstVisit {
                  landingPage
                  referrerUrl
                  utmParameters {
                    campaign
                    source
                    medium
                    term
                    content
                  }
                }
                lastVisit {
                  landingPage
                  referrerUrl
                  utmParameters {
                    campaign
                    source
                    medium
                    term
                    content
                  }
                }
              }
              lineItems(first: 250) {
                edges {
                  node {
                    id
                    quantity
                    variant {
                      id
                      product {
                        id
                      }
                    }
                    originalTotalSet {
                      shopMoney {
                        amount
                        currencyCode
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """

        query_filter = f"created_at:>={start_iso} created_at:<={end_iso}"

        url = (
            f"https://{self.shop_domain}/admin/api/{self.api_version}/graphql.json"
        )
        headers = {
            "X-Shopify-Access-Token": self._access_token,
            "Content-Type": "application/json",
        }

        all_orders: list[dict] = []
        cursor = None

        while True:
            payload = {
                "query": query,
                "variables": {"query": query_filter, "cursor": cursor},
            }

            async with self.session.post(
                url, json=payload, headers=headers
            ) as response:
                if response.status != 200:
                    error_body = await response.text()
                    logger.error(
                        "Shopify GraphQL error (%s): %s",
                        response.status,
                        _redact(error_body[:500], self._access_token),
                    )
                    raise RuntimeError(
                        f"Shopify GraphQL request failed: {response.status}"
                    )

                result = await response.json()

                if "errors" in result and result["errors"]:
                    logger.error("GraphQL errors: %s", result["errors"])
                    raise RuntimeError(f"GraphQL errors: {result['errors']}")

                orders_data = result["data"]["orders"]
                nodes = orders_data["nodes"]
                all_orders.extend(nodes)

                page_info = orders_data["pageInfo"]
                if not page_info["hasNextPage"]:
                    break

                cursor = page_info["endCursor"]

        logger.info("Fetched %s orders for %s", len(all_orders), target_date.isoformat())
        return all_orders

    async def persist_attributions(
        self,
        orders: list[dict],
        target_date: date,
        db_conn: sqlite3.Connection,
    ) -> None:
        """Persist order attributions to SQLite and raw JSONL.

        Args:
            orders: Order nodes from Shopify GraphQL
            target_date: Date of orders
            db_conn: SQLite connection
        """
        date_str = target_date.isoformat()
        fetched_at = datetime.now(timezone.utc).isoformat()

        jsonl_path = self.raw_dir / f"raw_shopify_orders_{date_str}.jsonl"

        with open(jsonl_path, "w", encoding="utf-8") as handle:
            for order in orders:
                envelope = {
                    "source": "shopify",
                    "metric_date": date_str,
                    "fetched_at": fetched_at,
                    "response_item": order,
                }
                handle.write(json.dumps(envelope, separators=(",", ":")) + "\n")

        logger.info("Wrote %s orders to %s", len(orders), jsonl_path)

        try:
            for order in orders:
                order_id = order["id"]
                order_name = order.get("name")
                created_at = order["createdAt"]

                price_set = order.get("totalPriceSet", {}).get("shopMoney", {})
                currency = price_set.get("currencyCode")
                total_price = float(price_set.get("amount", 0))

                attribution = choose_attribution(order)
                strategy_match = match_strategy_tag(
                    attribution["utm_campaign"], self.strategy_catalog
                )

                db_conn.execute(
                    """
                    INSERT INTO order_attributions (
                        order_id, order_name, created_at,
                        currency, total_price,
                        utm_source, utm_medium, utm_campaign, utm_term, utm_content,
                        strategy_tag,
                        attribution_tier, confidence, evidence_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(order_id)
                    DO UPDATE SET
                        utm_source=excluded.utm_source,
                        utm_medium=excluded.utm_medium,
                        utm_campaign=excluded.utm_campaign,
                        utm_term=excluded.utm_term,
                        utm_content=excluded.utm_content,
                        strategy_tag=excluded.strategy_tag,
                        attribution_tier=excluded.attribution_tier,
                        confidence=excluded.confidence,
                        evidence_json=excluded.evidence_json,
                        collected_at=CURRENT_TIMESTAMP
                    """,
                    (
                        order_id,
                        order_name,
                        created_at,
                        currency,
                        total_price,
                        attribution["utm_source"],
                        attribution["utm_medium"],
                        attribution["utm_campaign"],
                        attribution["utm_term"],
                        attribution["utm_content"],
                        strategy_match["strategy_tag"],
                        attribution["attribution_tier"],
                        attribution["confidence"],
                        attribution["evidence_json"],
                    ),
                )

            db_conn.commit()
            logger.info("Persisted %s order attributions to SQLite", len(orders))

            self._persist_line_items(orders, db_conn)
            logger.info("Persisted line items for %s orders", len(orders))

        except Exception as exc:
            logger.error("SQLite write failed for Shopify orders: %s", exc)
            raise

    def _persist_line_items(
        self, orders: list[dict], db_conn: sqlite3.Connection
    ) -> None:
        """Persist order line items with attribution inheritance.

        Args:
            orders: Order nodes from Shopify GraphQL
            db_conn: SQLite connection
        """
        for order in orders:
            order_id = order["id"]
            order_created = order["createdAt"]

            cursor = db_conn.execute(
                """
                SELECT strategy_tag, attribution_tier, confidence, evidence_json
                FROM order_attributions
                WHERE order_id=?
                """,
                (order_id,),
            )
            order_attr = cursor.fetchone()

            if not order_attr:
                logger.warning(
                    "No order attribution found for %s, skipping line items", order_id
                )
                continue

            strategy_tag, tier, confidence, evidence_json = order_attr
            evidence = json.loads(evidence_json)
            raw_source = evidence.get("source", "unknown")

            line_items = order.get("lineItems", {}).get("edges", [])

            for edge in line_items:
                node = edge.get("node") or {}
                variant = node.get("variant")

                if not variant:
                    logger.warning(
                        "Line item %s missing variant, skipping", node.get("id")
                    )
                    continue

                product = variant.get("product")
                if not product:
                    logger.warning(
                        "Variant %s missing product, skipping", variant.get("id")
                    )
                    continue

                product_id = product["id"]
                variant_id = variant.get("id")
                quantity = node.get("quantity", 0)

                price_set = node.get("originalTotalSet", {}).get("shopMoney", {})
                line_revenue = float(price_set.get("amount", 0))
                currency = price_set.get("currencyCode", "USD")

                db_conn.execute(
                    """
                    INSERT INTO order_line_attributions (
                        order_id, order_created_at,
                        product_id, variant_id, quantity,
                        line_revenue, currency,
                        strategy_tag, attribution_tier, confidence, raw_source
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(order_id, product_id, variant_id)
                    DO UPDATE SET
                        line_revenue=excluded.line_revenue,
                        strategy_tag=excluded.strategy_tag,
                        attribution_tier=excluded.attribution_tier,
                        confidence=excluded.confidence,
                        collected_at=CURRENT_TIMESTAMP
                    """,
                    (
                        order_id,
                        order_created,
                        product_id,
                        variant_id,
                        quantity,
                        line_revenue,
                        currency,
                        strategy_tag,
                        tier,
                        confidence,
                        raw_source,
                    ),
                )

        db_conn.commit()
