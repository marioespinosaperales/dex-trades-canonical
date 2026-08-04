"""Export marts into the Evidence DuckDB snapshot.

    uv run python -m dex_trades.export_snapshot
"""

from __future__ import annotations

import logging

import duckdb

from dex_trades.settings import PROJECT_ROOT, get_settings

logger = logging.getLogger(__name__)

SNAPSHOT_PATH = PROJECT_ROOT / "dashboard" / "sources" / "dex" / "dex_marts.duckdb"
MARTS_SCHEMA = "main_marts"
MART_TABLES = (
    "mart_dex_trades",
    "mart_dex_volume_by_protocol",
    "mart_orderflow_signals",
)


def export_snapshot() -> dict[str, int]:
    settings = get_settings()
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = SNAPSHOT_PATH.with_suffix(".duckdb.tmp")
    tmp_path.unlink(missing_ok=True)

    warehouse_path = str(settings.pipeline.duckdb_path).replace("'", "''")
    counts: dict[str, int] = {}
    with duckdb.connect(str(tmp_path)) as conn:
        conn.execute(f"ATTACH '{warehouse_path}' AS warehouse (READ_ONLY)")
        for table in MART_TABLES:
            conn.execute(
                f"CREATE TABLE {table} AS SELECT * FROM warehouse.{MARTS_SCHEMA}.{table}"
            )
            counts[table] = int(conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0])

    SNAPSHOT_PATH.unlink(missing_ok=True)
    tmp_path.rename(SNAPSHOT_PATH)
    return counts


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("Snapshot exported to %s: %s", SNAPSHOT_PATH, export_snapshot())


if __name__ == "__main__":
    main()
