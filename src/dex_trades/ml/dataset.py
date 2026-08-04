"""Feature matrix for noise-label learning from trade rows."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from dex_trades.evals.labels import annotate_rows

FEATURE_COLUMNS = [
    "amount_sold",
    "amount_bought",
    "volume_quote_stable",
    "log1p_volume",
    "min_amount",
    "quote_is_stable",
    "dir_0_to_1",
    "dir_1_to_0",
    "peer_count",
    "has_reverse_peer",
    "same_tx_swap_count",
    "same_block_pool_swap_count",
    "same_block_pool_tx_count",
]


def load_trade_rows(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected list of trades in {path}")
    return payload


def expand_synthetic_rows(base: list[dict], *, n_extra: int = 80, seed: int = 42) -> list[dict]:
    """Augment a small golden set so train/test splits are meaningful offline."""
    rng = np.random.default_rng(seed)
    rows = [dict(r) for r in base]
    block = 50_000
    for i in range(n_extra):
        kind = int(rng.integers(0, 5))
        if kind == 0:  # clean large trade
            vol = float(rng.uniform(20.0, 5000.0))
            rows.append(
                {
                    "tx_hash": f"0xsyn_clean_{i}",
                    "pool_address": "0xpool",
                    "trader": f"0xt_{i}",
                    "direction": "0_to_1" if rng.random() > 0.5 else "1_to_0",
                    "amount_sold": vol,
                    "amount_bought": vol / float(rng.uniform(2000.0, 4000.0)),
                    "volume_quote_stable": vol,
                    "quote_is_stable": True,
                    "block_number": block + i,
                    "log_index": 1,
                }
            )
        elif kind == 1:  # dust by USDC
            vol = float(rng.uniform(0.01, 0.99))
            rows.append(
                {
                    "tx_hash": f"0xsyn_dust_{i}",
                    "pool_address": "0xpool",
                    "trader": f"0xt_{i}",
                    "direction": "0_to_1",
                    "amount_sold": vol,
                    "amount_bought": vol / 3000.0,
                    "volume_quote_stable": vol,
                    "quote_is_stable": True,
                    "block_number": block + i,
                    "log_index": 1,
                }
            )
        elif kind == 2:  # micro dust by token threshold
            rows.append(
                {
                    "tx_hash": f"0xsyn_micro_{i}",
                    "pool_address": "0xpool",
                    "trader": f"0xt_{i}",
                    "direction": "1_to_0",
                    "amount_sold": float(rng.uniform(1e-12, 1e-7)),
                    "amount_bought": float(rng.uniform(1e-12, 1e-7)),
                    "volume_quote_stable": None,
                    "quote_is_stable": False,
                    "block_number": block + i,
                    "log_index": 1,
                }
            )
        elif kind == 3:  # self-churn pair
            vol = float(rng.uniform(10.0, 200.0))
            tx = f"0xsyn_churn_{i}"
            trader = f"0xtc_{i}"
            b = block + i
            rows.append(
                {
                    "tx_hash": tx,
                    "pool_address": "0xpool",
                    "trader": trader,
                    "direction": "0_to_1",
                    "amount_sold": vol,
                    "amount_bought": vol / 3000.0,
                    "volume_quote_stable": vol,
                    "quote_is_stable": True,
                    "block_number": b,
                    "log_index": 1,
                }
            )
            rows.append(
                {
                    "tx_hash": tx,
                    "pool_address": "0xpool",
                    "trader": trader,
                    "direction": "1_to_0",
                    "amount_sold": vol / 3000.0,
                    "amount_bought": vol * 0.99,
                    "volume_quote_stable": vol * 0.99,
                    "quote_is_stable": True,
                    "block_number": b,
                    "log_index": 2,
                }
            )
        else:  # sandwich-proxy triple in one block
            b = block + 10_000 + i
            vol = float(rng.uniform(50.0, 400.0))
            rows.extend(
                [
                    {
                        "tx_hash": f"0xsyn_sa_{i}",
                        "pool_address": "0xpool",
                        "trader": f"0xatt_{i}",
                        "direction": "0_to_1",
                        "amount_sold": vol,
                        "amount_bought": vol / 2500.0,
                        "volume_quote_stable": vol,
                        "quote_is_stable": True,
                        "block_number": b,
                        "log_index": 10,
                    },
                    {
                        "tx_hash": f"0xsyn_sv_{i}",
                        "pool_address": "0xpool",
                        "trader": f"0xvic_{i}",
                        "direction": "1_to_0",
                        "amount_sold": vol / 2500.0,
                        "amount_bought": vol * 0.6,
                        "volume_quote_stable": vol * 0.6,
                        "quote_is_stable": True,
                        "block_number": b,
                        "log_index": 11,
                    },
                    {
                        "tx_hash": f"0xsyn_sb_{i}",
                        "pool_address": "0xpool",
                        "trader": f"0xatt_{i}",
                        "direction": "0_to_1",
                        "amount_sold": vol * 0.9,
                        "amount_bought": vol * 0.9 / 2500.0,
                        "volume_quote_stable": vol * 0.9,
                        "quote_is_stable": True,
                        "block_number": b,
                        "log_index": 12,
                    },
                ]
            )
    return rows


def _peer_features(rows: list[dict]) -> list[tuple[int, int]]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        key = (r["tx_hash"], r["pool_address"], r["trader"])
        groups[key].append(r)
    out: list[tuple[int, int]] = []
    for r in rows:
        key = (r["tx_hash"], r["pool_address"], r["trader"])
        peers = groups[key]
        dirs = {p["direction"] for p in peers if p["direction"] in ("0_to_1", "1_to_0")}
        out.append((len(peers), int(len(dirs) >= 2)))
    return out


def build_feature_frame(rows: list[dict], *, dust_usdc: float = 1.0) -> pd.DataFrame:
    """Return features + weak labels from the auditable rubric (`is_noisy`)."""
    annotated = annotate_rows(rows, dust_usdc=dust_usdc)
    peers = _peer_features(annotated)
    records = []
    for row, (peer_count, has_reverse) in zip(annotated, peers, strict=True):
        vol = row.get("volume_quote_stable")
        vol_f = float(vol) if vol is not None else 0.0
        sold = float(row.get("amount_sold", 0.0))
        bought = float(row.get("amount_bought", 0.0))
        direction = row.get("direction", "")
        records.append(
            {
                "amount_sold": sold,
                "amount_bought": bought,
                "volume_quote_stable": vol_f,
                "log1p_volume": math.log1p(max(vol_f, 0.0)),
                "min_amount": min(sold, bought),
                "quote_is_stable": int(bool(row.get("quote_is_stable", True))),
                "dir_0_to_1": int(direction == "0_to_1"),
                "dir_1_to_0": int(direction == "1_to_0"),
                "peer_count": peer_count,
                "has_reverse_peer": has_reverse,
                "same_tx_swap_count": int(row.get("same_tx_swap_count", 1)),
                "same_block_pool_swap_count": int(row.get("same_block_pool_swap_count", 1)),
                "same_block_pool_tx_count": int(row.get("same_block_pool_tx_count", 1)),
                "is_noisy": int(not bool(row["is_clean"])),
                "is_orderflow_interesting": int(bool(row["is_orderflow_interesting"])),
                "is_clean": int(bool(row["is_clean"])),
                "is_dust": int(bool(row["is_dust"])),
                "is_self_churn": int(bool(row["is_self_churn"])),
            }
        )
    return pd.DataFrame.from_records(records)


def xy_from_frame(
    frame: pd.DataFrame,
    *,
    label: str = "is_noisy",
) -> tuple[np.ndarray, np.ndarray]:
    x = frame[FEATURE_COLUMNS].to_numpy(dtype=float)
    y = frame[label].to_numpy(dtype=int)
    return x, y
