"""Seed Evidence DuckDB from golden/synthetic trades (no RPC required).

    uv run python -m dex_trades.seed_dashboard_snapshot

Writes dashboard/sources/dex/dex_marts.duckdb so Evidence / Vercel have data.
"""

from __future__ import annotations

import logging

import duckdb
import pandas as pd

from dex_trades.dashboard_benchmarks import benchmarks_from_trades
from dex_trades.evals.labels import annotate_rows
from dex_trades.export_snapshot import SNAPSHOT_PATH
from dex_trades.ml.dataset import expand_synthetic_rows, load_trade_rows
from dex_trades.settings import PROJECT_ROOT

logger = logging.getLogger(__name__)
FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "golden_trades.json"


def _build_trades_frame() -> pd.DataFrame:
    base = load_trade_rows(FIXTURE)
    rows = expand_synthetic_rows(base, n_extra=40, seed=11)
    for i, r in enumerate(rows):
        r.setdefault("block_number", 10_000 + i)
        r.setdefault("log_index", 1)
        r.setdefault("chain", "ethereum")
        r.setdefault("chain_id", 1)
        r.setdefault("protocol", "uniswap_v3")
        r.setdefault("pool", "USDC/WETH")
        r.setdefault("pool_address", r.get("pool_address", "0xpool"))
        r.setdefault("block_time", None)
        r.setdefault("token_sold", "USDC")
        r.setdefault("token_bought", "WETH")
        r.setdefault("token0_symbol", "USDC")
        r.setdefault("token1_symbol", "WETH")
        r.setdefault("direction", r.get("direction", "0_to_1"))
        r.setdefault("fee_tier", 3000)
        tx = str(r.get("tx_hash", ""))
        if tx.startswith("0xsand") or "syn_s" in tx:
            r["fee_recipient"] = "0xbuilder_sandwich"
        else:
            r["fee_recipient"] = "0xbuilder_other"
    annotated = annotate_rows(rows)
    frame = pd.DataFrame(annotated)
    for col in (
        "amount_sold_raw",
        "amount_bought_raw",
        "price_token1_per_token0",
        "volume_token0",
    ):
        if col not in frame.columns:
            frame[col] = None
    return frame


def _orderflow_mart(trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (chain, protocol), grp in trades.groupby(["chain", "protocol"]):
        n = len(grp)
        total_vol = float(grp["volume_quote_stable"].fillna(0).sum())
        interesting = grp["is_orderflow_interesting"].astype(bool)
        clean = grp["is_clean"].astype(bool)
        interesting_vol = float(grp.loc[interesting, "volume_quote_stable"].fillna(0).sum())
        clean_vol = float(grp.loc[clean, "volume_quote_stable"].fillna(0).sum())
        rows.append(
            {
                "chain": chain,
                "protocol": protocol,
                "trade_count": n,
                "multi_swap_trades": int(grp["is_multi_swap_tx"].sum()),
                "burst_trades": int(grp["is_same_block_pool_burst"].sum()),
                "sandwich_proxy_trades": int(grp["is_potential_sandwich_leg"].sum()),
                "interesting_trades": int(interesting.sum()),
                "clean_trades": int(clean.sum()),
                "total_volume_quote_stable": total_vol,
                "clean_volume_quote_stable": clean_vol,
                "interesting_volume_quote_stable": interesting_vol,
                "interesting_trade_rate": round(float(interesting.mean()), 4) if n else 0.0,
                "interesting_volume_share": (
                    round(interesting_vol / total_vol, 4) if total_vol else 0.0
                ),
            }
        )
    return pd.DataFrame(rows)


def _volume_mart(trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (chain, protocol), grp in trades.groupby(["chain", "protocol"]):
        clean = grp["is_clean"].astype(bool)
        rows.append(
            {
                "chain": chain,
                "protocol": protocol,
                "trade_count": len(grp),
                "clean_trade_count": int(clean.sum()),
                "dust_trade_count": int(grp["is_dust"].sum()),
                "self_churn_trade_count": int(grp["is_self_churn"].sum()),
                "volume_quote_stable": float(grp["volume_quote_stable"].fillna(0).sum()),
                "clean_volume_quote_stable": float(
                    grp.loc[clean, "volume_quote_stable"].fillna(0).sum()
                ),
            }
        )
    return pd.DataFrame(rows)


def seed_snapshot() -> dict[str, int]:
    trades = _build_trades_frame()
    orderflow = _orderflow_mart(trades)
    volume = _volume_mart(trades)
    benches = benchmarks_from_trades(
        trades,
        source=str(FIXTURE),
        source_kind="seed_synthetic",
    )

    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = SNAPSHOT_PATH.with_suffix(".duckdb.tmp")
    tmp.unlink(missing_ok=True)
    with duckdb.connect(str(tmp)) as conn:
        conn.register("trades_df", trades)
        conn.register("orderflow_df", orderflow)
        conn.register("volume_df", volume)
        conn.execute("CREATE TABLE mart_dex_trades AS SELECT * FROM trades_df")
        conn.execute("CREATE TABLE mart_orderflow_signals AS SELECT * FROM orderflow_df")
        conn.execute("CREATE TABLE mart_dex_volume_by_protocol AS SELECT * FROM volume_df")
        for name, frame in benches.items():
            conn.register(f"{name}_df", frame)
            conn.execute(f"CREATE TABLE {name} AS SELECT * FROM {name}_df")

        def _count(table: str) -> int:
            return int(conn.execute(f"select count(*) from {table}").fetchone()[0])

        counts = {t: _count(t) for t in (
            "mart_dex_trades",
            "mart_orderflow_signals",
            "mart_dex_volume_by_protocol",
            *benches.keys(),
        )}
    SNAPSHOT_PATH.unlink(missing_ok=True)
    tmp.rename(SNAPSHOT_PATH)
    return counts


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    counts = seed_snapshot()
    logger.info("Seeded Evidence snapshot %s: %s", SNAPSHOT_PATH, counts)


if __name__ == "__main__":
    main()
