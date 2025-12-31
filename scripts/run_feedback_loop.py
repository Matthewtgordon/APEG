#!/usr/bin/env python3
"""CLI entry point for feedback loop.

Usage:
    # Analysis only (no job emission)
    PYTHONPATH=. python scripts/run_feedback_loop.py --mode analyze

    # Propose Challengers (create seo_versions, no emission)
    PYTHONPATH=. python scripts/run_feedback_loop.py --mode propose

    # Full run (propose + emit jobs if approval disabled)
    PYTHONPATH=. python scripts/run_feedback_loop.py --mode execute

    # Evaluate outcomes
    PYTHONPATH=. python scripts/run_feedback_loop.py --mode evaluate --version-id 123
"""
import argparse
import asyncio
import json
import logging
import os
import sqlite3
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.apeg_core.feedback.analyzer import FeedbackAnalyzer
from src.apeg_core.feedback.schema import init_feedback_schema
from src.apeg_core.feedback.version_control import SEOVersionControl
from src.apeg_core.metrics.schema import init_database


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def load_config() -> dict:
    """Load feedback configuration from environment."""
    return {
        "enabled": os.getenv("FEEDBACK_ENABLED", "false").lower() == "true",
        "window_days": int(os.getenv("FEEDBACK_WINDOW_DAYS", "7")),
        "baseline_days": int(os.getenv("FEEDBACK_BASELINE_DAYS", "7")),
        "min_spend_usd": float(os.getenv("FEEDBACK_MIN_SPEND_USD", "20.0")),
        "min_impressions": int(os.getenv("FEEDBACK_MIN_IMPRESSIONS", "1000")),
        "min_clicks_proxy": int(os.getenv("FEEDBACK_MIN_CLICKS_PROXY", "30")),
        "min_orders": int(os.getenv("FEEDBACK_MIN_ORDERS", "3")),
        "roas_bad": float(os.getenv("FEEDBACK_ROAS_BAD", "2.0")),
        "roas_good": float(os.getenv("FEEDBACK_ROAS_GOOD", "3.0")),
        "ctr_bad": float(os.getenv("FEEDBACK_CTR_BAD", "0.01")),
        "ctr_good": float(os.getenv("FEEDBACK_CTR_GOOD", "0.015")),
        "max_actions": int(os.getenv("FEEDBACK_MAX_ACTIONS_PER_RUN", "5")),
        "require_approval": os.getenv("FEEDBACK_REQUIRE_APPROVAL", "true").lower()
        == "true",
        "approval_mode": os.getenv("FEEDBACK_APPROVAL_MODE", "manual"),
        "log_dir": Path(os.getenv("FEEDBACK_DECISION_LOG_DIR", "data/feedback/raw")),
    }


def _write_decision_log(log_path: Path, payload: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, separators=(",", ":")) + "\n")


async def run_analysis(db_conn: sqlite3.Connection, config: dict, run_id: str) -> None:
    """Run analysis mode (candidates + diagnosis only).

    Args:
        db_conn: SQLite connection
        config: Configuration dict
        run_id: Unique run identifier
    """
    logger = logging.getLogger(__name__)

    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=config["window_days"])

    logger.info("Analysis window: %s to %s", start_date, end_date)

    analyzer = FeedbackAnalyzer(db_conn, config)

    metrics_map = analyzer.load_strategy_metrics(start_date, end_date)
    logger.info("Loaded metrics for %s strategies", len(metrics_map))

    candidates = analyzer.select_candidates(metrics_map)
    logger.info("Selected %s candidates", len(candidates))

    product_metrics = analyzer.load_product_metrics(
        start_date, end_date, metrics_map
    )
    logger.info("Computed %s product metrics", len(product_metrics))

    log_path = config["log_dir"] / f"feedback_run_{run_id}.jsonl"

    for idx, candidate in enumerate(candidates, start=1):
        action_id = f"action_{run_id}_{idx:03d}"
        decision_payload = {
            "run_id": run_id,
            "action_id": action_id,
            "strategy_tag": candidate.strategy_tag,
            "candidate_type": candidate.candidate_type,
            "diagnosis": candidate.diagnosis.diagnosis_type.value,
            "recommended_action": candidate.diagnosis.recommended_action.value,
            "confidence": candidate.diagnosis.confidence,
            "metrics": {
                "spend": candidate.metrics.spend,
                "impressions": candidate.metrics.impressions,
                "ctr": candidate.metrics.ctr,
                "roas": candidate.metrics.roas,
                "orders": candidate.metrics.orders,
                "revenue": candidate.metrics.revenue_attributed,
                "click_proxy": candidate.metrics.click_proxy,
            },
        }
        _write_decision_log(log_path, decision_payload)

        db_conn.execute(
            """
            INSERT INTO feedback_actions (
                run_id, action_id, action_type, target_type, target_id,
                strategy_tag, status, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                action_id,
                candidate.diagnosis.recommended_action.value,
                "strategy_tag",
                candidate.strategy_tag,
                candidate.strategy_tag,
                "diagnosed",
                candidate.diagnosis.rationale,
            ),
        )

    db_conn.execute(
        """
        INSERT INTO feedback_runs (
            run_id, window_start, window_end, mode, actions_count, status, completed_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            start_date.isoformat(),
            end_date.isoformat(),
            "analyze",
            len(candidates),
            "completed",
            datetime.utcnow().isoformat(),
        ),
    )
    db_conn.commit()

    logger.info("Analysis complete: %s candidates identified", len(candidates))


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="APEG feedback loop & refinement engine"
    )
    parser.add_argument(
        "--mode",
        choices=["analyze", "propose", "execute", "evaluate"],
        default="analyze",
        help="Execution mode",
    )
    parser.add_argument(
        "--version-id", type=int, help="Version ID for evaluate mode"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging"
    )

    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    config = load_config()

    if not config["enabled"] and args.mode != "analyze":
        logger.error("Feedback loop is disabled (FEEDBACK_ENABLED=false)")
        sys.exit(1)

    db_path = Path(os.getenv("METRICS_DB_PATH", "data/metrics.db"))
    init_database(db_path)

    db_conn = sqlite3.connect(db_path)

    try:
        init_feedback_schema(db_conn)

        run_id = f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        if args.mode == "analyze":
            await run_analysis(db_conn, config, run_id)
        elif args.mode == "propose":
            logger.error("Propose mode not yet implemented (requires LLM integration)")
            sys.exit(1)
        elif args.mode == "execute":
            logger.error(
                "Execute mode not yet implemented (requires Phase 3 API integration)"
            )
            sys.exit(1)
        elif args.mode == "evaluate":
            logger.error("Evaluate mode not yet implemented (requires outcome tracking)")
            sys.exit(1)

    finally:
        db_conn.close()


if __name__ == "__main__":
    asyncio.run(main())
