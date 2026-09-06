from dataclasses import replace

from app.config.trade_parameters import SCALPING_V2
from app.engine_paper.scalping_policy_v2 import EmpiricalSetupBucket
from app.engine_paper.scalping_shadow import (
    CausalTarget, ShadowCostInputs, ShadowGeometryCandidate,
    ShadowGeometryConfig, evaluate_scalping_shadow,
)


def fixture():
    candidate = ShadowGeometryCandidate(
        "trade-5m-v2", "BTCUSDT", 1000, "BULLISH", 100, 99.8, 0.05,
        (CausalTarget(101, "LOCAL_5M", 1000),), "breakout",
    )
    config = ShadowGeometryConfig(
        .25, 50, 45, production_rr_floor=.4,
        empirical_bucket=EmpiricalSetupBucket("BREAKOUT", "BULLISH", 100, 70),
    )
    return candidate, config


def test_adverse_fill_reserve_is_separate_and_in_effective_cost():
    costs = ShadowCostInputs(
        entry_fee_bps=10, exit_fee_bps=10, entry_slippage_bps=2,
        exit_slippage_bps=2, spread_bps=1, depth_impact_bps=1,
        adverse_fill_reserve_bps=3, safety_margin_bps=0,
        commission_authoritative=True, spread_authoritative=True,
        depth_authoritative=True,
    )
    candidate, config = fixture()
    result = evaluate_scalping_shadow(candidate, costs, config)
    assert result.adverse_fill_reserve_bps == 3
    assert result.effective_total_cost_bps == result.total_cost_bps == 29
    without_reserve = evaluate_scalping_shadow(
        candidate, replace(costs, adverse_fill_reserve_bps=0), config
    )
    assert without_reserve.total_cost_bps == 26


def test_config_reclassifies_existing_three_bps_margin_without_optimism():
    assert SCALPING_V2.costs.adverse_fill_reserve_bps == 3
    assert SCALPING_V2.costs.cost_safety_margin_bps == 0


def test_missing_commission_authority_never_becomes_zero_or_passes():
    costs = ShadowCostInputs(
        entry_fee_bps=10, exit_fee_bps=10, spread_bps=1, depth_impact_bps=1,
        spread_authoritative=True, depth_authoritative=True,
        commission_authoritative=False,
    )
    candidate, config = fixture()
    result = evaluate_scalping_shadow(candidate, costs, config)
    assert not result.valid_plan
    assert result.rejection_reason == "PAPER_NO_PLAN_NON_AUTHORITATIVE_COMMISSION"
    assert result.round_trip_commission_bps == 20
