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
- PBS / builder proxy: `fee_recipient` from `eth_getBlockByNumber` (`make enrich-blocks`)
  left-joined onto each trade (null when blocks are not enriched)
- Compare volume shares: clean vs interesting vs sandwich-proxy
- Reproduce: `uv run python -m dex_trades.research --no-augment` (golden fixture) or `make research`

## Evidence

See latest `artifacts/research_orderflow.md` (generated). Golden fixture includes an
explicit A→B→A sandwich-shaped triple so the heuristic is unit-tested.

**Dashboard (live):**
[Benchmarks](https://dex-trades-canonical.vercel.app/benchmarks) ·
[Orderflow](https://dex-trades-canonical.vercel.app/orderflow)

Local: `npm run dev` under `dashboard/`. Seed without RPC:

```bash
make seed-dashboard   # → dashboard/sources/dex/dex_marts.duckdb
```

## Limitations

- No mempool, relays, or millisecond timing — orderflow flags are **proxies**, not sandwich proof
- `fee_recipient` is a PBS/builder **address proxy**, not a relay bid or bundle proof
- Routers / aggregators create multi-swap txs without MEV
- Incidence rates on fixtures ≠ mainnet incidence

## Product implications

1. **Analytics:** expose retained orderflow flags so consumers can split clean vs interesting volume
2. **PBS join:** `fee_recipient` lets you ask “does interesting flow concentrate under certain builders?”
3. **Networking / data acceleration:** the next measurements that matter are inclusion delay and
   propagation asymmetry for contended pool/block flow — not just trade counts
4. **Next measurements:** relay/builder catalogs, mempool arrival vs on-chain inclusion,
   public Xatu-style latency datasets

## Related code

- Rubric: `src/dex_trades/evals/labels.py`
- Warehouse: `dbt/models/intermediate/int_dex_trades.sql`, `mart_orderflow_signals.sql`
- Block enrich: `src/dex_trades/index/enrich_blocks.py` (`make enrich-blocks`)
- ML companion: `uv run python -m dex_trades.ml --target orderflow`
- Evidence: `dashboard/pages/orderflow.md`
