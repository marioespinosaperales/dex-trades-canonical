select
    chain,
    protocol,
    pool,
    pool_address,
    cast(block_number as varchar) as block_number,
    tx_hash,
    log_index,
    trader,
    volume_quote_stable,
    price_token1_per_token0,
    fee_tier,
    is_clean,
    is_multi_swap_tx,
    is_same_block_pool_burst,
    is_potential_sandwich_leg,
    is_orderflow_interesting,
    direction,
    coalesce(fee_recipient, '') as fee_recipient
from mart_dex_trades
where is_orderflow_interesting
order by chain, cast(block_number as bigint) desc, log_index desc
