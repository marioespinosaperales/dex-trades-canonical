# dex-trades-canonical — Project conventions

Turn Uniswap V2/V3 Swap logs into a canonical `dex.trades` model (dbt), with dust /
self-churn noise flags and a QC scorecard for label impact.
Portfolio story: **labeling rubric + metric reliability** (sibling: crypto contracts, lp ground-truth).

## Architecture

- `src/dex_trades/rpc/` — JSON-RPC client (Alchemy): getLogs, blockNumber
- `src/dex_trades/index/` — V2 + V3 Swap decode, chunked multi-chain backfill
- `src/dex_trades/load/` — Parquet Hive store + DuckDB raw loader + checkpoints
- `src/dex_trades/evals/` — Python rubric (`labels.py`) + QC scorecard (distribution, volume impact, threshold sweep)
- `src/dex_trades/ml/` — rubric-vs-model noise + orderflow classifiers
- `src/dex_trades/research/` — hypothesis-driven orderflow / MEV-lite reports
- `RESEARCH.md` — atomic study writeup
- `dbt/` — staging → `int_dex_trades` (canonical) → volume marts
- `dashboard/` — Evidence over exported marts snapshot
- `config/` — chains + pools + pipeline params; secrets ONLY via `DEX_` env vars
- `Dockerfile` / `docker-compose.yml` — reproducible Linux pipeline + scorecard

## Git commits

- NEVER add `Co-authored-by: Cursor <cursoragent@cursor.com>`, `Made-with: Cursor`, or any Cursor/AI attribution trailer to commits or PRs.
- Commit messages must be authored only as the human repo owner (no Cursor co-author lines).
- Do not pass `--trailer` for Cursor attribution when committing.

## Rules

- Python 3.12, type hints on public signatures, functions over classes.
- New config → YAML in `config/` + pydantic model in `settings.py`. Never hardcode.
- Data, artifacts, and logs are NEVER committed (except `dashboard/sources/dex/dex_marts.duckdb`).
- Canonical trade semantics and noise flags live in dbt; the Python rubric in `evals/labels.py`
  must stay mirrored for tests/scorecard — update both together.
- Tests use fixtures of real Swap log payloads; mock HTTP with respx.
- English only in all committed text.

## Commands

- `make backfill` — index configured lookback per pool/chain
- `make transform` — DuckDB load + `dbt build`
- `make snapshot` — export marts for Evidence
- `make eval` — QC scorecard → `artifacts/qc_scorecard.md`
- `make research` — orderflow research report → `artifacts/research_orderflow.md`
- `make enrich-blocks` — PBS/builder `fee_recipient` for swap blocks
- `make seed-dashboard` — Evidence DuckDB without RPC (orderflow page)
- `make ml` — noise + orderflow ML reports
- `make docker-pipeline` / `make docker-test`
- `make lint && make test` — required before every commit
