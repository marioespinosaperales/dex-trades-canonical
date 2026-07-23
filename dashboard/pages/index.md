---
title: Canonical dex.trades
---

Uniswap V2/V3 Swap logs on **Ethereum + Base** → semantic `dex.trades` with dust and same-tx self-churn flags.

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
