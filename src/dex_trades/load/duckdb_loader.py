"""Load Parquet swap/block store into DuckDB for dbt."""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)


def load_raw_tables(duckdb_path: Path, data_dir: Path, raw_schema: str = "raw") -> dict[str, int]:
    """(Re)create raw.swaps and raw.blocks from Hive Parquet under ``data_dir``."""
    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    data = data_dir.as_posix()
    swap_glob = f"{data}/swaps/chain=*/pool=*/ingested_date=*/*.parquet"
    block_glob = f"{data}/blocks/chain=*/*.parquet"

    with duckdb.connect(str(duckdb_path)) as conn:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {raw_schema}")
        if list(data_dir.glob("swaps/chain=*/pool=*/ingested_date=*/*.parquet")):
            conn.execute(
                f"""
                CREATE OR REPLACE TABLE {raw_schema}.swaps AS
                SELECT * FROM read_parquet(
                    '{swap_glob}', hive_partitioning = true, union_by_name = true
                )
                """
            )
            counts["swaps"] = int(
                conn.execute(f"SELECT count(*) FROM {raw_schema}.swaps").fetchone()[0]
            )
            logger.info("%s.swaps: %d rows", raw_schema, counts["swaps"])
        else:
            logger.warning("No swap parquet under %s", data_dir)

        if list(data_dir.glob("blocks/chain=*/*.parquet")):
            conn.execute(
                f"""
                CREATE OR REPLACE TABLE {raw_schema}.blocks AS
                SELECT * FROM read_parquet(
                    '{block_glob}', hive_partitioning = true, union_by_name = true
                )
                """
            )
            counts["blocks"] = int(
                conn.execute(f"SELECT count(*) FROM {raw_schema}.blocks").fetchone()[0]
            )
            logger.info("%s.blocks: %d rows", raw_schema, counts["blocks"])
        else:
            # Empty stub so dbt left-join always resolves.
            conn.execute(
                f"""
                CREATE OR REPLACE TABLE {raw_schema}.blocks AS
                SELECT
                    CAST(NULL AS VARCHAR) AS chain,
                    CAST(NULL AS INTEGER) AS chain_id,
                    CAST(NULL AS BIGINT) AS block_number,
                    CAST(NULL AS VARCHAR) AS fee_recipient,
                    CAST(NULL AS VARCHAR) AS block_hash,
                    CAST(NULL AS BIGINT) AS timestamp
                WHERE FALSE
                """
            )
            counts["blocks"] = 0
            logger.info("%s.blocks: empty stub (run enrich_blocks for feeRecipient)", raw_schema)

    return counts
