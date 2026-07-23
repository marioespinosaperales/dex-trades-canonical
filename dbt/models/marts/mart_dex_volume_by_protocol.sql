select
    chain,
    protocol,
    count(*) as trade_count,
    count(*) filter (where is_clean) as clean_trade_count,
    count(*) filter (where is_dust) as dust_trade_count,
    count(*) filter (where is_self_churn) as self_churn_trade_count,
    sum(volume_quote_stable) as volume_quote_stable,
    sum(volume_quote_stable) filter (where is_clean) as clean_volume_quote_stable,
    min(block_number) as min_block,
    max(block_number) as max_block
from {{ ref('int_dex_trades') }}
group by 1, 2
