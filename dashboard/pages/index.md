---
title: Canonical dex.trades
---

Uniswap + native DEX Swap logs on **Ethereum, Base, Arbitrum, Avalanche**
(Camelot / Aerodrome / Pharaoh) → semantic `dex.trades` with dust and same-tx self-churn flags.

Noise rows are **flagged, not deleted**. Filter on `is_clean` for volume (USDC-as-quote heuristic).

Source: [dex-trades-canonical](https://github.com/marioespinosaperales/dex-trades-canonical).

Orderflow / MEV-lite proxies (multi-swap, burst, sandwich-leg, `fee_recipient`): see the
[Orderflow / MEV-lite](/orderflow) page.

## Volume by protocol

Trade counts **and** stable-quoted volume (`volume_quote_stable`) per chain × protocol.

```sql volume
select
    chain,
    protocol,
    trade_count,
    clean_trade_count,
    dust_trade_count,
    self_churn_trade_count,
    volume_quote_stable,
    clean_volume_quote_stable
from dex.volume_by_protocol
order by clean_volume_quote_stable desc nulls last
```

```sql volume_totals
select
    sum(trade_count) as trades,
    sum(clean_trade_count) as clean_trades,
    sum(volume_quote_stable) as volume_stable,
    sum(clean_volume_quote_stable) as clean_volume_stable
from dex.volume_by_protocol
```

<BigValue data={volume_totals} value=trades title="Trades" />
<BigValue data={volume_totals} value=clean_trades title="Clean trades" />
<BigValue data={volume_totals} value=volume_stable title="Volume (stable)" fmt=usd />
<BigValue data={volume_totals} value=clean_volume_stable title="Clean volume" fmt=usd />

<DataTable data={volume}>
  <Column id=chain />
  <Column id=protocol />
  <Column id=trade_count title="Trades" />
  <Column id=clean_trade_count title="Clean trades" />
  <Column id=volume_quote_stable title="Volume (stable)" fmt=usd />
  <Column id=clean_volume_quote_stable title="Clean volume" fmt=usd />
  <Column id=dust_trade_count title="Dust" />
  <Column id=self_churn_trade_count title="Self-churn" />
</DataTable>

```sql by_protocol
select * from dex.noise_summary order by chain, protocol
```

<BarChart
  data={by_protocol}
  x=protocol
  y=clean_trades
  series=chain
  title="Clean trades by protocol"
/>

<BarChart
  data={by_protocol}
  x=protocol
  y=clean_volume_stable
  series=chain
  title="Clean volume by protocol (stable / USDC)"
  yFmt=usd
/>

## dex.trades

Same grain as Allium-style `SELECT * FROM dex.trades` — one row per Swap log
`(chain, tx_hash, log_index)`. Dimensions: **chain × protocol × pool** (e.g. `USDC/WETH`).

```sql trades
select *
from dex.trades
```

```sql trades_stats
select
    count(*) as trade_rows,
    count(*) filter (where is_clean) as clean_rows,
    count(*) filter (where is_dust) as dust_rows,
    count(*) filter (where is_self_churn) as self_churn_rows,
    sum(volume_quote_stable) as volume_stable,
    sum(volume_quote_stable) filter (where is_clean) as clean_volume_stable
from dex.trades
```

<BigValue data={trades_stats} value=trade_rows title="Rows" />
<BigValue data={trades_stats} value=clean_rows title="Clean" />
<BigValue data={trades_stats} value=clean_volume_stable title="Clean volume" fmt=usd />
<BigValue data={trades_stats} value=dust_rows title="Dust" />
<BigValue data={trades_stats} value=self_churn_rows title="Self-churn" />

<DataTable data={trades} rows=25 search=true>
  <Column id=chain />
  <Column id=protocol />
  <Column id=pool title="Pool" />
  <Column id=block_number title="Block" />
  <Column id=tx_hash title="Tx" />
  <Column id=log_index title="Log #" />
  <Column id=trader />
  <Column id=token_sold title="Sold" />
  <Column id=token_bought title="Bought" />
  <Column id=amount_sold title="Amt sold" fmt=num4 />
  <Column id=amount_bought title="Amt bought" fmt=num4 />
  <Column id=volume_quote_stable title="Vol (stable)" fmt=usd />
  <Column id=price_token1_per_token0 title="Price t1/t0" fmt=num6 />
  <Column id=is_dust title="Dust" />
  <Column id=is_self_churn title="Self-churn" />
  <Column id=is_clean title="Clean" />
  <Column id=direction />
  <Column id=pool_address title="Pool address" />
  <Column id=fee_tier title="Fee" />
</DataTable>
