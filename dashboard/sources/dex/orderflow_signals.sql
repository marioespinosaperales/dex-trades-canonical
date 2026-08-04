select
    chain,
    protocol,
    trade_count,
    multi_swap_trades,
    burst_trades,
    sandwich_proxy_trades,
    interesting_trades,
    clean_trades,
    total_volume_quote_stable,
    clean_volume_quote_stable,
    interesting_volume_quote_stable,
    interesting_trade_rate,
    interesting_volume_share
from mart_orderflow_signals
order by interesting_volume_quote_stable desc nulls last
