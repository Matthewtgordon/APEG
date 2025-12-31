"""SQLite schema definitions for metrics collection.

Database: data/metrics.db (WAL mode)
Tables: metrics_meta_daily, order_attributions, collector_state
"""
import logging
import sqlite3
from pathlib import Path
from typing import Optional


logger = logging.getLogger(__name__)


SCHEMA_VERSION = 1


def init_database(db_path: str | Path) -> None:
    """Initialize metrics database with schema.

    Creates tables if they don't exist.
    Enables WAL mode for concurrent reads.

    Args:
        db_path: Path to SQLite database file
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)

    try:
        conn.execute("PRAGMA journal_mode=WAL")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor = conn.execute("SELECT MAX(version) FROM schema_version")
        current_version = cursor.fetchone()[0] or 0

        if current_version < SCHEMA_VERSION:
            _apply_schema(conn)
            conn.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,),
            )
            conn.commit()
            logger.info("Database schema initialized (version %s)", SCHEMA_VERSION)
        else:
            logger.debug("Database schema up to date (version %s)", current_version)

    finally:
        conn.close()


def _apply_schema(conn: sqlite3.Connection) -> None:
    """Apply database schema.

    Args:
        conn: SQLite connection (in transaction)
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS metrics_meta_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_date TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            campaign_id TEXT,
            adset_id TEXT,
            ad_id TEXT,
            account_id TEXT NOT NULL,
            spend REAL,
            impressions INTEGER,
            ctr REAL,
            cpc REAL,
            outbound_clicks INTEGER,
            raw_json TEXT,
            collected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(metric_date, entity_type, entity_id)
        )
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_meta_date_type
        ON metrics_meta_daily(metric_date, entity_type)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_meta_campaign
        ON metrics_meta_daily(campaign_id)
        WHERE campaign_id IS NOT NULL
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS order_attributions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL UNIQUE,
            order_name TEXT,
            created_at TEXT NOT NULL,
            currency TEXT,
            total_price REAL,
            utm_source TEXT,
            utm_medium TEXT,
            utm_campaign TEXT,
            utm_term TEXT,
            utm_content TEXT,
            strategy_tag TEXT,
            attribution_tier INTEGER NOT NULL,
            confidence REAL NOT NULL,
            evidence_json TEXT NOT NULL,
            collected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_orders_created
        ON order_attributions(created_at)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_orders_strategy
        ON order_attributions(strategy_tag)
        WHERE strategy_tag IS NOT NULL
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_orders_campaign
        ON order_attributions(utm_campaign)
        WHERE utm_campaign IS NOT NULL
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS collector_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT NOT NULL,
            metric_date TEXT NOT NULL,
            status TEXT NOT NULL,
            details TEXT,
            collected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source_name, metric_date)
        )
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_collector_date
        ON collector_state(metric_date, source_name)
        """
    )


def record_collection_success(
    conn: sqlite3.Connection,
    source_name: str,
    metric_date: str,
    details: Optional[str] = None,
) -> None:
    """Record successful collection run.

    Args:
        conn: SQLite connection
        source_name: 'meta' or 'shopify'
        metric_date: YYYY-MM-DD format
        details: Optional summary message
    """
    conn.execute(
        """
        INSERT INTO collector_state (source_name, metric_date, status, details)
        VALUES (?, ?, 'success', ?)
        ON CONFLICT(source_name, metric_date)
        DO UPDATE SET
            status='success',
            details=excluded.details,
            collected_at=CURRENT_TIMESTAMP
        """,
        (source_name, metric_date, details),
    )
    conn.commit()


def record_collection_failure(
    conn: sqlite3.Connection,
    source_name: str,
    metric_date: str,
    error: str,
) -> None:
    """Record failed collection run.

    Args:
        conn: SQLite connection
        source_name: 'meta' or 'shopify'
        metric_date: YYYY-MM-DD format
        error: Error message
    """
    conn.execute(
        """
        INSERT INTO collector_state (source_name, metric_date, status, details)
        VALUES (?, ?, 'failed', ?)
        ON CONFLICT(source_name, metric_date)
        DO UPDATE SET
            status='failed',
            details=excluded.details,
            collected_at=CURRENT_TIMESTAMP
        """,
        (source_name, metric_date, error),
    )
    conn.commit()


def should_collect(
    conn: sqlite3.Connection,
    source_name: str,
    metric_date: str,
) -> bool:
    """Check if collection should run for this source/date.

    Args:
        conn: SQLite connection
        source_name: 'meta' or 'shopify'
        metric_date: YYYY-MM-DD format

    Returns:
        True if no successful collection exists for this date
    """
    cursor = conn.execute(
        """
        SELECT status FROM collector_state
        WHERE source_name=? AND metric_date=?
        """,
        (source_name, metric_date),
    )
    row = cursor.fetchone()

    if row is None:
        return True

    if row[0] == "failed":
        logger.warning("Retrying failed collection: %s %s", source_name, metric_date)
        return True

    logger.debug("Skipping already collected: %s %s", source_name, metric_date)
    return False
