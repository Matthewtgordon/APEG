#!/usr/bin/env python3
"""CLI entry point for metrics collection.

Usage:
    # Collect yesterday's data
    PYTHONPATH=. python scripts/run_metrics_collector.py

    # Collect specific date
    PYTHONPATH=. python scripts/run_metrics_collector.py --date 2024-12-30

    # Backfill date range
    PYTHONPATH=. python scripts/run_metrics_collector.py --start 2024-12-01 --end 2024-12-07
"""
import argparse
import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.apeg_core.metrics.collector import MetricsCollectorService


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="APEG metrics collection service")
    parser.add_argument(
        "--date",
        type=str,
        help="Specific date to collect (YYYY-MM-DD). Defaults to yesterday.",
    )
    parser.add_argument(
        "--start",
        type=str,
        help="Start date for backfill range (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        type=str,
        help="End date for backfill range (YYYY-MM-DD)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    setup_logging(args.verbose)

    service = MetricsCollectorService()

    if args.start and args.end:
        start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
        end_date = datetime.strptime(args.end, "%Y-%m-%d").date()

        current_date = start_date
        while current_date <= end_date:
            await service.run_once(current_date)
            current_date += timedelta(days=1)

    elif args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        await service.run_once(target_date)

    else:
        await service.run_once()


if __name__ == "__main__":
    asyncio.run(main())
