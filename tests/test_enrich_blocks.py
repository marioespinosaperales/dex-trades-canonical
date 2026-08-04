"""Block feeRecipient enrichment tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pyarrow.parquet as pq
import respx

from dex_trades.index.enrich_blocks import enrich_blocks_for_swaps
from dex_trades.rpc.client import RpcClient


@respx.mock
def test_get_block_returns_fee_recipient():
    respx.post("https://example.rpc").mock(
        return_value=httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "number": "0x10",
                    "feeRecipient": "0xBuIlDeR",
                    "hash": "0xabc",
                    "timestamp": "0x64",
                },
            },
        )
    )
    client = RpcClient("https://example.rpc", max_retries=0)
    block = client.get_block(16)
    assert block["feeRecipient"] == "0xBuIlDeR"


def test_enrich_blocks_writes_parquet(tmp_path: Path):
    rpc = MagicMock()
    rpc.get_block.return_value = {
        "feeRecipient": "0xBuilderABC",
        "hash": "0xdead",
        "timestamp": "0x65",
    }
    n = enrich_blocks_for_swaps(
        rpc,
        chain="ethereum",
        chain_id=1,
        data_dir=tmp_path,
        block_numbers=[100, 100, 101],
    )
    assert n == 2
    out = tmp_path / "blocks" / "chain=ethereum" / "blocks.parquet"
    assert out.exists()
    table = pq.read_table(out)
    frame = table.to_pandas()
    assert set(frame["block_number"]) == {100, 101}
    assert (frame["fee_recipient"] == "0xbuilderabc").all()
    assert rpc.get_block.call_count == 2
