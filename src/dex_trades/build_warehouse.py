"""Build DuckDB warehouse from Parquet swaps.

    uv run python -m dex_trades.build_warehouse
"""

from __future__ import annotations

import logging
import sys

from dex_trades.load.duckdb_loader import load_raw_tables
from dex_trades.settings import get_settings

logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = get_settings()
    counts = load_raw_tables(settings.pipeline.duckdb_path, settings.pipeline.data_dir)
    logger.info("Warehouse ready at %s: %s", settings.pipeline.duckdb_path, counts)
    return 0 if counts else 1


if __name__ == "__main__":
    sys.exit(main())
