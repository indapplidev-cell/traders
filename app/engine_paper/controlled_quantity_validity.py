"""Offline controlled PAPER quantity and candle-lineage validity authorities."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal, ROUND_FLOOR
from typing import Final, Mapping

from app.engine_paper.accounting import PaperAccountSummary
from app.engine_paper.paper_approvals import (
    PaperQuantityApproval,
    PaperQuantityApprovalSource,
    PaperStrategyApproval,
    issue_paper_quantity_approval,
)
from app.engine_risk.risk_decision import RiskDecision
from app.engine_safety.paper_domain import ExecutionMode, PaperReasonCode, fail
from app.instrument_constraints.registry import (
    ACTIVE_QUANTITY_CONSTRAINT_REGISTRY,
    REGISTRY_VERSION,
    InstrumentQuantityConstraint,
    InstrumentQuantityConstraintRegistry,
)


QUANTITY_POLICY_VERSION: Final = "paper-quantity-policy-v1"
VALIDITY_POLICY_VERSION: Final = "paper-approval-validity-policy-v1"
RISK_FRACTION: Final = Decimal("0.01")
DECISION_TIMEFRAME_MS: Final = 900_000


@dataclass(frozen=True, slots=True)
class PaperQuantitySizingAudit:
    quantity_policy_version: str
    instrument_registry_version: str
    universe_id: str
    symbol: str
    paper_equity_at_approval: Decimal
    entry_price: Decimal
    stop_price: Decimal
    risk_budget: Decimal
    risk_per_unit: Decimal
    raw_quantity: Decimal
    balance_cap_quantity: Decimal
    applicable_quantity_step: Decimal
    applicable_min_quantity: Decimal
    applicable_max_quantity: Decimal
    applicable_min_notional: Decimal | None
    applicable_max_notional: Decimal | None
    normalized_quantity: Decimal

    def to_dict(self) -> dict[str, object]:
        return {
            key: format(value, "f") if isinstance(value, Decimal) else value
            for key, value in asdict(self).items()
        }


@dataclass(frozen=True, slots=True)
class ControlledPaperQuantityResult:
    approval: PaperQuantityApproval
    audit: PaperQuantitySizingAudit
    validity_policy_version: str
    source_candle_close_time_ms: int

    def to_persisted_payload(self) -> Mapping[str, object]:
        """JSON-safe content for ``paper_payload_json`` at ``finish()``."""
        approval = self.approval.to_dict()
        approval["approved_quantity"] = format(self.approval.approved_quantity, "f")
        approval["approved_at"] = self.approval.approved_at.isoformat()
        return {
            "controlled_quantity_approval": approval,
            "quantity_sizing_audit": self.audit.to_dict(),
            "approval_validity": {
                "policy_version": self.validity_policy_version,
                "source_timeframe": "15m",
                "source_candle_close_time_ms": self.source_candle_close_time_ms,
                "valid_until_ms": self.approval.valid_until_ms,
            },
        }


def derive_approval_valid_until_ms(
    source_candle_close_time_ms: int,
    *,
    stricter_valid_until_ms: tuple[int, ...] = (),
    evaluation_time_ms: int | None = None,
) -> int:
    """Return source close + one 15m candle, preserving stricter deadlines."""
    if isinstance(source_candle_close_time_ms, bool) or source_candle_close_time_ms < 0:
        fail(PaperReasonCode.PAPER_INPUT_TIME_INVALID, "invalid source candle close", "closed_until_ms")
    # Binance kline closeTime is the final millisecond of its interval.
    if (source_candle_close_time_ms + 1) % DECISION_TIMEFRAME_MS != 0:
        fail(PaperReasonCode.PAPER_INPUT_TIME_INVALID, "source candle is not 15m aligned", "closed_until_ms")
    causal_deadline = source_candle_close_time_ms + DECISION_TIMEFRAME_MS
    deadlines = (causal_deadline, *stricter_valid_until_ms)
    if any(isinstance(value, bool) or value < source_candle_close_time_ms for value in deadlines):
        fail(PaperReasonCode.PAPER_INPUT_VALIDITY_INVALID, "invalid upstream validity", "valid_until_ms")
    valid = min(deadlines)
    if evaluation_time_ms is not None and evaluation_time_ms > valid:
        fail(PaperReasonCode.PAPER_SAFETY_SOURCE_STALE, "approval validity is expired", "evaluation_time_ms")
    return valid


def _normalize_down(quantity: Decimal, step: Decimal) -> Decimal:
    units = (quantity / step).to_integral_value(rounding=ROUND_FLOOR)
    return units * step


def calculate_controlled_quantity(
    *,
    strategy: PaperStrategyApproval,
    account: PaperAccountSummary,
    registry: InstrumentQuantityConstraintRegistry = ACTIVE_QUANTITY_CONSTRAINT_REGISTRY,
) -> PaperQuantitySizingAudit:
    """Apply exactly paper-quantity-policy-v1 using only local authority data."""
    if not isinstance(strategy, PaperStrategyApproval) or not isinstance(account, PaperAccountSummary):
        fail(PaperReasonCode.PAPER_RISK_APPROVAL_MISSING, "authoritative PAPER inputs required", "strategy")
    if registry.version != REGISTRY_VERSION or strategy.symbol_constraints_id != registry.version:
        fail(PaperReasonCode.PAPER_INPUT_IDENTITY_INVALID, "instrument registry binding mismatch", "symbol_constraints_id")
    constraint: InstrumentQuantityConstraint = registry.for_symbol(strategy.symbol)
    equity = account.current_balance
    entry = strategy.entry_reference_price
    stop = strategy.stop_price
    if not isinstance(equity, Decimal) or not equity.is_finite() or equity <= 0:
        fail(PaperReasonCode.PAPER_INPUT_QUANTITY_INVALID, "PAPER equity must be positive", "current_balance")
    if entry <= 0 or stop <= 0:
        fail(PaperReasonCode.PAPER_INPUT_PRICE_INVALID, "entry and stop must be positive", "entry_price")
    risk_per_unit = abs(entry - stop)
    if risk_per_unit <= 0:
        fail(PaperReasonCode.PAPER_INPUT_STOP_TARGET_INVALID, "risk distance must be positive", "stop_price")
    risk_budget = equity * RISK_FRACTION
    raw = risk_budget / risk_per_unit
    balance_cap = equity / entry
    capped = min(raw, balance_cap, constraint.max_quantity)
    normalized = _normalize_down(capped, constraint.quantity_step)
    notional = normalized * entry
    if normalized <= 0 or normalized < constraint.min_quantity:
        fail(PaperReasonCode.PAPER_INPUT_QUANTITY_INVALID, "minimum quantity cannot be met without rounding up", "approved_quantity")
    if constraint.min_notional is not None and notional < constraint.min_notional:
        fail(PaperReasonCode.PAPER_INPUT_NOTIONAL_INVALID, "minimum notional cannot be met without rounding up", "approved_quantity")
    if normalized > constraint.max_quantity:
        fail(PaperReasonCode.PAPER_INPUT_QUANTITY_INVALID, "maximum quantity exceeded", "approved_quantity")
    if constraint.max_notional is not None and notional > constraint.max_notional:
        fail(PaperReasonCode.PAPER_INPUT_NOTIONAL_INVALID, "maximum notional exceeded", "approved_quantity")
    if normalized > capped or normalized * risk_per_unit > risk_budget or notional > equity:
        fail(PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION, "quantity safety cap violated", "approved_quantity")
    return PaperQuantitySizingAudit(
        QUANTITY_POLICY_VERSION, registry.version, registry.universe_id, strategy.symbol,
        equity, entry, stop, risk_budget, risk_per_unit, raw, balance_cap,
        constraint.quantity_step, constraint.min_quantity, constraint.max_quantity,
        constraint.min_notional, constraint.max_notional, normalized,
    )


def issue_controlled_paper_quantity_approval(
    strategy: PaperStrategyApproval,
    research_risk: RiskDecision,
    account: PaperAccountSummary,
    *,
    approved_at: datetime,
    evaluation_time_ms: int,
    registry: InstrumentQuantityConstraintRegistry = ACTIVE_QUANTITY_CONSTRAINT_REGISTRY,
) -> ControlledPaperQuantityResult:
    """Issue the deterministic immutable quantity approval for one causal run."""
    audit = calculate_controlled_quantity(strategy=strategy, account=account, registry=registry)
    valid = derive_approval_valid_until_ms(
        strategy.closed_until_ms,
        stricter_valid_until_ms=(strategy.valid_until_ms,),
        evaluation_time_ms=evaluation_time_ms,
    )
    approval = issue_paper_quantity_approval(
        strategy, research_risk, mode=ExecutionMode.PAPER, paper_authorized=True,
        requested_quantity=audit.normalized_quantity,
        approval_source=PaperQuantityApprovalSource.CONTROLLED_PAPER_AUTHORITY,
        approved_at=approved_at, valid_until_ms=valid,
        evaluation_time_ms=evaluation_time_ms,
        correlation_id=strategy.correlation_id, causation_id=strategy.approval_id,
    )
    return ControlledPaperQuantityResult(
        approval, audit, VALIDITY_POLICY_VERSION, strategy.closed_until_ms,
    )
