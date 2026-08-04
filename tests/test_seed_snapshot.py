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
        kpi_n = conn.execute("select count(*) from mart_qc_kpis").fetchone()[0]
        assert kpi_n >= 8
        meta = conn.execute("select source_kind from mart_run_meta").fetchone()[0]
        assert meta == "seed_demo"
        chains = {
            r[0]
            for r in conn.execute("select distinct chain from mart_dex_trades").fetchall()
        }
        assert chains >= {"ethereum", "base", "arbitrum", "avalanche"}
        protocols = {
            r[0]
            for r in conn.execute("select distinct protocol from mart_dex_trades").fetchall()
        }
        assert "uniswap_v3" in protocols
        assert "aerodrome_slipstream" in protocols or "camelot_v3" in protocols
        assert conn.execute("select count(*) from mart_stat_tests").fetchone()[0] >= 3
        null_price = conn.execute(
            "select count(*) from mart_dex_trades where price_token1_per_token0 is null"
        ).fetchone()[0]
        assert null_price == 0
        fake_pool = conn.execute(
            "select count(*) from mart_dex_trades where pool_address = '0xpool'"
        ).fetchone()[0]
        assert fake_pool == 0
        syn = conn.execute(
            "select count(*) from mart_dex_trades where tx_hash like '0xsyn%'"
        ).fetchone()[0]
        assert syn == 0
        # Ethereum blocks should be ~8 figures, not synthetic 5xxxx placeholders.
        eth_min = conn.execute(
            "select min(block_number) from mart_dex_trades where chain = 'ethereum'"
        ).fetchone()[0]
        assert eth_min >= 20_000_000
