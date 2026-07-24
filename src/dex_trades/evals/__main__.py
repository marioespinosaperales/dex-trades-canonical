"""CLI: ``uv run python -m dex_trades.evals`` → artifacts/qc_scorecard.md"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from dex_trades.evals.scorecard import (
    build_scorecard_from_rows,
    load_fixture_rows,
    load_warehouse_rows,
    write_scorecard,
)
from dex_trades.settings import PROJECT_ROOT, get_settings

logger = logging.getLogger(__name__)

DEFAULT_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "golden_trades.json"


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="DEX trades QC scorecard")
    parser.add_argument(
        "--fixture-only",
        action="store_true",
        help="Score golden fixture only (skip warehouse)",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=DEFAULT_FIXTURE,
        help="Path to golden trades JSON",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    rows = None
    source = str(args.fixture)
    already_labeled = False

    if not args.fixture_only:
        rows = load_warehouse_rows(settings.pipeline.duckdb_path)
        if rows is not None:
            source = str(settings.pipeline.duckdb_path)
            already_labeled = True
            logger.info("Scoring warehouse table (%d rows)", len(rows))

    if rows is None:
        if not args.fixture.exists():
            logger.error("Fixture not found: %s", args.fixture)
            return 1
        rows = load_fixture_rows(args.fixture)
        already_labeled = False
        logger.info("Scoring fixture (%d rows)", len(rows))

    scorecard = build_scorecard_from_rows(
        rows,
        source=source,
        already_labeled=already_labeled,
        dust_usdc=settings.pipeline.dust_usdc_threshold,
    )
    path = write_scorecard(scorecard)
    logger.info("Wrote scorecard → %s", path)
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
