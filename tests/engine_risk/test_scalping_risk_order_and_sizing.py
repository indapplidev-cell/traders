from types import SimpleNamespace

import pytest

from app.engine_risk.risk_limits import ResearchRiskLimits
from app.engine_risk.risk_policy import RiskPolicy
from app.engine_risk.risk_runner import RiskRunner
from app.engine_risk.scalping_sizing import size_scalping_position
from tests.engine_risk_01_helpers import strategy_decision


def runtime():
    return SimpleNamespace(
        profile_id="trade-5m-v2", parameter_set_id="5m-v2",
        risk_shadow_policy_id="risk", minimum_planned_rr=0.4,
    )


def test_preview_does_not_reserve_but_authoritative_risk_does():
    limits = ResearchRiskLimits()
    runner = RiskRunner(RiskPolicy(limits=limits, runtime_parameters=runtime()))
    source = strategy_decision(
        decision_id="strategy:scalping:risk-order",
        timeframe="5m",
        strategy_type="SCALP_BREAKOUT_RESEARCH",
    )

    preview = runner.preview_strategy_decision(source)
    assert preview.risk_pre_approved
    assert limits.profile_attempts("trade-5m-v2", source.closed_until_ms) == 0

    admitted = runner.process_strategy_decision(source)
    assert admitted.risk_pre_approved
    assert limits.profile_attempts("trade-5m-v2", source.closed_until_ms) == 1


def test_position_size_is_allowed_loss_over_stop_with_liquidity_and_notional_caps():
    base = size_scalping_position(
        account_equity=10_000, risk_per_trade_bps=10,
        stop_distance=5, entry_price=100,
    )
    capped = size_scalping_position(
        account_equity=10_000, risk_per_trade_bps=10,
        stop_distance=5, entry_price=100,
        liquidity_quantity_cap=15, maximum_notional=1_200,
    )

    assert base.allowed_loss == 10
    assert base.final_quantity == 2
    assert base.limiting_factor == "RISK"
    assert capped.final_quantity == 2
    assert capped.notional_quantity_cap == 12


def test_liquidity_cap_can_be_the_binding_limit():
    result = size_scalping_position(
        account_equity=100_000, risk_per_trade_bps=25,
        stop_distance=1, entry_price=100, liquidity_quantity_cap=5,
    )
    assert result.final_quantity == 5
    assert result.limiting_factor == "LIQUIDITY"


@pytest.mark.parametrize("risk", [1, 30])
def test_undeclared_risk_cohorts_fail_closed(risk):
    with pytest.raises(ValueError):
        size_scalping_position(
            account_equity=10_000, risk_per_trade_bps=risk,
            stop_distance=5, entry_price=100,
        )
