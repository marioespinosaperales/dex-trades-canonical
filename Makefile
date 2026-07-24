# Requires make (on Windows: Git Bash, or `winget install GnuWin32.Make`).

.PHONY: install lint test backfill warehouse transform snapshot pipeline eval docker-build docker-pipeline docker-test

install:
	uv sync

lint:
	uv run ruff check .

test:
	uv run pytest

backfill:
	uv run python -m dex_trades.run

warehouse:
	uv run python -m dex_trades.build_warehouse

transform: warehouse
	DEX_DUCKDB_PATH=warehouse/dex.duckdb uv run dbt build --project-dir dbt --profiles-dir dbt

snapshot:
	uv run python -m dex_trades.export_snapshot

pipeline: backfill transform snapshot

eval:
	uv run python -m dex_trades.evals

docker-build:
	docker compose build

docker-pipeline:
	docker compose run --rm pipeline

docker-test:
	docker compose run --rm test
