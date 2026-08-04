select
    test_name,
    hypothesis,
    statistic,
    p_value,
    estimate,
    ci_low,
    ci_high,
    n,
    interpretation
from mart_stat_tests
order by test_name
