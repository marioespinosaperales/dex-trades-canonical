select
    cast(chain as varchar) as chain,
    cast(chain_id as integer) as chain_id,
    cast(block_number as bigint) as block_number,
    lower(cast(fee_recipient as varchar)) as fee_recipient,
    cast(block_hash as varchar) as block_hash,
    cast(timestamp as bigint) as block_timestamp
from {{ source('raw', 'blocks') }}
qualify row_number() over (
    partition by chain, block_number
    order by block_timestamp desc nulls last
) = 1
