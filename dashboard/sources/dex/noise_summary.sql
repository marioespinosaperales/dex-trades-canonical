select
    chain,
    protocol,
    count(*) as trades,
    count(*) filter (where is_clean) as clean_trades,
    count(*) filter (where is_dust) as dust_trades,
    count(*) filter (where is_self_churn) as self_churn_trades
from mart_dex_trades
group by 1, 2
