"""Pure immutable authority for PAPER fill causal boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.engine_execution.paper_idempotency import order_idempotency_key
from app.engine_execution.paper_models import PaperExecutionCommand, PaperFill, PaperOrder
from app.engine_exit.paper_exit import PaperExitDecision
from app.engine_market_data.timeframe import is_aligned_to_timeframe
from app.engine_paper.fill_policy import PaperFillSimulationPolicy
from app.engine_paper.fill_roles import PaperFillRole
from app.engine_position.paper_models import PaperPosition
from app.engine_safety.paper_domain import normalize_symbol, require_identity


PAPER_FILL_CAUSAL_BOUNDARY_VERSION = "PAPER_FILL_CAUSAL_BOUNDARY_V1"


class PaperFillSourceEntityType(StrEnum):
    PAPER_EXECUTION_COMMAND = "PAPER_EXECUTION_COMMAND"
    PAPER_EXIT_DECISION = "PAPER_EXIT_DECISION"


class PaperFillBoundaryOutcome(StrEnum):
    BOUNDARY_RESOLVED = "BOUNDARY_RESOLVED"
    COMMAND_REQUIRED = "COMMAND_REQUIRED"
    EXIT_DECISION_REQUIRED = "EXIT_DECISION_REQUIRED"
    ORDER_REQUIRED = "ORDER_REQUIRED"
    POSITION_REQUIRED = "POSITION_REQUIRED"
    ROLE_SOURCE_MISMATCH = "ROLE_SOURCE_MISMATCH"
    SOURCE_GRAPH_INCONSISTENT = "SOURCE_GRAPH_INCONSISTENT"
    SOURCE_BOUNDARY_INVALID = "SOURCE_BOUNDARY_INVALID"
    SOURCE_BOUNDARY_PRECEDES_POSITION_OPEN = (
        "SOURCE_BOUNDARY_PRECEDES_POSITION_OPEN"
    )
    POLICY_MISMATCH = "POLICY_MISMATCH"
    SYMBOL_MISMATCH = "SYMBOL_MISMATCH"
    SIDE_MISMATCH = "SIDE_MISMATCH"


@dataclass(frozen=True, slots=True)
class PaperFillCausalBoundary:
    contract_version: str
    fill_role: PaperFillRole
    source_entity_type: PaperFillSourceEntityType
    source_entity_id: str
    source_closed_until_ms: int
    order_id: str
    symbol: str
    timeframe: str
    latency_candles: int
    simulation_policy_id: str
    slippage_policy_id: str
    fee_policy_id: str
    latency_policy_id: str
    correlation_id: str
    causation_id: str

    def __post_init__(self) -> None:
        if self.contract_version != PAPER_FILL_CAUSAL_BOUNDARY_VERSION:
            raise ValueError("unsupported fill causal-boundary contract version")
        role = PaperFillRole(self.fill_role)
        source_type = PaperFillSourceEntityType(self.source_entity_type)
        expected_source = (
            PaperFillSourceEntityType.PAPER_EXECUTION_COMMAND
            if role is PaperFillRole.ENTRY
            else PaperFillSourceEntityType.PAPER_EXIT_DECISION
        )
        if source_type is not expected_source:
            raise ValueError("fill role and causal source do not agree")
        object.__setattr__(self, "fill_role", role)
        object.__setattr__(self, "source_entity_type", source_type)
        for name in (
            "source_entity_id",
            "order_id",
            "simulation_policy_id",
            "slippage_policy_id",
            "fee_policy_id",
            "latency_policy_id",
            "correlation_id",
            "causation_id",
        ):
            object.__setattr__(
                self, name, require_identity(getattr(self, name), name)
            )
        object.__setattr__(self, "symbol", normalize_symbol(self.symbol))
        if (
            isinstance(self.source_closed_until_ms, bool)
            or not isinstance(self.source_closed_until_ms, int)
            or self.source_closed_until_ms < 0
            or not is_aligned_to_timeframe(self.source_closed_until_ms, "1m")
        ):
            raise ValueError("source boundary must be a nonnegative aligned 1m boundary")
        if self.timeframe != "1m":
            raise ValueError("fill causal-boundary timeframe must be 1m")
        if (
            isinstance(self.latency_candles, bool)
            or not isinstance(self.latency_candles, int)
            or self.latency_candles != 1
        ):
            raise ValueError("fill causal-boundary latency must be one candle")


@dataclass(frozen=True, slots=True)
class PaperFillCausalBoundaryResult:
    outcome: PaperFillBoundaryOutcome
    boundary: PaperFillCausalBoundary | None = None
    reason_code: str = "PAPER_FILL_BOUNDARY_OK"
    field_path: str | None = None

    @property
    def successful(self) -> bool:
        return (
            self.outcome is PaperFillBoundaryOutcome.BOUNDARY_RESOLVED
            and self.boundary is not None
        )


def _failure(
    outcome: PaperFillBoundaryOutcome, field_path: str
) -> PaperFillCausalBoundaryResult:
    return PaperFillCausalBoundaryResult(
        outcome=outcome,
        reason_code=f"PAPER_FILL_BOUNDARY_{outcome.value}",
        field_path=field_path,
    )


def resolve_paper_fill_causal_boundary(
    *,
    fill_role: PaperFillRole,
    command: PaperExecutionCommand | None,
    order: PaperOrder | None,
    simulation_policy: PaperFillSimulationPolicy,
    correlation_id: str,
    causation_id: str,
    exit_decision: PaperExitDecision | None = None,
    position: PaperPosition | None = None,
    entry_order: PaperOrder | None = None,
    entry_fill: PaperFill | None = None,
) -> PaperFillCausalBoundaryResult:
    """Resolve a boundary without database, network, clock, or random access."""

    try:
        role = PaperFillRole(fill_role)
    except (TypeError, ValueError):
        return _failure(PaperFillBoundaryOutcome.ROLE_SOURCE_MISMATCH, "fill_role")
    if command is None:
        return _failure(PaperFillBoundaryOutcome.COMMAND_REQUIRED, "command")
    if order is None:
        return _failure(PaperFillBoundaryOutcome.ORDER_REQUIRED, "order")
    if order.command_id != command.command_id:
        return _failure(
            PaperFillBoundaryOutcome.SOURCE_GRAPH_INCONSISTENT, "order.command_id"
        )
    expected_order_key = order_idempotency_key(
        command.command_id, role.persistence_role
    )
    if order.idempotency_key != expected_order_key:
        return _failure(
            PaperFillBoundaryOutcome.ROLE_SOURCE_MISMATCH, "order.idempotency_key"
        )
    if order.symbol != command.symbol:
        return _failure(PaperFillBoundaryOutcome.SYMBOL_MISMATCH, "order.symbol")
    if order.side is not command.side:
        return _failure(PaperFillBoundaryOutcome.SIDE_MISMATCH, "order.side")
    if (
        simulation_policy.simulation_policy_id != command.simulation_policy_id
        or simulation_policy.slippage_policy_id != command.slippage_policy_id
        or simulation_policy.fee_policy_id != command.fee_policy_id
        or simulation_policy.latency_policy_id != command.latency_policy_id
    ):
        return _failure(
            PaperFillBoundaryOutcome.POLICY_MISMATCH, "simulation_policy"
        )

    source_type = PaperFillSourceEntityType.PAPER_EXECUTION_COMMAND
    source_id = command.command_id
    source_boundary = command.closed_until_ms
    if role is PaperFillRole.ENTRY:
        if any(
            value is not None
            for value in (exit_decision, position, entry_order, entry_fill)
        ):
            return _failure(
                PaperFillBoundaryOutcome.ROLE_SOURCE_MISMATCH, "exit_decision"
            )
    else:
        if exit_decision is None:
            return _failure(
                PaperFillBoundaryOutcome.EXIT_DECISION_REQUIRED, "exit_decision"
            )
        if position is None:
            return _failure(PaperFillBoundaryOutcome.POSITION_REQUIRED, "position")
        if entry_order is None or entry_fill is None:
            return _failure(
                PaperFillBoundaryOutcome.SOURCE_GRAPH_INCONSISTENT, "entry_graph"
            )
        if (
            exit_decision.position_id != position.position_id
            or entry_order.order_id != position.entry_order_id
            or entry_fill.fill_id != position.entry_fill_id
            or entry_order.command_id != command.command_id
            or entry_fill.order_id != entry_order.order_id
            or exit_decision.requested_close_quantity != position.remaining_quantity
            or order.requested_quantity != position.remaining_quantity
        ):
            return _failure(
                PaperFillBoundaryOutcome.SOURCE_GRAPH_INCONSISTENT, "close_graph"
            )
        if (
            position.symbol != command.symbol
            or exit_decision.source_closed_until_ms < entry_fill.source_closed_until_ms
        ):
            outcome = (
                PaperFillBoundaryOutcome.SYMBOL_MISMATCH
                if position.symbol != command.symbol
                else PaperFillBoundaryOutcome.SOURCE_BOUNDARY_PRECEDES_POSITION_OPEN
            )
            return _failure(outcome, "exit_decision.source_closed_until_ms")
        if position.side is not command.side:
            return _failure(PaperFillBoundaryOutcome.SIDE_MISMATCH, "position.side")
        source_type = PaperFillSourceEntityType.PAPER_EXIT_DECISION
        source_id = exit_decision.exit_decision_id
        source_boundary = exit_decision.source_closed_until_ms

    if (
        isinstance(source_boundary, bool)
        or not isinstance(source_boundary, int)
        or source_boundary < 0
        or not is_aligned_to_timeframe(source_boundary, "1m")
    ):
        return _failure(
            PaperFillBoundaryOutcome.SOURCE_BOUNDARY_INVALID,
            "source_closed_until_ms",
        )
    try:
        boundary = PaperFillCausalBoundary(
            contract_version=PAPER_FILL_CAUSAL_BOUNDARY_VERSION,
            fill_role=role,
            source_entity_type=source_type,
            source_entity_id=source_id,
            source_closed_until_ms=source_boundary,
            order_id=order.order_id,
            symbol=command.symbol,
            timeframe=simulation_policy.timeframe,
            latency_candles=simulation_policy.latency_candles,
            simulation_policy_id=simulation_policy.simulation_policy_id,
            slippage_policy_id=simulation_policy.slippage_policy_id,
            fee_policy_id=simulation_policy.fee_policy_id,
            latency_policy_id=simulation_policy.latency_policy_id,
            correlation_id=correlation_id,
            causation_id=causation_id,
        )
    except ValueError:
        return _failure(
            PaperFillBoundaryOutcome.SOURCE_BOUNDARY_INVALID,
            "source_closed_until_ms",
        )
    return PaperFillCausalBoundaryResult(
        outcome=PaperFillBoundaryOutcome.BOUNDARY_RESOLVED,
        boundary=boundary,
    )
