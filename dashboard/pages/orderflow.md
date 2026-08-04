---
title: Orderflow / MEV-lite
---

Hypothesis-driven **orderflow proxies** on canonical `dex.trades`.

These flags are **auditable heuristics**, not sandwich proof. See
[Benchmarks](/benchmarks) for the exact rates we calculate, and
[RESEARCH.md](https://github.com/marioespinosaperales/dex-trades-canonical/blob/main/RESEARCH.md).

## Signal rates by chain × protocol

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
  title="Interesting trade rate by protocol"
  yFmt=pct
/>

## Interesting trades (sample)

Booleans cast to 0/1 for stable Evidence tables.

```sql interesting
select
    chain,
    protocol,
    pool,
    block_number,
    tx_hash,
    log_index,
    volume_quote_stable,
    case when is_multi_swap_tx then 1 else 0 end as multi_swap,
    case when is_same_block_pool_burst then 1 else 0 end as burst,
    case when is_potential_sandwich_leg then 1 else 0 end as sandwich_proxy,
    fee_recipient,
    direction
from dex.orderflow_trades
```

<DataTable data={interesting} rows=25>
  <Column id=chain />
  <Column id=protocol />
  <Column id=pool />
  <Column id=block_number title="Block" />
  <Column id=tx_hash title="Tx" />
  <Column id=log_index title="Log #" />
  <Column id=volume_quote_stable title="Vol (stable)" fmt=usd />
  <Column id=multi_swap title="Multi-swap" />
  <Column id=burst title="Burst" />
  <Column id=sandwich_proxy title="Sandwich proxy" />
  <Column id=fee_recipient title="Fee recipient" />
  <Column id=direction />
</DataTable>

## How to read this

- **Multi-swap:** ≥2 swaps in one tx (routers and MEV both show up)
- **Burst:** ≥2 txs hitting the same pool in the same block
- **Sandwich proxy:** A→B→A direction pattern by log index in a block+pool
- **Fee recipient:** block `feeRecipient` when enriched (PBS / builder proxy)

Next measurements: inclusion delay and propagation asymmetry for contended pool/block flow.
