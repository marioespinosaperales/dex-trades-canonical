# Orderflow / MEV-lite research (atomic study)

Hypothesis-driven note for market-structure and networking-adjacent product questions.
Runnable offline via `make research` → `artifacts/research_orderflow.md`.

## Hypothesis

Multi-swap and sandwich-proxy structure inflates **total** volume beyond what dust /
self-churn filters remove. Noise labels alone understate toxic or contended orderflow.

## Data and method

- Grain: one Swap log row (`chain`, `tx_hash`, `log_index`)
- Auditable proxies (retained flags, not deletes):
  - `is_multi_swap_tx` — ≥2 swaps in the same transaction
  - `is_same_block_pool_burst` — ≥2 swaps on the same pool in the same block from ≥2 txs
  - `is_potential_sandwich_leg` — A→B→A direction pattern by `log_index` in the same block+pool
  - `is_orderflow_interesting` — union of the above (plus self-churn)
- Compare volume shares: clean vs interesting vs sandwich-proxy
- Reproduce: `uv run python -m dex_trades.research --no-augment` (golden fixture) or `make research`

## Evidence

See latest `artifacts/research_orderflow.md` (generated). Golden fixture includes an
explicit A→B→A sandwich-shaped triple so the heuristic is unit-tested.

## Limitations

- No mempool, builder IDs, relays, or millisecond timing — these are **proxies**, not sandwich proof
- Routers / aggregators create multi-swap txs without MEV
- Incidence rates on fixtures ≠ mainnet incidence

## Product implications

1. **Analytics:** expose retained orderflow flags so consumers can split clean vs interesting volume
2. **Networking / data acceleration:** the next measurements that matter are inclusion delay and
   propagation asymmetry for contended pool/block flow — not just trade counts
3. **Next measurements (path to deeper MEV research):** builder/relay joins, mempool arrival vs
   on-chain inclusion, public Xatu-style latency datasets

## Related code

- Rubric: `src/dex_trades/evals/labels.py`
- Warehouse: `dbt/models/intermediate/int_dex_trades.sql`, `mart_orderflow_signals.sql`
- ML companion: `uv run python -m dex_trades.ml --target orderflow`
