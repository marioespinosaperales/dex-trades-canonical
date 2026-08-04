-- Canonical dex.trades grain: one row per Swap log (chain, tx_hash, log_index).
-- Noise + orderflow/MEV-lite flags are retained (not deleted) so consumers can filter.
-- Sandwich / burst flags are proxies, not proof of MEV.

with base as (
    select
        chain,
        chain_id,
        protocol,
        pool_address,
        block_number,
        cast(null as timestamp) as block_time,
        tx_hash,
        log_index,
        trader,
        token_sold,
        token_bought,
        amount_sold_raw,
        amount_bought_raw,
        amount_sold_raw / power(10, sold_decimals) as amount_sold,
        amount_bought_raw / power(10, bought_decimals) as amount_bought,
        token0_symbol,
        token1_symbol,
        token0_decimals,
        token1_decimals,
        amount0_raw,
        amount1_raw,
        abs(amount0_raw) / power(10, token0_decimals) as amount0_abs,
        abs(amount1_raw) / power(10, token1_decimals) as amount1_abs,
        direction,
        quote_token,
        quote_is_stable,
        fee_tier
    from {{ ref('stg_raw_swaps') }}
),

priced as (
    select
        *,
        case
            when amount0_abs > 0 and amount1_abs > 0
                then amount1_abs / amount0_abs
            else null
        end as price_token1_per_token0,
        amount0_abs as volume_token0,
        case
            when quote_is_stable and quote_token = 'token0' then amount0_abs
            when quote_is_stable and quote_token = 'token1' then amount1_abs
            else null
        end as volume_quote_stable
    from base
),

dusted as (
    select
        *,
        case
            when quote_is_stable
                and volume_quote_stable is not null
                and volume_quote_stable < {{ var('dust_usdc_threshold') }}
                then true
            when amount_sold < {{ var('dust_token_threshold') }}
                and amount_bought < {{ var('dust_token_threshold') }}
                then true
            else false
        end as is_dust
    from priced
),

with_windows as (
    select
        d.*,
        count(*) over (
            partition by chain, tx_hash, pool_address, trader
        ) as swaps_in_tx_pool,
        count(distinct direction) over (
            partition by chain, tx_hash, pool_address, trader
        ) as distinct_directions_in_tx_pool,
        count(*) over (
            partition by chain, tx_hash
        ) as same_tx_swap_count,
        count(*) over (
            partition by chain, block_number, pool_address
        ) as same_block_pool_swap_count,
        count(distinct tx_hash) over (
            partition by chain, block_number, pool_address
        ) as same_block_pool_tx_count,
        lag(direction) over (
            partition by chain, block_number, pool_address
            order by log_index
        ) as prev_direction,
        lead(direction) over (
            partition by chain, block_number, pool_address
            order by log_index
        ) as next_direction,
        lag(direction, 2) over (
            partition by chain, block_number, pool_address
            order by log_index
        ) as prev2_direction,
        lead(direction, 2) over (
            partition by chain, block_number, pool_address
            order by log_index
        ) as next2_direction
    from dusted d
),

flagged as (
    select
        *,
        (
            swaps_in_tx_pool >= 2
            and distinct_directions_in_tx_pool >= 2
            and direction in ('0_to_1', '1_to_0')
        ) as is_self_churn,
        (same_tx_swap_count >= 2) as is_multi_swap_tx,
        (
            same_block_pool_swap_count >= 2
            and same_block_pool_tx_count >= 2
        ) as is_same_block_pool_burst,
        -- A→B→A by log_index in the same block+pool (proxy; marks all three legs).
        (
            (
                prev_direction in ('0_to_1', '1_to_0')
                and next_direction = prev_direction
                and direction in ('0_to_1', '1_to_0')
                and direction <> prev_direction
            )
            or (
                next_direction in ('0_to_1', '1_to_0')
                and next2_direction = direction
                and direction in ('0_to_1', '1_to_0')
                and direction <> next_direction
            )
            or (
                prev_direction in ('0_to_1', '1_to_0')
                and prev2_direction = direction
                and direction in ('0_to_1', '1_to_0')
                and direction <> prev_direction
            )
        ) as is_potential_sandwich_leg
    from with_windows
)

select
    chain,
    chain_id,
    protocol,
    pool_address,
    token0_symbol || '/' || token1_symbol as pool,
    block_number,
    block_time,
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
    (not is_dust and not is_self_churn) as is_clean,
    same_tx_swap_count,
    is_multi_swap_tx,
    same_block_pool_swap_count,
    same_block_pool_tx_count,
    is_same_block_pool_burst,
    is_potential_sandwich_leg,
    (
        is_multi_swap_tx
        or is_same_block_pool_burst
        or is_potential_sandwich_leg
        or is_self_churn
    ) as is_orderflow_interesting,
    token0_symbol,
    token1_symbol,
    direction,
    fee_tier
from flagged
