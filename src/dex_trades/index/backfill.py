"""Chunked Swap event backfill via eth_getLogs (V2 + V3, multi-chain)."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from eth_utils import to_checksum_address

from dex_trades.index import v2_swap, v3_swap
from dex_trades.load.checkpoint import load_checkpoint, save_checkpoint
from dex_trades.load.parquet import write_swaps
from dex_trades.rpc.client import RpcClient
from dex_trades.settings import ChainConfig, PipelineConfig, PoolConfig

logger = logging.getLogger(__name__)


def resolve_range(
    rpc: RpcClient,
    pipeline: PipelineConfig,
    address: str,
    checkpoint_dir: Path,
    confirmations: int,
) -> tuple[int, int]:
    """Return (from_block, to_block_inclusive) for this run."""
    tip = rpc.block_number()
    to_block = tip - confirmations
    if to_block < 0:
        raise RuntimeError("Chain tip is below confirmation depth")

    checkpoint = load_checkpoint(checkpoint_dir, address)
    if checkpoint is not None:
        from_block = checkpoint + 1
    else:
        from_block = max(0, to_block - pipeline.lookback_blocks + 1)

    return from_block, to_block


def _decode(raw: dict, pool: PoolConfig, chain: ChainConfig) -> dict | None:
    kwargs = {
        "chain": chain.name,
        "chain_id": chain.chain_id,
        "pool_address": pool.address,
        "token0_symbol": pool.token0_symbol,
        "token1_symbol": pool.token1_symbol,
        "token0_decimals": pool.token0_decimals,
        "token1_decimals": pool.token1_decimals,
    }
    if pool.protocol == "uniswap_v2":
        row = v2_swap.decode_swap(raw, **kwargs)
    elif pool.protocol == "uniswap_v3":
        row = v3_swap.decode_swap(raw, **kwargs)
    else:
        raise ValueError(f"Unsupported protocol: {pool.protocol}")
    if row is None:
        return None
    row["quote_token"] = pool.quote_token
    row["quote_is_stable"] = pool.quote_is_stable
    row["fee_tier"] = pool.fee_tier
    return row


def _topic0(protocol: str) -> str:
    if protocol == "uniswap_v2":
        return v2_swap.topic0()
    if protocol == "uniswap_v3":
        return v3_swap.topic0()
    raise ValueError(f"Unsupported protocol: {protocol}")


def backfill_pool(
    rpc: RpcClient,
    pool: PoolConfig,
    chain: ChainConfig,
    pipeline: PipelineConfig,
) -> dict[str, int | str]:
    """Index Swap events for one pool over the resolved window."""
    address = to_checksum_address(pool.address)
    confirmations = chain.confirmations or pipeline.confirmations
    from_block, to_block = resolve_range(
        rpc, pipeline, address, pipeline.checkpoint_dir, confirmations
    )

    if from_block > to_block:
        logger.info(
            "%s already caught up (checkpoint >= tip-%d)", pool.name, confirmations
        )
        return {"events": 0, "from_block": from_block, "to_block": to_block, "chunks": 0}

    topic = _topic0(pool.protocol)
    total_events = 0
    chunks = 0
    cursor = from_block

    logger.info(
        "Backfilling %s [%s/%s] (%s) blocks %d..%d (chunk=%d)",
        pool.name,
        chain.name,
        pool.protocol,
        address,
        from_block,
        to_block,
        pipeline.chunk_size,
    )

    while cursor <= to_block:
        end = min(cursor + pipeline.chunk_size - 1, to_block)
        raw_logs = rpc.get_logs(
            address=address,
            topics=[topic],
            from_block=cursor,
            to_block=end,
        )
        rows = []
        for raw in raw_logs:
            decoded = _decode(raw, pool, chain)
            if decoded is not None:
                rows.append(decoded)

        if rows:
            frame = pd.DataFrame(rows)
            write_swaps(frame, pipeline.data_dir, chain.name, address)
            total_events += len(rows)

        save_checkpoint(pipeline.checkpoint_dir, address, end)
        chunks += 1
        logger.info(
            "  chunk %d..%d: %d swaps (total=%d)", cursor, end, len(rows), total_events
        )
        cursor = end + 1

    return {
        "events": total_events,
        "from_block": from_block,
        "to_block": to_block,
        "chunks": chunks,
        "protocol": pool.protocol,
        "chain": chain.name,
    }
