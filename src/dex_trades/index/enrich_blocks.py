"""Enrich unique swap blocks with feeRecipient (PBS / builder proxy)."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from dex_trades.rpc.client import RpcClient

logger = logging.getLogger(__name__)


def _fee_recipient(block: dict) -> str | None:
    raw = block.get("feeRecipient") or block.get("miner")
    if raw is None:
        return None
    return str(raw).lower()


def enrich_blocks_for_swaps(
    rpc: RpcClient,
    *,
    chain: str,
    chain_id: int,
    data_dir: Path,
    block_numbers: list[int],
) -> int:
    """Fetch and persist block fee recipients. Returns rows written."""
    unique = sorted({int(b) for b in block_numbers if b is not None})
    if not unique:
        return 0

    rows = []
    for bn in unique:
        block = rpc.get_block(bn)
        rows.append(
            {
                "chain": chain,
                "chain_id": chain_id,
                "block_number": bn,
                "fee_recipient": _fee_recipient(block),
                "block_hash": block.get("hash"),
                "timestamp": int(block["timestamp"], 16) if block.get("timestamp") else None,
            }
        )

    frame = pd.DataFrame(rows)
    out_dir = data_dir / "blocks" / f"chain={chain}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "blocks.parquet"
    table = pa.Table.from_pandas(frame, preserve_index=False)
    pq.write_table(table, out_path)
    logger.info("Wrote %d block enrichments → %s", len(frame), out_path)
    return len(frame)
