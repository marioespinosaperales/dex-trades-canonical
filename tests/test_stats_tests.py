import pandas as pd

from dex_trades.evals.labels import annotate_rows
from dex_trades.stats_tests import build_stat_tests, wilson_ci


def test_wilson_ci_bounds():
    lo, hi = wilson_ci(5, 20)
    assert 0.0 <= lo <= 0.25 <= hi <= 1.0


def test_build_stat_tests_has_pvalues():
    rows = annotate_rows(
        [
            {
                "tx_hash": "0xa",
                "pool_address": "0xpool",
                "trader": "0xt1",
                "direction": "0_to_1",
                "amount_sold": 100.0,
                "amount_bought": 0.03,
                "volume_quote_stable": 100.0,
                "quote_is_stable": True,
                "block_number": 1,
                "log_index": 1,
                "fee_recipient": "0xbuilder_a",
            },
            {
                "tx_hash": "0xb",
                "pool_address": "0xpool",
                "trader": "0xt2",
                "direction": "0_to_1",
                "amount_sold": 0.4,
                "amount_bought": 0.0001,
                "volume_quote_stable": 0.4,
                "quote_is_stable": True,
                "block_number": 2,
                "log_index": 1,
                "fee_recipient": "0xbuilder_b",
            },
            {
                "tx_hash": "0xc1",
                "pool_address": "0xpool",
                "trader": "0xta",
                "direction": "0_to_1",
                "amount_sold": 200.0,
                "amount_bought": 0.06,
                "volume_quote_stable": 200.0,
                "quote_is_stable": True,
                "block_number": 3,
                "log_index": 10,
                "fee_recipient": "0xbuilder_a",
            },
            {
                "tx_hash": "0xc2",
                "pool_address": "0xpool",
                "trader": "0xtv",
                "direction": "1_to_0",
                "amount_sold": 0.03,
                "amount_bought": 90.0,
                "volume_quote_stable": 90.0,
                "quote_is_stable": True,
                "block_number": 3,
                "log_index": 11,
                "fee_recipient": "0xbuilder_a",
            },
            {
                "tx_hash": "0xc3",
                "pool_address": "0xpool",
                "trader": "0xta",
                "direction": "0_to_1",
                "amount_sold": 180.0,
                "amount_bought": 0.05,
                "volume_quote_stable": 180.0,
                "quote_is_stable": True,
                "block_number": 3,
                "log_index": 12,
                "fee_recipient": "0xbuilder_a",
            },
            {
                "tx_hash": "0xd",
                "pool_address": "0xpool",
                "trader": "0xt3",
                "direction": "1_to_0",
                "amount_sold": 0.02,
                "amount_bought": 70.0,
                "volume_quote_stable": 70.0,
                "quote_is_stable": True,
                "block_number": 4,
                "log_index": 1,
                "fee_recipient": "0xbuilder_b",
            },
        ]
    )
    frame = pd.DataFrame(rows)
    out = build_stat_tests(frame)
    names = set(out["test_name"])
    assert "wilson_clean_rate" in names
    assert "bootstrap_noise_volume_share" in names
    assert out["ci_low"].notna().any()
