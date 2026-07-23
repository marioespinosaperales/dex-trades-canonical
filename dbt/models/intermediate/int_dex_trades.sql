-- Canonical dex.trades grain: one row per Swap log (chain, tx_hash, log_index).
-- Noise flags are retained (not deleted) so consumers can filter.

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
        -- Volume quoted in token0 units of the pool.
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

-- Same-tx self-churn: ≥2 swaps on same pool+trader that reverse direction.
with_peers as (
    select
        d.*,
        count(*) over (
            partition by chain, tx_hash, pool_address, trader
        ) as swaps_in_tx_pool,
        count(distinct direction) over (
            partition by chain, tx_hash, pool_address, trader
        ) as distinct_directions_in_tx_pool
    from dusted d
),

flagged as (
    select
        *,
        (
            swaps_in_tx_pool >= 2
            and distinct_directions_in_tx_pool >= 2
            and direction in ('0_to_1', '1_to_0')
        ) as is_self_churn
    from with_peers
)

select
    chain,
    chain_id,
    protocol,
    pool_address,
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
    token0_symbol,
    token1_symbol,
    direction,
    fee_tier
from flagged
