"""Feedback loop execution helpers for propose/execute/evaluate modes."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable

from .analyzer import ActionType, Candidate, ProductMetrics
from .version_control import VersionOutcome
from ..schemas.bulk_ops import ProductSEO, ProductUpdateSpec


@dataclass(frozen=True)
class ProposalTarget:
    """Target selection for proposer."""

    candidate: Candidate
    product_metrics: ProductMetrics


def select_proposal_targets(
    candidates: Iterable[Candidate],
    product_metrics: Iterable[ProductMetrics],
    max_actions: int,
) -> list[ProposalTarget]:
    """Select product targets for SEO refinement.

    Args:
        candidates: Analyzer candidates
        product_metrics: Product-level metrics list
        max_actions: Max actions per run

    Returns:
        List of proposal targets in priority order
    """
    targets: list[ProposalTarget] = []
    metrics_by_strategy: dict[str, list[ProductMetrics]] = {}
    for metrics in product_metrics:
        if not metrics.has_sufficient_data:
            continue
        metrics_by_strategy.setdefault(metrics.strategy_tag, []).append(metrics)

    for tag_metrics in metrics_by_strategy.values():
        tag_metrics.sort(
            key=lambda metrics: metrics.revenue_attributed,
            reverse=True,
        )

    used_products: set[str] = set()

    for candidate in candidates:
        if len(targets) >= max_actions:
            break
        if candidate.diagnosis.recommended_action != ActionType.REFINE_SHOPIFY_SEO:
            continue

        tag_metrics = metrics_by_strategy.get(candidate.strategy_tag, [])
        for metrics in tag_metrics:
            if metrics.product_id in used_products:
                continue
            used_products.add(metrics.product_id)
            targets.append(ProposalTarget(candidate=candidate, product_metrics=metrics))
            break

    return targets


def build_champion_snapshot(
    product_id: str,
    title: str | None,
    description: str | None,
    tags: list[str] | None,
) -> dict:
    """Build champion snapshot payload."""
    return {
        "product_id": product_id,
        "title": title or "",
        "meta_description": description or "",
        "tags": tags or [],
    }


def build_challenger_snapshot(
    champion_snapshot: dict,
    llm_output: dict,
) -> dict:
    """Apply LLM output to champion snapshot, ignoring unsupported fields."""
    changes = llm_output.get("changes") or {}
    title = changes.get("title") or champion_snapshot.get("title", "")
    description = changes.get("meta_description") or champion_snapshot.get(
        "meta_description", ""
    )
    tags = changes.get("tags")
    if not isinstance(tags, list):
        tags = champion_snapshot.get("tags", [])

    return {
        "product_id": champion_snapshot.get("product_id"),
        "title": title,
        "meta_description": description,
        "tags": tags,
    }


def build_product_update_spec(
    champion_snapshot: dict,
    challenger_snapshot: dict,
) -> ProductUpdateSpec:
    """Create ProductUpdateSpec from snapshots."""
    champion_tags = set(champion_snapshot.get("tags", []))
    challenger_tags = set(challenger_snapshot.get("tags", []))

    tags_add = sorted(challenger_tags - champion_tags)

    seo = ProductSEO(
        title=challenger_snapshot.get("title"),
        description=challenger_snapshot.get("meta_description"),
    )

    return ProductUpdateSpec(
        product_id=challenger_snapshot.get("product_id", ""),
        tags_add=tags_add,
        tags_remove=[],
        seo=seo,
    )


def chunk_items(items: list, chunk_size: int) -> Iterable[list]:
    """Yield items in fixed-size chunks."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    for idx in range(0, len(items), chunk_size):
        yield items[idx : idx + chunk_size]


def evaluate_outcome(
    baseline: ProductMetrics,
    challenger: ProductMetrics,
    min_orders: int,
    roas_win_threshold: float = 0.10,
    roas_loss_threshold: float = -0.15,
) -> VersionOutcome:
    """Evaluate challenger outcome using ROAS and order volume."""
    if (
        challenger.orders < min_orders
        or baseline.orders < min_orders
        or not baseline.has_sufficient_data
        or not challenger.has_sufficient_data
    ):
        return VersionOutcome.INCONCLUSIVE

    if baseline.roas <= 0:
        return VersionOutcome.INCONCLUSIVE

    roas_improvement = (challenger.roas - baseline.roas) / baseline.roas

    if roas_improvement <= roas_loss_threshold:
        return VersionOutcome.LOSS
    if roas_improvement >= roas_win_threshold:
        return VersionOutcome.WIN
    return VersionOutcome.INCONCLUSIVE


def evaluation_window_ready(
    evaluation_start_at: datetime,
    window_days: int,
    now: datetime | None = None,
) -> tuple[bool, datetime]:
    """Check if evaluation window has completed."""
    now = now or datetime.utcnow()
    evaluation_end = evaluation_start_at + timedelta(days=window_days)
    return (now >= evaluation_end, evaluation_end)
