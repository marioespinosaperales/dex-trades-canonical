"""Uniswap V2 Swap event decode."""

from __future__ import annotations

from typing import Any

from eth_abi import decode
from eth_utils import event_abi_to_log_topic, to_checksum_address

SWAP_ABI: dict[str, Any] = {
    "anonymous": False,
    "inputs": [
        {"indexed": True, "name": "sender", "type": "address"},
        {"indexed": False, "name": "amount0In", "type": "uint256"},
        {"indexed": False, "name": "amount1In", "type": "uint256"},
        {"indexed": False, "name": "amount0Out", "type": "uint256"},
        {"indexed": False, "name": "amount1Out", "type": "uint256"},
        {"indexed": True, "name": "to", "type": "address"},
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
    """Decode a V2 Swap log into a flat raw-swap row."""
    topics = raw.get("topics") or []
    if not topics or topics[0].lower() != SWAP_TOPIC0:
        return None

    data_hex = raw.get("data", "0x")
    data_bytes = bytes.fromhex(data_hex[2:] if data_hex.startswith("0x") else data_hex)
    amount0_in, amount1_in, amount0_out, amount1_out = decode(
        ["uint256", "uint256", "uint256", "uint256"], data_bytes
    )
    sender = _topic_address(topics[1])
    trader = _topic_address(topics[2])

    # Direction: token sold is the one with positive In.
    if amount0_in > 0 and amount1_out > 0:
        token_sold, token_bought = token0_symbol, token1_symbol
        amount_sold_raw, amount_bought_raw = amount0_in, amount1_out
        sold_decimals, bought_decimals = token0_decimals, token1_decimals
        direction = "0_to_1"
        amount0_raw = -int(amount0_in)  # pool perspective: negative = out of trader into pool
        amount1_raw = int(amount1_out)
    elif amount1_in > 0 and amount0_out > 0:
        token_sold, token_bought = token1_symbol, token0_symbol
        amount_sold_raw, amount_bought_raw = amount1_in, amount0_out
        sold_decimals, bought_decimals = token1_decimals, token0_decimals
        direction = "1_to_0"
        amount0_raw = int(amount0_out)
        amount1_raw = -int(amount1_in)
    else:
        # Exotic / flash-style; keep raw but mark unknown direction
        token_sold, token_bought = token0_symbol, token1_symbol
        amount_sold_raw = amount0_in or amount1_in
        amount_bought_raw = amount0_out or amount1_out
        sold_decimals, bought_decimals = token0_decimals, token1_decimals
        direction = "unknown"
        amount0_raw = int(amount0_out) - int(amount0_in)
        amount1_raw = int(amount1_out) - int(amount1_in)

    return {
        "chain": chain,
        "chain_id": chain_id,
        "protocol": "uniswap_v2",
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
        "amount0_raw": str(amount0_raw),
        "amount1_raw": str(amount1_raw),
        "token_sold": token_sold,
        "token_bought": token_bought,
        "amount_sold_raw": str(amount_sold_raw),
        "amount_bought_raw": str(amount_bought_raw),
        "sold_decimals": sold_decimals,
        "bought_decimals": bought_decimals,
        "direction": direction,
    }
