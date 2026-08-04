-- Orderflow / MEV-lite signal rates by chain × protocol.
-- Proxies only: interesting ≠ sandwich proof.

select
    chain,
    protocol,
    count(*) as trade_count,
    count(*) filter (where is_multi_swap_tx) as multi_swap_trades,
    count(*) filter (where is_same_block_pool_burst) as burst_trades,
    count(*) filter (where is_potential_sandwich_leg) as sandwich_proxy_trades,
    count(*) filter (where is_orderflow_interesting) as interesting_trades,
    count(*) filter (where is_clean) as clean_trades,
    coalesce(sum(volume_quote_stable), 0) as total_volume_quote_stable,
    coalesce(sum(volume_quote_stable) filter (where is_clean), 0) as clean_volume_quote_stable,
    coalesce(sum(volume_quote_stable) filter (where is_orderflow_interesting), 0)
        as interesting_volume_quote_stable,
    round(
        count(*) filter (where is_orderflow_interesting)::double / nullif(count(*), 0),
        4
    ) as interesting_trade_rate,
    round(
        coalesce(sum(volume_quote_stable) filter (where is_orderflow_interesting), 0)
            / nullif(coalesce(sum(volume_quote_stable), 0), 0),
        4
    ) as interesting_volume_share
from {{ ref('int_dex_trades') }}
group by chain, protocol
order by chain, protocol
