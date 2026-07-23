select
    chain,
    chain_id,
    protocol,
    pool,
    pool_address,
    -- Exact block as text so Evidence does not compact to "49.0M"
    cast(block_number as varchar) as block_number,
    tx_hash,
    log_index,
    trader,
    token_sold,
    token_bought,
    amount_sold,
    amount_bought,
    amount_sold_raw,
    amount_bought_raw,
    price_token1_per_token0,
    volume_token0,
    volume_quote_stable,
    is_dust,
    is_self_churn,
    is_clean,
    direction,
    fee_tier
from mart_dex_trades
order by chain, cast(block_number as bigint) desc, log_index desc
