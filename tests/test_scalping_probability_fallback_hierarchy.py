from app.engine_paper.scalping_policy_v2 import EmpiricalSetupBucket, evaluate_expectancy


def bucket(level, samples, wins):
    return EmpiricalSetupBucket("BREAKOUT", "BULLISH", samples, wins, level, level)


def test_exact_bucket_is_preferred_when_sufficient():
    result = evaluate_expectancy(
        net_win_bps=80, net_loss_bps=40, bucket=bucket("exact", 20, 14),
        parent_buckets=(bucket("parent", 100, 10),), minimum_samples=20,
    )
    assert result.fallback_level == "exact"
    assert result.admitted


def test_each_parent_level_can_supply_authority_in_order():
    parents = (
        bucket("setup_direction_regime", 5, 4),
        bucket("setup_direction", 40, 25),
        bucket("setup", 100, 1),
        bucket("global", 200, 1),
    )
    result = evaluate_expectancy(
        net_win_bps=80, net_loss_bps=40, bucket=bucket("exact", 3, 3),
        parent_buckets=parents, minimum_samples=20,
    )
    assert result.fallback_level == "setup_direction"


def test_insufficient_hierarchy_never_uses_static_rr_to_pass():
    result = evaluate_expectancy(
        net_win_bps=30, net_loss_bps=60, bucket=None,
        parent_buckets=(bucket("global", 3, 3),), minimum_samples=20,
        static_net_rr=99, static_minimum_net_rr=0,
    )
    assert not result.admitted
    assert result.reason == "INSUFFICIENT_STATISTICAL_AUTHORITY_NO_TRADE"
    assert result.expected_value_bps is None
