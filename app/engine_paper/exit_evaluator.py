"""Pure deterministic evaluation of one bounded PAPER exit window."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation, localcontext
from enum import StrEnum

from app.engine_market_data.timeframe import is_aligned_to_timeframe
from app.engine_paper.exit_evaluation_cursor import (
    MAX_EXIT_EVALUATION_WINDOW_CANDLES,
    ONE_MINUTE_MS,
)
from app.engine_paper.fill_simulator import PaperFillCandle
from app.engine_safety.paper_domain import (
    ExecutionMode,
    PaperExitCause,
    PaperSide,
    normalize_symbol,
    require_identity,
    require_nonnegative_int,
    require_utc,
)


MAX_EVALUATION_CANDLES = MAX_EXIT_EVALUATION_WINDOW_CANDLES
PAPER_EXIT_EVALUATION_POLICY_ID = "STOP_FIRST_CONSERVATIVE"
PAPER_EXIT_EVALUATION_POLICY_VERSION = 1


def _identity(value: object, name: str) -> str:
    return require_identity(value, name)


def _decimal(value: object, name: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, Decimal):
        raise TypeError(f"{name} must be Decimal")
    try:
        if not value.is_finite() or value <= 0:
            raise ValueError(f"{name} must be finite and positive")
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name} must be finite and positive") from exc
    return value


@dataclass(frozen=True, slots=True)
class PaperSafetyExitDirective:
    directive_id: str
    version: int
    position_id: str
    symbol: str
    side: PaperSide
    effective_closed_until_ms: int
    issued_at: datetime
    valid_until_ms: int
    final_safety_authorization: bool
    reason: str
    correlation_id: str
    causation_id: str
    mode: ExecutionMode

    def __post_init__(self) -> None:
        for name in (
            "directive_id",
            "position_id",
            "reason",
            "correlation_id",
            "causation_id",
        ):
            object.__setattr__(self, name, _identity(getattr(self, name), name))
        require_nonnegative_int(self.version, "version")
        object.__setattr__(self, "symbol", normalize_symbol(self.symbol))
        object.__setattr__(self, "side", PaperSide(self.side))
        boundary = require_nonnegative_int(
            self.effective_closed_until_ms, "effective_closed_until_ms"
        )
        if not is_aligned_to_timeframe(boundary, "1m"):
            raise ValueError("safety effective boundary must be 1m aligned")
        issued = require_utc(self.issued_at, "issued_at")
        valid_until = require_nonnegative_int(self.valid_until_ms, "valid_until_ms")
        if valid_until < int(issued.timestamp() * 1000):
            raise ValueError("safety directive expires before issuance")
        if self.final_safety_authorization is not True:
            raise ValueError("final safety authorization is required")
        if ExecutionMode(self.mode) is not ExecutionMode.PAPER:
            raise ValueError("safety directive mode must be PAPER")
        object.__setattr__(self, "mode", ExecutionMode.PAPER)


@dataclass(frozen=True, slots=True)
class PaperExitTriggerCandidate:
    position_id: str
    cursor_id: str
    expected_position_version: int
    expected_cursor_version: int
    cause: PaperExitCause
    trigger_source_closed_until_ms: int
    trigger_candle_open_time_ms: int | None
    stop_hit: bool
    target_hit: bool
    safety_directive_id: str | None
    source_command_id: str
    entry_fill_id: str
    symbol: str
    side: PaperSide
    remaining_quantity: Decimal
    evaluation_policy_id: str
    evaluation_policy_version: int
    correlation_id: str
    causation_id: str

    def __post_init__(self) -> None:
        for name in (
            "position_id",
            "cursor_id",
            "source_command_id",
            "entry_fill_id",
            "evaluation_policy_id",
            "correlation_id",
            "causation_id",
        ):
            object.__setattr__(self, name, _identity(getattr(self, name), name))
        for name in ("expected_position_version", "expected_cursor_version"):
            require_nonnegative_int(getattr(self, name), name)
        object.__setattr__(self, "cause", PaperExitCause(self.cause))
        boundary = require_nonnegative_int(
            self.trigger_source_closed_until_ms,
            "trigger_source_closed_until_ms",
        )
        if not is_aligned_to_timeframe(boundary, "1m"):
            raise ValueError("trigger boundary must be 1m aligned")
        if self.trigger_candle_open_time_ms is not None:
            opened = require_nonnegative_int(
                self.trigger_candle_open_time_ms,
                "trigger_candle_open_time_ms",
            )
            if opened + ONE_MINUTE_MS != boundary:
                raise ValueError("trigger candle boundary mismatch")
        if not isinstance(self.stop_hit, bool) or not isinstance(self.target_hit, bool):
            raise TypeError("trigger hit flags must be boolean")
        if self.cause is PaperExitCause.SYSTEM_SAFETY_EXIT:
            if self.safety_directive_id is None or self.trigger_candle_open_time_ms is not None:
                raise ValueError("safety trigger identity mismatch")
            object.__setattr__(
                self,
                "safety_directive_id",
                _identity(self.safety_directive_id, "safety_directive_id"),
            )
        elif self.safety_directive_id is not None:
            raise ValueError("market trigger may not carry a safety directive")
        object.__setattr__(self, "symbol", normalize_symbol(self.symbol))
        object.__setattr__(self, "side", PaperSide(self.side))
        _decimal(self.remaining_quantity, "remaining_quantity")
        if self.evaluation_policy_version != PAPER_EXIT_EVALUATION_POLICY_VERSION:
            raise ValueError("unsupported evaluation policy version")


class PaperExitEvaluationOutcome(StrEnum):
    NO_EXIT_TRIGGER = "NO_EXIT_TRIGGER"
    EXIT_TRIGGERED = "EXIT_TRIGGERED"
    EMPTY_WINDOW = "EMPTY_WINDOW"
    WINDOW_TOO_LARGE = "WINDOW_TOO_LARGE"
    WINDOW_START_MISMATCH = "WINDOW_START_MISMATCH"
    MARKET_DATA_GAP = "MARKET_DATA_GAP"
    DUPLICATE_CANDLE = "DUPLICATE_CANDLE"
    CANDLE_CONFLICT = "CANDLE_CONFLICT"
    FUTURE_DATA_REJECTED = "FUTURE_DATA_REJECTED"
    INVALID_CANDLE = "INVALID_CANDLE"
    SYMBOL_MISMATCH = "SYMBOL_MISMATCH"
    SIDE_MISMATCH = "SIDE_MISMATCH"
    INVALID_STOP_TARGET = "INVALID_STOP_TARGET"
    POLICY_MISMATCH = "POLICY_MISMATCH"
    SAFETY_DIRECTIVE_INVALID = "SAFETY_DIRECTIVE_INVALID"
    SAFETY_DIRECTIVE_EXPIRED = "SAFETY_DIRECTIVE_EXPIRED"


@dataclass(frozen=True, slots=True)
class PaperExitEvaluationResult:
    outcome: PaperExitEvaluationOutcome
    evaluated_close_boundaries_ms: tuple[int, ...] = ()
    trigger: PaperExitTriggerCandidate | None = None
    reason_code: str = "PAPER_EXIT_EVALUATION_OK"

    @property
    def successful(self) -> bool:
        return self.outcome in {
            PaperExitEvaluationOutcome.NO_EXIT_TRIGGER,
            PaperExitEvaluationOutcome.EXIT_TRIGGERED,
        }


def _failure(
    outcome: PaperExitEvaluationOutcome,
    reason: str | None = None,
) -> PaperExitEvaluationResult:
    return PaperExitEvaluationResult(
        outcome,
        reason_code=reason or f"PAPER_EXIT_{outcome.value}",
    )


def evaluate_paper_exit_window(
    *,
    position_id: str,
    cursor_id: str,
    expected_position_version: int,
    expected_cursor_version: int,
    cursor_closed_until_ms: int,
    candles: tuple[PaperFillCandle, ...],
    market_snapshot_closed_until_ms: int,
    safety_directive: PaperSafetyExitDirective | None,
    source_command_id: str,
    entry_fill_id: str,
    symbol: str,
    side: PaperSide,
    remaining_quantity: Decimal,
    stop_price: Decimal,
    target_price: Decimal,
    evaluation_policy_id: str,
    correlation_id: str,
    causation_id: str,
) -> PaperExitEvaluationResult:
    """Evaluate explicit immutable inputs with no I/O, clock, or randomness."""

    try:
        normalized_symbol = normalize_symbol(symbol)
        selected_side = PaperSide(side)
        quantity = _decimal(remaining_quantity, "remaining_quantity")
        stop = _decimal(stop_price, "stop_price")
        target = _decimal(target_price, "target_price")
        start = require_nonnegative_int(
            cursor_closed_until_ms, "cursor_closed_until_ms"
        )
        snapshot = require_nonnegative_int(
            market_snapshot_closed_until_ms,
            "market_snapshot_closed_until_ms",
        )
        for name, value in (
            ("position_id", position_id),
            ("cursor_id", cursor_id),
            ("source_command_id", source_command_id),
            ("entry_fill_id", entry_fill_id),
            ("evaluation_policy_id", evaluation_policy_id),
            ("correlation_id", correlation_id),
            ("causation_id", causation_id),
        ):
            _identity(value, name)
        require_nonnegative_int(
            expected_position_version, "expected_position_version"
        )
        require_nonnegative_int(expected_cursor_version, "expected_cursor_version")
    except (TypeError, ValueError):
        return _failure(PaperExitEvaluationOutcome.INVALID_CANDLE)
    if selected_side is PaperSide.LONG:
        if not stop < target:
            return _failure(PaperExitEvaluationOutcome.INVALID_STOP_TARGET)
    elif not target < stop:
        return _failure(PaperExitEvaluationOutcome.INVALID_STOP_TARGET)
    if not isinstance(candles, tuple):
        return _failure(PaperExitEvaluationOutcome.INVALID_CANDLE)
    if not candles:
        return _failure(PaperExitEvaluationOutcome.EMPTY_WINDOW)
    if len(candles) > MAX_EVALUATION_CANDLES:
        return _failure(PaperExitEvaluationOutcome.WINDOW_TOO_LARGE)

    seen: dict[int, tuple[object, ...]] = {}
    boundaries: list[int] = []
    expected_open = start
    for index, candle in enumerate(candles):
        if not isinstance(candle, PaperFillCandle):
            return _failure(PaperExitEvaluationOutcome.INVALID_CANDLE)
        identity = (
            candle.symbol,
            candle.timeframe,
            candle.open_time_ms,
            candle.close_boundary_ms,
            candle.market_values,
            candle.is_closed,
        )
        previous = seen.get(candle.open_time_ms)
        if previous is not None:
            outcome = (
                PaperExitEvaluationOutcome.DUPLICATE_CANDLE
                if previous == identity
                else PaperExitEvaluationOutcome.CANDLE_CONFLICT
            )
            return _failure(outcome)
        seen[candle.open_time_ms] = identity
        if candle.symbol != normalized_symbol:
            return _failure(PaperExitEvaluationOutcome.SYMBOL_MISMATCH)
        if candle.timeframe != "1m" or not candle.is_closed:
            return _failure(PaperExitEvaluationOutcome.INVALID_CANDLE)
        if index == 0 and candle.open_time_ms != start:
            return _failure(PaperExitEvaluationOutcome.WINDOW_START_MISMATCH)
        if candle.open_time_ms != expected_open:
            return _failure(PaperExitEvaluationOutcome.MARKET_DATA_GAP)
        if (
            candle.close_boundary_ms > snapshot
            or candle.observed_closed_until_ms > snapshot
        ):
            return _failure(PaperExitEvaluationOutcome.FUTURE_DATA_REJECTED)
        boundaries.append(candle.close_boundary_ms)
        expected_open = candle.close_boundary_ms

    if safety_directive is not None:
        if not isinstance(safety_directive, PaperSafetyExitDirective):
            return _failure(PaperExitEvaluationOutcome.SAFETY_DIRECTIVE_INVALID)
        if (
            safety_directive.position_id != position_id
            or safety_directive.symbol != normalized_symbol
            or safety_directive.side is not selected_side
            or safety_directive.mode is not ExecutionMode.PAPER
            or safety_directive.effective_closed_until_ms <= start
        ):
            return _failure(PaperExitEvaluationOutcome.SAFETY_DIRECTIVE_INVALID)
        if snapshot > safety_directive.valid_until_ms:
            return _failure(PaperExitEvaluationOutcome.SAFETY_DIRECTIVE_EXPIRED)
        if (
            safety_directive.effective_closed_until_ms <= boundaries[-1]
            and safety_directive.effective_closed_until_ms not in boundaries
        ):
            return _failure(PaperExitEvaluationOutcome.MARKET_DATA_GAP)

    with localcontext() as context:
        context.prec = 80
        for candle in candles:
            safety_here = (
                safety_directive is not None
                and safety_directive.effective_closed_until_ms
                == candle.close_boundary_ms
            )
            if selected_side is PaperSide.LONG:
                stop_hit = candle.low_price <= stop
                target_hit = candle.high_price >= target
            else:
                stop_hit = candle.high_price >= stop
                target_hit = candle.low_price <= target
            if not (safety_here or stop_hit or target_hit):
                continue
            if safety_here:
                cause = PaperExitCause.SYSTEM_SAFETY_EXIT
                opened = None
                directive_id = safety_directive.directive_id
                stop_flag = False
                target_flag = False
            else:
                cause = (
                    PaperExitCause.STOP_LOSS
                    if stop_hit
                    else PaperExitCause.TAKE_PROFIT
                )
                opened = candle.open_time_ms
                directive_id = None
                stop_flag = stop_hit
                target_flag = target_hit
            trigger = PaperExitTriggerCandidate(
                position_id=position_id,
                cursor_id=cursor_id,
                expected_position_version=expected_position_version,
                expected_cursor_version=expected_cursor_version,
                cause=cause,
                trigger_source_closed_until_ms=candle.close_boundary_ms,
                trigger_candle_open_time_ms=opened,
                stop_hit=stop_flag,
                target_hit=target_flag,
                safety_directive_id=directive_id,
                source_command_id=source_command_id,
                entry_fill_id=entry_fill_id,
                symbol=normalized_symbol,
                side=selected_side,
                remaining_quantity=quantity,
                evaluation_policy_id=evaluation_policy_id,
                evaluation_policy_version=PAPER_EXIT_EVALUATION_POLICY_VERSION,
                correlation_id=correlation_id,
                causation_id=causation_id,
            )
            evaluated = tuple(
                boundary for boundary in boundaries
                if boundary <= candle.close_boundary_ms
            )
            return PaperExitEvaluationResult(
                PaperExitEvaluationOutcome.EXIT_TRIGGERED,
                evaluated,
                trigger,
            )
    return PaperExitEvaluationResult(
        PaperExitEvaluationOutcome.NO_EXIT_TRIGGER,
        tuple(boundaries),
    )
