"""Unit tests for V2/V3 Swap decode and noise helpers."""

from __future__ import annotations

from eth_abi import encode
from eth_utils import to_checksum_address

from dex_trades.index import v2_swap, v3_swap


def _v3_log(*, amount0: int, amount1: int, tx: str = "0x" + "aa" * 32, log_index: int = 1) -> dict:
    data = encode(
        ["int256", "int256", "uint160", "uint128", "int24"],
        [amount0, amount1, 1 << 96, 1_000_000, 200000],
    )
    return {
        "topics": [
            v3_swap.topic0(),
            "0x" + "00" * 12 + "11" * 20,
            "0x" + "00" * 12 + "22" * 20,
        ],
        "data": "0x" + data.hex(),
        "blockNumber": hex(19_000_000),
        "transactionHash": tx,
        "logIndex": hex(log_index),
    }


def _v2_log(
    *,
    amount0_in: int = 0,
    amount1_in: int = 0,
    amount0_out: int = 0,
    amount1_out: int = 0,
    tx: str = "0x" + "bb" * 32,
    log_index: int = 2,
) -> dict:
    data = encode(
        ["uint256", "uint256", "uint256", "uint256"],
        [amount0_in, amount1_in, amount0_out, amount1_out],
    )
    return {
        "topics": [
            v2_swap.topic0(),
            "0x" + "00" * 12 + "33" * 20,
            "0x" + "00" * 12 + "44" * 20,
        ],
        "data": "0x" + data.hex(),
        "blockNumber": hex(19_000_001),
        "transactionHash": tx,
        "logIndex": hex(log_index),
    }


POOL_KW = dict(
    chain="ethereum",
    chain_id=1,
    pool_address="0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
    token0_symbol="USDC",
    token1_symbol="WETH",
    token0_decimals=6,
    token1_decimals=18,
)


def test_v3_decode_sell_token0():
    raw = _v3_log(amount0=1_000_000, amount1=-(10**18))
    row = v3_swap.decode_swap(raw, **POOL_KW)
    assert row is not None
    assert row["protocol"] == "uniswap_v3"
    assert row["direction"] == "0_to_1"
    assert row["token_sold"] == "USDC"
    assert row["token_bought"] == "WETH"
    assert row["amount_sold_raw"] == str(1_000_000)
    assert row["amount_bought_raw"] == str(10**18)
    assert row["trader"] == to_checksum_address("0x" + "22" * 20)


def test_v3_decode_sell_token1():
    raw = _v3_log(amount0=-(10**6), amount1=10**18)
    row = v3_swap.decode_swap(raw, **POOL_KW)
    assert row is not None
    assert row["direction"] == "1_to_0"
    assert row["token_sold"] == "WETH"
    assert row["token_bought"] == "USDC"


def test_v2_decode_sell_token0():
    raw = _v2_log(amount0_in=2_000_000, amount1_out=10**18)
    row = v2_swap.decode_swap(raw, **POOL_KW)
    assert row is not None
    assert row["protocol"] == "uniswap_v2"
    assert row["direction"] == "0_to_1"
    assert row["token_sold"] == "USDC"
    assert row["trader"] == to_checksum_address("0x" + "44" * 20)


def test_v2_decode_sell_token1():
    raw = _v2_log(amount1_in=10**18, amount0_out=3_000_000)
    row = v2_swap.decode_swap(raw, **POOL_KW)
    assert row is not None
    assert row["direction"] == "1_to_0"
    assert row["token_sold"] == "WETH"


def test_wrong_topic_returns_none():
    raw = _v3_log(amount0=1, amount1=-1)
    raw["topics"][0] = "0x" + "ff" * 32
    assert v3_swap.decode_swap(raw, **POOL_KW) is None


def is_dust(
    amount_sold: float,
    amount_bought: float,
    *,
    volume_quote_stable: float | None,
    quote_is_stable: bool,
    dust_token: float = 1e-6,
    dust_usdc: float = 1.0,
) -> bool:
    """Mirror dbt dust rule for unit coverage."""
    if quote_is_stable and volume_quote_stable is not None and volume_quote_stable < dust_usdc:
        return True
    return amount_sold < dust_token and amount_bought < dust_token


def is_self_churn(rows: list[dict]) -> list[bool]:
    """Mirror dbt self-churn: same tx/pool/trader with reverse directions."""
    from collections import defaultdict

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


def test_dust_usdc_threshold():
    assert is_dust(0.5, 0.0001, volume_quote_stable=0.5, quote_is_stable=True)
    assert not is_dust(100.0, 0.05, volume_quote_stable=100.0, quote_is_stable=True)


def test_self_churn_flag():
    rows = [
        {
            "tx_hash": "0x1",
            "pool_address": "0xp",
            "trader": "0xt",
            "direction": "0_to_1",
        },
        {
            "tx_hash": "0x1",
            "pool_address": "0xp",
            "trader": "0xt",
            "direction": "1_to_0",
        },
        {
            "tx_hash": "0x2",
            "pool_address": "0xp",
            "trader": "0xt",
            "direction": "0_to_1",
        },
    ]
    flags = is_self_churn(rows)
    assert flags == [True, True, False]
