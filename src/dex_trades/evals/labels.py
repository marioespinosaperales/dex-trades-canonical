"""Noise + orderflow/MEV-lite labels mirrored from dbt ``int_dex_trades``.

Kept in Python so unit tests, QC scorecards, and research CLIs share one rubric.
Sandwich / burst flags are **proxies**, not proof of MEV.
"""

from __future__ import annotations

from collections import defaultdict


def is_dust(
    amount_sold: float,
    amount_bought: float,
    *,
    volume_quote_stable: float | None,
    quote_is_stable: bool,
    dust_token: float = 1e-6,
    dust_usdc: float = 1.0,
) -> bool:
    """Mirror dbt dust rule."""
    if quote_is_stable and volume_quote_stable is not None and volume_quote_stable < dust_usdc:
        return True
    return amount_sold < dust_token and amount_bought < dust_token


def is_self_churn(rows: list[dict]) -> list[bool]:
    """Mirror dbt self-churn: same tx/pool/trader with reverse directions."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        key = (r["tx_hash"], r["pool_address"], r["trader"])
        groups[key].append(r)

    flags = []
    for r in rows:
        key = (r["tx_hash"], r["pool_address"], r["trader"])
        peers = groups[key]
        dirs = {p["direction"] for p in peers if p["direction"] in ("0_to_1", "1_to_0")}
        flags.append(len(peers) >= 2 and len(dirs) >= 2 and r["direction"] in dirs)
    return flags


def same_tx_swap_counts(rows: list[dict]) -> list[int]:
    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        counts[str(r["tx_hash"])] += 1
    return [counts[str(r["tx_hash"])] for r in rows]


def same_block_pool_stats(rows: list[dict]) -> tuple[list[int], list[int]]:
    """Return (swap_count, distinct_tx_count) per row for (block_number, pool)."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        key = (r.get("block_number"), r.get("pool_address"))
        groups[key].append(r)

    swap_counts: list[int] = []
    tx_counts: list[int] = []
    for r in rows:
        key = (r.get("block_number"), r.get("pool_address"))
        peers = groups[key]
        swap_counts.append(len(peers))
        tx_counts.append(len({p["tx_hash"] for p in peers}))
    return swap_counts, tx_counts


def is_potential_sandwich_leg(rows: list[dict]) -> list[bool]:
    """Heuristic: in same block+pool, pattern dir A → B → A by log_index.

    Proxy only — routers, aggregators, and coincidence can look identical.
    """
    flags = [False] * len(rows)
    groups: dict[tuple, list[tuple[int, dict]]] = defaultdict(list)
    for i, r in enumerate(rows):
        if r.get("block_number") is None:
            continue
        key = (r.get("block_number"), r.get("pool_address"))
        groups[key].append((i, r))

    for items in groups.values():
        ordered = sorted(items, key=lambda pair: int(pair[1].get("log_index") or 0))
        dirs = [pair[1].get("direction") for pair in ordered]
        for j in range(1, len(ordered) - 1):
            prev_d, cur_d, next_d = dirs[j - 1], dirs[j], dirs[j + 1]
            if (
                prev_d in ("0_to_1", "1_to_0")
                and next_d == prev_d
                and cur_d in ("0_to_1", "1_to_0")
                and cur_d != prev_d
            ):
                for k in (j - 1, j, j + 1):
                    flags[ordered[k][0]] = True
    return flags


def annotate_rows(
    rows: list[dict],
    *,
    dust_token: float = 1e-6,
    dust_usdc: float = 1.0,
) -> list[dict]:
    """Return copies with noise + orderflow/MEV-lite flags attached."""
    churn = is_self_churn(rows)
    tx_counts = same_tx_swap_counts(rows)
    block_pool_swaps, block_pool_txs = same_block_pool_stats(rows)
    sandwich = is_potential_sandwich_leg(rows)

    out: list[dict] = []
    for i, row in enumerate(rows):
        dust = is_dust(
            float(row.get("amount_sold", 0.0)),
            float(row.get("amount_bought", 0.0)),
            volume_quote_stable=row.get("volume_quote_stable"),
            quote_is_stable=bool(row.get("quote_is_stable", True)),
            dust_token=dust_token,
            dust_usdc=dust_usdc,
        )
        multi = tx_counts[i] >= 2
        burst = block_pool_swaps[i] >= 2 and block_pool_txs[i] >= 2
        interesting = multi or burst or sandwich[i] or churn[i]
        annotated = dict(row)
        annotated["is_dust"] = dust
        annotated["is_self_churn"] = churn[i]
        annotated["is_clean"] = not dust and not churn[i]
        annotated["same_tx_swap_count"] = tx_counts[i]
        annotated["is_multi_swap_tx"] = multi
        annotated["same_block_pool_swap_count"] = block_pool_swaps[i]
        annotated["same_block_pool_tx_count"] = block_pool_txs[i]
        annotated["is_same_block_pool_burst"] = burst
        annotated["is_potential_sandwich_leg"] = sandwich[i]
        annotated["is_orderflow_interesting"] = interesting
        out.append(annotated)
    return out
