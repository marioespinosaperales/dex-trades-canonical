with src as (
    select * from {{ source('raw', 'swaps') }}
),

deduped as (
    select *
    from src
    qualify row_number() over (
        partition by chain, tx_hash, log_index
        order by block_number desc
    ) = 1
)

select
    cast(chain as varchar) as chain,
    cast(chain_id as integer) as chain_id,
    cast(protocol as varchar) as protocol,
    lower(cast(pool_address as varchar)) as pool_address,
    cast(block_number as bigint) as block_number,
    cast(log_index as bigint) as log_index,
    cast(tx_hash as varchar) as tx_hash,
    lower(cast(trader as varchar)) as trader,
    lower(cast(sender as varchar)) as sender,
    cast(token0_symbol as varchar) as token0_symbol,
    cast(token1_symbol as varchar) as token1_symbol,
    cast(token0_decimals as integer) as token0_decimals,
    cast(token1_decimals as integer) as token1_decimals,
    try_cast(amount0_raw as decimal(38, 0)) as amount0_raw,
    try_cast(amount1_raw as decimal(38, 0)) as amount1_raw,
    cast(token_sold as varchar) as token_sold,
    cast(token_bought as varchar) as token_bought,
    try_cast(amount_sold_raw as decimal(38, 0)) as amount_sold_raw,
    try_cast(amount_bought_raw as decimal(38, 0)) as amount_bought_raw,
    cast(sold_decimals as integer) as sold_decimals,
    cast(bought_decimals as integer) as bought_decimals,
    cast(direction as varchar) as direction,
    cast(quote_token as varchar) as quote_token,
    cast(quote_is_stable as boolean) as quote_is_stable,
    try_cast(fee_tier as integer) as fee_tier
from deduped
