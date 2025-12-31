"""APEG metrics collection layer.

Collects daily performance metrics from:
- Meta Marketing API (campaigns + ads)
- Shopify orders with attribution (waterfall algorithm)

Persists to:
- SQLite: data/metrics.db (queryable)
- JSONL: data/metrics/raw/*.jsonl (immutable audit logs)
"""
from .attribution import choose_attribution, match_strategy_tag
from .collector import MetricsCollectorService
from .schema import init_database

__all__ = [
    "MetricsCollectorService",
    "choose_attribution",
    "match_strategy_tag",
    "init_database",
]
