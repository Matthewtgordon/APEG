"""Metrics collection service orchestrator.

Coordinates Meta and Shopify collectors for daily batch runs.
"""
import asyncio
import json
import logging
import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import aiohttp

from .meta_collector import MetaInsightsCollector
from .schema import (
    init_database,
    record_collection_failure,
    record_collection_success,
    should_collect,
)
from .shopify_collector import ShopifyOrdersCollector


logger = logging.getLogger(__name__)


def _redact_text(text: str, secrets: list[Optional[str]]) -> str:
    if not text:
        return text
    redacted = text
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    return redacted


def _load_strategy_catalog(catalog_path: str) -> list[str]:
    catalog_file = Path(catalog_path)

    if not catalog_file.exists():
        raise FileNotFoundError(
            f"Strategy catalog not found: {catalog_path}. "
            "Create it before running the collector."
        )

    with open(catalog_file, encoding="utf-8") as handle:
        data = json.load(handle)

    tags = data.get("strategy_tags")
    if not isinstance(tags, list):
        raise ValueError("strategy_tags must be a list in strategy tag catalog")

    return tags


def _resolve_timezone(tz_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name)
    except Exception:
        logger.warning("Invalid METRICS_TIMEZONE '%s', using UTC", tz_name)
        return ZoneInfo("UTC")


class MetricsCollectorService:
    """Orchestrates daily metrics collection from Meta and Shopify."""

    def __init__(self) -> None:
        """Initialize collector service from environment variables."""
        self.db_path = Path(os.getenv("METRICS_DB_PATH", "data/metrics.db"))
        self.raw_dir = Path(os.getenv("METRICS_RAW_DIR", "data/metrics/raw"))

        self.meta_access_token = os.getenv("META_ACCESS_TOKEN")
        self.meta_ad_account_id = os.getenv("META_AD_ACCOUNT_ID")

        self.shopify_domain = os.getenv("SHOPIFY_STORE_DOMAIN")
        self.shopify_token = os.getenv("SHOPIFY_ADMIN_ACCESS_TOKEN")
        self.shopify_api_version = os.getenv("SHOPIFY_API_VERSION", "2024-10")

        catalog_path = os.getenv(
            "STRATEGY_TAG_CATALOG", "data/metrics/strategy_tags.json"
        )
        self.strategy_catalog = _load_strategy_catalog(catalog_path)

        self.timezone = os.getenv("METRICS_TIMEZONE", "America/New_York")
        self._tzinfo = _resolve_timezone(self.timezone)

        init_database(self.db_path)

        logger.info("MetricsCollectorService initialized")
        logger.info("Database: %s", self.db_path)
        logger.info("Strategy catalog: %s tags", len(self.strategy_catalog))

    def _redact_error(self, text: str) -> str:
        return _redact_text(text, [self.meta_access_token, self.shopify_token])

    async def run_once(self, target_date: Optional[date] = None) -> None:
        """Run collection for a single date.

        Args:
            target_date: Date to collect (defaults to yesterday)
        """
        if target_date is None:
            target_date = datetime.now(self._tzinfo).date() - timedelta(days=1)

        logger.info("Starting collection for %s", target_date.isoformat())

        db_conn = sqlite3.connect(self.db_path)
        db_conn.execute("PRAGMA journal_mode=WAL")

        try:
            timeout = aiohttp.ClientTimeout(total=300, connect=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                if self.meta_access_token and self.meta_ad_account_id:
                    await self._collect_meta(target_date, session, db_conn)
                else:
                    logger.warning(
                        "Meta credentials not configured, skipping Meta collection"
                    )

                if self.shopify_domain and self.shopify_token:
                    await self._collect_shopify(target_date, session, db_conn)
                else:
                    logger.warning(
                        "Shopify credentials not configured, skipping Shopify collection"
                    )

        finally:
            db_conn.close()

        logger.info("Collection complete for %s", target_date.isoformat())

    async def _collect_meta(
        self,
        target_date: date,
        session: aiohttp.ClientSession,
        db_conn: sqlite3.Connection,
    ) -> None:
        """Collect Meta insights for target date."""
        date_str = target_date.isoformat()

        if not should_collect(db_conn, "meta", date_str):
            logger.info("Skipping Meta collection for %s (already collected)", date_str)
            return

        try:
            collector = MetaInsightsCollector(
                access_token=self.meta_access_token,
                ad_account_id=self.meta_ad_account_id,
                session=session,
                raw_dir=self.raw_dir,
            )

            campaign_data = await collector.fetch_daily("campaign", target_date)
            await collector.persist(campaign_data, "campaign", target_date, db_conn)

            ad_data = await collector.fetch_daily("ad", target_date)
            await collector.persist(ad_data, "ad", target_date, db_conn)

            record_collection_success(
                db_conn,
                "meta",
                date_str,
                f"Collected {len(campaign_data)} campaigns, {len(ad_data)} ads",
            )

            logger.info("Meta collection successful for %s", date_str)

        except Exception as exc:
            logger.error(
                "Meta collection failed for %s: %s",
                date_str,
                self._redact_error(str(exc)),
                exc_info=True,
            )
            try:
                record_collection_failure(db_conn, "meta", date_str, str(exc))
            except Exception as record_exc:
                logger.error(
                    "Failed to record Meta collection failure: %s",
                    self._redact_error(str(record_exc)),
                )
            raise

    async def _collect_shopify(
        self,
        target_date: date,
        session: aiohttp.ClientSession,
        db_conn: sqlite3.Connection,
    ) -> None:
        """Collect Shopify orders for target date."""
        date_str = target_date.isoformat()

        if not should_collect(db_conn, "shopify", date_str):
            logger.info(
                "Skipping Shopify collection for %s (already collected)", date_str
            )
            return

        try:
            collector = ShopifyOrdersCollector(
                shop_domain=self.shopify_domain,
                access_token=self.shopify_token,
                api_version=self.shopify_api_version,
                session=session,
                raw_dir=self.raw_dir,
                strategy_catalog=self.strategy_catalog,
            )

            orders = await collector.fetch_orders(target_date)
            await collector.persist_attributions(orders, target_date, db_conn)

            record_collection_success(
                db_conn,
                "shopify",
                date_str,
                f"Collected {len(orders)} orders",
            )

            logger.info("Shopify collection successful for %s", date_str)

        except Exception as exc:
            logger.error(
                "Shopify collection failed for %s: %s",
                date_str,
                self._redact_error(str(exc)),
                exc_info=True,
            )
            try:
                record_collection_failure(db_conn, "shopify", date_str, str(exc))
            except Exception as record_exc:
                logger.error(
                    "Failed to record Shopify collection failure: %s",
                    self._redact_error(str(record_exc)),
                )
            raise

    async def run_forever(self) -> None:
        """Run collection service continuously (daily schedule).

        Runs at configured time each day, with startup backfill.
        """
        await self._backfill_missing_dates()

        await self.run_once()

    async def _backfill_missing_dates(self) -> None:
        """Backfill missing dates from recent history."""
        backfill_days = int(os.getenv("METRICS_BACKFILL_DAYS", "3"))

        db_conn = sqlite3.connect(self.db_path)
        db_conn.execute("PRAGMA journal_mode=WAL")

        missing_dates: list[date] = []
        try:
            today = datetime.now(self._tzinfo).date()
            for days_ago in range(backfill_days, 0, -1):
                target_date = today - timedelta(days=days_ago)
                date_str = target_date.isoformat()

                meta_missing = should_collect(db_conn, "meta", date_str)
                shopify_missing = should_collect(db_conn, "shopify", date_str)

                if meta_missing or shopify_missing:
                    missing_dates.append(target_date)

        finally:
            db_conn.close()

        for target_date in missing_dates:
            logger.info("Backfilling %s", target_date.isoformat())
            await self.run_once(target_date)
