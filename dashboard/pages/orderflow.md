---
title: Orderflow / MEV-lite
---

Structural orderflow proxies on canonical `dex.trades`, retained as filterable flags
(not deletes). Rates and inference live on [Quality benchmarks](/benchmarks).

## Rates by chain × protocol

```sql signals
select
    chain,
    protocol,
    trade_count,
    interesting_trades,
    sandwich_proxy_trades,
    multi_swap_trades,
    burst_trades,
    clean_trades,
    interesting_trade_rate,
    interesting_volume_share,
    interesting_volume_quote_stable,
    clean_volume_quote_stable,
    total_volume_quote_stable
from dex.orderflow_signals
order by interesting_volume_quote_stable desc nulls last
```

```sql signal_totals
select
    sum(trade_count) as trades,
    sum(interesting_trades) as interesting_trades,
    sum(sandwich_proxy_trades) as sandwich_proxy_trades,
    sum(interesting_volume_quote_stable) as interesting_volume,
    sum(clean_volume_quote_stable) as clean_volume,
    sum(total_volume_quote_stable) as total_volume
from dex.orderflow_signals
```

<BigValue data={signal_totals} value=trades title="Trades" />
<BigValue data={signal_totals} value=interesting_trades title="Interesting" />
<BigValue data={signal_totals} value=sandwich_proxy_trades title="Sandwich proxy" />
<BigValue data={signal_totals} value=interesting_volume title="Interesting vol" fmt=usd />

<DataTable data={signals}>
  <Column id=chain />
  <Column id=protocol />
  <Column id=trade_count title="Trades" />
  <Column id=interesting_trades title="Interesting" />
  <Column id=interesting_trade_rate title="Interesting rate" fmt=pct />
  <Column id=sandwich_proxy_trades title="Sandwich proxy" />
  <Column id=multi_swap_trades title="Multi-swap" />
  <Column id=burst_trades title="Block burst" />
  <Column id=interesting_volume_quote_stable title="Interesting vol" fmt=usd />
  <Column id=clean_volume_quote_stable title="Clean vol" fmt=usd />
  <Column id=interesting_volume_share title="Interesting vol share" fmt=pct />
</DataTable>

<BarChart
  data={signals}
  x=protocol
  y=interesting_trade_rate
  series=chain
  title="Interesting trade rate by protocol × chain"
  yFmt=pct
/>

## Flagged trades

Rows with at least one orderflow proxy. Addresses and block numbers follow the
configured pools; demo snapshots use deterministic hashes until a warehouse export.

```sql interesting
select
    chain,
    protocol,
    pool,
    pool_address,
    cast(block_number as varchar) as block_number,
    tx_hash,
    log_index,
    trader,
    volume_quote_stable,
    price_token1_per_token0,
    fee_tier,
    case when is_multi_swap_tx then 1 else 0 end as multi_swap,
    case when is_same_block_pool_burst then 1 else 0 end as burst,
    case when is_potential_sandwich_leg then 1 else 0 end as sandwich_proxy,
    fee_recipient,
    direction
from dex.orderflow_trades
order by chain, cast(block_number as bigint) desc, log_index
```

<DataTable data={interesting} rows=30>
  <Column id=chain />
  <Column id=protocol />
  <Column id=pool />
  <Column id=pool_address title="Pool" />
  <Column id=block_number title="Block" />
  <Column id=tx_hash title="Tx" />
  <Column id=log_index title="Log" />
  <Column id=volume_quote_stable title="Vol $" fmt=usd />
  <Column id=price_token1_per_token0 title="Price t1/t0" fmt=num6 />
  <Column id=fee_tier title="Fee" />
  <Column id=multi_swap title="Multi" />
  <Column id=burst title="Burst" />
  <Column id=sandwich_proxy title="Sandwich" />
  <Column id=fee_recipient title="feeRecipient" />
  <Column id=direction />
</DataTable>

## Definitions

| Flag | Rule |
|---|---|
| Multi-swap | ≥2 swaps in one transaction |
| Burst | ≥2 txs on the same pool in the same block |
| Sandwich proxy | A→B→A direction pattern by `log_index` in block+pool |
| feeRecipient | Block builder/proposer address when blocks are enriched |

These are auditable heuristics for volume hygiene and contention screens. They are
not sandwich proof and do not use mempool or relay timing. Natural next metrics:
inclusion delay and propagation asymmetry on contended pool/block flow.
