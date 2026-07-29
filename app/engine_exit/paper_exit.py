"""Immutable PAPER exit decisions and conservative intrabar resolution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.engine_journal.paper_events import PaperDomainEvent
from app.engine_position.paper_models import PaperPosition
from app.engine_safety.paper_domain import (
    PaperEventType,
    PaperExitCause,
    PaperPositionState,
    PaperReasonCode,
    PaperSide,
    fail,
    require_decimal,
    require_enum,
    require_identity,
    require_nonnegative_int,
    require_utc,
)


PAPER_INTRABAR_CONFLICT_POLICY = "STOP_FIRST_CONSERVATIVE"


@dataclass(frozen=True, slots=True)
class PaperExitResolution:
    cause: PaperExitCause | None
    reason_code: PaperReasonCode


@dataclass(frozen=True, slots=True)
class PaperExitDecision:
    exit_decision_id: str
    idempotency_key: str
    position_id: str
    position_version: int
    cause: PaperExitCause
    decision_price: Decimal
    requested_close_quantity: Decimal
    source_closed_until_ms: int
    decided_at: datetime
    reason_code: PaperReasonCode

    def __post_init__(self) -> None:
        for name in ("exit_decision_id", "idempotency_key", "position_id"):
            object.__setattr__(self, name, require_identity(getattr(self, name), name))
        require_nonnegative_int(self.position_version, "position_version")
        object.__setattr__(
            self,
            "cause",
            require_enum(
                self.cause,
                PaperExitCause,
                PaperReasonCode.PAPER_EXIT_CAUSE_UNSUPPORTED,
                "cause",
            ),
        )
        require_decimal(self.decision_price, "decision_price", positive=True)
        require_decimal(
            self.requested_close_quantity,
            "requested_close_quantity",
            positive=True,
            reason_code=PaperReasonCode.PAPER_INPUT_QUANTITY_INVALID,
        )
        require_nonnegative_int(self.source_closed_until_ms, "source_closed_until_ms")
        require_utc(self.decided_at, "decided_at")
        object.__setattr__(
            self,
            "reason_code",
            require_enum(
                self.reason_code,
                PaperReasonCode,
                PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION,
                "reason_code",
            ),
        )


def resolve_intrabar_exit(
    position: PaperPosition,
    *,
    high_price: Decimal,
    low_price: Decimal,
) -> PaperExitResolution:
    if position.state not in {PaperPositionState.OPEN, PaperPositionState.CLOSING}:
        fail(
            PaperReasonCode.PAPER_POSITION_INVALID_TRANSITION,
            "exit evaluation requires an active position",
            "position.state",
        )
    high = require_decimal(high_price, "high_price", positive=True)
    low = require_decimal(low_price, "low_price", positive=True)
    if low > high:
        fail(
            PaperReasonCode.PAPER_INPUT_PRICE_INVALID,
            "intrabar low exceeds high",
            "low_price",
        )
    if position.side is PaperSide.LONG:
        stop_hit = low <= position.stop_price
        target_hit = high >= position.target_price
    else:
        stop_hit = high >= position.stop_price
        target_hit = low <= position.target_price
    if stop_hit and target_hit:
        return PaperExitResolution(
            PaperExitCause.STOP_LOSS,
            PaperReasonCode.PAPER_EXIT_STOP_FIRST_CONFLICT,
        )
    if stop_hit:
        return PaperExitResolution(
            PaperExitCause.STOP_LOSS,
            PaperReasonCode.PAPER_EXIT_STOP_LOSS_TRIGGERED,
        )
    if target_hit:
        return PaperExitResolution(
            PaperExitCause.TAKE_PROFIT,
            PaperReasonCode.PAPER_EXIT_TAKE_PROFIT_TRIGGERED,
        )
    return PaperExitResolution(None, PaperReasonCode.PAPER_EXIT_NO_TRIGGER)


def create_exit_decision(
    position: PaperPosition,
    *,
    exit_decision_id: str,
    idempotency_key: str,
    expected_position_version: int,
    cause: PaperExitCause,
    decision_price: Decimal,
    source_closed_until_ms: int,
    decided_at: datetime,
    reason_code: PaperReasonCode,
    event_id: str,
    future_bars_used: bool = False,
) -> tuple[PaperExitDecision, PaperDomainEvent]:
    if expected_position_version != position.version:
        fail(
            PaperReasonCode.PAPER_EXIT_VERSION_CONFLICT,
            "stale position version",
            "expected_position_version",
        )
    if position.state is not PaperPositionState.OPEN:
        fail(
            PaperReasonCode.PAPER_POSITION_INVALID_TRANSITION,
            "exit decision requires open position",
            "position.state",
        )
    if future_bars_used is not False:
        fail(
            PaperReasonCode.PAPER_SAFETY_FUTURE_DATA_DETECTED,
            "future exit data is forbidden",
            "future_bars_used",
        )
    decision = PaperExitDecision(
        exit_decision_id=exit_decision_id,
        idempotency_key=idempotency_key,
        position_id=position.position_id,
        position_version=position.version,
        cause=cause,
        decision_price=decision_price,
        requested_close_quantity=position.remaining_quantity,
        source_closed_until_ms=source_closed_until_ms,
        decided_at=decided_at,
        reason_code=reason_code,
    )
    event = PaperDomainEvent(
        event_id=event_id,
        event_type=PaperEventType.PAPER_EXIT_TRIGGERED,
        occurred_at=decided_at,
        aggregate_type="paper_exit",
        aggregate_id=decision.exit_decision_id,
        correlation_id=position.entry_order_id,
        causation_id=position.position_id,
        reason_code=decision.reason_code,
        aggregate_version=position.version,
    )
    return decision, event
