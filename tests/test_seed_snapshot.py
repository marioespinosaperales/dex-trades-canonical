"""Evidence snapshot seed (offline, no RPC)."""

from pathlib import Path

import duckdb

from dex_trades.seed_dashboard_snapshot import seed_snapshot


def test_seed_snapshot_has_orderflow_and_fee_recipient(monkeypatch, tmp_path: Path):
    snap = tmp_path / "dex_marts.duckdb"
    monkeypatch.setattr("dex_trades.seed_dashboard_snapshot.SNAPSHOT_PATH", snap)
    counts = seed_snapshot()
    assert counts["mart_dex_trades"] > 0
    assert counts["mart_orderflow_signals"] >= 1
    with duckdb.connect(str(snap), read_only=True) as conn:
        cols = [r[0] for r in conn.execute("describe mart_dex_trades").fetchall()]
        assert "fee_recipient" in cols
        assert "is_orderflow_interesting" in cols
        of_cols = [r[0] for r in conn.execute("describe mart_orderflow_signals").fetchall()]
        assert "interesting_trade_rate" in of_cols
        n_interesting = conn.execute(
            "select count(*) from mart_dex_trades where is_orderflow_interesting"
        ).fetchone()[0]
        assert n_interesting >= 1
