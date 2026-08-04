"""Seed Evidence DuckDB across configured pools (offline, no RPC).

    uv run python -m dex_trades.seed_dashboard_snapshot

Mirrors ``config/pools.yaml`` so the dashboard shows Eth/Base/Arb/Avax ×
protocols before a live Alchemy backfill. Rows use realistic addresses and
block magnitudes; ``source_kind=seed_demo`` until ``make snapshot`` from warehouse.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import yaml

from dex_trades.dashboard_benchmarks import benchmarks_from_trades
from dex_trades.evals.labels import annotate_rows
from dex_trades.export_snapshot import SNAPSHOT_PATH
from dex_trades.settings import PROJECT_ROOT

logger = logging.getLogger(__name__)
POOLS_PATH = PROJECT_ROOT / "config" / "pools.yaml"

# Approximate recent tip magnitudes so block numbers look chain-native.
_CHAIN_BLOCK_BASE = {
    "ethereum": 22_450_000,
    "base": 33_200_000,
    "arbitrum": 355_000_000,
    "avalanche": 64_500_000,
}
_CHAIN_IDS = {
    "ethereum": 1,
    "base": 8453,
    "arbitrum": 42161,
    "avalanche": 43114,
}


def _hex(label: str, nbytes: int = 20) -> str:
    digest = hashlib.sha256(label.encode()).hexdigest()
    return "0x" + digest[: nbytes * 2]


def _load_enabled_pools(path: Path) -> list[dict]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    pools = payload.get("pools") or []
    return [p for p in pools if p.get("enabled", True)]


def _price_and_amounts(
    *,
    direction: str,
    vol_stable: float,
    token0: str,
    token1: str,
    quote_token: str,
    rng: np.random.Generator,
) -> dict:
    """Return sold/bought symbols, amounts, and price_token1_per_token0."""
    # Rough mid prices for demo realism (not a market claim).
    mid = {
        ("USDC", "WETH"): 1 / 3200.0,  # token1 per token0 if token0=USDC
        ("WETH", "USDC"): 3200.0,
        ("WAVAX", "USDC"): 28.0,
        ("USDC", "WAVAX"): 1 / 28.0,
    }
    key = (token0, token1)
    # price always token1 per token0
    if key in mid:
        px = mid[key] * float(rng.uniform(0.98, 1.02))
    else:
        px = float(rng.uniform(0.5, 4000.0))

    if quote_token == "token0":
        # token0 is stable (USDC)
        if direction == "0_to_1":
            amount_sold = vol_stable
            amount_bought = vol_stable * px  # WETH out ≈ USDC * (WETH/USDC)
            # wait: price_token1_per_token0 = WETH per USDC = small
            # amount_bought (token1) = amount_sold (token0) * price
            token_sold, token_bought = token0, token1
        else:
            amount_bought = vol_stable
            amount_sold = vol_stable * px
            token_sold, token_bought = token1, token0
    else:
        # token1 is stable
        if direction == "0_to_1":
            # sell token0 (WETH), buy USDC
            amount_bought = vol_stable
            amount_sold = vol_stable / px if px else 0.0
            token_sold, token_bought = token0, token1
        else:
            amount_sold = vol_stable
            amount_bought = vol_stable / px if px else 0.0
            token_sold, token_bought = token1, token0

    return {
        "token_sold": token_sold,
        "token_bought": token_bought,
        "amount_sold": float(amount_sold),
        "amount_bought": float(amount_bought),
        "price_token1_per_token0": float(px),
        "volume_quote_stable": float(vol_stable),
    }


def _build_trades_frame(*, n_per_pool: int = 14, seed: int = 11) -> pd.DataFrame:
    pools = _load_enabled_pools(POOLS_PATH)
    if not pools:
        raise RuntimeError(f"No enabled pools in {POOLS_PATH}")

    rng = np.random.default_rng(seed)
    rows: list[dict] = []
    builders = [
        _hex("builder_flashbots", 20),
        _hex("builder_beaver", 20),
        _hex("builder_rsync", 20),
        _hex("builder_other", 20),
    ]

    for p_i, pool in enumerate(pools):
        chain = pool["chain"]
        protocol = pool["protocol"]
        address = str(pool["address"]).lower()
        token0 = pool["token0_symbol"]
        token1 = pool["token1_symbol"]
        fee_tier = pool.get("fee_tier")
        quote_token = pool.get("quote_token", "token1")
        chain_id = _CHAIN_IDS.get(chain, 0)
        block0 = _CHAIN_BLOCK_BASE.get(chain, 1_000_000) + p_i * 1_000

        for i in range(n_per_pool):
            kind = int(rng.integers(0, 5))
            block_number = block0 + int(rng.integers(0, 400)) + i
            fee_recipient = builders[int(rng.integers(0, len(builders)))]
            base = {
                "chain": chain,
                "chain_id": chain_id,
                "protocol": protocol,
                "pool": f"{token0}/{token1}",
                "pool_address": address,
                "token0_symbol": token0,
                "token1_symbol": token1,
                "fee_tier": fee_tier,
                "quote_is_stable": bool(pool.get("quote_is_stable", True)),
                "block_number": block_number,
                "block_time": None,
                "fee_recipient": fee_recipient,
                "volume_token0": None,
                "amount_sold_raw": None,
                "amount_bought_raw": None,
            }

            if kind == 0:  # clean
                direction = "0_to_1" if rng.random() > 0.5 else "1_to_0"
                vol = float(rng.uniform(50.0, 8000.0))
                am = _price_and_amounts(
                    direction=direction,
                    vol_stable=vol,
                    token0=token0,
                    token1=token1,
                    quote_token=quote_token,
                    rng=rng,
                )
                rows.append(
                    {
                        **base,
                        **am,
                        "tx_hash": _hex(f"tx-clean-{chain}-{protocol}-{i}", 32),
                        "log_index": 1,
                        "trader": _hex(f"trader-clean-{chain}-{i}", 20),
                        "direction": direction,
                    }
                )
            elif kind == 1:  # dust USDC
                direction = "0_to_1"
                vol = float(rng.uniform(0.05, 0.9))
                am = _price_and_amounts(
                    direction=direction,
                    vol_stable=vol,
                    token0=token0,
                    token1=token1,
                    quote_token=quote_token,
                    rng=rng,
                )
                rows.append(
                    {
                        **base,
                        **am,
                        "tx_hash": _hex(f"tx-dust-{chain}-{protocol}-{i}", 32),
                        "log_index": 1,
                        "trader": _hex(f"trader-dust-{chain}-{i}", 20),
                        "direction": direction,
                    }
                )
            elif kind == 2:  # micro dust
                rows.append(
                    {
                        **base,
                        "tx_hash": _hex(f"tx-micro-{chain}-{protocol}-{i}", 32),
                        "log_index": 1,
                        "trader": _hex(f"trader-micro-{chain}-{i}", 20),
                        "direction": "1_to_0",
                        "token_sold": token1,
                        "token_bought": token0,
                        "amount_sold": float(rng.uniform(1e-12, 1e-7)),
                        "amount_bought": float(rng.uniform(1e-12, 1e-7)),
                        "price_token1_per_token0": float(rng.uniform(0.5, 4000.0)),
                        "volume_quote_stable": None,
                        "quote_is_stable": False,
                    }
                )
            elif kind == 3:  # self-churn same tx
                vol = float(rng.uniform(20.0, 300.0))
                tx = _hex(f"tx-churn-{chain}-{protocol}-{i}", 32)
                trader = _hex(f"trader-churn-{chain}-{i}", 20)
                am0 = _price_and_amounts(
                    direction="0_to_1",
                    vol_stable=vol,
                    token0=token0,
                    token1=token1,
                    quote_token=quote_token,
                    rng=rng,
                )
                am1 = _price_and_amounts(
                    direction="1_to_0",
                    vol_stable=vol * 0.98,
                    token0=token0,
                    token1=token1,
                    quote_token=quote_token,
                    rng=rng,
                )
                rows.append(
                    {
                        **base,
                        **am0,
                        "tx_hash": tx,
                        "log_index": 1,
                        "trader": trader,
                        "direction": "0_to_1",
                    }
                )
                rows.append(
                    {
                        **base,
                        **am1,
                        "tx_hash": tx,
                        "log_index": 2,
                        "trader": trader,
                        "direction": "1_to_0",
                    }
                )
            else:  # sandwich-shaped triple; share a builder
                vol = float(rng.uniform(80.0, 600.0))
                b = block_number
                fee_recipient = builders[0]  # concentrate under one builder
                for leg, direction, log_i, scale in (
                    ("a", "0_to_1", 10, 1.0),
                    ("v", "1_to_0", 11, 0.55),
                    ("b", "0_to_1", 12, 0.9),
                ):
                    am = _price_and_amounts(
                        direction=direction,
                        vol_stable=vol * scale,
                        token0=token0,
                        token1=token1,
                        quote_token=quote_token,
                        rng=rng,
                    )
                    rows.append(
                        {
                            **base,
                            **am,
                            "block_number": b,
                            "fee_recipient": fee_recipient,
                            "tx_hash": _hex(f"tx-sand-{leg}-{chain}-{protocol}-{i}", 32),
                            "log_index": log_i,
                            "trader": _hex(
                                f"trader-sand-{leg}-{chain}-{i}",
                                20,
                            ),
                            "direction": direction,
                        }
                    )

    annotated = annotate_rows(rows)
    return pd.DataFrame(annotated)


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
        source=str(POOLS_PATH),
        source_kind="seed_demo",
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

        counts = {
            t: _count(t)
            for t in (
                "mart_dex_trades",
                "mart_orderflow_signals",
                "mart_dex_volume_by_protocol",
                *benches.keys(),
            )
        }
    SNAPSHOT_PATH.unlink(missing_ok=True)
    tmp.rename(SNAPSHOT_PATH)
    return counts


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    counts = seed_snapshot()
    logger.info("Seeded Evidence snapshot %s: %s", SNAPSHOT_PATH, counts)


if __name__ == "__main__":
    main()
