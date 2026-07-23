# dex-trades-canonical — Project conventions

Turn Uniswap V2/V3 Swap logs on Ethereum and Base into a canonical `dex.trades`
model (dbt), with dust / self-churn noise flags and interview-ready methodology.

## Architecture

- `src/dex_trades/rpc/` — JSON-RPC client (Alchemy): getLogs, blockNumber
- `src/dex_trades/index/` — V2 + V3 Swap decode, chunked multi-chain backfill
- `src/dex_trades/load/` — Parquet Hive store + DuckDB raw loader + checkpoints
- `dbt/` — staging → `int_dex_trades` (canonical) → volume marts
- `dashboard/` — Evidence over exported marts snapshot
- `config/` — chains + pools + pipeline params; secrets ONLY via `DEX_` env vars

## Rules

- Python 3.12, type hints on public signatures, functions over classes.
- New config → YAML in `config/` + pydantic model in `settings.py`. Never hardcode.
- Data and logs are NEVER committed (except `dashboard/sources/dex/dex_marts.duckdb`).
- Canonical trade semantics and noise flags live in dbt, not in the indexer.
- Tests use fixtures of real Swap log payloads; mock HTTP with respx.
- English only in all committed text.

## Commands

- `make backfill` — index configured lookback per pool/chain
- `make transform` — DuckDB load + `dbt build`
- `make snapshot` — export marts for Evidence
- `make lint && make test` — required before every commit
