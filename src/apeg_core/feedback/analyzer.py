"""Feedback loop analyzer - candidate selection & diagnosis.

Loads metrics, computes aggregates, selects candidates, diagnoses issues.
"""
import logging
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Optional


logger = logging.getLogger(__name__)


class DiagnosisType(str, Enum):
    """Diagnosis categories."""

    CTR_LOW_ROAS_HIGH = "ctr_low_roas_high"
    CTR_HIGH_ROAS_LOW = "ctr_high_roas_low"
    CTR_LOW_ROAS_LOW = "ctr_low_roas_low"
    CTR_HIGH_ROAS_HIGH = "ctr_high_roas_high"
    INSUFFICIENT_DATA = "insufficient_data"


class ActionType(str, Enum):
    """Recommended action types."""

    REFINE_AD_CREATIVE = "refine_ad_creative"
    REFINE_SHOPIFY_SEO = "refine_shopify_seo"
    PAUSE_STRATEGY = "pause_strategy"
    SCALE_BUDGET = "scale_budget"
    CLONE_WINNER = "clone_winner"
    NO_ACTION = "no_action"


@dataclass
class StrategyMetrics:
    """Aggregated metrics for a strategy_tag."""

    strategy_tag: str
    window_start: date
    window_end: date
    spend: float
    impressions: int
    ctr: float
    cpc: float
    click_proxy: int
    orders: int
    revenue_attributed: float
    roas: float
    cvr_proxy: float
    meets_min_spend: bool
    meets_min_impressions: bool
    meets_min_clicks: bool
    meets_min_orders: bool
    has_sufficient_data: bool


@dataclass
class ProductMetrics:
    """Product-level metrics (if line-item data available)."""

    product_id: str
    strategy_tag: str
    window_start: date
    window_end: date
    orders: int
    revenue_attributed: float
    units_sold: int
    estimated_spend: float
    estimated_impressions: int
    roas: float
    has_sufficient_data: bool


@dataclass
class Diagnosis:
    """Diagnosis result with recommended action."""

    strategy_tag: str
    diagnosis_type: DiagnosisType
    recommended_action: ActionType
    metrics: StrategyMetrics
    rationale: str
    confidence: float


@dataclass
class Candidate:
    """Candidate for action (underperformer or winner)."""

    strategy_tag: str
    candidate_type: str
    metrics: StrategyMetrics
    diagnosis: Diagnosis


class FeedbackAnalyzer:
    """Analyze metrics and select candidates for action."""

    def __init__(self, db_conn: sqlite3.Connection, config: dict) -> None:
        """Initialize analyzer.

        Args:
            db_conn: SQLite connection
            config: Configuration dict with thresholds
        """
        self.db_conn = db_conn
        self.config = config

    def load_strategy_metrics(
        self, window_start: date, window_end: date
    ) -> dict[str, StrategyMetrics]:
        """Load and aggregate metrics by strategy_tag.

        Args:
            window_start: Start of analysis window
            window_end: End of analysis window (inclusive)

        Returns:
            Dict of strategy_tag -> StrategyMetrics
        """
        start_str = window_start.isoformat()
        end_str = window_end.isoformat()

        meta_query = """
        SELECT
            stm.strategy_tag,
            SUM(m.spend) as spend,
            SUM(m.impressions) as impressions,
            AVG(m.ctr) as avg_ctr,
            AVG(m.cpc) as avg_cpc,
            SUM(m.outbound_clicks) as outbound_clicks
        FROM metrics_meta_daily m
        JOIN strategy_tag_mappings stm
            ON m.entity_type = stm.entity_type
            AND m.entity_id = stm.entity_id
        WHERE m.metric_date >= ? AND m.metric_date <= ?
        GROUP BY stm.strategy_tag
        """

        cursor = self.db_conn.execute(meta_query, (start_str, end_str))
        meta_rows = {row[0]: row for row in cursor.fetchall()}

        shopify_query = """
        SELECT
            strategy_tag,
            COUNT(*) as orders,
            SUM(total_price) as revenue
        FROM order_attributions
        WHERE created_at >= ? AND created_at <= ?
        AND strategy_tag IS NOT NULL
        GROUP BY strategy_tag
        """

        cursor = self.db_conn.execute(
            shopify_query,
            (
                datetime.combine(window_start, datetime.min.time()).isoformat(),
                datetime.combine(window_end, datetime.max.time()).isoformat(),
            ),
        )
        shopify_rows = {row[0]: row for row in cursor.fetchall()}

        all_tags = set(meta_rows.keys()) | set(shopify_rows.keys())

        metrics_map: dict[str, StrategyMetrics] = {}

        for tag in all_tags:
            meta = meta_rows.get(tag)
            shopify = shopify_rows.get(tag)

            spend = meta[1] if meta else 0.0
            impressions = meta[2] if meta else 0
            ctr = meta[3] if meta else 0.0
            cpc = meta[4] if meta else 0.0
            click_proxy = meta[5] if meta else 0

            orders = shopify[1] if shopify else 0
            revenue = shopify[2] if shopify else 0.0

            roas = revenue / max(spend, 0.01)
            cvr_proxy = orders / max(click_proxy, 1)

            min_spend = self.config.get("min_spend_usd", 20.0)
            min_impressions = self.config.get("min_impressions", 1000)
            min_clicks = self.config.get("min_clicks_proxy", 30)
            min_orders = self.config.get("min_orders", 3)

            meets_spend = spend >= min_spend
            meets_imp = impressions >= min_impressions
            meets_clicks = click_proxy >= min_clicks
            meets_orders = orders >= min_orders

            has_data = meets_spend and meets_imp and meets_clicks and meets_orders

            metrics_map[tag] = StrategyMetrics(
                strategy_tag=tag,
                window_start=window_start,
                window_end=window_end,
                spend=spend,
                impressions=impressions,
                ctr=ctr,
                cpc=cpc,
                click_proxy=click_proxy,
                orders=orders,
                revenue_attributed=revenue,
                roas=roas,
                cvr_proxy=cvr_proxy,
                meets_min_spend=meets_spend,
                meets_min_impressions=meets_imp,
                meets_min_clicks=meets_clicks,
                meets_min_orders=meets_orders,
                has_sufficient_data=has_data,
            )

        return metrics_map

    def load_product_metrics(
        self,
        window_start: date,
        window_end: date,
        strategy_metrics: dict[str, StrategyMetrics],
    ) -> list[ProductMetrics]:
        """Load product-level metrics using order_line_attributions.

        Args:
            window_start: Start of analysis window
            window_end: End of analysis window
            strategy_metrics: Strategy-level metrics for spend/impressions

        Returns:
            List of ProductMetrics with estimated ROAS
        """
        start_iso = datetime.combine(window_start, datetime.min.time()).isoformat()
        end_iso = datetime.combine(window_end, datetime.max.time()).isoformat()

        query = """
        SELECT
            product_id,
            strategy_tag,
            COUNT(*) as line_count,
            SUM(quantity) as units_sold,
            SUM(line_revenue) as revenue
        FROM order_line_attributions
        WHERE order_created_at >= ? AND order_created_at <= ?
        GROUP BY product_id, strategy_tag
        """

        cursor = self.db_conn.execute(query, (start_iso, end_iso))
        rows = cursor.fetchall()

        results: list[ProductMetrics] = []

        for row in rows:
            product_id, strategy_tag, line_count, units_sold, revenue = row

            strategy = strategy_metrics.get(strategy_tag)
            if not strategy:
                continue

            revenue = revenue or 0.0
            total_strategy_revenue = max(strategy.revenue_attributed, 0.01)
            allocation = revenue / total_strategy_revenue

            estimated_spend = strategy.spend * allocation
            estimated_impressions = int(strategy.impressions * allocation)

            roas = revenue / max(estimated_spend, 0.01)

            results.append(
                ProductMetrics(
                    product_id=product_id,
                    strategy_tag=strategy_tag,
                    window_start=window_start,
                    window_end=window_end,
                    orders=int(line_count or 0),
                    revenue_attributed=float(revenue),
                    units_sold=int(units_sold or 0),
                    estimated_spend=float(estimated_spend),
                    estimated_impressions=estimated_impressions,
                    roas=roas,
                    has_sufficient_data=strategy.has_sufficient_data,
                )
            )

        return results

    def diagnose(self, metrics: StrategyMetrics) -> Diagnosis:
        """Apply diagnosis matrix.

        Args:
            metrics: Strategy metrics

        Returns:
            Diagnosis with recommended action
        """
        if not metrics.has_sufficient_data:
            return Diagnosis(
                strategy_tag=metrics.strategy_tag,
                diagnosis_type=DiagnosisType.INSUFFICIENT_DATA,
                recommended_action=ActionType.NO_ACTION,
                metrics=metrics,
                rationale="Insufficient data volume to make reliable diagnosis",
                confidence=0.0,
            )

        ctr_bad = self.config.get("ctr_bad", 0.01)
        ctr_good = self.config.get("ctr_good", 0.015)
        roas_bad = self.config.get("roas_bad", 2.0)
        roas_good = self.config.get("roas_good", 3.0)

        ctr_low = metrics.ctr < ctr_bad
        ctr_high = metrics.ctr >= ctr_good
        roas_low = metrics.roas < roas_bad
        roas_high = metrics.roas >= roas_good

        if ctr_low and roas_high:
            return Diagnosis(
                strategy_tag=metrics.strategy_tag,
                diagnosis_type=DiagnosisType.CTR_LOW_ROAS_HIGH,
                recommended_action=ActionType.REFINE_AD_CREATIVE,
                metrics=metrics,
                rationale=(
                    f"CTR ({metrics.ctr:.2%}) is low but ROAS ({metrics.roas:.2f}) is strong. "
                    "Ad creative likely needs work to increase click-through without harming conversion."
                ),
                confidence=0.8,
            )

        if ctr_high and roas_low:
            return Diagnosis(
                strategy_tag=metrics.strategy_tag,
                diagnosis_type=DiagnosisType.CTR_HIGH_ROAS_LOW,
                recommended_action=ActionType.REFINE_SHOPIFY_SEO,
                metrics=metrics,
                rationale=(
                    f"CTR ({metrics.ctr:.2%}) is good but ROAS ({metrics.roas:.2f}) is poor. "
                    "Landing page/SEO mismatch - visitors clicking but not converting."
                ),
                confidence=0.9,
            )

        if ctr_low and roas_low:
            return Diagnosis(
                strategy_tag=metrics.strategy_tag,
                diagnosis_type=DiagnosisType.CTR_LOW_ROAS_LOW,
                recommended_action=ActionType.PAUSE_STRATEGY,
                metrics=metrics,
                rationale=(
                    f"Both CTR ({metrics.ctr:.2%}) and ROAS ({metrics.roas:.2f}) are poor. "
                    "Strategy is failing - recommend pause and rethink angle."
                ),
                confidence=0.7,
            )

        if ctr_high and roas_high:
            return Diagnosis(
                strategy_tag=metrics.strategy_tag,
                diagnosis_type=DiagnosisType.CTR_HIGH_ROAS_HIGH,
                recommended_action=ActionType.SCALE_BUDGET,
                metrics=metrics,
                rationale=(
                    f"CTR ({metrics.ctr:.2%}) and ROAS ({metrics.roas:.2f}) are both excellent. "
                    "Winner - recommend budget scale and cloning to adjacent products."
                ),
                confidence=0.95,
            )

        return Diagnosis(
            strategy_tag=metrics.strategy_tag,
            diagnosis_type=DiagnosisType.INSUFFICIENT_DATA,
            recommended_action=ActionType.NO_ACTION,
            metrics=metrics,
            rationale=(
                f"Performance is middle-range (CTR {metrics.ctr:.2%}, ROAS {metrics.roas:.2f}). "
                "Continue monitoring."
            ),
            confidence=0.5,
        )

    def select_candidates(
        self, metrics_map: dict[str, StrategyMetrics]
    ) -> list[Candidate]:
        """Select candidates for action.

        Args:
            metrics_map: Dict of strategy_tag -> metrics

        Returns:
            List of candidates (underperformers + winners)
        """
        candidates: list[Candidate] = []

        for tag, metrics in metrics_map.items():
            diagnosis = self.diagnose(metrics)

            if diagnosis.recommended_action in {
                ActionType.REFINE_AD_CREATIVE,
                ActionType.REFINE_SHOPIFY_SEO,
                ActionType.PAUSE_STRATEGY,
                ActionType.SCALE_BUDGET,
            }:
                candidate_type = (
                    "winner"
                    if diagnosis.diagnosis_type == DiagnosisType.CTR_HIGH_ROAS_HIGH
                    else "underperformer"
                )

                candidates.append(
                    Candidate(
                        strategy_tag=tag,
                        candidate_type=candidate_type,
                        metrics=metrics,
                        diagnosis=diagnosis,
                    )
                )

        candidates.sort(
            key=lambda candidate: (
                0 if candidate.candidate_type == "underperformer" else 1,
                -candidate.metrics.spend,
            )
        )

        return candidates
