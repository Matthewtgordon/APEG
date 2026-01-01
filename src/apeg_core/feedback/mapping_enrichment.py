"""Strategy tag mapping enrichment from Meta metrics."""
import json
import logging
import sqlite3
from datetime import date
from typing import Optional

from .mapping import MappingMethod, StrategyTagMapper


logger = logging.getLogger(__name__)


def enrich_strategy_tag_mappings(
    db_conn: sqlite3.Connection,
    strategy_catalog: list[str],
    window_start: Optional[date] = None,
    window_end: Optional[date] = None,
) -> int:
    """Populate strategy_tag_mappings for Meta entities using naming conventions.

    Args:
        db_conn: SQLite connection
        strategy_catalog: List of known strategy tags
        window_start: Optional start date to limit scan
        window_end: Optional end date to limit scan

    Returns:
        Count of mappings inserted/updated
    """
    mapper = StrategyTagMapper(db_conn, strategy_catalog)

    query = """
        SELECT m.entity_type, m.entity_id, m.raw_json
        FROM metrics_meta_daily m
        LEFT JOIN strategy_tag_mappings s
            ON m.entity_type = s.entity_type AND m.entity_id = s.entity_id
        WHERE s.entity_id IS NULL
          AND m.raw_json IS NOT NULL
    """
    params: list[str] = []

    if window_start and window_end:
        query += " AND m.metric_date >= ? AND m.metric_date <= ?"
        params.extend([window_start.isoformat(), window_end.isoformat()])

    rows = db_conn.execute(query, params).fetchall()

    updated = 0

    for entity_type, entity_id, raw_json in rows:
        if not raw_json:
            continue

        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError:
            logger.warning(
                "Skipping Meta row with invalid raw_json: %s/%s",
                entity_type,
                entity_id,
            )
            continue

        if entity_type == "campaign":
            name = payload.get("campaign_name")
        else:
            name = payload.get("ad_name") or payload.get("campaign_name")

        if not name:
            continue

        strategy_tag, confidence = mapper.parse_name(name)
        if not strategy_tag:
            continue

        metadata = {
            "source": "metrics_meta_daily",
            "entity_name": name,
        }

        db_conn.execute(
            """
            INSERT INTO strategy_tag_mappings (
                entity_type, entity_id, strategy_tag,
                mapping_method, mapping_confidence, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_type, entity_id)
            DO UPDATE SET
                strategy_tag=excluded.strategy_tag,
                mapping_method=excluded.mapping_method,
                mapping_confidence=excluded.mapping_confidence,
                metadata_json=excluded.metadata_json,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                entity_type,
                entity_id,
                strategy_tag,
                MappingMethod.NAMING_CONVENTION.value,
                confidence,
                json.dumps(metadata, separators=(",", ":")),
            ),
        )
        updated += 1

    if updated:
        db_conn.commit()

    logger.info("Enriched %s strategy_tag mappings from Meta metrics", updated)
    return updated
