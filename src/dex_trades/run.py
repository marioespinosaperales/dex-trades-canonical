"""CLI entrypoint: multi-chain Swap backfill.

    uv run python -m dex_trades.run
"""

from __future__ import annotations

import logging
import sys

from dex_trades.index.backfill import backfill_pool
from dex_trades.rpc.client import RpcClient
from dex_trades.settings import get_settings, rpc_url_for_chain

logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = get_settings()
    pipeline = settings.pipeline

    pools = [p for p in settings.pools if p.enabled]
    if not pools:
        logger.error("No enabled pools in config/pools.yaml")
        return 1

    # One RpcClient per chain (reuse across pools on the same chain).
    clients: dict[str, RpcClient] = {}
    for chain in settings.chains:
        url = rpc_url_for_chain(chain, settings)
        clients[chain.name] = RpcClient(
            url,
            timeout_seconds=pipeline.rpc_timeout_seconds,
            max_retries=pipeline.rpc_max_retries,
            backoff_seconds=pipeline.rpc_backoff_seconds,
        )

    for pool in pools:
        chain = settings.chain_by_name(pool.chain)
        rpc = clients[chain.name]
        stats = backfill_pool(rpc, pool, chain, pipeline)
        logger.info("Backfill %s: %s", pool.name, stats)

    return 0


if __name__ == "__main__":
    sys.exit(main())
