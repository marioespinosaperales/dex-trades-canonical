"""CLI: enrich unique swap blocks with feeRecipient (PBS / builder proxy).

    uv run python -m dex_trades.index.enrich_blocks_cli
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pyarrow.parquet as pq

from dex_trades.index.enrich_blocks import enrich_blocks_for_swaps
from dex_trades.rpc.client import RpcClient
from dex_trades.settings import get_settings, rpc_url_for_chain

logger = logging.getLogger(__name__)


def _block_numbers_from_swaps(data_dir: Path, chain: str) -> list[int]:
    paths = list(data_dir.glob(f"swaps/chain={chain}/pool=*/ingested_date=*/*.parquet"))
    if not paths:
        return []
    blocks: set[int] = set()
    for path in paths:
        table = pq.read_table(path, columns=["block_number"])
        for val in table.column("block_number").to_pylist():
            if val is not None:
                blocks.add(int(val))
    return sorted(blocks)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = get_settings()
    pipeline = settings.pipeline
    data_dir = Path(pipeline.data_dir)
    total = 0

    for chain in settings.chains:
        blocks = _block_numbers_from_swaps(data_dir, chain.name)
        if not blocks:
            logger.info("No swap parquet for chain=%s; skip enrich", chain.name)
            continue
        url = rpc_url_for_chain(chain, settings)
        rpc = RpcClient(
            url,
            timeout_seconds=pipeline.rpc_timeout_seconds,
            max_retries=pipeline.rpc_max_retries,
            backoff_seconds=pipeline.rpc_backoff_seconds,
        )
        written = enrich_blocks_for_swaps(
            rpc,
            chain=chain.name,
            chain_id=chain.chain_id,
            data_dir=data_dir,
            block_numbers=blocks,
        )
        logger.info("Enriched %d blocks for %s", written, chain.name)
        total += written

    if total == 0:
        logger.warning(
            "No blocks enriched. Run backfill first, or seed Evidence via "
            "`python -m dex_trades.seed_dashboard_snapshot`."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
