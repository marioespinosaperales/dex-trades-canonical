select
    chain,
    protocol,
    count(*) as trades,
    count(*) filter (where is_clean) as clean_trades,
    count(*) filter (where is_dust) as dust_trades,
    count(*) filter (where is_self_churn) as self_churn_trades,
    coalesce(sum(volume_quote_stable), 0) as volume_stable,
    coalesce(sum(volume_quote_stable) filter (where is_clean), 0) as clean_volume_stable
from mart_dex_trades
group by 1, 2
