---
title: Benchmarks (what we measure)
---

Interview-facing **measurement card**: definitions, rates, and sensitivity.
Same numbers the QC scorecard (`make eval`) and orderflow research report compute.

```sql meta
select generated_at, source_kind, trade_count, notes, source
from dex.run_meta
```

<DataTable data={meta}>
  <Column id=source_kind title="Source kind" />
  <Column id=trade_count title="Trades" />
  <Column id=generated_at title="Generated at" />
  <Column id=notes title="Notes" />
</DataTable>

## Headline KPIs

```sql kpis
select metric, value, unit, definition
from dex.qc_kpis
order by
    case metric
        when 'trades' then 1
        when 'clean_rate' then 2
        when 'dust_rate' then 3
        when 'self_churn_rate' then 4
        when 'noise_share_of_volume' then 5
        when 'interesting_rate' then 6
        when 'interesting_volume_share' then 7
        when 'sandwich_proxy_rate' then 8
        when 'multi_swap_rate' then 9
        when 'burst_rate' then 10
        when 'total_volume_quote_stable' then 11
        when 'clean_volume_quote_stable' then 12
        else 99
    end
```

```sql kpi_rates
select metric, value
from dex.qc_kpis
where unit = 'share'
```

```sql kpi_count
select value as trades
from dex.qc_kpis
where metric = 'trades'
```

```sql kpi_clean
select value as clean_rate
from dex.qc_kpis
where metric = 'clean_rate'
```

```sql kpi_interesting
select value as interesting_rate
from dex.qc_kpis
where metric = 'interesting_rate'
```

```sql kpi_noise_vol
select value as noise_share_of_volume
from dex.qc_kpis
where metric = 'noise_share_of_volume'
```

<BigValue data={kpi_count} value=trades title="Trades scored" />
<BigValue data={kpi_clean} value=clean_rate title="Clean rate" fmt=pct />
<BigValue data={kpi_interesting} value=interesting_rate title="Interesting rate" fmt=pct />
<BigValue data={kpi_noise_vol} value=noise_share_of_volume title="Noise share of vol" fmt=pct />

<DataTable data={kpis}>
  <Column id=metric title="Metric" />
  <Column id=value title="Value" fmt=num4 />
  <Column id=unit title="Unit" />
  <Column id=definition title="Definition (what we calculate)" />
</DataTable>

<BarChart
  data={kpi_rates}
  x=metric
  y=value
  title="Rate benchmarks (shares)"
  yFmt=pct
/>

## Dust threshold sensitivity

How the `$ dust_usdc` cut moves clean rate and noise share of volume.
This is the QC **threshold sweep** from `make eval`.

```sql sweep
select
    dust_usdc_threshold,
    clean_rate,
    dust_rate,
    clean_volume_quote_stable,
    noise_share_of_volume
from dex.dust_threshold_sweep
order by dust_usdc_threshold
```

<LineChart
  data={sweep}
  x=dust_usdc_threshold
  y=clean_rate
  title="Clean rate vs dust USDC threshold"
  yFmt=pct
/>

<LineChart
  data={sweep}
  x=dust_usdc_threshold
  y=noise_share_of_volume
  title="Noise share of volume vs dust threshold"
  yFmt=pct
/>

<DataTable data={sweep}>
  <Column id=dust_usdc_threshold title="Dust USDC $" fmt=num1 />
  <Column id=clean_rate title="Clean rate" fmt=pct />
  <Column id=dust_rate title="Dust rate" fmt=pct />
  <Column id=clean_volume_quote_stable title="Clean volume" fmt=usd />
  <Column id=noise_share_of_volume title="Noise vol share" fmt=pct />
</DataTable>

## How to read this in an interview

1. **Clean vs total volume** — dust + self-churn inflate headline volume; prefer `is_clean`
2. **Interesting orderflow** — multi-swap / burst / sandwich-proxy are retained flags, not deletes
3. **Threshold sweep** — shows the metric is sensitive to a documented knob (`dust_usdc`)
4. **Not sandwich proof** — no mempool/relay timing; next measurement is inclusion delay

Related: [Orderflow page](/orderflow) · [RESEARCH.md](https://github.com/marioespinosaperales/dex-trades-canonical/blob/main/RESEARCH.md)
