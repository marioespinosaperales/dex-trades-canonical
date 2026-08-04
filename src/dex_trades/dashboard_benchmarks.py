"""Build QC / orderflow benchmark tables for the Evidence snapshot."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd

from dex_trades.evals.scorecard import build_scorecard_from_rows
from dex_trades.stats_tests import build_stat_tests


def benchmarks_from_trades(
    trades: pd.DataFrame,
    *,
    source: str,
    source_kind: str,
) -> dict[str, pd.DataFrame]:
    """Return DuckDB-ready QC + inference tables for Evidence."""
    rows: list[dict[str, Any]] = trades.to_dict(orient="records")
    scorecard = build_scorecard_from_rows(rows, source=source, already_labeled=True)
    stat_tests = build_stat_tests(trades)
    dist = scorecard.label_distribution
    impact = scorecard.volume_impact
    n = int(dist["trades"])

    interesting_vol = 0.0
    if "is_orderflow_interesting" in trades.columns and n:
        interesting_vol = float(
            trades.loc[
                trades["is_orderflow_interesting"].astype(bool), "volume_quote_stable"
            ]
            .fillna(0)
            .sum()
        )
    sandwich = (
        int(trades["is_potential_sandwich_leg"].astype(bool).sum())
        if "is_potential_sandwich_leg" in trades.columns
        else int(dist.get("potential_sandwich_leg", 0))
    )
    multi = (
        int(trades["is_multi_swap_tx"].astype(bool).sum())
        if "is_multi_swap_tx" in trades.columns
        else 0
    )
    burst = (
        int(trades["is_same_block_pool_burst"].astype(bool).sum())
        if "is_same_block_pool_burst" in trades.columns
        else 0
    )
    total_vol = float(impact["total_volume_quote_stable"])

    kpis = pd.DataFrame(
        [
            {
                "metric": "trades",
                "value": float(n),
                "unit": "count",
                "definition": "Swap log rows (chain, tx_hash, log_index)",
            },
            {
                "metric": "clean_rate",
                "value": float(dist["clean_rate"]),
                "unit": "share",
                "definition": "Share of trades with not dust and not self-churn",
            },
            {
                "metric": "dust_rate",
                "value": float(dist["dust_rate"]),
                "unit": "share",
                "definition": "Share flagged is_dust (USDC<$1 or micro amounts)",
            },
            {
                "metric": "self_churn_rate",
                "value": float(dist["self_churn_rate"]),
                "unit": "share",
                "definition": "Share with same-tx reverse-direction self-churn",
            },
            {
                "metric": "noise_share_of_volume",
                "value": float(impact["noise_share_of_volume"]),
                "unit": "share",
                "definition": "1 - clean_volume / total_volume (stable quote)",
            },
            {
                "metric": "interesting_rate",
                "value": float(dist["interesting_rate"]),
                "unit": "share",
                "definition": "Share with orderflow proxy flags (multi/burst/sandwich/churn)",
            },
            {
                "metric": "interesting_volume_share",
                "value": round(interesting_vol / total_vol, 4) if total_vol else 0.0,
                "unit": "share",
                "definition": "Interesting volume / total volume (stable quote)",
            },
            {
                "metric": "sandwich_proxy_rate",
                "value": round(sandwich / n, 4) if n else 0.0,
                "unit": "share",
                "definition": "A→B→A same block+pool direction pattern (proxy, not proof)",
            },
            {
                "metric": "multi_swap_rate",
                "value": round(multi / n, 4) if n else 0.0,
                "unit": "share",
                "definition": "≥2 swaps in the same transaction",
            },
            {
                "metric": "burst_rate",
                "value": round(burst / n, 4) if n else 0.0,
                "unit": "share",
                "definition": "≥2 txs on same pool in same block",
            },
            {
                "metric": "total_volume_quote_stable",
                "value": total_vol,
                "unit": "usd",
                "definition": "Sum of volume_quote_stable (USDC-as-quote when configured)",
            },
            {
                "metric": "clean_volume_quote_stable",
                "value": float(impact["clean_volume_quote_stable"]),
                "unit": "usd",
                "definition": "Volume on is_clean trades only",
            },
        ]
    )

    notes = (
        "Executable QC rubric (Python labels mirrored in dbt) plus rate CIs and "
        "association tests. Orderflow flags are structural proxies, not sandwich proof. "
    )
    if source_kind.startswith("seed"):
        notes += (
            "Snapshot is a multi-pool demo seeded from config/pools.yaml "
            "(replace with make backfill → transform → snapshot for live RPC data)."
        )
    else:
        notes += "Snapshot exported from the DuckDB warehouse marts."

    return {
        "mart_qc_kpis": kpis,
        "mart_dust_threshold_sweep": pd.DataFrame(scorecard.threshold_sweep),
        "mart_stat_tests": stat_tests,
        "mart_run_meta": pd.DataFrame(
            [
                {
                    "generated_at": datetime.now(UTC).isoformat(),
                    "source": source,
                    "source_kind": source_kind,
                    "trade_count": n,
                    "notes": notes,
                }
            ]
        ),
    }
