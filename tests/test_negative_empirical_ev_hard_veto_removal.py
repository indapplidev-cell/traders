from __future__ import annotations

import pytest

from app.engine_paper.paper_reason_codes import PaperReasonCode as R
from app.engine_paper.scalping_policy_v2 import (
    ADMISSION_EMPIRICAL,
    EmpiricalSetupBucket,
    evaluate_expectancy,
)
from app.engine_paper.scalping_shadow import (
    CausalTarget,
    ShadowCostInputs,
    ShadowGeometryCandidate,
    ShadowGeometryConfig,
    evaluate_scalping_shadow,
)


BOUNDARY = 1_790_000_000_000
AVERAGE_WIN_NET_BPS = 20.616319467665843
AVERAGE_LOSS_NET_BPS = 32.106007563036805
ENA_NET_RR = 2.80469675


def _authority(*, wins: int = 7) -> EmpiricalSetupBucket:
    return EmpiricalSetupBucket(
        setup_type="SCALP_MOMENTUM_CONTINUATION",
        direction="BULLISH",
        samples=20,
        wins=wins,
        level="setup",
        bucket_key="empirical-regime-v1|setup|ENAUSDT",
        average_win_net_bps=AVERAGE_WIN_NET_BPS,
        average_loss_net_bps=AVERAGE_LOSS_NET_BPS,
    )


def _shadow(
    *,
    net_rr: float,
    targets: tuple[CausalTarget, ...] | None = None,
    spread_authoritative: bool = True,
):
    entry = 100.0
    stop_distance_bps = 50.0
    target = entry * (1 + (stop_distance_bps * net_rr) / 10_000)
    return evaluate_scalping_shadow(
        ShadowGeometryCandidate(
            trade_profile_id="trade-5m-v2",
            symbol="ENAUSDT",
            boundary_ms=BOUNDARY,
            direction="BULLISH",
            entry=entry,
            causal_invalidation=99.5,
            atr=0.0,
            targets=(CausalTarget(target, "LOCAL_5M", BOUNDARY),) if targets is None else targets,
            setup_identity="SCALP_MOMENTUM_CONTINUATION",
        ),
        ShadowCostInputs(
            entry_fee_bps=0.0,
            exit_fee_bps=0.0,
            entry_slippage_bps=0.0,
            exit_slippage_bps=0.0,
            safety_margin_bps=0.0,
            adverse_fill_reserve_bps=0.0,
            spread_bps=0.0 if spread_authoritative else None,
            depth_impact_bps=0.0,
            spread_authoritative=spread_authoritative,
            depth_authoritative=True,
            commission_authoritative=True,
        ),
        ShadowGeometryConfig(
            atr_buffer_multiplier=0.25,
            stop_envelope_bps=60.0,
            minimum_target_diagnostic_bps=1.0,
            production_rr_floor=0.476674,
            empirical_bucket=_authority(),
            minimum_empirical_samples=20,
            minimum_expected_value_bps=0.0,
            minimum_positive_ev_r=0.0,
            minimum_ev_reserve_r=0.0,
        ),
    )


def test_ena_negative_empirical_ev_is_diagnostic_above_dynamic_rr() -> None:
    decision = evaluate_expectancy(
        net_win_bps=ENA_NET_RR * AVERAGE_LOSS_NET_BPS,
        net_loss_bps=AVERAGE_LOSS_NET_BPS,
        bucket=_authority(),
    )

    assert decision.sample_size == 20
    assert decision.bucket_wins == 7
    assert decision.bucket_losses == 13
    assert decision.expected_value_bps == pytest.approx(-18.081946112391396)
    assert decision.dynamic_required_net_rr == pytest.approx(2.759419282085097)
    assert decision.candidate_net_rr == pytest.approx(ENA_NET_RR)
    assert decision.candidate_net_rr > decision.dynamic_required_net_rr
    assert decision.admitted is True
    assert decision.empirical_pass is False
    assert decision.admission_mode == ADMISSION_EMPIRICAL
    assert decision.reason == "EMPIRICAL_SUFFICIENT_NEGATIVE_EV"

    result = _shadow(net_rr=ENA_NET_RR)
    assert result.expected_value_bps == pytest.approx(-18.081946112391396)
    assert result.expectancy_gate_reason == "EMPIRICAL_SUFFICIENT_NEGATIVE_EV"
    assert result.rr_empirical_status == "NEGATIVE_DIAGNOSTIC"
    assert result.net_rr > result.dynamic_required_net_rr
    assert result.admission_decision == "PASS"
    assert result.valid_plan is True
    assert result.final_shadow_approval is True
    assert result.rejection_reason is None


def test_negative_ev_below_dynamic_rr_keeps_actual_terminal_blocker() -> None:
    result = _shadow(net_rr=2.70)

    assert result.expected_value_bps < 0
    assert result.net_rr < result.dynamic_required_net_rr
    assert result.expectancy_gate_reason == "DYNAMIC_NET_RR_CONSERVATIVE_EV_REJECT"
    assert result.rejection_stage == "EXPECTANCY_GATE"
    assert result.rejection_reason == "DYNAMIC_NET_RR_CONSERVATIVE_EV_REJECT"
    assert result.rejection_reason != "SCALPING_EMPIRICAL_EXPECTANCY_REJECTED"
    assert result.valid_plan is False


def test_positive_empirical_ev_and_insufficient_sample_semantics_are_unchanged() -> None:
    positive = evaluate_expectancy(
        net_win_bps=120.0,
        net_loss_bps=40.0,
        bucket=EmpiricalSetupBucket(
            "SCALP_MOMENTUM_CONTINUATION",
            "BULLISH",
            20,
            18,
            average_win_net_bps=120.0,
            average_loss_net_bps=40.0,
        ),
        paper_bootstrap_allowed=True,
    )
    insufficient = evaluate_expectancy(
        net_win_bps=120.0,
        net_loss_bps=40.0,
        bucket=EmpiricalSetupBucket(
            "SCALP_MOMENTUM_CONTINUATION",
            "BULLISH",
            19,
            18,
            average_win_net_bps=120.0,
            average_loss_net_bps=40.0,
        ),
        paper_bootstrap_allowed=True,
    )

    assert positive.admitted is True
    assert positive.empirical_pass is True
    assert positive.reason == "EMPIRICAL_SUFFICIENT_POSITIVE_EV"
    assert positive.admission_mode == ADMISSION_EMPIRICAL
    assert insufficient.admitted is True
    assert insufficient.empirical_pass is False
    assert insufficient.reason == "EMPIRICAL_INSUFFICIENT_SAMPLE_BOOTSTRAP_ALLOWED"
    assert insufficient.admission_mode == "PAPER_BOOTSTRAP"


def test_target_cost_and_base_rr_blockers_are_unchanged() -> None:
    missing_target = _shadow(net_rr=ENA_NET_RR, targets=())
    missing_cost = _shadow(net_rr=ENA_NET_RR, spread_authoritative=False)
    below_base_rr = _shadow(net_rr=0.40)

    assert missing_target.rejection_reason == R.PAPER_NO_PLAN_MISSING_TARGET_LEVEL
    assert missing_cost.rejection_reason == R.PAPER_NO_PLAN_MISSING_AUTHORITATIVE_SPREAD
    assert below_base_rr.rejection_reason == R.ECONOMIC_GEOMETRY_NOT_FEASIBLE
    assert missing_target.expectancy_gate_reason is None
    assert missing_cost.expectancy_gate_reason is None
    assert below_base_rr.expectancy_gate_reason is None
