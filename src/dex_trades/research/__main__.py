"""CLI: ``uv run python -m dex_trades.research`` → artifacts/research_orderflow.md"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from dex_trades.research.orderflow import build_orderflow_report, write_orderflow_report
from dex_trades.settings import PROJECT_ROOT

logger = logging.getLogger(__name__)
DEFAULT_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "golden_trades.json"


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Orderflow / MEV-lite research report")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-augment", action="store_true")
    args = parser.parse_args(argv)

    if not args.fixture.exists():
        logger.error("Fixture not found: %s", args.fixture)
        return 1

    report = build_orderflow_report(
        fixture=args.fixture,
        seed=args.seed,
        augment=not args.no_augment,
    )
    path = write_orderflow_report(report)
    share = report["evidence"]["volume"]["interesting_share_of_volume"]
    logger.info("Wrote research report → %s (interesting_volume_share=%.3f)", path, share)
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
