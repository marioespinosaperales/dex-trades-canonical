---
title: Quality benchmarks
---

Measurement card for canonical `dex.trades`: label rates, volume impact, threshold
sensitivity, and lightweight inference (Wilson CIs, bootstrap, Mann–Whitney, χ²).

Computed by the same rubric as `make eval` / `make research`.

```sql meta
select generated_at, source_kind, trade_count, notes
from dex.run_meta
```

<DataTable data={meta}>
  <Column id=source_kind title="Source" />
  <Column id=trade_count title="Trades" />
  <Column id=generated_at title="Generated" />
  <Column id=notes title="Notes" />
</DataTable>

## Headline results

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
select value as trades from dex.qc_kpis where metric = 'trades'
```

```sql kpi_clean
select value as clean_rate from dex.qc_kpis where metric = 'clean_rate'
```

```sql kpi_interesting
select value as interesting_rate from dex.qc_kpis where metric = 'interesting_rate'
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
  <Column id=definition title="Definition" />
</DataTable>

<BarChart
  data={kpi_rates}
  x=metric
  y=value
  title="Rate benchmarks"
  yFmt=pct
/>

## Inference

Wilson intervals on rates, bootstrap CI on noise volume share, Mann–Whitney on
stable volume (interesting vs other), and χ² of interesting × `fee_recipient`
(builder proxy). p-values test stated nulls — they do not prove MEV.

```sql tests
select
    test_name,
    hypothesis,
    statistic,
    p_value,
    estimate,
    ci_low,
    ci_high,
    n,
    interpretation
from dex.stat_tests
order by test_name
```

<DataTable data={tests}>
  <Column id=test_name title="Test" />
  <Column id=hypothesis title="Hypothesis / estimand" />
  <Column id=statistic title="Stat" fmt=num4 />
  <Column id=p_value title="p-value" fmt=num4 />
  <Column id=estimate title="Estimate" fmt=num4 />
  <Column id=ci_low title="CI low" fmt=num4 />
  <Column id=ci_high title="CI high" fmt=num4 />
  <Column id=interpretation title="Result" />
</DataTable>

## Dust threshold sensitivity

How the `$ dust_usdc` cut moves clean rate and noise share of volume.

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

## Takeaways

1. Headline volume without `is_clean` mixes dust and self-churn into economic activity
2. Orderflow proxies (multi-swap / burst / sandwich-leg) stay on the row so volume can be split
3. Threshold sweep shows metric movement under a documented knob (`dust_usdc`)
4. Builder/`fee_recipient` association is a PBS join surface — not inclusion-delay proof

[Orderflow](/orderflow) · [RESEARCH.md](https://github.com/marioespinosaperales/dex-trades-canonical/blob/main/RESEARCH.md)
