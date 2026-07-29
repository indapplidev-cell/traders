"""Immutable PAPER position aggregate."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.engine_safety.paper_domain import (
    ExecutionMode,
    PaperPositionState,
    PaperReasonCode,
    PaperSide,
    fail,
    normalize_symbol,
    require_decimal,
    require_enum,
    require_identity,
    require_nonnegative_int,
    require_paper_mode,
    require_utc,
)


PAPER_POSITION_MULTIPLICITY = (
    "ONE_ACTIVE_POSITION_PER_MODE_AND_SYMBOL_PERSISTENCE_ENFORCED_LATER"
)


@dataclass(frozen=True, slots=True)
class PaperPosition:
    position_id: str
    mode: ExecutionMode
    symbol: str
    side: PaperSide
    state: PaperPositionState
    entry_order_id: str
    entry_fill_id: str
    entry_quantity: Decimal
    remaining_quantity: Decimal
    average_entry_price: Decimal
    average_exit_price: Decimal | None
    entry_fees: Decimal
    exit_fees: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    stop_price: Decimal
    target_price: Decimal
    opened_at: datetime
    closed_at: datetime | None
    last_mark_price: Decimal
    last_mark_closed_until_ms: int
    version: int
    reason_code: PaperReasonCode
    exit_fill_id: str | None = None

    def __post_init__(self) -> None:
        for name in ("position_id", "entry_order_id", "entry_fill_id"):
            object.__setattr__(self, name, require_identity(getattr(self, name), name))
        object.__setattr__(self, "mode", require_paper_mode(self.mode))
        object.__setattr__(self, "symbol", normalize_symbol(self.symbol))
        object.__setattr__(
            self,
            "side",
            require_enum(self.side, PaperSide, PaperReasonCode.PAPER_INPUT_SIDE_INVALID, "side"),
        )
        object.__setattr__(
            self,
            "state",
            require_enum(
                self.state,
                PaperPositionState,
                PaperReasonCode.PAPER_POSITION_INVALID_TRANSITION,
                "state",
            ),
        )
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
        for name in (
            "entry_quantity",
            "average_entry_price",
            "stop_price",
            "target_price",
            "last_mark_price",
        ):
            require_decimal(
                getattr(self, name),
                name,
                positive=True,
                reason_code=PaperReasonCode.PAPER_POSITION_INVALID_TRANSITION,
            )
        require_decimal(
            self.remaining_quantity,
            "remaining_quantity",
            nonnegative=True,
            reason_code=PaperReasonCode.PAPER_POSITION_NEGATIVE_REMAINDER,
        )
        if self.remaining_quantity > self.entry_quantity:
            fail(
                PaperReasonCode.PAPER_POSITION_NEGATIVE_REMAINDER,
                "remaining quantity exceeds entry quantity",
                "remaining_quantity",
            )
        if self.average_exit_price is not None:
            require_decimal(
                self.average_exit_price,
                "average_exit_price",
                positive=True,
                reason_code=PaperReasonCode.PAPER_POSITION_INVALID_TRANSITION,
            )
        for name in ("entry_fees", "exit_fees"):
            require_decimal(
                getattr(self, name),
                name,
                nonnegative=True,
                reason_code=PaperReasonCode.PAPER_POSITION_INVALID_TRANSITION,
            )
        for name in ("realized_pnl", "unrealized_pnl"):
            require_decimal(
                getattr(self, name),
                name,
                reason_code=PaperReasonCode.PAPER_POSITION_INVALID_TRANSITION,
            )
        require_utc(self.opened_at, "opened_at")
        if self.closed_at is not None:
            require_utc(self.closed_at, "closed_at")
            if self.closed_at < self.opened_at:
                fail(
                    PaperReasonCode.PAPER_INPUT_TIME_INVALID,
                    "position closed before it opened",
                    "closed_at",
                )
        require_nonnegative_int(self.last_mark_closed_until_ms, "last_mark_closed_until_ms")
        require_nonnegative_int(self.version, "version")
        if self.state in {PaperPositionState.OPEN, PaperPositionState.CLOSING}:
            if (
                self.remaining_quantity <= 0
                or self.closed_at is not None
                or self.average_exit_price is not None
                or self.exit_fill_id is not None
            ):
                fail(
                    PaperReasonCode.PAPER_POSITION_INVALID_TRANSITION,
                    "active position invariant failed",
                    "state",
                )
        if self.state is PaperPositionState.CLOSED:
            if (
                self.remaining_quantity != Decimal("0")
                or self.closed_at is None
                or self.average_exit_price is None
                or self.exit_fill_id is None
            ):
                fail(
                    PaperReasonCode.PAPER_POSITION_INVALID_TRANSITION,
                    "closed position invariant failed",
                    "state",
                )
            object.__setattr__(
                self,
                "exit_fill_id",
                require_identity(self.exit_fill_id, "exit_fill_id"),
            )
