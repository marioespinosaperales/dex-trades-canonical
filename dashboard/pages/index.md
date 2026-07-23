---
title: Canonical dex.trades
---

Uniswap + native DEX Swap logs on **Ethereum, Base, Arbitrum, Avalanche**
(Camelot / Aerodrome / Pharaoh) → semantic `dex.trades` with dust and same-tx self-churn flags.

Noise rows are **flagged, not deleted**. Filter on `is_clean` for volume.

Source: [dex-trades-canonical](https://github.com/marioespinosaperales/dex-trades-canonical).

```sql volume
select *
from dex.volume_by_protocol
order by chain, protocol
```

<DataTable data={volume}>
  <Column id=chain />
  <Column id=protocol />
  <Column id=trade_count title="Trades" />
  <Column id=clean_trade_count title="Clean" />
  <Column id=dust_trade_count title="Dust" />
  <Column id=self_churn_trade_count title="Self-churn" />
  <Column id=clean_volume_quote_stable title="Clean volume (stable)" fmt=num2 />
</DataTable>

```sql noise
select * from dex.noise_summary order by chain, protocol
```

<BarChart
  data={noise}
  x=protocol
  y=clean_trades
  series=chain
  title="Clean trades by protocol"
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
    count(*) filter (where is_self_churn) as self_churn_rows
from dex.trades
```

<BigValue data={trades_stats} value=trade_rows title="Rows" />
<BigValue data={trades_stats} value=clean_rows title="Clean" />
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
  <Column id=volume_quote_stable title="Vol (stable)" fmt=num2 />
  <Column id=price_token1_per_token0 title="Price t1/t0" fmt=num6 />
  <Column id=is_dust title="Dust" />
  <Column id=is_self_churn title="Self-churn" />
  <Column id=is_clean title="Clean" />
  <Column id=direction />
  <Column id=pool_address title="Pool address" />
  <Column id=fee_tier title="Fee" />
</DataTable>
