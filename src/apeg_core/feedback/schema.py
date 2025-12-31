"""SQLite schema extensions for feedback loop.

Tables: seo_versions, feedback_runs, feedback_actions
"""
import logging
import sqlite3


logger = logging.getLogger(__name__)


def init_feedback_schema(db_conn: sqlite3.Connection) -> None:
    """Initialize feedback loop schema.

    Args:
        db_conn: SQLite connection
    """
    db_conn.execute(
        """
        CREATE TABLE IF NOT EXISTS seo_versions (
            version_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            author TEXT NOT NULL,
            status TEXT NOT NULL,
            champion_snapshot_json TEXT NOT NULL,
            challenger_snapshot_json TEXT,
            diff_summary_json TEXT,
            decision_context_json TEXT NOT NULL,
            phase3_job_id TEXT,
            evaluation_start_at TEXT,
            evaluation_end_at TEXT,
            outcome TEXT
        )
        """
    )

    db_conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_seo_product
        ON seo_versions(product_id)
        """
    )

    db_conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_seo_status
        ON seo_versions(status)
        """
    )

    db_conn.execute(
        """
        CREATE TABLE IF NOT EXISTS feedback_runs (
            run_id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            window_start TEXT NOT NULL,
            window_end TEXT NOT NULL,
            mode TEXT NOT NULL,
            actions_count INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL
        )
        """
    )

    db_conn.execute(
        """
        CREATE TABLE IF NOT EXISTS feedback_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            action_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            strategy_tag TEXT,
            status TEXT NOT NULL,
            seo_version_id INTEGER,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (run_id) REFERENCES feedback_runs(run_id),
            FOREIGN KEY (seo_version_id) REFERENCES seo_versions(version_id)
        )
        """
    )

    db_conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_action_run
        ON feedback_actions(run_id)
        """
    )

    db_conn.commit()
    logger.info("Feedback schema initialized")
