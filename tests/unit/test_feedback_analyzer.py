"""Unit tests for feedback analyzer."""
import sqlite3
from datetime import date

import pytest

from src.apeg_core.feedback.analyzer import (
    ActionType,
    DiagnosisType,
    FeedbackAnalyzer,
    StrategyMetrics,
)
from src.apeg_core.feedback.schema import init_feedback_schema
from src.apeg_core.metrics.schema import init_database


@pytest.fixture
def db_conn():
    """Create in-memory test database."""
    conn = sqlite3.connect(":memory:")
    init_database(conn)
    init_feedback_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def config():
    """Test configuration."""
    return {
        "min_spend_usd": 20.0,
        "min_impressions": 1000,
        "min_clicks_proxy": 30,
        "min_orders": 3,
        "ctr_bad": 0.01,
        "ctr_good": 0.015,
        "roas_bad": 2.0,
        "roas_good": 3.0,
    }


def test_diagnose_ctr_low_roas_high(config):
    """Test diagnosis: CTR low, ROAS high -> refine ad creative."""
    metrics = StrategyMetrics(
        strategy_tag="test_tag",
        window_start=date(2024, 12, 1),
        window_end=date(2024, 12, 7),
        spend=100.0,
        impressions=10000,
        ctr=0.008,
        cpc=0.50,
        click_proxy=80,
        orders=10,
        revenue_attributed=400.0,
        roas=4.0,
        cvr_proxy=0.125,
        meets_min_spend=True,
        meets_min_impressions=True,
        meets_min_clicks=True,
        meets_min_orders=True,
        has_sufficient_data=True,
    )

    analyzer = FeedbackAnalyzer(sqlite3.connect(":memory:"), config)
    diagnosis = analyzer.diagnose(metrics)

    assert diagnosis.diagnosis_type == DiagnosisType.CTR_LOW_ROAS_HIGH
    assert diagnosis.recommended_action == ActionType.REFINE_AD_CREATIVE


def test_diagnose_ctr_high_roas_low(config):
    """Test diagnosis: CTR high, ROAS low -> refine Shopify SEO."""
    metrics = StrategyMetrics(
        strategy_tag="test_tag",
        window_start=date(2024, 12, 1),
        window_end=date(2024, 12, 7),
        spend=100.0,
        impressions=5000,
        ctr=0.020,
        cpc=0.50,
        click_proxy=100,
        orders=5,
        revenue_attributed=150.0,
        roas=1.5,
        cvr_proxy=0.05,
        meets_min_spend=True,
        meets_min_impressions=True,
        meets_min_clicks=True,
        meets_min_orders=True,
        has_sufficient_data=True,
    )

    analyzer = FeedbackAnalyzer(sqlite3.connect(":memory:"), config)
    diagnosis = analyzer.diagnose(metrics)

    assert diagnosis.diagnosis_type == DiagnosisType.CTR_HIGH_ROAS_LOW
    assert diagnosis.recommended_action == ActionType.REFINE_SHOPIFY_SEO


def test_diagnose_insufficient_data(config):
    """Test diagnosis: Insufficient data -> no action."""
    metrics = StrategyMetrics(
        strategy_tag="test_tag",
        window_start=date(2024, 12, 1),
        window_end=date(2024, 12, 7),
        spend=10.0,
        impressions=500,
        ctr=0.015,
        cpc=0.50,
        click_proxy=7,
        orders=1,
        revenue_attributed=50.0,
        roas=5.0,
        cvr_proxy=0.14,
        meets_min_spend=False,
        meets_min_impressions=False,
        meets_min_clicks=False,
        meets_min_orders=False,
        has_sufficient_data=False,
    )

    analyzer = FeedbackAnalyzer(sqlite3.connect(":memory:"), config)
    diagnosis = analyzer.diagnose(metrics)

    assert diagnosis.diagnosis_type == DiagnosisType.INSUFFICIENT_DATA
    assert diagnosis.recommended_action == ActionType.NO_ACTION
