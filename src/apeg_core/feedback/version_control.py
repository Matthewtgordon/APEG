"""SEO version control - Champion/Challenger tracking with rollback.

Persists every SEO snapshot and provides byte-perfect revert capability.
"""
import json
import logging
import sqlite3
from datetime import datetime
from enum import Enum


logger = logging.getLogger(__name__)


class VersionStatus(str, Enum):
    """SEO version status."""

    PROPOSED = "proposed"
    APPROVED = "approved"
    APPLIED = "applied"
    REVERTED = "reverted"
    SUPERSEDED = "superseded"


class VersionOutcome(str, Enum):
    """Evaluation outcome."""

    WIN = "win"
    LOSS = "loss"
    INCONCLUSIVE = "inconclusive"
    PENDING = "pending"


class SEOVersionControl:
    """Manage SEO version snapshots and rollback."""

    def __init__(self, db_conn: sqlite3.Connection) -> None:
        """Initialize version control.

        Args:
            db_conn: SQLite connection
        """
        self.db_conn = db_conn

    def create_proposal(
        self,
        product_id: str,
        champion_snapshot: dict,
        challenger_snapshot: dict,
        decision_context: dict,
        author: str = "feedback_loop",
    ) -> int:
        """Create new SEO version proposal.

        Args:
            product_id: Shopify product GID
            champion_snapshot: Current SEO state
            challenger_snapshot: Proposed SEO state
            decision_context: Metrics window, diagnosis, thresholds
            author: Who created this version

        Returns:
            version_id
        """
        diff = self._compute_diff(champion_snapshot, challenger_snapshot)

        cursor = self.db_conn.execute(
            """
            INSERT INTO seo_versions (
                product_id, author, status,
                champion_snapshot_json, challenger_snapshot_json,
                diff_summary_json, decision_context_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product_id,
                author,
                VersionStatus.PROPOSED.value,
                json.dumps(champion_snapshot, separators=(",", ":")),
                json.dumps(challenger_snapshot, separators=(",", ":")),
                json.dumps(diff, separators=(",", ":")),
                json.dumps(decision_context, separators=(",", ":")),
            ),
        )

        self.db_conn.commit()
        version_id = cursor.lastrowid

        logger.info("Created SEO version proposal: %s for %s", version_id, product_id)

        return version_id

    def approve(self, version_id: int) -> None:
        """Mark version as approved.

        Args:
            version_id: Version to approve
        """
        self.db_conn.execute(
            "UPDATE seo_versions SET status=? WHERE version_id=?",
            (VersionStatus.APPROVED.value, version_id),
        )
        self.db_conn.commit()

        logger.info("Approved SEO version: %s", version_id)

    def mark_applied(
        self, version_id: int, phase3_job_id: str, evaluation_start: datetime
    ) -> None:
        """Mark version as applied with evaluation window.

        Args:
            version_id: Version that was applied
            phase3_job_id: Job ID from Phase 3 API
            evaluation_start: When evaluation window starts
        """
        self.db_conn.execute(
            """
            UPDATE seo_versions
            SET status=?, phase3_job_id=?, evaluation_start_at=?, outcome=?
            WHERE version_id=?
            """,
            (
                VersionStatus.APPLIED.value,
                phase3_job_id,
                evaluation_start.isoformat(),
                VersionOutcome.PENDING.value,
                version_id,
            ),
        )
        self.db_conn.commit()

        logger.info("Marked version %s as applied (job %s)", version_id, phase3_job_id)

    def revert(self, product_id: str) -> tuple[int, str]:
        """Revert product to last applied Champion snapshot.

        Returns raw JSON to preserve byte-perfect snapshot.

        Args:
            product_id: Product to revert

        Returns:
            (version_id, champion_snapshot_json)
        """
        cursor = self.db_conn.execute(
            """
            SELECT version_id, champion_snapshot_json
            FROM seo_versions
            WHERE product_id=? AND status=?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (product_id, VersionStatus.APPLIED.value),
        )

        row = cursor.fetchone()

        if not row:
            raise ValueError(f"No applied version found for {product_id}")

        version_id, champion_json = row

        self.db_conn.execute(
            "UPDATE seo_versions SET status=? WHERE version_id=?",
            (VersionStatus.REVERTED.value, version_id),
        )
        self.db_conn.commit()

        logger.info("Reverted product %s (version %s)", product_id, version_id)

        return (version_id, champion_json)

    def record_outcome(
        self, version_id: int, outcome: VersionOutcome, evaluation_end: datetime
    ) -> None:
        """Record evaluation outcome.

        Args:
            version_id: Version evaluated
            outcome: WIN/LOSS/INCONCLUSIVE
            evaluation_end: When evaluation ended
        """
        self.db_conn.execute(
            """
            UPDATE seo_versions
            SET outcome=?, evaluation_end_at=?
            WHERE version_id=?
            """,
            (outcome.value, evaluation_end.isoformat(), version_id),
        )
        self.db_conn.commit()

        logger.info("Recorded outcome %s for version %s", outcome, version_id)

    def _compute_diff(self, champion: dict, challenger: dict) -> dict:
        """Compute diff summary between snapshots.

        Args:
            champion: Current state
            challenger: Proposed state

        Returns:
            Dict with changed fields
        """
        diff = {}

        all_keys = set(champion.keys()) | set(challenger.keys())

        for key in all_keys:
            champ_val = champion.get(key)
            chal_val = challenger.get(key)

            if champ_val != chal_val:
                diff[key] = {"from": champ_val, "to": chal_val}

        return diff
