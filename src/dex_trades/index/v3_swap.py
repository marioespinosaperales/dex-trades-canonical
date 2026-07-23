"""Uniswap V3 Swap event decode."""

from __future__ import annotations

from typing import Any

from eth_abi import decode
from eth_utils import event_abi_to_log_topic, to_checksum_address

SWAP_ABI: dict[str, Any] = {
    "anonymous": False,
    "inputs": [
        {"indexed": True, "name": "sender", "type": "address"},
        {"indexed": True, "name": "recipient", "type": "address"},
        {"indexed": False, "name": "amount0", "type": "int256"},
        {"indexed": False, "name": "amount1", "type": "int256"},
        {"indexed": False, "name": "sqrtPriceX96", "type": "uint160"},
        {"indexed": False, "name": "liquidity", "type": "uint128"},
        {"indexed": False, "name": "tick", "type": "int24"},
    ],
    "name": "Swap",
    "type": "event",
}

SWAP_TOPIC0 = ("0x" + event_abi_to_log_topic(SWAP_ABI).hex()).lower()


def topic0() -> str:
    return SWAP_TOPIC0


def _topic_address(topic: str) -> str:
    return to_checksum_address("0x" + topic[-40:])


def decode_swap(
    raw: dict[str, Any],
    *,
    chain: str,
    chain_id: int,
    pool_address: str,
    token0_symbol: str,
    token1_symbol: str,
    token0_decimals: int,
    token1_decimals: int,
) -> dict[str, Any] | None:
    """Decode a V3 Swap log into a flat raw-swap row.

    V3 amounts are signed from the pool's perspective: positive = pool received
    (trader sold), negative = pool sent (trader bought).
    """
    topics = raw.get("topics") or []
    if not topics or topics[0].lower() != SWAP_TOPIC0:
        return None

    data_hex = raw.get("data", "0x")
    data_bytes = bytes.fromhex(data_hex[2:] if data_hex.startswith("0x") else data_hex)
    amount0, amount1, _sqrt, _liq, _tick = decode(
        ["int256", "int256", "uint160", "uint128", "int24"], data_bytes
    )
    sender = _topic_address(topics[1])
    trader = _topic_address(topics[2])

    # Trader sold the token the pool received (positive amount).
    if amount0 > 0 and amount1 < 0:
        token_sold, token_bought = token0_symbol, token1_symbol
        amount_sold_raw, amount_bought_raw = amount0, -amount1
        sold_decimals, bought_decimals = token0_decimals, token1_decimals
        direction = "0_to_1"
    elif amount1 > 0 and amount0 < 0:
        token_sold, token_bought = token1_symbol, token0_symbol
        amount_sold_raw, amount_bought_raw = amount1, -amount0
        sold_decimals, bought_decimals = token1_decimals, token0_decimals
        direction = "1_to_0"
    else:
        token_sold, token_bought = token0_symbol, token1_symbol
        amount_sold_raw = abs(amount0)
        amount_bought_raw = abs(amount1)
        sold_decimals, bought_decimals = token0_decimals, token1_decimals
        direction = "unknown"

    return {
        "chain": chain,
        "chain_id": chain_id,
        "protocol": "uniswap_v3",
        "pool_address": to_checksum_address(pool_address),
        "block_number": int(raw["blockNumber"], 16),
        "log_index": int(raw["logIndex"], 16),
        "tx_hash": raw["transactionHash"],
        "trader": trader,
        "sender": sender,
        "token0_symbol": token0_symbol,
        "token1_symbol": token1_symbol,
        "token0_decimals": token0_decimals,
        "token1_decimals": token1_decimals,
        "amount0_raw": str(amount0),
        "amount1_raw": str(amount1),
        "token_sold": token_sold,
        "token_bought": token_bought,
        "amount_sold_raw": str(amount_sold_raw),
        "amount_bought_raw": str(amount_bought_raw),
        "sold_decimals": sold_decimals,
        "bought_decimals": bought_decimals,
        "direction": direction,
    }
