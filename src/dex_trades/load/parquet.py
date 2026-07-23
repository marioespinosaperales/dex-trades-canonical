"""Hive-partitioned Parquet swap store."""

from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path

import pandas as pd
from eth_utils import to_checksum_address

logger = logging.getLogger(__name__)


def write_swaps(
    frame: pd.DataFrame,
    data_dir: Path,
    chain: str,
    pool_address: str,
    *,
    ingested_date: dt.date | None = None,
) -> Path:
    """Write under data/swaps/chain=<c>/pool=<addr>/ingested_date=YYYY-MM-DD/."""
    if frame.empty:
        raise ValueError("Cannot write empty swap frame")

    ingested_date = ingested_date or dt.datetime.now(dt.UTC).date()
    addr = to_checksum_address(pool_address)
    partition = (
        data_dir
        / "swaps"
        / f"chain={chain}"
        / f"pool={addr}"
        / f"ingested_date={ingested_date.isoformat()}"
    )
    partition.mkdir(parents=True, exist_ok=True)
    min_block = int(frame["block_number"].min())
    max_block = int(frame["block_number"].max())
    path = partition / f"blocks_{min_block}_{max_block}.parquet"
    frame.to_parquet(path, index=False)
    logger.info("Wrote %d swaps to %s", len(frame), path)
    return path
