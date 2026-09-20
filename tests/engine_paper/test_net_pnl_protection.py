from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.engine_paper.exit_evaluator import (
    PaperSafetyExitDirective,
    evaluate_paper_exit_window,
)
from app.engine_paper.fill_simulator import PaperFillCandle
from app.engine_paper.scalping_hold_lifecycle import (
    CanonicalHoldEvidence,
    HoldExitReason,
    HoldLifecycleState,
    ModeledNetExitPnl,
    ScalpingEntryThesis,
    evaluate_hold_lifecycle,
    modeled_executable_net_exit_pnl,
)
from app.engine_paper.scalping_shadow import ShadowCostInputs
from app.engine_position.paper_models import PaperPosition
from app.engine_safety.paper_domain import (
    ExecutionMode,
    PaperExitCause,
    PaperPositionState,
    PaperReasonCode,
    PaperSide,
)


OPENED = datetime(2026, 9, 20, 10, tzinfo=timezone.utc)
T0 = int(OPENED.timestamp() * 1000)


def _thesis() -> ScalpingEntryThesis:
    return ScalpingEntryThesis(
        pipeline_run_id="run", profile="trade-5m-v2",
        setup_type="SCALP_BREAKOUT", direction="LONG",
        signal_closed_until_ms=T0 - 300_000, entry_closed_until_ms=T0,
        entry_regime="UP", entry_impulse_phase="IMPULSE_EXTENSION",
        setup_id="setup", config_hash="a" * 64,
    )


def _evidence(seconds: int, **changes) -> CanonicalHoldEvidence:
    values = dict(
        boundary_ms=int((OPENED + timedelta(seconds=seconds)).timestamp() * 1000),
        regime="UP", structure_direction="BULLISH_STRUCTURE",
        impulse_phase="IMPULSE_EXTENSION", entry_quality="GOOD",
        confidence=0.9, engine_status="COMPOSED", reason_codes=(),
    )
    values.update(changes)
    return CanonicalHoldEvidence(**values)


def _net(value: str) -> ModeledNetExitPnl:
    amount = Decimal(value)
    zero = Decimal("0")
    return ModeledNetExitPnl(
        raw_net_exit_pnl=amount, quantized_net_exit_pnl=amount,
        currency="USDT", executable_reference_price=Decimal("100"),
        gross_pnl=amount, entry_fee_incurred=zero,
        expected_exit_fee=zero, spread_cost=zero, exit_slippage_cost=zero,
        depth_impact_cost=zero, adverse_fill_reserve=zero, cost_provenance={},
    )


@pytest.mark.parametrize(
    ("seconds", "amount", "triggered", "reason"),
    [
        (500, "1", False, None),
        (600, "1", False, None),
        (601, "0", False, None),
        (700, "-0.000000000000000001", False, None),
        (601, "0.000000000000000001", True, HoldExitReason.NET_PNL_PROTECTION),
        (1199, "1", True, HoldExitReason.NET_PNL_PROTECTION),
        (1200, "1", True, HoldExitReason.MAX_HOLD_TIME),
    ],
)
def test_authoritative_window_is_strict_and_hard_timeout_wins(
    seconds, amount, triggered, reason
):
    decision = evaluate_hold_lifecycle(
        position_id="position", opened_at=OPENED, thesis=_thesis(),
        evidence=_evidence(seconds), modeled_net_exit=_net(amount),
    )
    assert decision.force_exit is triggered
    assert decision.exit_reason is reason
    assert decision.net_pnl_protection_triggered is (
        reason is HoldExitReason.NET_PNL_PROTECTION
    )
    if seconds in {601, 700, 1199}:
        assert decision.net_pnl_protection_window_active is True


@pytest.mark.parametrize(
    "evidence_changes,expected",
    [
        ({"structure_direction": "BEARISH_STRUCTURE"}, HoldExitReason.STRUCTURE_INVALIDATED),
        ({"regime": "DOWN", "structure_direction": "UNCLEAR"}, HoldExitReason.MOMENTUM_REVERSAL),
        ({"entry_quality": "INVALID"}, HoldExitReason.SETUP_INVALIDATED),
        ({"impulse_phase": "IMPULSE_EXHAUSTION"}, HoldExitReason.MOMENTUM_INVALIDATED),
    ],
)
def test_existing_causal_exit_has_priority_over_positive_net_pnl(
    evidence_changes, expected
):
    decision = evaluate_hold_lifecycle(
        position_id="position", opened_at=OPENED, thesis=_thesis(),
        evidence=_evidence(601, **evidence_changes), modeled_net_exit=_net("10"),
    )
    assert decision.exit_reason is expected
    assert decision.net_pnl_protection_triggered is False


def test_expired_stale_exit_is_not_relabelled_as_net_pnl_protection():
    decision = evaluate_hold_lifecycle(
        position_id="position", opened_at=OPENED, thesis=_thesis(),
        evidence=_evidence(900), modeled_net_exit=_net("10"),
        prior_extension_count=1,
        prior_extension_until_ms=_evidence(900).boundary_ms,
    )
    assert decision.exit_reason is HoldExitReason.STALE_SCALP
    assert decision.net_pnl_protection_triggered is False


def _position() -> PaperPosition:
    return PaperPosition(
        position_id="position:net", mode=ExecutionMode.PAPER, symbol="BTCUSDT",
        side=PaperSide.LONG, state=PaperPositionState.OPEN,
        entry_order_id="order:entry", entry_fill_id="fill:entry",
        entry_quantity=Decimal("1"), remaining_quantity=Decimal("1"),
        average_entry_price=Decimal("100"), average_exit_price=None,
        entry_fees=Decimal("0"), exit_fees=Decimal("0"),
        realized_pnl=Decimal("0"), unrealized_pnl=Decimal("0"),
        stop_price=Decimal("90"), target_price=Decimal("110"),
        opened_at=OPENED, closed_at=None, last_mark_price=Decimal("100"),
        last_mark_closed_until_ms=T0, version=0,
        reason_code=PaperReasonCode.PAPER_POSITION_OPENED,
    )


def _costs(**changes) -> ShadowCostInputs:
    values = dict(
        entry_fee_bps=0.0, exit_fee_bps=0.0, entry_slippage_bps=0.0,
        exit_slippage_bps=0.0, safety_margin_bps=0.0,
        adverse_fill_reserve_bps=0.0, spread_bps=0.0, depth_impact_bps=0.0,
        fee_source="BINANCE_ACCOUNT_COMMISSION_SNAPSHOT",
        commission_authoritative=True, spread_authoritative=True,
        depth_authoritative=True, economic_input_timestamp_ms=1_000,
        decision_cutoff_timestamp_ms=1_001, maximum_age_ms=5_000,
    )
    values.update(changes)
    return ShadowCostInputs(**values)


def test_decimal_quantization_suppresses_sub_quantum_float_like_noise():
    result = modeled_executable_net_exit_pnl(
        position=_position(),
        closed_1m_price=Decimal("100.0000000000000000004"),
        costs=_costs(),
    )
    assert result is not None
    assert result.raw_net_exit_pnl > 0
    assert result.quantized_net_exit_pnl == Decimal("0E-18")
    decision = evaluate_hold_lifecycle(
        position_id="position", opened_at=OPENED, thesis=_thesis(),
        evidence=_evidence(601), modeled_net_exit=result,
    )
    assert decision.force_exit is False


def test_model_includes_every_exit_cost_and_fails_closed_without_account_fee():
    costs = _costs(
        exit_fee_bps=1.0, spread_bps=2.0, exit_slippage_bps=3.0,
        depth_impact_bps=4.0, adverse_fill_reserve_bps=5.0,
    )
    result = modeled_executable_net_exit_pnl(
        position=replace(_position(), entry_fees=Decimal("0.10")),
        closed_1m_price=Decimal("101"), costs=costs,
    )
    assert result is not None
    assert result.gross_pnl == Decimal("1")
    assert result.quantized_net_exit_pnl == Decimal("0.748500000000000000")
    assert result.depth_impact_cost == Decimal("0.0404")
    assert modeled_executable_net_exit_pnl(
        position=_position(), closed_1m_price=Decimal("101"),
        costs=replace(costs, commission_authoritative=False),
    ) is None


def _candle(*, stop=False) -> PaperFillCandle:
    return PaperFillCandle(
        symbol="BTCUSDT", timeframe="1m", open_time_ms=T0,
        close_boundary_ms=T0 + 60_000, open_price=Decimal("100"),
        high_price=Decimal("101"), low_price=Decimal("89") if stop else Decimal("99"),
        close_price=Decimal("100.5"), is_closed=True,
        observed_closed_until_ms=T0 + 60_000,
    )


def _directive() -> PaperSafetyExitDirective:
    return PaperSafetyExitDirective(
        directive_id="directive:net", version=1, position_id="position:net",
        symbol="BTCUSDT", side=PaperSide.LONG,
        effective_closed_until_ms=T0 + 60_000, issued_at=OPENED,
        valid_until_ms=T0 + 600_000, final_safety_authorization=True,
        reason="NET_PNL_PROTECTION", correlation_id="correlation:net",
        causation_id="command:net", mode=ExecutionMode.PAPER,
    )


def _evaluate_exit(bar: PaperFillCandle):
    return evaluate_paper_exit_window(
        position_id="position:net", cursor_id="cursor:net",
        expected_position_version=0, expected_cursor_version=0,
        cursor_closed_until_ms=T0, candles=(bar,),
        market_snapshot_closed_until_ms=T0 + 60_000,
        safety_directive=_directive(), source_command_id="command:net",
        entry_fill_id="fill:entry", symbol="BTCUSDT", side=PaperSide.LONG,
        remaining_quantity=Decimal("1"), stop_price=Decimal("90"),
        target_price=Decimal("110"), evaluation_policy_id="STOP_FIRST_CONSERVATIVE",
        correlation_id="correlation:net", causation_id="command:net",
    )


def test_canonical_exit_marks_net_reason_and_stop_wins_same_boundary():
    assert _evaluate_exit(_candle()).trigger.cause is PaperExitCause.NET_PNL_PROTECTION
    assert _evaluate_exit(_candle(stop=True)).trigger.cause is PaperExitCause.STOP_LOSS
