"""Pure deterministic fill simulation for the approved PAPER foundation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import (
    MAX_EMAX,
    MIN_EMIN,
    Context,
    Decimal,
    DecimalException,
    ROUND_CEILING,
    ROUND_FLOOR,
    ROUND_HALF_EVEN,
    localcontext,
)
from enum import StrEnum
from typing import Final

from app.engine_execution.paper_idempotency import (
    order_idempotency_key,
    simulated_close_fill_id,
    simulated_close_fill_idempotency_key,
    simulated_fill_id,
    simulated_fill_idempotency_key,
)
from app.engine_execution.paper_models import PaperExecutionCommand, PaperFill, PaperOrder
from app.engine_market_data.freshness_monitor import close_boundary_ms
from app.engine_market_data.timeframe import (
    is_aligned_to_timeframe,
)
from app.engine_paper.fill_causal_boundary import (
    PaperFillCausalBoundary,
    PaperFillSourceEntityType,
)
from app.engine_paper.fill_policy import (
    PaperFillSimulationPolicy,
    is_numeric_38_18_compatible,
)
from app.engine_paper.fill_roles import PaperFillRole
from app.engine_safety.paper_domain import (
    PaperOrderState,
    PaperDomainError,
    PaperSide,
    normalize_symbol,
    require_identity,
)


BPS_DENOMINATOR: Final = Decimal("10000")
MAX_CANDIDATE_CANDLES: Final = 64
_DECIMAL_PRECISION: Final = 128
_EPOCH_UTC: Final = datetime(1970, 1, 1, tzinfo=timezone.utc)


class SimulatedTradeAction(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class FillSimulationOutcome(StrEnum):
    FILLED = "FILLED"
    NOT_YET_ELIGIBLE = "NOT_YET_ELIGIBLE"
    ELIGIBLE_CANDLE_MISSING = "ELIGIBLE_CANDLE_MISSING"
    MARKET_DATA_GAP = "MARKET_DATA_GAP"
    DUPLICATE_CANDLE = "DUPLICATE_CANDLE"
    CANDLE_CONFLICT = "CANDLE_CONFLICT"
    COMMAND_EXPIRED = "COMMAND_EXPIRED"
    SYMBOL_MISMATCH = "SYMBOL_MISMATCH"
    TIMEFRAME_MISMATCH = "TIMEFRAME_MISMATCH"
    CANDLE_NOT_CLOSED = "CANDLE_NOT_CLOSED"
    FUTURE_DATA_REJECTED = "FUTURE_DATA_REJECTED"
    INVALID_CANDLE = "INVALID_CANDLE"
    INVALID_POLICY = "INVALID_POLICY"
    INVALID_PRECISION = "INVALID_PRECISION"
    INVALID_ORDER_STATE = "INVALID_ORDER_STATE"
    INVALID_QUANTITY = "INVALID_QUANTITY"
    UNSUPPORTED_PARTIAL_FILL = "UNSUPPORTED_PARTIAL_FILL"
    INVALID_SIMULATED_PRICE = "INVALID_SIMULATED_PRICE"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    INTERNAL_INVARIANT_FAILURE = "INTERNAL_INVARIANT_FAILURE"
    INVALID_CAUSAL_BOUNDARY = "INVALID_CAUSAL_BOUNDARY"


@dataclass(frozen=True, slots=True)
class FillCandleValidationError(ValueError):
    outcome: FillSimulationOutcome
    public_message: str
    field_path: str | None = None

    def __post_init__(self) -> None:
        message = str(self.public_message).strip() or self.outcome.value
        object.__setattr__(self, "public_message", message[:160])
        if self.field_path is not None:
            object.__setattr__(self, "field_path", str(self.field_path)[:80])
        ValueError.__init__(self, self.public_message)


def _candle_fail(
    outcome: FillSimulationOutcome,
    message: str,
    field_path: str,
) -> None:
    raise FillCandleValidationError(outcome, message, field_path)


def _nonnegative_int(value: object, field_path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        _candle_fail(
            FillSimulationOutcome.INVALID_CANDLE,
            "nonnegative integer required",
            field_path,
        )
    return value


def _price(value: object, field_path: str) -> Decimal:
    if (
        isinstance(value, bool)
        or not isinstance(value, Decimal)
        or not value.is_finite()
        or value <= 0
    ):
        _candle_fail(
            FillSimulationOutcome.INVALID_CANDLE,
            "positive finite Decimal required",
            field_path,
        )
    return value


@dataclass(frozen=True, slots=True)
class PaperFillCandle:
    """Narrow exact-Decimal adapter with an exclusive close boundary."""

    symbol: str
    timeframe: str
    open_time_ms: int
    close_boundary_ms: int
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    is_closed: bool
    observed_closed_until_ms: int

    def __post_init__(self) -> None:
        try:
            symbol = normalize_symbol(self.symbol)
        except PaperDomainError as exc:
            raise FillCandleValidationError(
                FillSimulationOutcome.INVALID_CANDLE,
                "invalid candle symbol",
                "symbol",
            ) from exc
        object.__setattr__(self, "symbol", symbol)
        if self.timeframe != "1m":
            _candle_fail(
                FillSimulationOutcome.TIMEFRAME_MISMATCH,
                "fill candle timeframe must be 1m",
                "timeframe",
            )
        opened = _nonnegative_int(self.open_time_ms, "open_time_ms")
        boundary = _nonnegative_int(self.close_boundary_ms, "close_boundary_ms")
        observed = _nonnegative_int(
            self.observed_closed_until_ms,
            "observed_closed_until_ms",
        )
        if not is_aligned_to_timeframe(opened, "1m"):
            _candle_fail(
                FillSimulationOutcome.INVALID_CANDLE,
                "candle open is not 1m aligned",
                "open_time_ms",
            )
        if boundary != close_boundary_ms(opened, "1m"):
            _candle_fail(
                FillSimulationOutcome.INVALID_CANDLE,
                "candle close boundary does not match the 1m interval",
                "close_boundary_ms",
            )
        if not isinstance(self.is_closed, bool):
            _candle_fail(
                FillSimulationOutcome.INVALID_CANDLE,
                "is_closed must be boolean",
                "is_closed",
            )
        prices = {
            name: _price(getattr(self, name), name)
            for name in ("open_price", "high_price", "low_price", "close_price")
        }
        if prices["low_price"] > prices["high_price"]:
            _candle_fail(
                FillSimulationOutcome.INVALID_CANDLE,
                "candle low exceeds high",
                "low_price",
            )
        if prices["low_price"] > min(
            prices["open_price"],
            prices["close_price"],
        ):
            _candle_fail(
                FillSimulationOutcome.INVALID_CANDLE,
                "candle low exceeds open or close",
                "low_price",
            )
        if prices["high_price"] < max(
            prices["open_price"],
            prices["close_price"],
        ):
            _candle_fail(
                FillSimulationOutcome.INVALID_CANDLE,
                "candle high is below open or close",
                "high_price",
            )
        if observed < opened:
            _candle_fail(
                FillSimulationOutcome.INVALID_CANDLE,
                "snapshot boundary precedes candle open",
                "observed_closed_until_ms",
            )

    @property
    def identity(self) -> tuple[str, str, int, int]:
        return (
            self.symbol,
            self.timeframe,
            self.open_time_ms,
            self.close_boundary_ms,
        )

    @property
    def market_values(self) -> tuple[Decimal, Decimal, Decimal, Decimal]:
        return self.open_price, self.high_price, self.low_price, self.close_price


@dataclass(frozen=True, slots=True)
class FillSimulationRequest:
    command: PaperExecutionCommand
    order: PaperOrder
    fill_role: PaperFillRole
    causal_boundary: PaperFillCausalBoundary
    quote_asset: str
    simulation_policy: PaperFillSimulationPolicy
    candidate_candles: tuple[PaperFillCandle, ...]
    market_snapshot_closed_until_ms: int
    correlation_id: str
    causation_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.command, PaperExecutionCommand):
            raise TypeError("command must be PaperExecutionCommand")
        if not isinstance(self.order, PaperOrder):
            raise TypeError("order must be PaperOrder")
        if not isinstance(self.causal_boundary, PaperFillCausalBoundary):
            raise TypeError("causal_boundary must be PaperFillCausalBoundary")
        if not isinstance(self.simulation_policy, PaperFillSimulationPolicy):
            raise TypeError("simulation_policy must be PaperFillSimulationPolicy")
        try:
            role = PaperFillRole(self.fill_role)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid fill_role") from exc
        object.__setattr__(self, "fill_role", role)
        if self.causal_boundary.fill_role is not role:
            raise ValueError("fill role and causal boundary do not agree")
        object.__setattr__(self, "quote_asset", normalize_symbol(self.quote_asset))
        object.__setattr__(
            self,
            "correlation_id",
            require_identity(self.correlation_id, "correlation_id"),
        )
        object.__setattr__(
            self,
            "causation_id",
            require_identity(self.causation_id, "causation_id"),
        )
        if not isinstance(self.candidate_candles, tuple):
            raise TypeError("candidate_candles must be an immutable tuple")
        if len(self.candidate_candles) > MAX_CANDIDATE_CANDLES:
            raise ValueError("candidate_candles exceeds the bounded limit")
        if not all(isinstance(value, PaperFillCandle) for value in self.candidate_candles):
            raise TypeError("candidate_candles must contain PaperFillCandle values")
        if (
            isinstance(self.market_snapshot_closed_until_ms, bool)
            or not isinstance(self.market_snapshot_closed_until_ms, int)
            or self.market_snapshot_closed_until_ms < 0
        ):
            raise ValueError("market_snapshot_closed_until_ms must be nonnegative")


@dataclass(frozen=True, slots=True)
class FillSimulationResult:
    outcome: FillSimulationOutcome
    fill: PaperFill | None
    reason_code: str
    message: str
    field_path: str | None = None
    action: SimulatedTradeAction | None = None
    selected_candle: PaperFillCandle | None = None

    def __post_init__(self) -> None:
        try:
            outcome = FillSimulationOutcome(self.outcome)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid simulation outcome") from exc
        object.__setattr__(self, "outcome", outcome)
        if (outcome is FillSimulationOutcome.FILLED) != (self.fill is not None):
            raise ValueError("fill presence must match the FILLED outcome")
        if self.fill is not None and not isinstance(self.fill, PaperFill):
            raise TypeError("fill must be PaperFill")
        if self.action is not None:
            object.__setattr__(self, "action", SimulatedTradeAction(self.action))
        if self.selected_candle is not None and not isinstance(
            self.selected_candle,
            PaperFillCandle,
        ):
            raise TypeError("selected_candle must be PaperFillCandle")
        if outcome is FillSimulationOutcome.FILLED and (
            self.action is None or self.selected_candle is None
        ):
            raise ValueError("FILLED result requires action and selected_candle")
        code = str(self.reason_code).strip()
        message = str(self.message).strip()
        if not code or len(code) > 96 or not code.isascii():
            raise ValueError("reason_code must be bounded ASCII")
        if not message:
            message = outcome.value
        object.__setattr__(self, "reason_code", code)
        object.__setattr__(self, "message", message[:160])
        if self.field_path is not None:
            object.__setattr__(self, "field_path", str(self.field_path)[:80])

    @property
    def successful(self) -> bool:
        return self.outcome is FillSimulationOutcome.FILLED and self.fill is not None


def _result(
    outcome: FillSimulationOutcome,
    *,
    fill: PaperFill | None = None,
    message: str | None = None,
    field_path: str | None = None,
    action: SimulatedTradeAction | None = None,
    selected_candle: PaperFillCandle | None = None,
) -> FillSimulationResult:
    return FillSimulationResult(
        outcome=outcome,
        fill=fill,
        reason_code=f"PAPER_FILL_SIMULATOR_{outcome.value}",
        message=(message or outcome.value.lower().replace("_", " "))[:160],
        field_path=field_path[:80] if field_path else None,
        action=action,
        selected_candle=selected_candle,
    )


def authoritative_next_1m_open_after_command_boundary(
    command_closed_until_ms: int,
) -> int:
    """Map an exclusive closed-through boundary to the next interval's open."""

    if (
        isinstance(command_closed_until_ms, bool)
        or not isinstance(command_closed_until_ms, int)
        or command_closed_until_ms < 0
        or not is_aligned_to_timeframe(command_closed_until_ms, "1m")
    ):
        raise ValueError("command closed_until_ms must be an aligned exclusive boundary")
    return command_closed_until_ms


def resolve_trade_action(
    paper_side: PaperSide,
    fill_role: PaperFillRole,
) -> SimulatedTradeAction:
    side = PaperSide(paper_side)
    role = PaperFillRole(fill_role)
    if (side is PaperSide.LONG and role is PaperFillRole.ENTRY) or (
        side is PaperSide.SHORT and role is PaperFillRole.CLOSE
    ):
        return SimulatedTradeAction.BUY
    return SimulatedTradeAction.SELL


def _round_to_quantum(
    value: Decimal,
    quantum: Decimal,
    rounding: str,
) -> Decimal:
    with localcontext(_decimal_context()):
        units = (value / quantum).to_integral_value(rounding=rounding)
        return units * quantum


def _decimal_context() -> Context:
    return Context(
        prec=_DECIMAL_PRECISION,
        rounding=ROUND_HALF_EVEN,
        Emin=MIN_EMIN,
        Emax=MAX_EMAX,
        capitals=1,
        clamp=0,
    )


def adverse_fill_price(
    base_price: Decimal,
    slippage_bps: Decimal,
    price_quantum: Decimal,
    action: SimulatedTradeAction,
) -> Decimal:
    """Calculate and adversely round a price without global context dependence."""

    if any(
        isinstance(value, bool)
        or not isinstance(value, Decimal)
        or not value.is_finite()
        for value in (base_price, slippage_bps, price_quantum)
    ):
        raise ValueError("finite Decimal inputs required")
    if base_price <= 0 or slippage_bps < 0 or slippage_bps >= BPS_DENOMINATOR:
        raise ValueError("invalid price or slippage")
    if price_quantum <= 0:
        raise ValueError("price_quantum must be positive")
    direction = SimulatedTradeAction(action)
    with localcontext(_decimal_context()):
        fraction = slippage_bps / BPS_DENOMINATOR
        raw = (
            base_price * (Decimal("1") + fraction)
            if direction is SimulatedTradeAction.BUY
            else base_price * (Decimal("1") - fraction)
        )
        rounding = ROUND_CEILING if direction is SimulatedTradeAction.BUY else ROUND_FLOOR
        rounded = _round_to_quantum(raw, price_quantum, rounding)
    if rounded <= 0:
        raise ValueError("simulated price must remain positive")
    return rounded


def quote_fee_amount(
    fill_price: Decimal,
    quantity: Decimal,
    fee_bps: Decimal,
    fee_quantum: Decimal,
) -> Decimal:
    """Calculate a quote-asset fee from the final rounded fill price."""

    if any(
        isinstance(value, bool)
        or not isinstance(value, Decimal)
        or not value.is_finite()
        for value in (fill_price, quantity, fee_bps, fee_quantum)
    ):
        raise ValueError("finite Decimal inputs required")
    if fill_price <= 0 or quantity <= 0 or fee_bps < 0 or fee_bps > BPS_DENOMINATOR:
        raise ValueError("invalid fee inputs")
    if fee_quantum <= 0:
        raise ValueError("fee_quantum must be positive")
    with localcontext(_decimal_context()):
        raw_fee = fill_price * quantity * fee_bps / BPS_DENOMINATOR
        return _round_to_quantum(raw_fee, fee_quantum, ROUND_CEILING)


def _ordered_candidates(
    candidates: tuple[PaperFillCandle, ...],
) -> tuple[PaperFillCandle, ...]:
    return tuple(
        sorted(
            candidates,
            key=lambda value: (
                value.symbol,
                value.timeframe,
                value.open_time_ms,
                value.close_boundary_ms,
                value.open_price,
                value.high_price,
                value.low_price,
                value.close_price,
                value.is_closed,
                value.observed_closed_until_ms,
            ),
        )
    )


def _duplicate_outcome(
    candidates: tuple[PaperFillCandle, ...],
) -> FillSimulationOutcome | None:
    by_identity: dict[tuple[str, str, int, int], PaperFillCandle] = {}
    for candle in candidates:
        prior = by_identity.get(candle.identity)
        if prior is None:
            by_identity[candle.identity] = candle
            continue
        if prior.market_values == candle.market_values:
            return FillSimulationOutcome.DUPLICATE_CANDLE
        return FillSimulationOutcome.CANDLE_CONFLICT
    return None


def _policy_matches_command(request: FillSimulationRequest) -> bool:
    policy = request.simulation_policy
    command = request.command
    boundary = request.causal_boundary
    return (
        policy.simulation_policy_id == command.simulation_policy_id
        and policy.slippage_policy_id == command.slippage_policy_id
        and policy.fee_policy_id == command.fee_policy_id
        and policy.latency_policy_id == command.latency_policy_id
        and boundary.simulation_policy_id == policy.simulation_policy_id
        and boundary.slippage_policy_id == policy.slippage_policy_id
        and boundary.fee_policy_id == policy.fee_policy_id
        and boundary.latency_policy_id == policy.latency_policy_id
        and boundary.timeframe == policy.timeframe
        and boundary.latency_candles == policy.latency_candles
    )


def simulate_paper_fill(request: FillSimulationRequest) -> FillSimulationResult:
    """Return one immutable fill or a typed fail-closed non-success outcome."""

    command = request.command
    order = request.order
    policy = request.simulation_policy
    boundary = request.causal_boundary

    expected_source_type = (
        PaperFillSourceEntityType.PAPER_EXECUTION_COMMAND
        if request.fill_role is PaperFillRole.ENTRY
        else PaperFillSourceEntityType.PAPER_EXIT_DECISION
    )
    if (
        boundary.fill_role is not request.fill_role
        or boundary.source_entity_type is not expected_source_type
        or boundary.order_id != order.order_id
        or boundary.symbol != command.symbol
        or (
            request.fill_role is PaperFillRole.ENTRY
            and (
                boundary.source_entity_id != command.command_id
                or boundary.source_closed_until_ms != command.closed_until_ms
            )
        )
    ):
        return _result(
            FillSimulationOutcome.INVALID_CAUSAL_BOUNDARY,
            field_path="causal_boundary",
        )

    if order.state is not PaperOrderState.OPEN:
        return _result(
            FillSimulationOutcome.INVALID_ORDER_STATE,
            field_path="order.state",
        )
    if order.command_id != command.command_id:
        return _result(
            FillSimulationOutcome.IDEMPOTENCY_CONFLICT,
            field_path="order.command_id",
        )
    expected_order_key = order_idempotency_key(
        command.command_id,
        request.fill_role.persistence_role,
    )
    if order.idempotency_key != expected_order_key:
        return _result(
            FillSimulationOutcome.IDEMPOTENCY_CONFLICT,
            field_path="order.idempotency_key",
        )
    if order.symbol != command.symbol:
        return _result(
            FillSimulationOutcome.SYMBOL_MISMATCH,
            field_path="order.symbol",
        )
    if order.side is not command.side:
        return _result(
            FillSimulationOutcome.IDEMPOTENCY_CONFLICT,
            field_path="order.side",
        )
    if order.requested_quantity != command.requested_quantity:
        return _result(
            FillSimulationOutcome.UNSUPPORTED_PARTIAL_FILL,
            field_path="order.requested_quantity",
        )
    if (
        order.requested_quantity <= 0
        or not is_numeric_38_18_compatible(order.requested_quantity)
    ):
        outcome = (
            FillSimulationOutcome.INVALID_QUANTITY
            if order.requested_quantity <= 0
            else FillSimulationOutcome.INVALID_PRECISION
        )
        return _result(outcome, field_path="order.requested_quantity")
    if not _policy_matches_command(request):
        return _result(
            FillSimulationOutcome.INVALID_POLICY,
            field_path="simulation_policy",
        )

    try:
        expected_open = authoritative_next_1m_open_after_command_boundary(
            boundary.source_closed_until_ms
        )
    except ValueError:
        return _result(
            FillSimulationOutcome.INVALID_CANDLE,
            field_path="causal_boundary.source_closed_until_ms",
        )
    expected_close = close_boundary_ms(expected_open, "1m")

    ordered = _ordered_candidates(request.candidate_candles)
    for candle in ordered:
        if candle.symbol != command.symbol:
            return _result(
                FillSimulationOutcome.SYMBOL_MISMATCH,
                field_path="candidate_candles.symbol",
            )
        if candle.timeframe != policy.timeframe:
            return _result(
                FillSimulationOutcome.TIMEFRAME_MISMATCH,
                field_path="candidate_candles.timeframe",
            )

    duplicate = _duplicate_outcome(ordered)
    if duplicate is not None:
        return _result(duplicate, field_path="candidate_candles")

    exact = tuple(value for value in ordered if value.open_time_ms == expected_open)
    selected = exact[0] if exact else None
    if selected is not None:
        if not selected.is_closed:
            return _result(
                FillSimulationOutcome.CANDLE_NOT_CLOSED,
                field_path="candidate_candles.is_closed",
            )
        if (
            selected.close_boundary_ms > request.market_snapshot_closed_until_ms
            or selected.close_boundary_ms > selected.observed_closed_until_ms
        ):
            return _result(
                FillSimulationOutcome.NOT_YET_ELIGIBLE,
                field_path="market_snapshot_closed_until_ms",
            )
        if (
            selected.observed_closed_until_ms
            > request.market_snapshot_closed_until_ms
        ):
            return _result(
                FillSimulationOutcome.FUTURE_DATA_REJECTED,
                field_path="candidate_candles.observed_closed_until_ms",
            )

    for candle in ordered:
        if candle is selected:
            continue
        if (
            candle.close_boundary_ms > request.market_snapshot_closed_until_ms
            or (
                candle.is_closed
                and candle.close_boundary_ms > candle.observed_closed_until_ms
            )
            or candle.observed_closed_until_ms
            > request.market_snapshot_closed_until_ms
        ):
            return _result(
                FillSimulationOutcome.FUTURE_DATA_REJECTED,
                field_path="candidate_candles",
            )
        if not candle.is_closed:
            return _result(
                FillSimulationOutcome.CANDLE_NOT_CLOSED,
                field_path="candidate_candles.is_closed",
            )

    if selected is None:
        if any(value.open_time_ms > expected_open for value in ordered):
            return _result(
                FillSimulationOutcome.MARKET_DATA_GAP,
                field_path="candidate_candles",
            )
        if request.market_snapshot_closed_until_ms < expected_close:
            return _result(
                FillSimulationOutcome.NOT_YET_ELIGIBLE,
                field_path="market_snapshot_closed_until_ms",
            )
        return _result(
            FillSimulationOutcome.ELIGIBLE_CANDLE_MISSING,
            field_path="candidate_candles",
        )

    if (
        request.fill_role is PaperFillRole.ENTRY
        and command.valid_until_ms < expected_close
    ):
        return _result(
            FillSimulationOutcome.COMMAND_EXPIRED,
            field_path="command.valid_until_ms",
            selected_candle=selected,
        )

    action = resolve_trade_action(command.side, request.fill_role)
    try:
        price = adverse_fill_price(
            selected.open_price,
            policy.slippage_bps,
            policy.price_quantum,
            action,
        )
    except (DecimalException, ValueError):
        return _result(
            FillSimulationOutcome.INVALID_SIMULATED_PRICE,
            field_path="price",
            action=action,
            selected_candle=selected,
        )
    if not is_numeric_38_18_compatible(price):
        return _result(
            FillSimulationOutcome.INVALID_PRECISION,
            field_path="price",
            action=action,
            selected_candle=selected,
        )
    try:
        fee = quote_fee_amount(
            price,
            order.requested_quantity,
            policy.fee_bps,
            policy.fee_quantum,
        )
    except (DecimalException, ValueError):
        return _result(
            FillSimulationOutcome.INVALID_PRECISION,
            field_path="fee_amount",
            action=action,
            selected_candle=selected,
        )
    if not is_numeric_38_18_compatible(fee):
        return _result(
            FillSimulationOutcome.INVALID_PRECISION,
            field_path="fee_amount",
            action=action,
            selected_candle=selected,
        )

    identity_arguments = {
        "contract_version": policy.contract_version,
        "order_id": order.order_id,
        "fill_role": request.fill_role.value,
        "source_open_time_ms": expected_open,
        "source_close_boundary_ms": expected_close,
        "simulation_policy_id": policy.simulation_policy_id,
        "slippage_policy_id": policy.slippage_policy_id,
        "fee_policy_id": policy.fee_policy_id,
        "latency_policy_id": policy.latency_policy_id,
    }
    try:
        if request.fill_role is PaperFillRole.CLOSE:
            close_identity_arguments = {
                "fill_contract_version": boundary.contract_version,
                "order_id": order.order_id,
                "exit_decision_id": boundary.source_entity_id,
                "exit_source_closed_until_ms": boundary.source_closed_until_ms,
                "source_open_time_ms": expected_open,
                "source_close_boundary_ms": expected_close,
                "simulation_policy_id": policy.simulation_policy_id,
                "slippage_policy_id": policy.slippage_policy_id,
                "fee_policy_id": policy.fee_policy_id,
                "latency_policy_id": policy.latency_policy_id,
            }
            fill_id = simulated_close_fill_id(**close_identity_arguments)
            fill_key = simulated_close_fill_idempotency_key(
                **close_identity_arguments
            )
        else:
            fill_id = simulated_fill_id(**identity_arguments)
            fill_key = simulated_fill_idempotency_key(**identity_arguments)
        fill = PaperFill(
            fill_id=fill_id,
            order_id=order.order_id,
            idempotency_key=fill_key,
            symbol=command.symbol,
            side=command.side,
            quantity=order.requested_quantity,
            price=price,
            fee_amount=fee,
            fee_asset=request.quote_asset,
            filled_at=_EPOCH_UTC + timedelta(milliseconds=expected_close),
            source_closed_until_ms=expected_close,
            simulation_policy_id=policy.simulation_policy_id,
            slippage_policy_id=policy.slippage_policy_id,
            fee_policy_id=policy.fee_policy_id,
            latency_policy_id=policy.latency_policy_id,
            future_bars_used=False,
        )
    except (ArithmeticError, OverflowError, ValueError):
        return _result(
            FillSimulationOutcome.INTERNAL_INVARIANT_FAILURE,
            field_path="fill",
            action=action,
            selected_candle=selected,
        )
    return _result(
        FillSimulationOutcome.FILLED,
        fill=fill,
        action=action,
        selected_candle=selected,
    )
