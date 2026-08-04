---
title: Orderflow / MEV-lite
---

Hypothesis-driven **orderflow proxies** on canonical `dex.trades`.

These flags are **auditable heuristics**, not sandwich proof. No mempool or relay
timing is required for this view — see
[RESEARCH.md](https://github.com/marioespinosaperales/dex-trades-canonical/blob/main/RESEARCH.md).

## Signal rates by chain × protocol

```sql signals
select * from dex.orderflow_signals
```

```sql signal_totals
select
    sum(trade_count) as trades,
    sum(interesting_trades) as interesting_trades,
    sum(sandwich_proxy_trades) as sandwich_proxy_trades,
    sum(multi_swap_trades) as multi_swap_trades,
    sum(burst_trades) as burst_trades,
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
  title="Interesting trade rate by protocol"
  yFmt=pct
/>

<BarChart
  data={signals}
  x=protocol
  y=interesting_volume_quote_stable
  series=chain
  title="Interesting volume by protocol (stable)"
  yFmt=usd
/>

## Interesting trades (sample)

```sql interesting
select * from dex.orderflow_trades
```

<DataTable data={interesting} rows=25 search=true>
  <Column id=chain />
  <Column id=protocol />
  <Column id=pool />
  <Column id=block_number title="Block" />
  <Column id=tx_hash title="Tx" />
  <Column id=log_index title="Log #" />
  <Column id=volume_quote_stable title="Vol (stable)" fmt=usd />
  <Column id=is_multi_swap_tx title="Multi-swap" />
  <Column id=is_same_block_pool_burst title="Burst" />
  <Column id=is_potential_sandwich_leg title="Sandwich proxy" />
  <Column id=fee_recipient title="Fee recipient" />
  <Column id=direction />
</DataTable>

## How to read this

- **Multi-swap:** ≥2 swaps in one tx (routers and MEV both show up)
- **Burst:** ≥2 txs hitting the same pool in the same block
- **Sandwich proxy:** A→B→A direction pattern by log index in a block+pool
- **Fee recipient:** block `feeRecipient` when enriched (PBS / builder proxy)

Next measurements for a networking product: inclusion delay and propagation asymmetry
for contended pool/block flow.
