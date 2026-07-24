import json
from pathlib import Path

from dex_trades.evals.labels import annotate_rows, is_dust, is_self_churn
from dex_trades.evals.scorecard import (
    build_scorecard_from_rows,
    label_distribution,
    threshold_sweep,
    volume_impact,
    write_scorecard,
)

FIXTURE = Path(__file__).parent / "fixtures" / "golden_trades.json"


def test_dust_and_churn_rubric():
    assert is_dust(0.5, 0.0001, volume_quote_stable=0.5, quote_is_stable=True)
    assert not is_dust(100.0, 0.05, volume_quote_stable=100.0, quote_is_stable=True)
    rows = [
        {"tx_hash": "0x1", "pool_address": "0xp", "trader": "0xt", "direction": "0_to_1"},
        {"tx_hash": "0x1", "pool_address": "0xp", "trader": "0xt", "direction": "1_to_0"},
        {"tx_hash": "0x2", "pool_address": "0xp", "trader": "0xt", "direction": "0_to_1"},
    ]
    assert is_self_churn(rows) == [True, True, False]


def test_golden_fixture_scorecard(tmp_path):
    rows = json.loads(FIXTURE.read_text(encoding="utf-8"))
    annotated = annotate_rows(rows, dust_usdc=1.0)
    dist = label_distribution(annotated)
    assert dist["trades"] == 6
    assert dist["dust"] >= 1
    assert dist["self_churn"] == 2
    assert dist["clean"] >= 1

    impact = volume_impact(annotated)
    assert impact["total_volume_quote_stable"] > impact["clean_volume_quote_stable"]

    sweep = threshold_sweep(rows)
    rates = {row["dust_usdc_threshold"]: row["dust_rate"] for row in sweep}
    assert rates[0.1] <= rates[10.0] or rates[1.0] != rates[10.0]

    scorecard = build_scorecard_from_rows(rows, source="golden_trades.json")
    out = write_scorecard(scorecard, artifacts_dir=tmp_path)
    assert out.exists()
    body = out.read_text(encoding="utf-8")
    assert "DEX trades QC scorecard" in body
    assert "Dust threshold sensitivity" in body
