"""Unit tests for feedback loop helpers."""
from datetime import date

from src.apeg_core.feedback.analyzer import (
    ActionType,
    Candidate,
    Diagnosis,
    DiagnosisType,
    ProductMetrics,
    StrategyMetrics,
)
from src.apeg_core.feedback.loop import (
    build_challenger_snapshot,
    build_product_update_spec,
    evaluate_outcome,
    select_proposal_targets,
)
from src.apeg_core.feedback.version_control import VersionOutcome


def _strategy_metrics(tag: str) -> StrategyMetrics:
    return StrategyMetrics(
        strategy_tag=tag,
        window_start=date(2024, 12, 1),
        window_end=date(2024, 12, 7),
        spend=100.0,
        impressions=10000,
        ctr=0.02,
        cpc=0.5,
        click_proxy=200,
        orders=12,
        revenue_attributed=500.0,
        roas=5.0,
        cvr_proxy=0.06,
        meets_min_spend=True,
        meets_min_impressions=True,
        meets_min_clicks=True,
        meets_min_orders=True,
        has_sufficient_data=True,
    )


def _candidate(tag: str, action: ActionType) -> Candidate:
    metrics = _strategy_metrics(tag)
    diagnosis = Diagnosis(
        strategy_tag=tag,
        diagnosis_type=DiagnosisType.CTR_HIGH_ROAS_LOW,
        recommended_action=action,
        metrics=metrics,
        rationale="Test rationale",
        confidence=0.8,
    )
    return Candidate(
        strategy_tag=tag,
        candidate_type="underperformer",
        metrics=metrics,
        diagnosis=diagnosis,
    )


def test_select_proposal_targets_uses_top_revenue_per_strategy():
    candidates = [
        _candidate("tag_a", ActionType.REFINE_SHOPIFY_SEO),
        _candidate("tag_b", ActionType.REFINE_SHOPIFY_SEO),
    ]
    metrics = [
        ProductMetrics(
            product_id="prod_1",
            strategy_tag="tag_a",
            window_start=date(2024, 12, 1),
            window_end=date(2024, 12, 7),
            orders=5,
            revenue_attributed=100.0,
            units_sold=5,
            estimated_spend=20.0,
            estimated_impressions=200,
            roas=5.0,
            has_sufficient_data=True,
        ),
        ProductMetrics(
            product_id="prod_2",
            strategy_tag="tag_a",
            window_start=date(2024, 12, 1),
            window_end=date(2024, 12, 7),
            orders=6,
            revenue_attributed=200.0,
            units_sold=6,
            estimated_spend=40.0,
            estimated_impressions=300,
            roas=5.0,
            has_sufficient_data=True,
        ),
        ProductMetrics(
            product_id="prod_3",
            strategy_tag="tag_b",
            window_start=date(2024, 12, 1),
            window_end=date(2024, 12, 7),
            orders=4,
            revenue_attributed=150.0,
            units_sold=4,
            estimated_spend=30.0,
            estimated_impressions=250,
            roas=5.0,
            has_sufficient_data=True,
        ),
    ]

    targets = select_proposal_targets(candidates, metrics, max_actions=2)

    assert [target.product_metrics.product_id for target in targets] == [
        "prod_2",
        "prod_3",
    ]


def test_build_challenger_snapshot_ignores_unsupported_fields():
    champion = {
        "product_id": "prod_1",
        "title": "Old Title",
        "meta_description": "Old desc",
        "tags": ["alpha"],
    }
    llm_output = {
        "changes": {
            "title": "New Title",
            "meta_description": "New desc",
            "tags": ["alpha", "beta"],
            "alt_text_rules": ["ignored"],
        }
    }

    challenger = build_challenger_snapshot(champion, llm_output)

    assert challenger["title"] == "New Title"
    assert challenger["meta_description"] == "New desc"
    assert challenger["tags"] == ["alpha", "beta"]


def test_build_product_update_spec_adds_only_new_tags():
    champion = {
        "product_id": "prod_1",
        "title": "Old Title",
        "meta_description": "Old desc",
        "tags": ["alpha"],
    }
    challenger = {
        "product_id": "prod_1",
        "title": "New Title",
        "meta_description": "New desc",
        "tags": ["alpha", "beta"],
    }

    update = build_product_update_spec(champion, challenger)

    assert update.product_id == "prod_1"
    assert update.tags_add == ["beta"]
    assert update.seo.title == "New Title"


def test_evaluate_outcome_handles_win_loss_inconclusive():
    baseline = ProductMetrics(
        product_id="prod_1",
        strategy_tag="tag_a",
        window_start=date(2024, 12, 1),
        window_end=date(2024, 12, 7),
        orders=5,
        revenue_attributed=100.0,
        units_sold=5,
        estimated_spend=50.0,
        estimated_impressions=200,
        roas=2.0,
        has_sufficient_data=True,
    )
    challenger_win = ProductMetrics(
        product_id="prod_1",
        strategy_tag="tag_a",
        window_start=date(2024, 12, 8),
        window_end=date(2024, 12, 14),
        orders=6,
        revenue_attributed=150.0,
        units_sold=6,
        estimated_spend=50.0,
        estimated_impressions=200,
        roas=3.0,
        has_sufficient_data=True,
    )
    challenger_loss = ProductMetrics(
        product_id="prod_1",
        strategy_tag="tag_a",
        window_start=date(2024, 12, 8),
        window_end=date(2024, 12, 14),
        orders=6,
        revenue_attributed=60.0,
        units_sold=6,
        estimated_spend=50.0,
        estimated_impressions=200,
        roas=1.2,
        has_sufficient_data=True,
    )

    assert (
        evaluate_outcome(baseline, challenger_win, min_orders=3)
        == VersionOutcome.WIN
    )
    assert (
        evaluate_outcome(baseline, challenger_loss, min_orders=3)
        == VersionOutcome.LOSS
    )
    assert (
        evaluate_outcome(baseline, challenger_win, min_orders=10)
        == VersionOutcome.INCONCLUSIVE
    )
