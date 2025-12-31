"""Meta Marketing API insights collector.

Fetches daily campaign and ad-level performance metrics.

WARNING: Meta API field validation is TEST REQUIRED.
Official docs unavailable (429). Field names verified via third-party references.
"""
import asyncio
import json
import logging
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

import aiohttp


logger = logging.getLogger(__name__)


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class MetaInsightsCollector:
    """Async collector for Meta Ads insights."""

    def __init__(
        self,
        access_token: str,
        ad_account_id: str,
        session: aiohttp.ClientSession,
        raw_dir: Path,
    ) -> None:
        """Initialize Meta insights collector.

        Args:
            access_token: Meta Marketing API access token
            ad_account_id: Ad account ID (with or without 'act_' prefix)
            session: aiohttp session for requests
            raw_dir: Directory for raw JSONL audit logs
        """
        self._access_token = access_token

        if not ad_account_id.startswith("act_"):
            ad_account_id = f"act_{ad_account_id}"
        self.ad_account_id = ad_account_id

        self.session = session
        self.raw_dir = Path(raw_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)

        self._semaphore = asyncio.Semaphore(5)

    def _redact(self, text: str) -> str:
        if not text:
            return text
        return text.replace(self._access_token, "[REDACTED]")

    async def fetch_daily(self, level: str, target_date: date) -> list[dict]:
        """Fetch insights for a specific date and level.

        Args:
            level: 'campaign' or 'ad'
            target_date: Date to fetch (YYYY-MM-DD)

        Returns:
            List of insight objects
        """
        date_str = target_date.isoformat()
        url = f"https://graph.facebook.com/v18.0/{self.ad_account_id}/insights"

        params = {
            "access_token": self._access_token,
            "level": level,
            "time_increment": "1",
            "time_range": json.dumps({"since": date_str, "until": date_str}),
            "fields": ",".join(
                [
                    "campaign_id",
                    "campaign_name",
                    "adset_id",
                    "adset_name",
                    "ad_id",
                    "ad_name",
                    "spend",
                    "impressions",
                    "ctr",
                    "cpc",
                    "outbound_clicks",
                ]
            ),
            "limit": "1000",
        }

        all_data: list[dict] = []

        async with self._semaphore:
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    error_body = await response.text()
                    logger.error(
                        "Meta API error (%s): %s",
                        response.status,
                        self._redact(error_body[:500]),
                    )
                    raise RuntimeError(
                        f"Meta API request failed: {response.status}"
                    )

                result = await response.json()
                data = result.get("data", [])
                all_data.extend(data)

                while "paging" in result and "next" in result["paging"]:
                    next_url = result["paging"]["next"]

                    async with self.session.get(next_url) as next_response:
                        if next_response.status != 200:
                            logger.warning(
                                "Meta pagination failed: %s", next_response.status
                            )
                            break

                        result = await next_response.json()
                        data = result.get("data", [])
                        all_data.extend(data)

        logger.info(
            "Fetched %s %s-level insights for %s",
            len(all_data),
            level,
            date_str,
        )
        return all_data

    async def persist(
        self,
        rows: list[dict],
        level: str,
        target_date: date,
        db_conn: sqlite3.Connection,
    ) -> None:
        """Persist insights to SQLite and raw JSONL.

        Args:
            rows: Insight objects from Meta API
            level: 'campaign' or 'ad'
            target_date: Date of data
            db_conn: SQLite connection
        """
        date_str = target_date.isoformat()
        fetched_at = datetime.now(timezone.utc).isoformat()

        jsonl_path = self.raw_dir / f"raw_meta_{level}_{date_str}.jsonl"

        with open(jsonl_path, "w", encoding="utf-8") as handle:
            for row in rows:
                envelope = {
                    "source": "meta",
                    "level": level,
                    "metric_date": date_str,
                    "fetched_at": fetched_at,
                    "response_item": row,
                }
                handle.write(json.dumps(envelope, separators=(",", ":")) + "\n")

        logger.info("Wrote %s rows to %s", len(rows), jsonl_path)

        try:
            for row in rows:
                campaign_id = row.get("campaign_id")
                adset_id = row.get("adset_id")
                ad_id = row.get("ad_id")

                if level == "campaign":
                    entity_id = campaign_id
                else:
                    entity_id = ad_id

                if not entity_id:
                    logger.warning("Skipping row with missing entity_id")
                    continue

                outbound_clicks = row.get("outbound_clicks")

                if outbound_clicks is None:
                    actions = row.get("actions", [])
                    for action in actions:
                        if action.get("action_type") == "outbound_click":
                            outbound_clicks = _safe_int(action.get("value", 0))
                            break
                else:
                    outbound_clicks = _safe_int(outbound_clicks)

                db_conn.execute(
                    """
                    INSERT INTO metrics_meta_daily (
                        metric_date, entity_type, entity_id,
                        campaign_id, adset_id, ad_id, account_id,
                        spend, impressions, ctr, cpc, outbound_clicks,
                        raw_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(metric_date, entity_type, entity_id)
                    DO UPDATE SET
                        spend=excluded.spend,
                        impressions=excluded.impressions,
                        ctr=excluded.ctr,
                        cpc=excluded.cpc,
                        outbound_clicks=excluded.outbound_clicks,
                        raw_json=excluded.raw_json,
                        collected_at=CURRENT_TIMESTAMP
                    """,
                    (
                        date_str,
                        level,
                        entity_id,
                        campaign_id,
                        adset_id,
                        ad_id,
                        self.ad_account_id,
                        _safe_float(row.get("spend", 0)) or 0.0,
                        _safe_int(row.get("impressions", 0)) or 0,
                        _safe_float(row.get("ctr", 0)) or 0.0,
                        _safe_float(row.get("cpc", 0)) or 0.0,
                        outbound_clicks,
                        json.dumps(row, separators=(",", ":")),
                    ),
                )

            db_conn.commit()
            logger.info("Persisted %s %s metrics to SQLite", len(rows), level)

        except Exception as exc:
            logger.error(
                "SQLite write failed for Meta %s metrics: %s", level, exc
            )
            raise
