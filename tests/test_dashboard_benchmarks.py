import pandas as pd

from dex_trades.dashboard_benchmarks import benchmarks_from_trades
from dex_trades.evals.labels import annotate_rows


def test_benchmarks_include_definitions():
    rows = annotate_rows(
        [
            {
                "tx_hash": "0xa",
                "pool_address": "0xpool",
                "trader": "0xt",
                "direction": "0_to_1",
                "amount_sold": 100.0,
                "amount_bought": 0.05,
                "volume_quote_stable": 100.0,
                "quote_is_stable": True,
                "block_number": 1,
                "log_index": 1,
            },
            {
                "tx_hash": "0xb",
                "pool_address": "0xpool",
                "trader": "0xt",
                "direction": "0_to_1",
                "amount_sold": 0.5,
                "amount_bought": 0.0001,
                "volume_quote_stable": 0.5,
                "quote_is_stable": True,
                "block_number": 2,
                "log_index": 1,
            },
        ]
    )
    out = benchmarks_from_trades(
        pd.DataFrame(rows), source="test", source_kind="unit"
    )
    assert "mart_qc_kpis" in out
    assert "definition" in out["mart_qc_kpis"].columns
    assert len(out["mart_dust_threshold_sweep"]) >= 3
    assert out["mart_run_meta"].iloc[0]["source_kind"] == "unit"
