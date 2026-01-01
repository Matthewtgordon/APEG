"""Integration test for feedback loop propose mode (Shopify + DB)."""
from __future__ import annotations

import asyncio
import os
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest

from scripts.run_feedback_loop import run_propose
from src.apeg_core.feedback.schema import init_feedback_schema
from src.apeg_core.metrics.schema import init_database


REQUIRED_ENV_VARS = [
    "SHOPIFY_STORE_DOMAIN",
    "SHOPIFY_ADMIN_ACCESS_TOKEN",
    "TEST_PRODUCT_ID",
    "ANTHROPIC_API_KEY",
]


def _missing_env() -> list[str]:
    missing = []
    for key in REQUIRED_ENV_VARS:
        if not os.getenv(key):
            missing.append(key)
    return missing


def _seed_metrics(
    conn: sqlite3.Connection, product_id: str, strategy_tag: str
) -> None:
    today = date.today()
    metric_date = (today - timedelta(days=1)).isoformat()
    created_at = f"{metric_date}T12:00:00"
    campaign_id = "cmp_feedback_integration"

    conn.execute(
        """
        INSERT OR REPLACE INTO metrics_meta_daily (
            metric_date, entity_type, entity_id, campaign_id, account_id,
            spend, impressions, ctr, outbound_clicks, raw_json
        ) VALUES (?, 'campaign', ?, ?, 'act_INTEGRATION', ?, ?, ?, ?, ?)
        """,
        (
            metric_date,
            campaign_id,
            campaign_id,
            80.0,
            8000,
            0.02,
            160,
            '{"campaign_name":"integration_seed"}',
        ),
    )

    conn.execute(
        """
        INSERT OR REPLACE INTO strategy_tag_mappings (
            entity_type, entity_id, strategy_tag,
            mapping_method, mapping_confidence, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "campaign",
            campaign_id,
            strategy_tag,
            "integration_seed",
            1.0,
            '{"seeded":true}',
        ),
    )

    conn.execute(
        """
        INSERT OR IGNORE INTO order_attributions (
            order_id, order_name, created_at, total_price, currency,
            attribution_tier, confidence, strategy_tag, evidence_json
        ) VALUES (?, ?, ?, ?, 'USD', 1, 1.0, ?, '{}')
        """,
        (
            f"order_{metric_date}",
            "Order #9001",
            created_at,
            120.0,
            strategy_tag,
        ),
    )

    conn.execute(
        """
        INSERT OR IGNORE INTO order_line_attributions (
            order_id, order_created_at, product_id, variant_id,
            quantity, line_revenue, currency, strategy_tag,
            attribution_tier, confidence, raw_source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"order_{metric_date}",
            created_at,
            product_id,
            None,
            1,
            120.0,
            "USD",
            strategy_tag,
            1,
            1.0,
            "integration_seed",
        ),
    )

    conn.commit()


@pytest.mark.integration
def test_propose_mode_creates_version(tmp_path: Path) -> None:
    """Run propose mode with real Shopify + Anthropic credentials."""
    missing = _missing_env()
    if missing:
        pytest.skip(f"Missing required env vars: {', '.join(missing)}")

    db_path = tmp_path / "metrics.db"
    init_database(db_path)
    conn = sqlite3.connect(db_path)
    init_feedback_schema(conn)

    product_id = os.environ["TEST_PRODUCT_ID"]
    strategy_tag = "feedback_integration_tag"
    _seed_metrics(conn, product_id, strategy_tag)

    config = {
        "enabled": True,
        "window_days": 1,
        "baseline_days": 1,
        "min_spend_usd": 10.0,
        "min_impressions": 100,
        "min_clicks_proxy": 10,
        "min_orders": 1,
        "roas_bad": 2.0,
        "roas_good": 3.0,
        "ctr_bad": 0.01,
        "ctr_good": 0.015,
        "max_actions": 1,
        "require_approval": True,
        "approval_mode": "manual",
        "log_dir": tmp_path / "feedback_logs",
        "shop_domain": os.environ["SHOPIFY_STORE_DOMAIN"],
        "shopify_access_token": os.environ["SHOPIFY_ADMIN_ACCESS_TOKEN"],
        "shopify_api_version": os.getenv("SHOPIFY_API_VERSION", "2024-10"),
        "api_base_url": os.getenv("APEG_API_BASE_URL", "http://localhost:8000"),
        "apeg_api_key": os.getenv("APEG_API_KEY", ""),
        "dry_run": True,
        "llm_api_key": os.environ["ANTHROPIC_API_KEY"],
        "llm_model": os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620"),
        "llm_max_tokens": int(os.getenv("FEEDBACK_LLM_MAX_TOKENS", "800")),
        "allow_dummy_products": False,
        "use_stub_llm": False,
    }

    run_id = "integration_propose"
    asyncio.run(run_propose(conn, config, run_id))

    version_count = conn.execute(
        "SELECT COUNT(*) FROM seo_versions"
    ).fetchone()[0]
    action_count = conn.execute(
        "SELECT COUNT(*) FROM feedback_actions"
    ).fetchone()[0]

    conn.close()

    assert version_count >= 1
    assert action_count >= 1
