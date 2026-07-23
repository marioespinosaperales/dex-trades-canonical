"""RPC client tests with mocked HTTP."""

from __future__ import annotations

import httpx
import respx

from dex_trades.rpc.client import RpcClient


@respx.mock
def test_block_number():
    route = respx.post("https://example.rpc").mock(
        return_value=httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": "0x10"})
    )
    client = RpcClient("https://example.rpc", max_retries=0)
    assert client.block_number() == 16
    assert route.called


@respx.mock
def test_get_logs():
    respx.post("https://example.rpc").mock(
        return_value=httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": 1, "result": [{"blockNumber": "0x1"}]},
        )
    )
    client = RpcClient("https://example.rpc", max_retries=0)
    logs = client.get_logs(address="0xabc", from_block=1, to_block=10)
    assert len(logs) == 1
