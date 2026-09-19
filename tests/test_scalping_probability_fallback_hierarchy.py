from app.engine_paper.scalping_policy_v2 import (
    ADMISSION_EMPIRICAL,
    ADMISSION_PAPER_BOOTSTRAP,
    EmpiricalSetupBucket,
    bootstrap_execution_permitted,
    evaluate_expectancy,
)


def bucket(level, samples, wins):
    return EmpiricalSetupBucket(
        "BREAKOUT", "BULLISH", samples, wins, level, level,
        average_win_net_bps=80, average_loss_net_bps=40,
    )


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
    assert result.reason == "EMPIRICAL_INSUFFICIENT_SAMPLE_BOOTSTRAP_REJECTED_PRECONDITION"
    assert result.expected_value_bps is None


def test_zero_and_partial_samples_use_explicit_paper_bootstrap_only_when_enabled():
    for samples in (0, 1, 19):
        result = evaluate_expectancy(
            net_win_bps=60, net_loss_bps=40,
            bucket=bucket("exact", samples, min(samples, 1)),
            minimum_samples=20,
            paper_bootstrap_allowed=True,
        )
        assert result.admitted is True
        assert result.empirical_pass is False
        assert result.admission_mode == ADMISSION_PAPER_BOOTSTRAP
        assert result.empirical_authority_status == "NOT_ESTABLISHED"
        assert result.expected_value_bps is None
        assert result.paper_bootstrap_eligible is True
        assert result.empirical_required_sample == 20


def test_sufficient_positive_authority_uses_empirical_mode_not_bootstrap():
    result = evaluate_expectancy(
        net_win_bps=80, net_loss_bps=40,
        bucket=bucket("exact", 20, 14), minimum_samples=20,
        paper_bootstrap_allowed=True,
    )
    assert result.admitted is True
    assert result.empirical_pass is True
    assert result.admission_mode == ADMISSION_EMPIRICAL
    assert result.paper_bootstrap_eligible is False
    assert result.reason == "EMPIRICAL_SUFFICIENT_POSITIVE_EV"


def test_sufficient_negative_ev_cannot_fall_back_to_bootstrap():
    result = evaluate_expectancy(
        net_win_bps=80, net_loss_bps=40,
        bucket=bucket("exact", 20, 1), minimum_samples=20,
        paper_bootstrap_allowed=True,
    )
    assert result.admitted is False
    assert result.empirical_pass is False
    assert result.admission_mode == "REJECTED"
    assert result.paper_bootstrap_eligible is False
    assert result.reason == "EMPIRICAL_SUFFICIENT_NEGATIVE_EV"


def test_sufficient_compatible_parent_prevents_bootstrap():
    result = evaluate_expectancy(
        net_win_bps=80, net_loss_bps=40,
        bucket=bucket("exact", 3, 2),
        parent_buckets=(bucket("setup_direction", 25, 1),),
        minimum_samples=20,
        paper_bootstrap_allowed=True,
    )
    assert result.paper_bootstrap_eligible is False
    assert result.admission_mode == "REJECTED"
    assert result.fallback_level == "setup_direction"


def test_bootstrap_execution_is_permanently_paper_only():
    assert bootstrap_execution_permitted(
        admission_mode=ADMISSION_PAPER_BOOTSTRAP, execution_mode="PAPER"
    )
    assert not bootstrap_execution_permitted(
        admission_mode=ADMISSION_PAPER_BOOTSTRAP, execution_mode="LIVE"
    )
