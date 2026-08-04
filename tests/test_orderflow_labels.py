from pathlib import Path

from dex_trades.evals.labels import annotate_rows, is_potential_sandwich_leg
from dex_trades.ml.dataset import load_trade_rows

FIXTURE = Path(__file__).parent / "fixtures" / "golden_trades.json"


def test_sandwich_proxy_on_golden_fixture():
    rows = load_trade_rows(FIXTURE)
    flags = is_potential_sandwich_leg(rows)
    assert sum(flags) == 3
    annotated = annotate_rows(rows)
    sand = [r for r in annotated if r["tx_hash"].startswith("0xsand")]
    assert all(r["is_potential_sandwich_leg"] for r in sand)
    assert all(r["is_orderflow_interesting"] for r in sand)
    assert all(r["is_same_block_pool_burst"] for r in sand)


def test_multi_swap_and_churn_interesting():
    rows = load_trade_rows(FIXTURE)
    annotated = annotate_rows(rows)
    churn = [r for r in annotated if r["tx_hash"] == "0xchurn1"]
    assert all(r["is_multi_swap_tx"] for r in churn)
    assert all(r["is_orderflow_interesting"] for r in churn)
    clean = next(r for r in annotated if r["tx_hash"] == "0xclean1")
    assert not clean["is_orderflow_interesting"]
