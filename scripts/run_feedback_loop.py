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
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import aiohttp

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.apeg_core.feedback.analyzer import FeedbackAnalyzer, ProductMetrics
from src.apeg_core.feedback.loop import (
    build_challenger_snapshot,
    build_champion_snapshot,
    build_product_update_spec,
    chunk_items,
    evaluate_outcome,
    evaluation_window_ready,
    select_proposal_targets,
)
from src.apeg_core.feedback.mapping_enrichment import enrich_strategy_tag_mappings
from src.apeg_core.feedback.prompts import SEOChallengerPrompt
from src.apeg_core.feedback.schema import init_feedback_schema
from src.apeg_core.feedback.version_control import (
    SEOVersionControl,
    VersionOutcome,
    VersionStatus,
)
from src.apeg_core.metrics.schema import init_database
from src.apeg_core.schemas.bulk_ops import ProductUpdateSpec
from src.apeg_core.shopify.graphql_strings import QUERY_PRODUCT_BY_ID


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
        "shop_domain": os.getenv("SHOPIFY_STORE_DOMAIN", ""),
        "shopify_access_token": os.getenv("SHOPIFY_ADMIN_ACCESS_TOKEN", ""),
        "shopify_api_version": os.getenv("SHOPIFY_API_VERSION", "2024-10"),
        "api_base_url": os.getenv("APEG_API_BASE_URL", "http://localhost:8000"),
        "apeg_api_key": os.getenv("APEG_API_KEY", ""),
        "dry_run": os.getenv("APEG_ALLOW_WRITES", "NO").upper() != "YES",
        "llm_api_key": os.getenv("FEEDBACK_LLM_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY", ""),
        "llm_model": os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620"),
        "llm_max_tokens": int(os.getenv("FEEDBACK_LLM_MAX_TOKENS", "800")),
        "allow_dummy_products": os.getenv("FEEDBACK_ALLOW_DUMMY_PRODUCTS", "false")
        .lower()
        .strip()
        == "true",
        "use_stub_llm": os.getenv("FEEDBACK_USE_STUB_LLM", "false")
        .lower()
        .strip()
        == "true",
    }


def _load_strategy_catalog() -> list[str]:
    catalog_path = os.getenv(
        "STRATEGY_TAG_CATALOG", "data/metrics/strategy_tags.json"
    )
    catalog_file = Path(catalog_path)

    if not catalog_file.exists():
        raise FileNotFoundError(
            f"Strategy catalog not found: {catalog_path}. "
            "Create it before running the feedback loop."
        )

    with open(catalog_file, encoding="utf-8") as handle:
        data = json.load(handle)

    tags = data.get("strategy_tags")
    if not isinstance(tags, list):
        raise ValueError("strategy_tags must be a list in strategy tag catalog")

    return tags


def _require_config_value(value: str, name: str) -> None:
    if not value:
        raise ValueError(f"Missing required config value: {name}")


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

    strategy_catalog = _load_strategy_catalog()
    enriched = enrich_strategy_tag_mappings(
        db_conn, strategy_catalog, start_date, end_date
    )
    if enriched:
        logger.info("Enriched %s strategy_tag mappings before analysis", enriched)

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
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    db_conn.commit()

    logger.info("Analysis complete: %s candidates identified", len(candidates))


async def _fetch_product_snapshot(
    session: aiohttp.ClientSession,
    config: dict,
    product_id: str,
) -> dict:
    _require_config_value(config["shop_domain"], "SHOPIFY_STORE_DOMAIN")
    _require_config_value(
        config["shopify_access_token"], "SHOPIFY_ADMIN_ACCESS_TOKEN"
    )

    endpoint = (
        f"https://{config['shop_domain']}/admin/api/"
        f"{config['shopify_api_version']}/graphql.json"
    )

    payload = {"query": QUERY_PRODUCT_BY_ID, "variables": {"id": product_id}}
    headers = {"X-Shopify-Access-Token": config["shopify_access_token"]}

    async with session.post(endpoint, json=payload, headers=headers) as resp:
        resp.raise_for_status()
        response_data = await resp.json()

    if response_data.get("errors"):
        raise ValueError(f"Shopify GraphQL errors: {response_data['errors']}")

    product = response_data.get("data", {}).get("product")
    if not product:
        raise ValueError(f"Product not found for id: {product_id}")

    seo = product.get("seo") or {}

    return build_champion_snapshot(
        product_id=product.get("id"),
        title=seo.get("title"),
        description=seo.get("description"),
        tags=product.get("tags") or [],
    )


async def _call_anthropic(
    session: aiohttp.ClientSession, config: dict, prompt: str
) -> dict:
    _require_config_value(config["llm_api_key"], "FEEDBACK_LLM_API_KEY/ANTHROPIC_API_KEY")

    payload = {
        "model": config["llm_model"],
        "max_tokens": config["llm_max_tokens"],
        "temperature": 0.2,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "x-api-key": config["llm_api_key"],
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    async with session.post(
        "https://api.anthropic.com/v1/messages", json=payload, headers=headers
    ) as resp:
        resp.raise_for_status()
        response_data = await resp.json()

    content = response_data.get("content", [])
    if not content:
        raise ValueError("LLM response missing content")

    text = content[0].get("text", "")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM response invalid JSON: {text}") from exc


async def run_propose(db_conn: sqlite3.Connection, config: dict, run_id: str) -> None:
    """Generate SEO challenger proposals via LLM."""
    logger = logging.getLogger(__name__)

    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=config["window_days"])

    strategy_catalog = _load_strategy_catalog()
    enrich_strategy_tag_mappings(db_conn, strategy_catalog, start_date, end_date)

    analyzer = FeedbackAnalyzer(db_conn, config)
    metrics_map = analyzer.load_strategy_metrics(start_date, end_date)
    candidates = analyzer.select_candidates(metrics_map)
    product_metrics = analyzer.load_product_metrics(start_date, end_date, metrics_map)

    targets = select_proposal_targets(
        candidates, product_metrics, config["max_actions"]
    )
    if not targets:
        logger.info("No eligible targets for propose mode")
        return

    log_path = config["log_dir"] / f"feedback_propose_{run_id}.jsonl"
    version_control = SEOVersionControl(db_conn)

    async with aiohttp.ClientSession() as session:
        for idx, target in enumerate(targets, start=1):
            product_id = target.product_metrics.product_id
            candidate = target.candidate

            if config["allow_dummy_products"] and not config["shopify_access_token"]:
                champion = build_champion_snapshot(
                    product_id=product_id,
                    title=f"Seeded {candidate.strategy_tag} title",
                    description="Seeded meta description for sample data.",
                    tags=[candidate.strategy_tag],
                )
            else:
                champion = await _fetch_product_snapshot(
                    session, config, product_id
                )

            prompt = SEOChallengerPrompt.build_refinement_prompt(
                product_snapshot=champion,
                diagnosis=candidate.diagnosis.diagnosis_type.value,
                metrics={
                    "ctr": candidate.metrics.ctr,
                    "roas": candidate.metrics.roas,
                    "spend": candidate.metrics.spend,
                    "orders": candidate.metrics.orders,
                    "click_proxy": candidate.metrics.click_proxy,
                },
                strategy_tag=candidate.strategy_tag,
            )

            if config["use_stub_llm"]:
                llm_output = {
                    "product_id": product_id,
                    "strategy_tag": candidate.strategy_tag,
                    "changes": {
                        "title": f"{champion['title']} (Refined)",
                        "meta_description": (
                            f"{champion['meta_description']} Updated for {candidate.strategy_tag}."
                        ),
                        "tags": list(
                            {candidate.strategy_tag, "feedback_stub"}
                        ),
                    },
                    "rationale": {
                        "diagnosis": candidate.diagnosis.diagnosis_type.value,
                        "hypothesis": "Seeded stub LLM output for testing.",
                        "risk_notes": ["Stub output - replace with real LLM."],
                    },
                    "validation": {
                        "character_limits_ok": True,
                        "prohibited_claims_ok": True,
                    },
                }
            else:
                llm_output = await _call_anthropic(session, config, prompt)

            valid, errors = SEOChallengerPrompt.validate_output(llm_output)
            if not valid:
                logger.warning(
                    "Invalid LLM output for %s: %s", product_id, errors
                )
                continue

            challenger = build_challenger_snapshot(champion, llm_output)

            decision_context = {
                "run_id": run_id,
                "strategy_tag": candidate.strategy_tag,
                "diagnosis": candidate.diagnosis.diagnosis_type.value,
                "recommended_action": candidate.diagnosis.recommended_action.value,
                "window_start": start_date.isoformat(),
                "window_end": end_date.isoformat(),
                "metrics": {
                    "spend": candidate.metrics.spend,
                    "impressions": candidate.metrics.impressions,
                    "ctr": candidate.metrics.ctr,
                    "roas": candidate.metrics.roas,
                    "orders": candidate.metrics.orders,
                },
            }

            version_id = version_control.create_proposal(
                product_id=product_id,
                champion_snapshot=champion,
                challenger_snapshot=challenger,
                decision_context=decision_context,
            )

            action_id = f"proposal_{run_id}_{idx:03d}"
            db_conn.execute(
                """
                INSERT INTO feedback_actions (
                    run_id, action_id, action_type, target_type, target_id,
                    strategy_tag, status, seo_version_id, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    action_id,
                    candidate.diagnosis.recommended_action.value,
                    "product",
                    product_id,
                    candidate.strategy_tag,
                    "proposed",
                    version_id,
                    candidate.diagnosis.rationale,
                ),
            )

            _write_decision_log(
                log_path,
                {
                    "run_id": run_id,
                    "action_id": action_id,
                    "product_id": product_id,
                    "strategy_tag": candidate.strategy_tag,
                    "version_id": version_id,
                    "llm_valid": True,
                    "changes": llm_output.get("changes", {}),
                    "used_stub_llm": config["use_stub_llm"],
                    "used_dummy_snapshot": config["allow_dummy_products"]
                    and not config["shopify_access_token"],
                },
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
            "propose",
            len(targets),
            "completed",
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    db_conn.commit()

    logger.info("Propose mode complete: %s proposals created", len(targets))


async def _post_phase3_job(
    session: aiohttp.ClientSession,
    config: dict,
    run_id: str,
    updates: list[ProductUpdateSpec],
) -> dict:
    _require_config_value(config["api_base_url"], "APEG_API_BASE_URL")
    _require_config_value(config["shop_domain"], "SHOPIFY_STORE_DOMAIN")
    _require_config_value(config["apeg_api_key"], "APEG_API_KEY")

    url = f"{config['api_base_url'].rstrip('/')}/api/v1/jobs/seo-update"
    payload = {
        "run_id": run_id,
        "shop_domain": config["shop_domain"],
        "dry_run": config["dry_run"],
        "products": [
            {
                "product_id": update.product_id,
                "tags_add": update.tags_add,
                "tags_remove": update.tags_remove,
                "seo": update.seo.model_dump(exclude_none=True)
                if update.seo
                else None,
            }
            for update in updates
        ],
    }
    headers = {"X-APEG-API-KEY": config["apeg_api_key"]}

    async with session.post(url, json=payload, headers=headers) as resp:
        resp.raise_for_status()
        return await resp.json()


async def run_execute(db_conn: sqlite3.Connection, config: dict, run_id: str) -> None:
    """Emit Phase 3 jobs for approved proposals."""
    logger = logging.getLogger(__name__)

    if not config["shop_domain"] or not config["apeg_api_key"]:
        logger.error(
            "Execute mode requires SHOPIFY_STORE_DOMAIN and APEG_API_KEY"
        )
        return

    cursor = db_conn.execute(
        """
        SELECT
            version_id,
            product_id,
            status,
            champion_snapshot_json,
            challenger_snapshot_json
        FROM seo_versions
        WHERE status IN (?, ?)
        ORDER BY created_at ASC
        """,
        (VersionStatus.PROPOSED.value, VersionStatus.APPROVED.value),
    )
    rows = cursor.fetchall()

    if not rows:
        logger.info("No proposals ready for execution")
        return

    version_control = SEOVersionControl(db_conn)
    updates: list[tuple[int, ProductUpdateSpec]] = []

    for (
        version_id,
        product_id,
        status,
        champion_json,
        challenger_json,
    ) in rows:
        if status == VersionStatus.PROPOSED.value and not config["require_approval"]:
            version_control.approve(version_id)
            status = VersionStatus.APPROVED.value

        if status != VersionStatus.APPROVED.value:
            continue

        challenger = json.loads(challenger_json)
        champion = json.loads(champion_json)

        update_spec = build_product_update_spec(champion, challenger)
        updates.append((version_id, update_spec))

    if not updates:
        logger.info("No approved proposals to execute")
        return

    applied_count = 0
    batch_failed = False

    async with aiohttp.ClientSession() as session:
        for batch_idx, batch in enumerate(
            chunk_items(updates, config["max_actions"]), start=1
        ):
            job_run_id = f"{run_id}_batch_{batch_idx:02d}"
            try:
                job_payload = await _post_phase3_job(
                    session,
                    config,
                    job_run_id,
                    [update for _, update in batch],
                )
            except aiohttp.ClientError as exc:
                logger.error("Phase 3 API request failed: %s", exc)
                batch_failed = True
                break

            job_id = job_payload.get("job_id", "")

            for version_id, _ in batch:
                version_control.mark_applied(
                    version_id, job_id or "unknown", datetime.now(timezone.utc)
                )
                db_conn.execute(
                    """
                    UPDATE feedback_actions
                    SET status=?, notes=?
                    WHERE seo_version_id=?
                    """,
                    ("applied", f"phase3_job_id={job_id}", version_id),
                )
                applied_count += 1

    status = "completed"
    if batch_failed and applied_count == 0:
        status = "failed"
    elif batch_failed:
        status = "partial"

    db_conn.execute(
        """
        INSERT INTO feedback_runs (
            run_id, window_start, window_end, mode, actions_count, status, completed_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            "",
            "",
            "execute",
            applied_count,
            status,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    db_conn.commit()
    logger.info("Execute mode complete: %s proposals applied", applied_count)


def _get_version_metrics(
    db_conn: sqlite3.Connection,
    config: dict,
    product_id: str,
    window_start: date,
    window_end: date,
) -> ProductMetrics | None:
    analyzer = FeedbackAnalyzer(db_conn, config)
    strategy_metrics = analyzer.load_strategy_metrics(window_start, window_end)
    product_metrics = analyzer.load_product_metrics(
        window_start, window_end, strategy_metrics
    )
    for metrics in product_metrics:
        if metrics.product_id == product_id:
            return metrics
    return None


async def run_evaluate(
    db_conn: sqlite3.Connection, config: dict, run_id: str, version_id: int | None
) -> None:
    """Evaluate applied SEO versions."""
    logger = logging.getLogger(__name__)

    if version_id:
        cursor = db_conn.execute(
            """
            SELECT version_id, product_id, evaluation_start_at, outcome
            FROM seo_versions
            WHERE version_id=?
            """,
            (version_id,),
        )
    else:
        cursor = db_conn.execute(
            """
            SELECT version_id, product_id, evaluation_start_at, outcome
            FROM seo_versions
            WHERE status=? AND outcome=?
            """,
            (VersionStatus.APPLIED.value, VersionOutcome.PENDING.value),
        )

    rows = cursor.fetchall()
    if not rows:
        logger.info("No versions ready for evaluation")
        return

    version_control = SEOVersionControl(db_conn)
    evaluated = 0

    for row in rows:
        version_id, product_id, evaluation_start_at, outcome = row
        if not evaluation_start_at:
            logger.warning("Version %s missing evaluation_start_at", version_id)
            continue

        start_dt = datetime.fromisoformat(evaluation_start_at)
        ready, evaluation_end = evaluation_window_ready(
            start_dt, config["window_days"]
        )
        if not ready:
            logger.info(
                "Version %s evaluation window not complete (end %s)",
                version_id,
                evaluation_end.isoformat(),
            )
            continue

        baseline_end = start_dt.date() - timedelta(days=1)
        baseline_start = baseline_end - timedelta(days=config["baseline_days"])

        baseline_metrics = _get_version_metrics(
            db_conn, config, product_id, baseline_start, baseline_end
        )
        challenger_metrics = _get_version_metrics(
            db_conn, config, product_id, start_dt.date(), evaluation_end.date()
        )

        if not baseline_metrics or not challenger_metrics:
            version_control.record_outcome(
                version_id, VersionOutcome.INCONCLUSIVE, evaluation_end
            )
            db_conn.execute(
                """
                UPDATE feedback_actions
                SET status=?, notes=?
                WHERE seo_version_id=?
                """,
                ("evaluated", "metrics missing; outcome inconclusive", version_id),
            )
            evaluated += 1
            continue

        outcome = evaluate_outcome(
            baseline_metrics, challenger_metrics, config["min_orders"]
        )
        version_control.record_outcome(version_id, outcome, evaluation_end)
        db_conn.execute(
            """
            UPDATE feedback_actions
            SET status=?, notes=?
            WHERE seo_version_id=?
            """,
            ("evaluated", f"outcome={outcome.value}", version_id),
        )
        evaluated += 1

    db_conn.execute(
        """
        INSERT INTO feedback_runs (
            run_id, window_start, window_end, mode, actions_count, status, completed_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            "",
            "",
            "evaluate",
            evaluated,
            "completed",
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    db_conn.commit()
    logger.info("Evaluate mode complete: %s versions evaluated", evaluated)


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

        now_utc = datetime.now(timezone.utc)
        run_id = f"run_{now_utc.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        if args.mode == "analyze":
            await run_analysis(db_conn, config, run_id)
        elif args.mode == "propose":
            await run_propose(db_conn, config, run_id)
        elif args.mode == "execute":
            await run_execute(db_conn, config, run_id)
        elif args.mode == "evaluate":
            await run_evaluate(db_conn, config, run_id, args.version_id)

    finally:
        db_conn.close()


if __name__ == "__main__":
    asyncio.run(main())
