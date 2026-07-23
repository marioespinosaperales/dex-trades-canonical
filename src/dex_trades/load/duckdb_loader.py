"""Load Parquet swap store into DuckDB for dbt."""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)


def load_raw_tables(duckdb_path: Path, data_dir: Path, raw_schema: str = "raw") -> dict[str, int]:
    """(Re)create raw.swaps from Hive Parquet under ``data_dir``."""
    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    data = data_dir.as_posix()
    glob = f"{data}/swaps/chain=*/pool=*/ingested_date=*/*.parquet"

    with duckdb.connect(str(duckdb_path)) as conn:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {raw_schema}")
        if list(data_dir.glob("swaps/chain=*/pool=*/ingested_date=*/*.parquet")):
            conn.execute(
                f"""
                CREATE OR REPLACE TABLE {raw_schema}.swaps AS
                SELECT * FROM read_parquet('{glob}', hive_partitioning = true, union_by_name = true)
                """
            )
            counts["swaps"] = int(
                conn.execute(f"SELECT count(*) FROM {raw_schema}.swaps").fetchone()[0]
            )
            logger.info("%s.swaps: %d rows", raw_schema, counts["swaps"])
        else:
            logger.warning("No swap parquet under %s", data_dir)

    return counts
