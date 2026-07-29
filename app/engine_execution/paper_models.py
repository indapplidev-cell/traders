"""Immutable PAPER command, order, and fill contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.engine_safety.paper_domain import (
    ExecutionMode,
    PaperInputHealthStatus,
    PaperOrderState,
    PaperOrderType,
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


@dataclass(frozen=True, slots=True)
class PaperExecutionCommand:
    """Authoritative PAPER command.

    ``requested_quantity`` is the sole authoritative size. When supplied,
    ``requested_notional`` is a derived equality check only.
    """

    command_id: str
    idempotency_key: str
    mode: ExecutionMode
    symbol: str
    side: PaperSide
    order_type: PaperOrderType
    requested_quantity: Decimal
    requested_notional: Decimal | None
    entry_reference_price: Decimal
    stop_price: Decimal
    target_price: Decimal
    strategy_decision_id: str
    risk_decision_id: str
    setup_id: str
    pipeline_run_id: str
    analysis_result_id: str
    closed_until_ms: int
    created_at: datetime
    valid_until_ms: int
    configuration_fingerprint: str
    simulation_policy_id: str
    fee_policy_id: str
    slippage_policy_id: str
    latency_policy_id: str
    final_paper_approval: bool
    input_health_status: PaperInputHealthStatus
    future_bars_used: bool

    def __post_init__(self) -> None:
        for name in (
            "command_id",
            "idempotency_key",
            "strategy_decision_id",
            "risk_decision_id",
            "setup_id",
            "pipeline_run_id",
            "analysis_result_id",
            "configuration_fingerprint",
            "simulation_policy_id",
            "fee_policy_id",
            "slippage_policy_id",
            "latency_policy_id",
        ):
            object.__setattr__(self, name, require_identity(getattr(self, name), name))
        object.__setattr__(self, "mode", require_paper_mode(self.mode))
        object.__setattr__(self, "symbol", normalize_symbol(self.symbol))
        object.__setattr__(
            self,
            "side",
            require_enum(
                self.side,
                PaperSide,
                PaperReasonCode.PAPER_INPUT_SIDE_INVALID,
                "side",
            ),
        )
        object.__setattr__(
            self,
            "order_type",
            require_enum(
                self.order_type,
                PaperOrderType,
                PaperReasonCode.PAPER_ORDER_TYPE_UNSUPPORTED,
                "order_type",
            ),
        )
        require_decimal(
            self.requested_quantity,
            "requested_quantity",
            positive=True,
            reason_code=PaperReasonCode.PAPER_INPUT_QUANTITY_INVALID,
        )
        if self.requested_notional is not None:
            require_decimal(
                self.requested_notional,
                "requested_notional",
                positive=True,
                reason_code=PaperReasonCode.PAPER_INPUT_NOTIONAL_INVALID,
            )
        for name in ("entry_reference_price", "stop_price", "target_price"):
            require_decimal(getattr(self, name), name, positive=True)
        if self.requested_notional is not None:
            expected_notional = self.requested_quantity * self.entry_reference_price
            if self.requested_notional != expected_notional:
                fail(
                    PaperReasonCode.PAPER_INPUT_NOTIONAL_INVALID,
                    "requested notional must match authoritative quantity",
                    "requested_notional",
                )
        if self.side is PaperSide.LONG:
            valid_geometry = self.stop_price < self.entry_reference_price < self.target_price
        else:
            valid_geometry = self.target_price < self.entry_reference_price < self.stop_price
        if not valid_geometry:
            fail(
                PaperReasonCode.PAPER_INPUT_STOP_TARGET_INVALID,
                "invalid stop-entry-target ordering",
                "stop_price",
            )
        require_nonnegative_int(self.closed_until_ms, "closed_until_ms")
        require_nonnegative_int(self.valid_until_ms, "valid_until_ms")
        if self.valid_until_ms < self.closed_until_ms:
            fail(
                PaperReasonCode.PAPER_INPUT_VALIDITY_INVALID,
                "validity precedes source boundary",
                "valid_until_ms",
            )
        require_utc(self.created_at, "created_at")
        if self.final_paper_approval is not True:
            fail(
                PaperReasonCode.PAPER_RISK_APPROVAL_MISSING,
                "final paper approval is required",
                "final_paper_approval",
            )
        if self.future_bars_used is not False:
            fail(
                PaperReasonCode.PAPER_SAFETY_FUTURE_DATA_DETECTED,
                "future data is forbidden",
                "future_bars_used",
            )
        raw_health = getattr(self.input_health_status, "value", self.input_health_status)
        try:
            health = PaperInputHealthStatus(str(raw_health).upper())
        except ValueError:
            text = str(raw_health).upper()
            if "STALE" in text:
                code = PaperReasonCode.PAPER_SAFETY_SOURCE_STALE
            elif "DEGRADED" in text:
                code = PaperReasonCode.PAPER_SAFETY_HEALTH_DEGRADED
            else:
                code = PaperReasonCode.PAPER_SAFETY_HEALTH_UNKNOWN
            fail(code, "input health is not executable", "input_health_status")
        object.__setattr__(self, "input_health_status", health)


@dataclass(frozen=True, slots=True)
class PaperOrder:
    order_id: str
    command_id: str
    idempotency_key: str
    symbol: str
    side: PaperSide
    order_type: PaperOrderType
    state: PaperOrderState
    requested_quantity: Decimal
    filled_quantity: Decimal
    average_fill_price: Decimal | None
    total_fees: Decimal
    created_at: datetime
    updated_at: datetime
    version: int
    reason_code: PaperReasonCode
    applied_fill_id: str | None = None

    def __post_init__(self) -> None:
        for name in ("order_id", "command_id", "idempotency_key"):
            object.__setattr__(self, name, require_identity(getattr(self, name), name))
        object.__setattr__(self, "symbol", normalize_symbol(self.symbol))
        object.__setattr__(
            self,
            "side",
            require_enum(self.side, PaperSide, PaperReasonCode.PAPER_INPUT_SIDE_INVALID, "side"),
        )
        object.__setattr__(
            self,
            "order_type",
            require_enum(
                self.order_type,
                PaperOrderType,
                PaperReasonCode.PAPER_ORDER_TYPE_UNSUPPORTED,
                "order_type",
            ),
        )
        object.__setattr__(
            self,
            "state",
            require_enum(
                self.state,
                PaperOrderState,
                PaperReasonCode.PAPER_ORDER_INVALID_TRANSITION,
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
        require_decimal(
            self.requested_quantity,
            "requested_quantity",
            positive=True,
            reason_code=PaperReasonCode.PAPER_INPUT_QUANTITY_INVALID,
        )
        require_decimal(
            self.filled_quantity,
            "filled_quantity",
            nonnegative=True,
            reason_code=PaperReasonCode.PAPER_FILL_INVALID,
        )
        require_decimal(
            self.total_fees,
            "total_fees",
            nonnegative=True,
            reason_code=PaperReasonCode.PAPER_FILL_INVALID,
        )
        if self.average_fill_price is not None:
            require_decimal(self.average_fill_price, "average_fill_price", positive=True)
        require_utc(self.created_at, "created_at")
        require_utc(self.updated_at, "updated_at")
        if self.updated_at < self.created_at:
            fail(
                PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION,
                "order timestamp regressed",
                "updated_at",
            )
        require_nonnegative_int(self.version, "version")
        if self.state is PaperOrderState.FILLED:
            if (
                self.filled_quantity != self.requested_quantity
                or self.average_fill_price is None
                or self.applied_fill_id is None
            ):
                fail(
                    PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION,
                    "filled order is incomplete",
                    "filled_quantity",
                )
            object.__setattr__(
                self,
                "applied_fill_id",
                require_identity(self.applied_fill_id, "applied_fill_id"),
            )
        elif (
            self.filled_quantity != Decimal("0")
            or self.average_fill_price is not None
            or self.total_fees != Decimal("0")
            or self.applied_fill_id is not None
        ):
            fail(
                PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION,
                "unfilled order carries fill accounting",
                "filled_quantity",
            )


@dataclass(frozen=True, slots=True)
class PaperFill:
    fill_id: str
    order_id: str
    idempotency_key: str
    symbol: str
    side: PaperSide
    quantity: Decimal
    price: Decimal
    fee_amount: Decimal
    fee_asset: str
    filled_at: datetime
    source_closed_until_ms: int
    simulation_policy_id: str
    slippage_policy_id: str
    fee_policy_id: str
    latency_policy_id: str
    future_bars_used: bool = False

    def __post_init__(self) -> None:
        for name in (
            "fill_id",
            "order_id",
            "idempotency_key",
            "simulation_policy_id",
            "slippage_policy_id",
            "fee_policy_id",
            "latency_policy_id",
        ):
            object.__setattr__(self, name, require_identity(getattr(self, name), name))
        object.__setattr__(self, "symbol", normalize_symbol(self.symbol))
        object.__setattr__(
            self,
            "side",
            require_enum(self.side, PaperSide, PaperReasonCode.PAPER_INPUT_SIDE_INVALID, "side"),
        )
        require_decimal(
            self.quantity,
            "quantity",
            positive=True,
            reason_code=PaperReasonCode.PAPER_FILL_INVALID,
        )
        require_decimal(self.price, "price", positive=True)
        require_decimal(
            self.fee_amount,
            "fee_amount",
            nonnegative=True,
            reason_code=PaperReasonCode.PAPER_FILL_INVALID,
        )
        object.__setattr__(self, "fee_asset", normalize_symbol(self.fee_asset))
        require_utc(self.filled_at, "filled_at")
        require_nonnegative_int(self.source_closed_until_ms, "source_closed_until_ms")
        if self.future_bars_used is not False:
            fail(
                PaperReasonCode.PAPER_FILL_FUTURE_DATA,
                "future fill data is forbidden",
                "future_bars_used",
            )
