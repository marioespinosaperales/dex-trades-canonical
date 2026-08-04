select
    dust_usdc_threshold,
    clean_rate,
    dust_rate,
    clean_volume_quote_stable,
    noise_share_of_volume
from mart_dust_threshold_sweep
order by dust_usdc_threshold
