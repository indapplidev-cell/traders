from app.engine_paper.scalping_policy_v2 import (
    EmpiricalSetupBucket,
    estimate_conservative_probability,
    evaluate_expectancy,
)


def test_estimator_persists_complete_deterministic_provenance():
    source = EmpiricalSetupBucket("BREAKOUT", "BULLISH", 100, 60, "setup", "setup:breakout")
    first = estimate_conservative_probability(source, parent_sample_size=300)
    second = estimate_conservative_probability(source, parent_sample_size=300)
    assert first == second
    assert first.p_win_raw == 0.6
    assert 0 < first.p_win_conservative < first.p_win_adjusted < first.p_win_raw
    assert first.sample_size == 100
    assert first.parent_sample_size == 300
    assert first.bucket_key == "setup:breakout"
    assert first.fallback_level == "setup"


def test_tiny_symbol_bucket_cannot_override_sufficient_parent():
    tiny_symbol = EmpiricalSetupBucket("BREAKOUT", "BULLISH", 3, 3, "symbol", "BTC")
    parent = EmpiricalSetupBucket("BREAKOUT", "BULLISH", 100, 55, "setup", "BREAKOUT")
    result = evaluate_expectancy(
        net_win_bps=100, net_loss_bps=40, bucket=tiny_symbol,
        parent_buckets=(parent,), minimum_samples=20,
    )
    assert result.fallback_level == "setup"
    assert result.bucket_key == "BREAKOUT"
    assert result.sample_size == 100
    assert result.p_win_raw == 0.55
    assert result.probability == result.p_win_conservative


def test_conservative_probability_not_raw_rate_controls_admission():
    bucket = EmpiricalSetupBucket("BREAKOUT", "BULLISH", 20, 10)
    result = evaluate_expectancy(
        net_win_bps=100, net_loss_bps=40, bucket=bucket, minimum_samples=20,
    )
    assert result.p_win_raw == 0.5
    assert result.p_win_conservative < result.p_win_raw
    expected = result.p_win_conservative * 100 - (1 - result.p_win_conservative) * 40
    assert result.expected_value_bps == expected
