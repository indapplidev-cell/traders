import pytest

from app.engine_paper.scalping_policy_v2 import EmpiricalSetupBucket, evaluate_expectancy


def test_dynamic_required_rr_uses_conservative_probability():
    result = evaluate_expectancy(
        net_win_bps=120, net_loss_bps=40,
        bucket=EmpiricalSetupBucket("BREAKOUT", "BULLISH", 100, 60),
        minimum_positive_ev_r=0.05, minimum_ev_reserve_r=0.1,
    )
    p = result.p_win_conservative
    assert result.dynamic_required_net_rr == pytest.approx(max(
        (1 - p) / p + 0.1, (1 - p + 0.05) / p,
    ))
    assert result.expected_ev_r == pytest.approx(p * 3 - (1 - p))
    assert result.ev_reserve == pytest.approx(3 - (1 - p) / p)
    assert result.admitted


def test_negative_conservative_ev_never_passes_even_with_old_static_floor():
    result = evaluate_expectancy(
        net_win_bps=20, net_loss_bps=100,
        bucket=EmpiricalSetupBucket("BREAKOUT", "BULLISH", 100, 40),
        static_net_rr=99, static_minimum_net_rr=0,
    )
    assert result.expected_ev_r < 0
    assert not result.admitted
    assert result.reason == "DYNAMIC_NET_RR_CONSERVATIVE_EV_REJECT"


def test_ev_and_reserve_thresholds_are_independent_gates():
    bucket = EmpiricalSetupBucket("BREAKOUT", "BULLISH", 100, 60)
    baseline = evaluate_expectancy(net_win_bps=80, net_loss_bps=40, bucket=bucket)
    strict = evaluate_expectancy(
        net_win_bps=80, net_loss_bps=40, bucket=bucket,
        minimum_positive_ev_r=baseline.expected_ev_r + 0.01,
    )
    assert baseline.admitted
    assert not strict.admitted
