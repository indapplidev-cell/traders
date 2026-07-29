"""Pure, fail-closed final PAPER approval authorities.

Research strategy and risk decisions remain non-executable inputs.  These
contracts are the separate, explicit authority chain required before a later
command-ingestion service may construct a PAPER command.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from typing import Mapping

from app.engine_risk.risk_decision import RiskDecision
from app.engine_safety.paper_domain import (
    ExecutionMode,
    PaperInputHealthStatus,
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
from app.engine_strategy.strategy_decision import StrategyDecision


PAPER_APPROVAL_IDEMPOTENCY_VERSION = "v1"
PAPER_APPROVAL_CONTRACT_VERSION = "paper-approval-v1"


class PaperApprovalReasonCode(StrEnum):
    PAPER_STRATEGY_FINAL_APPROVED = "PAPER_STRATEGY_FINAL_APPROVED"
    PAPER_QUANTITY_CONTROLLED_APPROVED = "PAPER_QUANTITY_CONTROLLED_APPROVED"
    PAPER_RISK_FINAL_APPROVED = "PAPER_RISK_FINAL_APPROVED"


class PaperQuantityApprovalSource(StrEnum):
    CONTROLLED_PAPER_AUTHORITY = "CONTROLLED_PAPER_AUTHORITY"


def _identity(kind: str, parts: tuple[object, ...]) -> str:
    normalized: list[str] = []
    for index, part in enumerate(parts):
        value = getattr(part, "value", part)
        if value is None:
            fail(
                PaperReasonCode.PAPER_IDEMPOTENCY_KEY_INVALID,
                "missing approval identity component",
                f"identity[{index}]",
            )
        text = (
            format(value.normalize(), "f")
            if isinstance(value, Decimal) and value.is_finite()
            else str(value)
        )
        if not text or not text.isascii() or len(text) > 128:
            fail(
                PaperReasonCode.PAPER_IDEMPOTENCY_KEY_INVALID,
                "invalid approval identity component",
                f"identity[{index}]",
            )
        normalized.append(text)
    canonical = "|".join(f"{len(value)}:{value}" for value in normalized)
    digest = sha256(canonical.encode("ascii")).hexdigest()
    return f"paper:{kind}:{PAPER_APPROVAL_IDEMPOTENCY_VERSION}:{digest}"


def _epoch_ms(value: datetime, field_path: str) -> int:
    require_utc(value, field_path)
    delta = value - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return (
        delta.days * 86_400_000
        + delta.seconds * 1_000
        + delta.microseconds // 1_000
    )


def _require_explicit_paper(mode: object, paper_authorized: object) -> None:
    require_paper_mode(mode)
    if paper_authorized is not True:
        fail(
            PaperReasonCode.PAPER_RISK_APPROVAL_MISSING,
            "explicit PAPER authorization is required",
            "paper_authorized",
        )


def _require_current_health(value: object) -> PaperInputHealthStatus:
    try:
        health = PaperInputHealthStatus(getattr(value, "value", value))
    except (TypeError, ValueError):
        text = str(getattr(value, "value", value)).upper()
        if "STALE" in text:
            code = PaperReasonCode.PAPER_SAFETY_SOURCE_STALE
        elif "DEGRADED" in text:
            code = PaperReasonCode.PAPER_SAFETY_HEALTH_DEGRADED
        else:
            code = PaperReasonCode.PAPER_SAFETY_HEALTH_UNKNOWN
        fail(code, "input health is not current", "input_health_status")
    if health is not PaperInputHealthStatus.CURRENT:
        fail(
            PaperReasonCode.PAPER_SAFETY_HEALTH_DEGRADED,
            "only CURRENT input health may receive final approval",
            "input_health_status",
        )
    return health


def _require_validity(
    *,
    closed_until_ms: object,
    approved_at: datetime,
    valid_until_ms: object,
    evaluation_time_ms: object,
) -> tuple[int, int]:
    closed = require_nonnegative_int(closed_until_ms, "closed_until_ms")
    valid = require_nonnegative_int(valid_until_ms, "valid_until_ms")
    evaluated = require_nonnegative_int(evaluation_time_ms, "evaluation_time_ms")
    approved_ms = _epoch_ms(approved_at, "approved_at")
    if valid < closed or valid < approved_ms:
        fail(
            PaperReasonCode.PAPER_INPUT_VALIDITY_INVALID,
            "approval validity precedes its source or issuance",
            "valid_until_ms",
        )
    if evaluated > valid:
        fail(
            PaperReasonCode.PAPER_SAFETY_SOURCE_STALE,
            "approval is expired",
            "evaluation_time_ms",
        )
    return closed, valid


def _strategy_causal_tuple(
    *,
    research_strategy_decision_id: str,
    setup_id: str,
    pipeline_run_id: str,
    analysis_result_id: str,
    symbol: str,
    side: PaperSide,
    entry_reference_price: Decimal,
    stop_price: Decimal,
    target_price: Decimal,
    closed_until_ms: int,
    approved_at: datetime,
    valid_until_ms: int,
    configuration_fingerprint: str,
    symbol_constraints_id: str,
    correlation_id: str,
    causation_id: str,
) -> tuple[object, ...]:
    return (
        PAPER_APPROVAL_CONTRACT_VERSION,
        research_strategy_decision_id,
        setup_id,
        pipeline_run_id,
        analysis_result_id,
        symbol,
        side,
        entry_reference_price,
        stop_price,
        target_price,
        closed_until_ms,
        approved_at.isoformat(),
        valid_until_ms,
        configuration_fingerprint,
        symbol_constraints_id,
        correlation_id,
        causation_id,
    )


@dataclass(frozen=True, slots=True)
class PaperStrategyApproval:
    approval_id: str
    contract_version: str
    research_strategy_decision_id: str
    setup_id: str
    pipeline_run_id: str
    analysis_result_id: str
    symbol: str
    side: PaperSide
    entry_reference_price: Decimal
    stop_price: Decimal
    target_price: Decimal
    closed_until_ms: int
    approved_at: datetime
    valid_until_ms: int
    configuration_fingerprint: str
    symbol_constraints_id: str
    input_health_status: PaperInputHealthStatus
    future_bars_used: bool
    paper_execution_approved: bool
    reason_code: PaperApprovalReasonCode
    correlation_id: str
    causation_id: str

    def __post_init__(self) -> None:
        if self.contract_version != PAPER_APPROVAL_CONTRACT_VERSION:
            fail(
                PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION,
                "unsupported strategy approval contract version",
                "contract_version",
            )
        for name in (
            "research_strategy_decision_id",
            "setup_id",
            "pipeline_run_id",
            "analysis_result_id",
            "configuration_fingerprint",
            "symbol_constraints_id",
            "correlation_id",
            "causation_id",
        ):
            object.__setattr__(self, name, require_identity(getattr(self, name), name))
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
        for name in ("entry_reference_price", "stop_price", "target_price"):
            require_decimal(getattr(self, name), name, positive=True)
        valid_geometry = (
            self.stop_price < self.entry_reference_price < self.target_price
            if self.side is PaperSide.LONG
            else self.target_price < self.entry_reference_price < self.stop_price
        )
        if not valid_geometry:
            fail(
                PaperReasonCode.PAPER_INPUT_STOP_TARGET_INVALID,
                "invalid stop-entry-target ordering",
                "stop_price",
            )
        require_nonnegative_int(self.closed_until_ms, "closed_until_ms")
        require_nonnegative_int(self.valid_until_ms, "valid_until_ms")
        if (
            self.valid_until_ms < self.closed_until_ms
            or self.valid_until_ms < _epoch_ms(self.approved_at, "approved_at")
        ):
            fail(
                PaperReasonCode.PAPER_INPUT_VALIDITY_INVALID,
                "invalid strategy approval validity",
                "valid_until_ms",
            )
        object.__setattr__(
            self,
            "input_health_status",
            _require_current_health(self.input_health_status),
        )
        if self.future_bars_used is not False or self.paper_execution_approved is not True:
            fail(
                PaperReasonCode.PAPER_RISK_APPROVAL_MISSING,
                "strategy approval flags are invalid",
                "paper_execution_approved",
            )
        object.__setattr__(
            self,
            "reason_code",
            require_enum(
                self.reason_code,
                PaperApprovalReasonCode,
                PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION,
                "reason_code",
            ),
        )
        if self.reason_code is not PaperApprovalReasonCode.PAPER_STRATEGY_FINAL_APPROVED:
            fail(
                PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION,
                "invalid strategy approval reason",
                "reason_code",
            )
        if (
            self.correlation_id != self.pipeline_run_id
            or self.causation_id != self.research_strategy_decision_id
        ):
            fail(
                PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION,
                "strategy approval causal IDs mismatch",
                "causation_id",
            )
        expected = _identity(
            "strategy-approval",
            _strategy_causal_tuple(
                research_strategy_decision_id=self.research_strategy_decision_id,
                setup_id=self.setup_id,
                pipeline_run_id=self.pipeline_run_id,
                analysis_result_id=self.analysis_result_id,
                symbol=self.symbol,
                side=self.side,
                entry_reference_price=self.entry_reference_price,
                stop_price=self.stop_price,
                target_price=self.target_price,
                closed_until_ms=self.closed_until_ms,
                approved_at=self.approved_at,
                valid_until_ms=self.valid_until_ms,
                configuration_fingerprint=self.configuration_fingerprint,
                symbol_constraints_id=self.symbol_constraints_id,
                correlation_id=self.correlation_id,
                causation_id=self.causation_id,
            ),
        )
        if self.approval_id != expected:
            fail(
                PaperReasonCode.PAPER_IDEMPOTENCY_KEY_INVALID,
                "strategy approval identity mismatch",
                "approval_id",
            )

    def to_dict(self) -> dict[str, object]:
        values = asdict(self)
        for name in ("side", "input_health_status", "reason_code"):
            values[name] = getattr(values[name], "value", values[name])
        return values


def finalize_paper_strategy_approval(
    research_decision: StrategyDecision,
    *,
    mode: ExecutionMode,
    paper_authorized: bool,
    setup_id: str,
    pipeline_run_id: str,
    analysis_result_id: str,
    side: PaperSide,
    entry_reference_price: Decimal,
    stop_price: Decimal,
    target_price: Decimal,
    approved_at: datetime,
    valid_until_ms: int,
    configuration_fingerprint: str,
    symbol_constraints_id: str,
    input_health_status: PaperInputHealthStatus,
    future_bars_used: bool,
    correlation_id: str,
    causation_id: str,
    evaluation_time_ms: int,
) -> PaperStrategyApproval:
    _require_explicit_paper(mode, paper_authorized)
    if not isinstance(research_decision, StrategyDecision):
        fail(
            PaperReasonCode.PAPER_INPUT_STRATEGY_MISSING,
            "research StrategyDecision is required",
            "research_decision",
        )
    if research_decision.decision_status != "ALLOW_RESEARCH_TRADE_PLAN":
        fail(
            PaperReasonCode.PAPER_RISK_NOT_APPROVED,
            "research strategy outcome does not allow a trade plan",
            "research_decision.decision_status",
        )
    if research_decision.future_bars_used is not False or future_bars_used is not False:
        fail(
            PaperReasonCode.PAPER_SAFETY_FUTURE_DATA_DETECTED,
            "future data is forbidden",
            "future_bars_used",
        )
    setup = require_identity(setup_id, "setup_id")
    run = require_identity(pipeline_run_id, "pipeline_run_id")
    analysis = require_identity(analysis_result_id, "analysis_result_id")
    config = require_identity(configuration_fingerprint, "configuration_fingerprint")
    constraints = require_identity(symbol_constraints_id, "symbol_constraints_id")
    correlation = require_identity(correlation_id, "correlation_id")
    causation = require_identity(causation_id, "causation_id")
    if (
        research_decision.source_setup_id != setup
        or research_decision.source_analysis_snapshot_id != analysis
        or correlation != run
        or causation != research_decision.decision_id
    ):
        fail(
            PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION,
            "strategy approval causal graph mismatch",
            "research_decision",
        )
    symbol = normalize_symbol(research_decision.symbol)
    selected_side = require_enum(
        side,
        PaperSide,
        PaperReasonCode.PAPER_INPUT_SIDE_INVALID,
        "side",
    )
    expected_direction = "BULLISH" if selected_side is PaperSide.LONG else "BEARISH"
    if research_decision.direction_hint != expected_direction:
        fail(
            PaperReasonCode.PAPER_INPUT_SIDE_INVALID,
            "side does not match research direction",
            "side",
        )
    entry = require_decimal(entry_reference_price, "entry_reference_price", positive=True)
    stop = require_decimal(stop_price, "stop_price", positive=True)
    target = require_decimal(target_price, "target_price", positive=True)
    if (
        selected_side is PaperSide.LONG
        and not stop < entry < target
    ) or (
        selected_side is PaperSide.SHORT
        and not target < entry < stop
    ):
        fail(
            PaperReasonCode.PAPER_INPUT_STOP_TARGET_INVALID,
            "invalid stop-entry-target ordering",
            "stop_price",
        )
    closed, valid = _require_validity(
        closed_until_ms=research_decision.closed_until_ms,
        approved_at=approved_at,
        valid_until_ms=valid_until_ms,
        evaluation_time_ms=evaluation_time_ms,
    )
    health = _require_current_health(input_health_status)
    decision_id = require_identity(research_decision.decision_id, "decision_id")
    parts = _strategy_causal_tuple(
        research_strategy_decision_id=decision_id,
        setup_id=setup,
        pipeline_run_id=run,
        analysis_result_id=analysis,
        symbol=symbol,
        side=selected_side,
        entry_reference_price=entry,
        stop_price=stop,
        target_price=target,
        closed_until_ms=closed,
        approved_at=approved_at,
        valid_until_ms=valid,
        configuration_fingerprint=config,
        symbol_constraints_id=constraints,
        correlation_id=correlation,
        causation_id=causation,
    )
    return PaperStrategyApproval(
        approval_id=_identity("strategy-approval", parts),
        contract_version=PAPER_APPROVAL_CONTRACT_VERSION,
        research_strategy_decision_id=decision_id,
        setup_id=setup,
        pipeline_run_id=run,
        analysis_result_id=analysis,
        symbol=symbol,
        side=selected_side,
        entry_reference_price=entry,
        stop_price=stop,
        target_price=target,
        closed_until_ms=closed,
        approved_at=approved_at,
        valid_until_ms=valid,
        configuration_fingerprint=config,
        symbol_constraints_id=constraints,
        input_health_status=health,
        future_bars_used=False,
        paper_execution_approved=True,
        reason_code=PaperApprovalReasonCode.PAPER_STRATEGY_FINAL_APPROVED,
        correlation_id=correlation,
        causation_id=causation,
    )


@dataclass(frozen=True, slots=True)
class PaperQuantityApproval:
    quantity_approval_id: str
    contract_version: str
    paper_strategy_approval_id: str
    research_risk_decision_id: str
    symbol: str
    side: PaperSide
    approved_quantity: Decimal
    approval_source: PaperQuantityApprovalSource
    approved_at: datetime
    valid_until_ms: int
    configuration_fingerprint: str
    symbol_constraints_id: str
    position_size_approved: bool
    reason_code: PaperApprovalReasonCode
    correlation_id: str
    causation_id: str

    def __post_init__(self) -> None:
        if self.contract_version != PAPER_APPROVAL_CONTRACT_VERSION:
            fail(
                PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION,
                "unsupported quantity approval contract version",
                "contract_version",
            )
        for name in (
            "paper_strategy_approval_id",
            "research_risk_decision_id",
            "configuration_fingerprint",
            "symbol_constraints_id",
            "correlation_id",
            "causation_id",
        ):
            object.__setattr__(self, name, require_identity(getattr(self, name), name))
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
        require_decimal(
            self.approved_quantity,
            "approved_quantity",
            positive=True,
            reason_code=PaperReasonCode.PAPER_INPUT_QUANTITY_INVALID,
        )
        object.__setattr__(
            self,
            "approval_source",
            require_enum(
                self.approval_source,
                PaperQuantityApprovalSource,
                PaperReasonCode.PAPER_RISK_APPROVAL_MISSING,
                "approval_source",
            ),
        )
        require_nonnegative_int(self.valid_until_ms, "valid_until_ms")
        if self.valid_until_ms < _epoch_ms(self.approved_at, "approved_at"):
            fail(
                PaperReasonCode.PAPER_INPUT_VALIDITY_INVALID,
                "invalid quantity approval validity",
                "valid_until_ms",
            )
        if self.position_size_approved is not True:
            fail(
                PaperReasonCode.PAPER_RISK_APPROVAL_MISSING,
                "position size approval must be true",
                "position_size_approved",
            )
        object.__setattr__(
            self,
            "reason_code",
            require_enum(
                self.reason_code,
                PaperApprovalReasonCode,
                PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION,
                "reason_code",
            ),
        )
        if self.reason_code is not PaperApprovalReasonCode.PAPER_QUANTITY_CONTROLLED_APPROVED:
            fail(
                PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION,
                "invalid quantity approval reason",
                "reason_code",
            )
        if self.causation_id != self.paper_strategy_approval_id:
            fail(
                PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION,
                "quantity approval causation mismatch",
                "causation_id",
            )
        parts = (
            PAPER_APPROVAL_CONTRACT_VERSION,
            self.paper_strategy_approval_id,
            self.research_risk_decision_id,
            self.symbol,
            self.side,
            self.approved_quantity,
            self.approval_source,
            self.approved_at.isoformat(),
            self.valid_until_ms,
            self.configuration_fingerprint,
            self.symbol_constraints_id,
            self.correlation_id,
            self.causation_id,
        )
        if self.quantity_approval_id != _identity("quantity-approval", parts):
            fail(
                PaperReasonCode.PAPER_IDEMPOTENCY_KEY_INVALID,
                "quantity approval identity mismatch",
                "quantity_approval_id",
            )

    def to_dict(self) -> dict[str, object]:
        values = asdict(self)
        for name in ("side", "approval_source", "reason_code"):
            values[name] = getattr(values[name], "value", values[name])
        return values


def _require_matching_research_risk(
    strategy: PaperStrategyApproval,
    research_risk: RiskDecision,
) -> None:
    if not isinstance(research_risk, RiskDecision):
        fail(
            PaperReasonCode.PAPER_INPUT_RISK_MISSING,
            "research RiskDecision is required",
            "research_risk",
        )
    if research_risk.risk_status != "RISK_PRE_APPROVED_RESEARCH":
        fail(
            PaperReasonCode.PAPER_RISK_NOT_APPROVED,
            "research risk outcome is not pre-approved",
            "research_risk.risk_status",
        )
    expected_direction = "BULLISH" if strategy.side is PaperSide.LONG else "BEARISH"
    if (
        research_risk.source_strategy_decision_id
        != strategy.research_strategy_decision_id
        or research_risk.source_setup_id != strategy.setup_id
        or research_risk.source_analysis_snapshot_id != strategy.analysis_result_id
        or normalize_symbol(research_risk.symbol) != strategy.symbol
        or research_risk.closed_until_ms != strategy.closed_until_ms
        or research_risk.direction_hint != expected_direction
        or research_risk.future_bars_used is not False
    ):
        fail(
            PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION,
            "research risk causal graph mismatch",
            "research_risk",
        )


def issue_paper_quantity_approval(
    strategy: PaperStrategyApproval,
    research_risk: RiskDecision,
    *,
    mode: ExecutionMode,
    paper_authorized: bool,
    requested_quantity: Decimal,
    approval_source: PaperQuantityApprovalSource,
    approved_at: datetime,
    valid_until_ms: int,
    evaluation_time_ms: int,
    correlation_id: str,
    causation_id: str,
) -> PaperQuantityApproval:
    _require_explicit_paper(mode, paper_authorized)
    if (
        not isinstance(strategy, PaperStrategyApproval)
        or strategy.paper_execution_approved is not True
    ):
        fail(
            PaperReasonCode.PAPER_RISK_APPROVAL_MISSING,
            "final strategy approval is required",
            "strategy",
        )
    _require_matching_research_risk(strategy, research_risk)
    source = require_enum(
        approval_source,
        PaperQuantityApprovalSource,
        PaperReasonCode.PAPER_RISK_APPROVAL_MISSING,
        "approval_source",
    )
    quantity = require_decimal(
        requested_quantity,
        "requested_quantity",
        positive=True,
        reason_code=PaperReasonCode.PAPER_INPUT_QUANTITY_INVALID,
    )
    _, valid = _require_validity(
        closed_until_ms=strategy.closed_until_ms,
        approved_at=approved_at,
        valid_until_ms=valid_until_ms,
        evaluation_time_ms=evaluation_time_ms,
    )
    if valid > strategy.valid_until_ms:
        fail(
            PaperReasonCode.PAPER_INPUT_VALIDITY_INVALID,
            "quantity authority outlives strategy authority",
            "valid_until_ms",
        )
    correlation = require_identity(correlation_id, "correlation_id")
    causation = require_identity(causation_id, "causation_id")
    if (
        correlation != strategy.correlation_id
        or causation != strategy.approval_id
    ):
        fail(
            PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION,
            "quantity approval causal graph mismatch",
            "causation_id",
        )
    risk_id = require_identity(research_risk.risk_decision_id, "risk_decision_id")
    parts = (
        PAPER_APPROVAL_CONTRACT_VERSION,
        strategy.approval_id,
        risk_id,
        strategy.symbol,
        strategy.side,
        quantity,
        source,
        approved_at.isoformat(),
        valid,
        strategy.configuration_fingerprint,
        strategy.symbol_constraints_id,
        correlation,
        causation,
    )
    return PaperQuantityApproval(
        quantity_approval_id=_identity("quantity-approval", parts),
        contract_version=PAPER_APPROVAL_CONTRACT_VERSION,
        paper_strategy_approval_id=strategy.approval_id,
        research_risk_decision_id=risk_id,
        symbol=strategy.symbol,
        side=strategy.side,
        approved_quantity=quantity,
        approval_source=source,
        approved_at=approved_at,
        valid_until_ms=valid,
        configuration_fingerprint=strategy.configuration_fingerprint,
        symbol_constraints_id=strategy.symbol_constraints_id,
        position_size_approved=True,
        reason_code=PaperApprovalReasonCode.PAPER_QUANTITY_CONTROLLED_APPROVED,
        correlation_id=correlation,
        causation_id=causation,
    )


@dataclass(frozen=True, slots=True)
class PaperRiskApproval:
    approval_id: str
    contract_version: str
    paper_strategy_approval_id: str
    research_risk_decision_id: str
    quantity_approval_id: str
    setup_id: str
    pipeline_run_id: str
    analysis_result_id: str
    symbol: str
    side: PaperSide
    approved_quantity: Decimal
    approved_at: datetime
    valid_until_ms: int
    configuration_fingerprint: str
    symbol_constraints_id: str
    order_approved: bool
    execution_approved: bool
    position_size_approved: bool
    final_paper_approval: bool
    reason_code: PaperApprovalReasonCode
    correlation_id: str
    causation_id: str

    def __post_init__(self) -> None:
        if self.contract_version != PAPER_APPROVAL_CONTRACT_VERSION:
            fail(
                PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION,
                "unsupported risk approval contract version",
                "contract_version",
            )
        for name in (
            "paper_strategy_approval_id",
            "research_risk_decision_id",
            "quantity_approval_id",
            "setup_id",
            "pipeline_run_id",
            "analysis_result_id",
            "configuration_fingerprint",
            "symbol_constraints_id",
            "correlation_id",
            "causation_id",
        ):
            object.__setattr__(self, name, require_identity(getattr(self, name), name))
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
        require_decimal(
            self.approved_quantity,
            "approved_quantity",
            positive=True,
            reason_code=PaperReasonCode.PAPER_INPUT_QUANTITY_INVALID,
        )
        require_nonnegative_int(self.valid_until_ms, "valid_until_ms")
        if self.valid_until_ms < _epoch_ms(self.approved_at, "approved_at"):
            fail(
                PaperReasonCode.PAPER_INPUT_VALIDITY_INVALID,
                "invalid final risk approval validity",
                "valid_until_ms",
            )
        if (
            self.order_approved,
            self.execution_approved,
            self.position_size_approved,
            self.final_paper_approval,
        ) != (True, True, True, True):
            fail(
                PaperReasonCode.PAPER_RISK_APPROVAL_MISSING,
                "all final PAPER risk flags must be true",
                "final_paper_approval",
            )
        object.__setattr__(
            self,
            "reason_code",
            require_enum(
                self.reason_code,
                PaperApprovalReasonCode,
                PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION,
                "reason_code",
            ),
        )
        if self.reason_code is not PaperApprovalReasonCode.PAPER_RISK_FINAL_APPROVED:
            fail(
                PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION,
                "invalid final risk approval reason",
                "reason_code",
            )
        if (
            self.correlation_id != self.pipeline_run_id
            or self.causation_id != self.quantity_approval_id
        ):
            fail(
                PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION,
                "final risk approval causal IDs mismatch",
                "causation_id",
            )
        parts = (
            PAPER_APPROVAL_CONTRACT_VERSION,
            self.paper_strategy_approval_id,
            self.research_risk_decision_id,
            self.quantity_approval_id,
            self.setup_id,
            self.pipeline_run_id,
            self.analysis_result_id,
            self.symbol,
            self.side,
            self.approved_quantity,
            self.approved_at.isoformat(),
            self.valid_until_ms,
            self.configuration_fingerprint,
            self.symbol_constraints_id,
            self.correlation_id,
            self.causation_id,
        )
        if self.approval_id != _identity("risk-approval", parts):
            fail(
                PaperReasonCode.PAPER_IDEMPOTENCY_KEY_INVALID,
                "final risk approval identity mismatch",
                "approval_id",
            )

    def to_dict(self) -> dict[str, object]:
        values = asdict(self)
        for name in ("side", "reason_code"):
            values[name] = getattr(values[name], "value", values[name])
        return values


def finalize_paper_risk_approval(
    strategy: PaperStrategyApproval,
    research_risk: RiskDecision,
    quantity: PaperQuantityApproval,
    *,
    mode: ExecutionMode,
    paper_authorized: bool,
    approved_at: datetime,
    evaluation_time_ms: int,
    correlation_id: str,
    causation_id: str,
) -> PaperRiskApproval:
    _require_explicit_paper(mode, paper_authorized)
    if (
        not isinstance(strategy, PaperStrategyApproval)
        or strategy.paper_execution_approved is not True
    ):
        fail(
            PaperReasonCode.PAPER_RISK_APPROVAL_MISSING,
            "final strategy approval is required",
            "strategy",
        )
    _require_matching_research_risk(strategy, research_risk)
    if not isinstance(quantity, PaperQuantityApproval):
        fail(
            PaperReasonCode.PAPER_INPUT_QUANTITY_INVALID,
            "PaperQuantityApproval authority is required",
            "quantity",
        )
    if (
        quantity.paper_strategy_approval_id != strategy.approval_id
        or quantity.research_risk_decision_id != research_risk.risk_decision_id
        or quantity.symbol != strategy.symbol
        or quantity.side is not strategy.side
        or quantity.configuration_fingerprint != strategy.configuration_fingerprint
        or quantity.symbol_constraints_id != strategy.symbol_constraints_id
        or quantity.position_size_approved is not True
    ):
        fail(
            PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION,
            "quantity approval causal graph mismatch",
            "quantity",
        )
    correlation = require_identity(correlation_id, "correlation_id")
    causation = require_identity(causation_id, "causation_id")
    if correlation != strategy.correlation_id or causation != quantity.quantity_approval_id:
        fail(
            PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION,
            "final risk approval causal graph mismatch",
            "causation_id",
        )
    valid = min(strategy.valid_until_ms, quantity.valid_until_ms)
    _require_validity(
        closed_until_ms=strategy.closed_until_ms,
        approved_at=approved_at,
        valid_until_ms=valid,
        evaluation_time_ms=evaluation_time_ms,
    )
    parts = (
        PAPER_APPROVAL_CONTRACT_VERSION,
        strategy.approval_id,
        research_risk.risk_decision_id,
        quantity.quantity_approval_id,
        strategy.setup_id,
        strategy.pipeline_run_id,
        strategy.analysis_result_id,
        strategy.symbol,
        strategy.side,
        quantity.approved_quantity,
        approved_at.isoformat(),
        valid,
        strategy.configuration_fingerprint,
        strategy.symbol_constraints_id,
        correlation,
        causation,
    )
    return PaperRiskApproval(
        approval_id=_identity("risk-approval", parts),
        contract_version=PAPER_APPROVAL_CONTRACT_VERSION,
        paper_strategy_approval_id=strategy.approval_id,
        research_risk_decision_id=research_risk.risk_decision_id,
        quantity_approval_id=quantity.quantity_approval_id,
        setup_id=strategy.setup_id,
        pipeline_run_id=strategy.pipeline_run_id,
        analysis_result_id=strategy.analysis_result_id,
        symbol=strategy.symbol,
        side=strategy.side,
        approved_quantity=quantity.approved_quantity,
        approved_at=approved_at,
        valid_until_ms=valid,
        configuration_fingerprint=strategy.configuration_fingerprint,
        symbol_constraints_id=strategy.symbol_constraints_id,
        order_approved=True,
        execution_approved=True,
        position_size_approved=True,
        final_paper_approval=True,
        reason_code=PaperApprovalReasonCode.PAPER_RISK_FINAL_APPROVED,
        correlation_id=correlation,
        causation_id=causation,
    )


@dataclass(frozen=True, slots=True)
class PaperCommandApprovalCompatibility:
    strategy_decision_id: str
    risk_decision_id: str
    setup_id: str
    pipeline_run_id: str
    analysis_result_id: str
    symbol: str
    side: PaperSide
    entry_reference_price: Decimal
    stop_price: Decimal
    target_price: Decimal
    approved_quantity: Decimal
    closed_until_ms: int
    valid_until_ms: int
    configuration_fingerprint: str
    symbol_constraints_id: str
    paper_execution_approved: bool
    order_approved: bool
    execution_approved: bool
    position_size_approved: bool
    final_paper_approval: bool


def map_final_approvals_to_command_compatibility(
    strategy: PaperStrategyApproval,
    quantity: PaperQuantityApproval,
    risk: PaperRiskApproval,
) -> PaperCommandApprovalCompatibility:
    """Return command inputs only; never create a command or order."""

    if (
        risk.paper_strategy_approval_id != strategy.approval_id
        or risk.quantity_approval_id != quantity.quantity_approval_id
        or risk.research_risk_decision_id != quantity.research_risk_decision_id
        or quantity.paper_strategy_approval_id != strategy.approval_id
        or risk.approved_quantity != quantity.approved_quantity
        or risk.symbol != strategy.symbol
        or risk.side is not strategy.side
        or risk.configuration_fingerprint != strategy.configuration_fingerprint
        or risk.symbol_constraints_id != strategy.symbol_constraints_id
        or (
            strategy.paper_execution_approved,
            quantity.position_size_approved,
            risk.order_approved,
            risk.execution_approved,
            risk.position_size_approved,
            risk.final_paper_approval,
        )
        != (True, True, True, True, True, True)
    ):
        fail(
            PaperReasonCode.PAPER_RISK_APPROVAL_MISSING,
            "complete final PAPER approval chain is required",
            "risk",
        )
    return PaperCommandApprovalCompatibility(
        strategy_decision_id=strategy.research_strategy_decision_id,
        risk_decision_id=risk.research_risk_decision_id,
        setup_id=strategy.setup_id,
        pipeline_run_id=strategy.pipeline_run_id,
        analysis_result_id=strategy.analysis_result_id,
        symbol=strategy.symbol,
        side=strategy.side,
        entry_reference_price=strategy.entry_reference_price,
        stop_price=strategy.stop_price,
        target_price=strategy.target_price,
        approved_quantity=quantity.approved_quantity,
        closed_until_ms=strategy.closed_until_ms,
        valid_until_ms=risk.valid_until_ms,
        configuration_fingerprint=strategy.configuration_fingerprint,
        symbol_constraints_id=strategy.symbol_constraints_id,
        paper_execution_approved=True,
        order_approved=True,
        execution_approved=True,
        position_size_approved=True,
        final_paper_approval=True,
    )


def approval_serialization(value: object) -> Mapping[str, object]:
    if not isinstance(value, (PaperStrategyApproval, PaperQuantityApproval, PaperRiskApproval)):
        raise TypeError("unsupported PAPER approval contract")
    return value.to_dict()
