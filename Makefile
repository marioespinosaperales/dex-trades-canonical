# Requires make (on Windows: Git Bash, or `winget install GnuWin32.Make`).

.PHONY: install lint test backfill enrich-blocks warehouse transform snapshot seed-dashboard pipeline eval research ml docker-build docker-pipeline docker-test

install:
	uv sync

lint:
	uv run ruff check .

test:
	uv run pytest

backfill:
	uv run python -m dex_trades.run

enrich-blocks:
	uv run python -m dex_trades.index.enrich_blocks_cli

warehouse:
	uv run python -m dex_trades.build_warehouse

transform: warehouse
	DEX_DUCKDB_PATH=warehouse/dex.duckdb uv run dbt build --project-dir dbt --profiles-dir dbt

snapshot:
	uv run python -m dex_trades.export_snapshot

seed-dashboard:
	uv run python -m dex_trades.seed_dashboard_snapshot

pipeline: backfill enrich-blocks transform snapshot

eval:
	uv run python -m dex_trades.evals

research:
	uv run python -m dex_trades.research

ml:
	uv run python -m dex_trades.ml
	uv run python -m dex_trades.ml --target orderflow

docker-build:
	docker compose build

docker-pipeline:
	docker compose run --rm pipeline

docker-test:
	docker compose run --rm test
