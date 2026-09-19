from datetime import datetime, timedelta, timezone

import pytest

from app.engine_paper.scalping_hold_lifecycle import (
    CanonicalHoldEvidence, HoldExitReason, HoldLifecycleState, HoldValidity,
    ScalpingEntryThesis, classify_hold_validity, evaluate_hold_lifecycle,
)

OPENED = datetime(2026, 9, 19, 17, 46, tzinfo=timezone.utc)


def thesis(setup_type="SCALP_BREAKOUT", direction="LONG"):
    return ScalpingEntryThesis(
        pipeline_run_id="run", profile="trade-5m-v2", setup_type=setup_type,
        direction=direction, signal_closed_until_ms=1, entry_closed_until_ms=2,
        entry_regime="UP", entry_impulse_phase="IMPULSE_EXTENSION",
        setup_id="setup", config_hash="a" * 64,
    )


def evidence(seconds, **values):
    defaults = dict(regime="UP", structure_direction="BULLISH_STRUCTURE",
                    impulse_phase="IMPULSE_EXTENSION", entry_quality="GOOD",
                    confidence=.8, engine_status="COMPOSED", reason_codes=())
    defaults.update(values)
    return CanonicalHoldEvidence(
        boundary_ms=int((OPENED + timedelta(seconds=seconds)).timestamp() * 1000),
        **defaults,
    )


@pytest.mark.parametrize("setup_type", [
    "SCALP_TREND_PULLBACK", "SCALP_BREAKOUT", "SCALP_BREAKOUT_RETEST",
    "SCALP_RANGE_BOUNCE", "SCALP_LIQUIDITY_SWEEP",
    "SCALP_MOMENTUM_CONTINUATION", "SCALP_COMPRESSION_BREAK",
])
def test_all_scalping_setups_use_hold_revalidation(setup_type):
    validity, reason = classify_hold_validity(thesis(setup_type), evidence(60))
    assert validity is HoldValidity.VALID
    assert reason is None


def test_explicit_opposite_structure_forces_causal_exit():
    decision = evaluate_hold_lifecycle(
        position_id="position", opened_at=OPENED, thesis=thesis(),
        evidence=evidence(180, structure_direction="BEARISH_STRUCTURE"),
    )
    assert decision.lifecycle_state is HoldLifecycleState.FORCE_EXIT
    assert decision.validity is HoldValidity.REVERSED
    assert decision.exit_reason is HoldExitReason.STRUCTURE_INVALIDATED


def test_explicit_opposite_regime_is_momentum_reversal():
    validity, reason = classify_hold_validity(
        thesis(), evidence(180, regime="DOWN", structure_direction="UNCLEAR_STRUCTURE")
    )
    assert validity is HoldValidity.REVERSED
    assert reason is HoldExitReason.MOMENTUM_REVERSAL


def test_soft_timeout_only_extends_explicitly_valid_thesis_once():
    first = evaluate_hold_lifecycle(
        position_id="position", opened_at=OPENED, thesis=thesis(), evidence=evidence(600)
    )
    assert first.lifecycle_state is HoldLifecycleState.EXTENSION_ALLOWED
    assert first.extension_count == 1
    assert first.extension_until_ms == int((OPENED + timedelta(seconds=900)).timestamp() * 1000)
    expired = evaluate_hold_lifecycle(
        position_id="position", opened_at=OPENED, thesis=thesis(), evidence=evidence(900),
        prior_extension_count=first.extension_count,
        prior_extension_until_ms=first.extension_until_ms,
    )
    assert expired.lifecycle_state is HoldLifecycleState.FORCE_EXIT
    assert expired.exit_reason is HoldExitReason.STALE_SCALP


def test_missing_analysis_does_not_panic_close_before_soft_timeout():
    decision = evaluate_hold_lifecycle(
        position_id="position", opened_at=OPENED, thesis=thesis(),
        evidence=evidence(300, engine_status="DATA_UNAVAILABLE", regime=None,
                          structure_direction=None, impulse_phase=None),
    )
    assert decision.lifecycle_state is HoldLifecycleState.AT_RISK
    assert decision.exit_reason is None


def test_hard_timeout_is_absolute_even_when_analysis_errors():
    decision = evaluate_hold_lifecycle(
        position_id="position", opened_at=OPENED, thesis=thesis(),
        evidence=evidence(1200, engine_status="ERROR", regime=None,
                          structure_direction=None, impulse_phase=None),
    )
    assert decision.lifecycle_state is HoldLifecycleState.FORCE_EXIT
    assert decision.exit_reason is HoldExitReason.MAX_HOLD_TIME


def test_fifteen_minute_profile_is_not_part_of_hold_thesis():
    assert thesis().profile == "trade-5m-v2"
    assert "15m" not in thesis().profile
