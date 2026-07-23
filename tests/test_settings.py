"""Settings / config load smoke test."""

from __future__ import annotations

from dex_trades.settings import get_settings


def test_settings_load():
    get_settings.cache_clear()
    settings = get_settings()
    assert len(settings.chains) >= 4
    assert {c.name for c in settings.chains} >= {"ethereum", "base", "arbitrum", "avalanche"}
    enabled = [p for p in settings.pools if p.enabled]
    assert len(enabled) >= 8
    protocols = {p.protocol for p in enabled}
    assert protocols >= {
        "uniswap_v2",
        "uniswap_v3",
        "camelot_v3",
        "aerodrome_slipstream",
        "pharaoh_v3",
    }
    assert settings.pipeline.chunk_size == 10
