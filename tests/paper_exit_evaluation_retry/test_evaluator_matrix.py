from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal, getcontext

import pytest

from app.engine_paper.exit_evaluator import (
    MAX_EVALUATION_CANDLES,
    PaperExitEvaluationOutcome,
    PaperSafetyExitDirective,
    evaluate_paper_exit_window,
)
from app.engine_paper.fill_simulator import PaperFillCandle
from app.engine_safety import ExecutionMode, PaperExitCause, PaperSide


T0 = 1_785_340_800_000
NOW = datetime.fromtimestamp(T0 / 1000, tz=timezone.utc)
POLICY = "exit-evaluation:stop-target:v1"


def candle(index: int, *, side=PaperSide.LONG, trigger=None, **changes):
    if side is PaperSide.LONG:
        high, low = Decimal("105"), Decimal("95")
        if trigger == "STOP":
            low = Decimal("90")
        elif trigger == "TARGET":
            high = Decimal("110")
    else:
        high, low = Decimal("105"), Decimal("95")
        if trigger == "STOP":
            high = Decimal("110")
        elif trigger == "TARGET":
            low = Decimal("90")
    values = {
        "symbol": "BTCUSDT",
        "timeframe": "1m",
        "open_time_ms": T0 + index * 60_000,
        "close_boundary_ms": T0 + (index + 1) * 60_000,
        "open_price": Decimal("100"),
        "high_price": high,
        "low_price": low,
        "close_price": Decimal("101"),
        "is_closed": True,
        "observed_closed_until_ms": T0 + (index + 1) * 60_000,
    }
    values.update(changes)
    return PaperFillCandle(**values)


def evaluate(candles, *, side=PaperSide.LONG, safety=None, snapshot=None, **changes):
    values = {
        "position_id": "position:exit:1",
        "cursor_id": "cursor:exit:1",
        "expected_position_version": 0,
        "expected_cursor_version": 0,
        "cursor_closed_until_ms": T0,
        "candles": tuple(candles),
        "market_snapshot_closed_until_ms": (
            snapshot
            if snapshot is not None
            else (candles[-1].close_boundary_ms if candles else T0)
        ),
        "safety_directive": safety,
        "source_command_id": "command:exit:1",
        "entry_fill_id": "fill:entry:1",
        "symbol": "BTCUSDT",
        "side": side,
        "remaining_quantity": Decimal("2"),
        "stop_price": Decimal("90") if side is PaperSide.LONG else Decimal("110"),
        "target_price": Decimal("110") if side is PaperSide.LONG else Decimal("90"),
        "evaluation_policy_id": POLICY,
        "correlation_id": "correlation:exit:1",
        "causation_id": "causation:exit:1",
    }
    values.update(changes)
    return evaluate_paper_exit_window(**values)


CASES = [
    (side, cause, trigger_index)
    for side in (PaperSide.LONG, PaperSide.SHORT)
    for cause in ("STOP", "TARGET")
    for trigger_index in range(MAX_EVALUATION_CANDLES)
]


@pytest.mark.parametrize(("side", "trigger_kind", "trigger_index"), CASES)
def test_256_earliest_market_trigger_matrix(side, trigger_kind, trigger_index):
    candles = [
        candle(
            index,
            side=side,
            trigger=trigger_kind if index == trigger_index else None,
        )
        for index in range(trigger_index + 1)
    ]
    result = evaluate(candles, side=side)
    assert result.outcome is PaperExitEvaluationOutcome.EXIT_TRIGGERED
    assert result.trigger.cause is (
        PaperExitCause.STOP_LOSS
        if trigger_kind == "STOP"
        else PaperExitCause.TAKE_PROFIT
    )
    assert result.trigger.trigger_source_closed_until_ms == (
        T0 + (trigger_index + 1) * 60_000
    )
    assert result.evaluated_close_boundaries_ms[-1] == (
        result.trigger.trigger_source_closed_until_ms
    )


@pytest.mark.parametrize("side", [PaperSide.LONG, PaperSide.SHORT])
def test_boundary_equality_and_intrabar_conflict_are_stop_first(side):
    bar = candle(0, side=side, trigger="STOP")
    bar = replace(
        bar,
        high_price=Decimal("110"),
        low_price=Decimal("90"),
    )
    result = evaluate((bar,), side=side)
    assert result.trigger.cause is PaperExitCause.STOP_LOSS
    assert result.trigger.stop_hit is True
    assert result.trigger.target_hit is True


def safety(boundary, *, valid_until=None, **changes):
    values = {
        "directive_id": "safety:exit:1",
        "version": 1,
        "position_id": "position:exit:1",
        "symbol": "BTCUSDT",
        "side": PaperSide.LONG,
        "effective_closed_until_ms": boundary,
        "issued_at": NOW,
        "valid_until_ms": valid_until or boundary + 600_000,
        "final_safety_authorization": True,
        "reason": "operator-risk-stop",
        "correlation_id": "correlation:safety:1",
        "causation_id": "causation:safety:1",
        "mode": ExecutionMode.PAPER,
    }
    values.update(changes)
    return PaperSafetyExitDirective(**values)


def test_safety_wins_at_same_boundary():
    directive = safety(T0 + 60_000)
    result = evaluate(
        (candle(0, trigger="STOP"),),
        safety=directive,
    )
    assert result.trigger.cause is PaperExitCause.SYSTEM_SAFETY_EXIT
    assert result.trigger.safety_directive_id == directive.directive_id
    assert result.trigger.trigger_candle_open_time_ms is None


def test_earlier_market_trigger_wins_before_safety():
    result = evaluate(
        (candle(0, trigger="TARGET"), candle(1)),
        safety=safety(T0 + 120_000),
    )
    assert result.trigger.cause is PaperExitCause.TAKE_PROFIT
    assert result.trigger.trigger_source_closed_until_ms == T0 + 60_000


def test_safety_before_later_market_trigger_wins():
    result = evaluate(
        (candle(0), candle(1, trigger="TARGET")),
        safety=safety(T0 + 60_000),
    )
    assert result.trigger.cause is PaperExitCause.SYSTEM_SAFETY_EXIT


def test_no_trigger_returns_entire_contiguous_window():
    bars = tuple(candle(index) for index in range(64))
    result = evaluate(bars)
    assert result.outcome is PaperExitEvaluationOutcome.NO_EXIT_TRIGGER
    assert len(result.evaluated_close_boundaries_ms) == 64


@pytest.mark.parametrize(
    ("bars", "changes", "outcome"),
    [
        ((), {}, PaperExitEvaluationOutcome.EMPTY_WINDOW),
        (
            tuple(candle(index) for index in range(65)),
            {},
            PaperExitEvaluationOutcome.WINDOW_TOO_LARGE,
        ),
        (
            (candle(1),),
            {},
            PaperExitEvaluationOutcome.WINDOW_START_MISMATCH,
        ),
        (
            (candle(0), candle(2)),
            {},
            PaperExitEvaluationOutcome.MARKET_DATA_GAP,
        ),
        (
            (candle(0), candle(0)),
            {},
            PaperExitEvaluationOutcome.DUPLICATE_CANDLE,
        ),
        (
            (candle(0), replace(candle(0), close_price=Decimal("102"))),
            {},
            PaperExitEvaluationOutcome.CANDLE_CONFLICT,
        ),
        (
            (candle(0),),
            {"snapshot": T0},
            PaperExitEvaluationOutcome.FUTURE_DATA_REJECTED,
        ),
        (
            (replace(candle(0), is_closed=False),),
            {},
            PaperExitEvaluationOutcome.INVALID_CANDLE,
        ),
        (
            (replace(candle(0), symbol="ETHUSDT"),),
            {},
            PaperExitEvaluationOutcome.SYMBOL_MISMATCH,
        ),
    ],
)
def test_window_fail_closed_matrix(bars, changes, outcome):
    assert evaluate(bars, **changes).outcome is outcome


def test_expired_safety_is_typed_failure():
    directive = safety(T0 + 60_000, valid_until=T0)
    result = evaluate(
        (candle(0),),
        safety=directive,
        snapshot=T0 + 60_000,
    )
    assert result.outcome is PaperExitEvaluationOutcome.SAFETY_DIRECTIVE_EXPIRED


def test_safety_cannot_skip_unprocessed_history():
    directive = safety(T0 + 120_000)
    result = evaluate(
        (candle(0),),
        safety=directive,
    )
    assert result.outcome is PaperExitEvaluationOutcome.NO_EXIT_TRIGGER
    assert result.evaluated_close_boundaries_ms == (T0 + 60_000,)


def test_evaluator_is_decimal_context_and_timezone_deterministic():
    bars = (candle(0), candle(1, trigger="TARGET"))
    original = getcontext().prec
    try:
        getcontext().prec = 6
        first = evaluate(bars)
        getcontext().prec = 50
        second = evaluate(bars)
    finally:
        getcontext().prec = original
    assert first == second


def test_trigger_candidate_contains_no_fill_price_or_pnl():
    trigger = evaluate((candle(0, trigger="STOP"),)).trigger
    assert "fill_price" not in trigger.__dataclass_fields__
    assert "realized_pnl" not in trigger.__dataclass_fields__
