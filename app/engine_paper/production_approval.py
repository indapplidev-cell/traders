"""Read-only production decision source boundary for future PAPER commands.

The adapter reads the revision-0008 online orchestrator persistence.  It does
not run analysis, setup, strategy, risk, approval, sizing, or command services.
An eligible candidate is possible only when the persisted result already
contains the complete immutable approval objects accepted by command
ingestion.  The currently deployed research pipeline normally has no such
objects, which is a healthy, fail-closed outcome.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from hashlib import sha256
import json
from typing import TYPE_CHECKING, Any, Final, Protocol

from sqlalchemy import Select, select, text
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import TextClause

from app.engine_orchestrator.orchestrator_models import (
    OnlinePipelineResultRow,
    OnlinePipelineRun,
)
from app.trading_universe.domain import PREPARED_NEXT_TRADING_UNIVERSE
if TYPE_CHECKING:
    from app.engine_paper.paper_approvals import PaperQuantityApprovalSource
    from app.engine_safety.paper_domain import PaperSide


ADAPTER_SCHEMA_VERSION: Final = "PAPER_PRODUCTION_APPROVAL_SOURCE/1.0"
ADAPTER_VERSION: Final = "1.0.0"
AUTHORITATIVE_SOURCE: Final = "PRODUCTION_PERSISTED_ONLINE_PIPELINE_RESULTS"
AUTHORITATIVE_ANALYSIS_SOURCE: Final = "online_pipeline_results.analysis_payload_json"
AUTHORITATIVE_SETUP_SOURCE: Final = "online_pipeline_results.setup_payload_json"
AUTHORITATIVE_STRATEGY_SOURCE: Final = "online_pipeline_results.strategy_payload_json"
AUTHORITATIVE_RISK_SOURCE: Final = "online_pipeline_results.risk_payload_json"
AUTHORITATIVE_FINAL_APPROVAL_SOURCE: Final = "paper_payload_json.persisted_final_approvals"
AUTHORITATIVE_QUANTITY_SOURCE: Final = "PaperQuantityApproval.CONTROLLED_PAPER_AUTHORITY"
SYMBOL_ALLOWLIST: Final = PREPARED_NEXT_TRADING_UNIVERSE.symbols
PRIMARY_TIMEFRAME: Final = "15m"
MAX_SYMBOLS_PER_REQUEST: Final = 10
MAX_RUN_LOOKBACK: Final = 8
MAX_RESULTS_PER_MODULE: Final = 8
MAX_ROWS_PER_REQUEST: Final = 80
MAX_CANDIDATES_PER_REQUEST: Final = 10
MAX_TIME_RANGE_MS: Final = 7 * 24 * 60 * 60 * 1000
_TRANSACTION_CONTROL: Final = "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
_COMPLETE_STATUSES: Final = frozenset({"COMPLETED"})
_SETUP_ELIGIBLE: Final = frozenset({"SETUP_CANDIDATE"})
_STRATEGY_ALLOWED: Final = frozenset({"ALLOW_RESEARCH_TRADE_PLAN"})
_RISK_APPROVED: Final = frozenset({"RISK_PRE_APPROVED_RESEARCH", "RISK_APPROVED"})
_RISK_REJECTED: Final = frozenset({"REJECT", "RISK_REJECTED"})
_RISK_DEFERRED: Final = frozenset({"WAIT", "RISK_DEFERRED"})
_FINAL_APPROVAL_KEYS: Final = (
    "paper_strategy_approval",
    "paper_quantity_approval",
    "paper_risk_approval",
)


class PaperProductionApprovalOutcome(StrEnum):
    ELIGIBLE_APPROVAL = "ELIGIBLE_APPROVAL"
    NO_ELIGIBLE_APPROVAL = "NO_ELIGIBLE_APPROVAL"
    NO_TRADE_SIGNAL = "NO_TRADE_SIGNAL"
    SETUP_NOT_ELIGIBLE = "SETUP_NOT_ELIGIBLE"
    STRATEGY_NOT_EXECUTABLE = "STRATEGY_NOT_EXECUTABLE"
    RISK_REJECTED = "RISK_REJECTED"
    RISK_DEFERRED = "RISK_DEFERRED"
    APPROVAL_NOT_FINAL = "APPROVAL_NOT_FINAL"
    EXECUTION_NOT_APPROVED = "EXECUTION_NOT_APPROVED"
    QUANTITY_NOT_APPROVED = "QUANTITY_NOT_APPROVED"
    INVALID_QUANTITY = "INVALID_QUANTITY"
    STALE_APPROVAL = "STALE_APPROVAL"
    SUPERSEDED_APPROVAL = "SUPERSEDED_APPROVAL"
    AMBIGUOUS_APPROVAL = "AMBIGUOUS_APPROVAL"
    CAUSALITY_MISMATCH = "CAUSALITY_MISMATCH"
    MARKET_DATA_WATERMARK_MISMATCH = "MARKET_DATA_WATERMARK_MISMATCH"
    SYMBOL_MISMATCH = "SYMBOL_MISMATCH"
    SIDE_MISMATCH = "SIDE_MISMATCH"
    FUTURE_DECISION = "FUTURE_DECISION"
    TARGET_NOT_ALLOWED = "TARGET_NOT_ALLOWED"
    SCHEMA_NOT_SUPPORTED = "SCHEMA_NOT_SUPPORTED"
    BOUNDED_LIMIT_EXCEEDED = "BOUNDED_LIMIT_EXCEEDED"
    READ_ONLY_POLICY_VIOLATION = "READ_ONLY_POLICY_VIOLATION"
    CANCELLED = "CANCELLED"
    SAFE_FAILURE = "SAFE_FAILURE"


class PaperProductionApprovalReadiness(StrEnum):
    READY = "READY"
    HEALTHY_NO_ELIGIBLE_APPROVAL = "HEALTHY_NO_ELIGIBLE_APPROVAL"
    NOT_READY = "NOT_READY"
    CANCELLED = "CANCELLED"


class PaperProductionApprovalFindingCode(StrEnum):
    APPROVAL_SOURCE_ELIGIBLE = "APPROVAL_SOURCE_ELIGIBLE"
    APPROVAL_SOURCE_NO_ELIGIBLE_APPROVAL = "APPROVAL_SOURCE_NO_ELIGIBLE_APPROVAL"
    APPROVAL_SOURCE_NO_TRADE_SIGNAL = "APPROVAL_SOURCE_NO_TRADE_SIGNAL"
    APPROVAL_SOURCE_SETUP_NOT_ELIGIBLE = "APPROVAL_SOURCE_SETUP_NOT_ELIGIBLE"
    APPROVAL_SOURCE_STRATEGY_NOT_EXECUTABLE = "APPROVAL_SOURCE_STRATEGY_NOT_EXECUTABLE"
    APPROVAL_SOURCE_RISK_REJECTED = "APPROVAL_SOURCE_RISK_REJECTED"
    APPROVAL_SOURCE_RISK_DEFERRED = "APPROVAL_SOURCE_RISK_DEFERRED"
    APPROVAL_SOURCE_FINAL_APPROVAL_MISSING = "APPROVAL_SOURCE_FINAL_APPROVAL_MISSING"
    APPROVAL_SOURCE_EXECUTION_NOT_APPROVED = "APPROVAL_SOURCE_EXECUTION_NOT_APPROVED"
    APPROVAL_SOURCE_QUANTITY_NOT_APPROVED = "APPROVAL_SOURCE_QUANTITY_NOT_APPROVED"
    APPROVAL_SOURCE_INVALID_QUANTITY = "APPROVAL_SOURCE_INVALID_QUANTITY"
    APPROVAL_SOURCE_STALE = "APPROVAL_SOURCE_STALE"
    APPROVAL_SOURCE_SUPERSEDED = "APPROVAL_SOURCE_SUPERSEDED"
    APPROVAL_SOURCE_AMBIGUOUS = "APPROVAL_SOURCE_AMBIGUOUS"
    APPROVAL_SOURCE_CAUSALITY_MISMATCH = "APPROVAL_SOURCE_CAUSALITY_MISMATCH"
    APPROVAL_SOURCE_MARKET_DATA_WATERMARK_MISMATCH = "APPROVAL_SOURCE_MARKET_DATA_WATERMARK_MISMATCH"
    APPROVAL_SOURCE_SYMBOL_MISMATCH = "APPROVAL_SOURCE_SYMBOL_MISMATCH"
    APPROVAL_SOURCE_SIDE_MISMATCH = "APPROVAL_SOURCE_SIDE_MISMATCH"
    APPROVAL_SOURCE_FUTURE_DECISION = "APPROVAL_SOURCE_FUTURE_DECISION"
    APPROVAL_SOURCE_TARGET_NOT_ALLOWED = "APPROVAL_SOURCE_TARGET_NOT_ALLOWED"
    APPROVAL_SOURCE_SCHEMA_NOT_SUPPORTED = "APPROVAL_SOURCE_SCHEMA_NOT_SUPPORTED"
    APPROVAL_SOURCE_LIMIT_EXCEEDED = "APPROVAL_SOURCE_LIMIT_EXCEEDED"
    APPROVAL_SOURCE_READ_ONLY_VIOLATION = "APPROVAL_SOURCE_READ_ONLY_VIOLATION"
    APPROVAL_SOURCE_CANCELLED = "APPROVAL_SOURCE_CANCELLED"
    APPROVAL_SOURCE_SAFE_FAILURE = "APPROVAL_SOURCE_SAFE_FAILURE"


_FINDING_BY_OUTCOME: Final = {
    PaperProductionApprovalOutcome.ELIGIBLE_APPROVAL: PaperProductionApprovalFindingCode.APPROVAL_SOURCE_ELIGIBLE,
    PaperProductionApprovalOutcome.NO_ELIGIBLE_APPROVAL: PaperProductionApprovalFindingCode.APPROVAL_SOURCE_NO_ELIGIBLE_APPROVAL,
    PaperProductionApprovalOutcome.NO_TRADE_SIGNAL: PaperProductionApprovalFindingCode.APPROVAL_SOURCE_NO_TRADE_SIGNAL,
    PaperProductionApprovalOutcome.SETUP_NOT_ELIGIBLE: PaperProductionApprovalFindingCode.APPROVAL_SOURCE_SETUP_NOT_ELIGIBLE,
    PaperProductionApprovalOutcome.STRATEGY_NOT_EXECUTABLE: PaperProductionApprovalFindingCode.APPROVAL_SOURCE_STRATEGY_NOT_EXECUTABLE,
    PaperProductionApprovalOutcome.RISK_REJECTED: PaperProductionApprovalFindingCode.APPROVAL_SOURCE_RISK_REJECTED,
    PaperProductionApprovalOutcome.RISK_DEFERRED: PaperProductionApprovalFindingCode.APPROVAL_SOURCE_RISK_DEFERRED,
    PaperProductionApprovalOutcome.APPROVAL_NOT_FINAL: PaperProductionApprovalFindingCode.APPROVAL_SOURCE_FINAL_APPROVAL_MISSING,
    PaperProductionApprovalOutcome.EXECUTION_NOT_APPROVED: PaperProductionApprovalFindingCode.APPROVAL_SOURCE_EXECUTION_NOT_APPROVED,
    PaperProductionApprovalOutcome.QUANTITY_NOT_APPROVED: PaperProductionApprovalFindingCode.APPROVAL_SOURCE_QUANTITY_NOT_APPROVED,
    PaperProductionApprovalOutcome.INVALID_QUANTITY: PaperProductionApprovalFindingCode.APPROVAL_SOURCE_INVALID_QUANTITY,
    PaperProductionApprovalOutcome.STALE_APPROVAL: PaperProductionApprovalFindingCode.APPROVAL_SOURCE_STALE,
    PaperProductionApprovalOutcome.SUPERSEDED_APPROVAL: PaperProductionApprovalFindingCode.APPROVAL_SOURCE_SUPERSEDED,
    PaperProductionApprovalOutcome.AMBIGUOUS_APPROVAL: PaperProductionApprovalFindingCode.APPROVAL_SOURCE_AMBIGUOUS,
    PaperProductionApprovalOutcome.CAUSALITY_MISMATCH: PaperProductionApprovalFindingCode.APPROVAL_SOURCE_CAUSALITY_MISMATCH,
    PaperProductionApprovalOutcome.MARKET_DATA_WATERMARK_MISMATCH: PaperProductionApprovalFindingCode.APPROVAL_SOURCE_MARKET_DATA_WATERMARK_MISMATCH,
    PaperProductionApprovalOutcome.SYMBOL_MISMATCH: PaperProductionApprovalFindingCode.APPROVAL_SOURCE_SYMBOL_MISMATCH,
    PaperProductionApprovalOutcome.SIDE_MISMATCH: PaperProductionApprovalFindingCode.APPROVAL_SOURCE_SIDE_MISMATCH,
    PaperProductionApprovalOutcome.FUTURE_DECISION: PaperProductionApprovalFindingCode.APPROVAL_SOURCE_FUTURE_DECISION,
    PaperProductionApprovalOutcome.TARGET_NOT_ALLOWED: PaperProductionApprovalFindingCode.APPROVAL_SOURCE_TARGET_NOT_ALLOWED,
    PaperProductionApprovalOutcome.SCHEMA_NOT_SUPPORTED: PaperProductionApprovalFindingCode.APPROVAL_SOURCE_SCHEMA_NOT_SUPPORTED,
    PaperProductionApprovalOutcome.BOUNDED_LIMIT_EXCEEDED: PaperProductionApprovalFindingCode.APPROVAL_SOURCE_LIMIT_EXCEEDED,
    PaperProductionApprovalOutcome.READ_ONLY_POLICY_VIOLATION: PaperProductionApprovalFindingCode.APPROVAL_SOURCE_READ_ONLY_VIOLATION,
    PaperProductionApprovalOutcome.CANCELLED: PaperProductionApprovalFindingCode.APPROVAL_SOURCE_CANCELLED,
    PaperProductionApprovalOutcome.SAFE_FAILURE: PaperProductionApprovalFindingCode.APPROVAL_SOURCE_SAFE_FAILURE,
}


@dataclass(frozen=True, slots=True)
class PaperProductionApprovalScope:
    symbols: tuple[str, ...]
    primary_timeframe: str = PRIMARY_TIMEFRAME
    max_run_lookback: int = MAX_RUN_LOOKBACK
    max_results_per_module: int = MAX_RESULTS_PER_MODULE
    max_candidates: int = MAX_CANDIDATES_PER_REQUEST
    start_ms: int | None = None


@dataclass(frozen=True, slots=True)
class PaperProductionApprovalRequest:
    scope: PaperProductionApprovalScope
    request_id: str
    as_of_ms: int | None = None


@dataclass(frozen=True, slots=True)
class PaperProductionApprovalWatermark:
    symbol: str
    primary_timeframe: str
    closed_until_ms: int
    source_market_data_snapshot_id: str
    watermark_id: str


@dataclass(frozen=True, slots=True)
class PaperProductionApprovalLineage:
    source_run_id: str
    analysis_result_id: str
    setup_id: str
    strategy_decision_id: str
    risk_decision_id: str
    strategy_approval_id: str
    quantity_approval_id: str
    final_approval_id: str
    lineage_id: str


@dataclass(frozen=True, slots=True)
class PaperProductionApprovalQuantityAuthority:
    quantity_approval_id: str
    approved_quantity: Decimal
    approval_source: PaperQuantityApprovalSource
    approved_at: datetime
    valid_until_ms: int


@dataclass(frozen=True, slots=True)
class PaperProductionApprovalRankingInputs:
    """Validated dimensionless quality inputs copied from the persisted decision."""

    risk_score: Decimal | None
    planned_risk_reward: Decimal
    strategy_score: Decimal | None
    closed_until_ms: int
    source_run_id: str
    final_approval_id: str


@dataclass(frozen=True, slots=True)
class PaperProductionApprovalCandidate:
    candidate_id: str
    source: str
    symbol: str
    side: PaperSide
    entry_reference_price: Decimal
    stop_price: Decimal
    target_price: Decimal
    decision_timestamp: datetime
    valid_until_ms: int
    watermark: PaperProductionApprovalWatermark
    lineage: PaperProductionApprovalLineage
    quantity_authority: PaperProductionApprovalQuantityAuthority
    configuration_fingerprint: str
    symbol_constraints_id: str
    paper_strategy_approval: PaperStrategyApproval
    paper_quantity_approval: PaperQuantityApproval
    paper_risk_approval: PaperRiskApproval
    ranking: PaperProductionApprovalRankingInputs


@dataclass(frozen=True, slots=True)
class PaperProductionApprovalFinding:
    code: PaperProductionApprovalFindingCode
    symbol: str | None = None
    source_run_id: str | None = None


@dataclass(frozen=True, slots=True)
class PaperProductionApprovalSymbolResult:
    symbol: str
    outcome: PaperProductionApprovalOutcome
    trade_signal_class: str
    strategy_class: str
    risk_class: str
    approval_class: str
    quantity_authority_class: str
    lineage_valid: bool
    freshness_class: str
    source_run_id: str | None
    candidate: PaperProductionApprovalCandidate | None = None


@dataclass(frozen=True, slots=True)
class PaperProductionApprovalResult:
    outcome: PaperProductionApprovalOutcome
    readiness: PaperProductionApprovalReadiness
    request_id: str
    as_of_ms: int | None
    symbol_results: tuple[PaperProductionApprovalSymbolResult, ...] = ()
    findings: tuple[PaperProductionApprovalFinding, ...] = ()
    query_count: int = 0
    rows_read: int = 0
    duration_ms: float = 0.0
    read_only: bool = True
    consistent_snapshot: bool = True

    @property
    def candidates(self) -> tuple[PaperProductionApprovalCandidate, ...]:
        return tuple(value.candidate for value in self.symbol_results if value.candidate)

    def safe_report(self) -> dict[str, object]:
        return {
            "schema_version": ADAPTER_SCHEMA_VERSION,
            "adapter_version": ADAPTER_VERSION,
            "request_id": self.request_id,
            "source_class": AUTHORITATIVE_SOURCE,
            "outcome": self.outcome.value,
            "readiness": self.readiness.value,
            "as_of_ms": self.as_of_ms,
            "symbols": [
                {
                    "symbol": value.symbol,
                    "outcome": value.outcome.value,
                    "trade_signal_class": value.trade_signal_class,
                    "strategy_class": value.strategy_class,
                    "risk_class": value.risk_class,
                    "approval_class": value.approval_class,
                    "quantity_authority_class": value.quantity_authority_class,
                    "lineage_valid": value.lineage_valid,
                    "freshness_class": value.freshness_class,
                    "source_run_id": value.source_run_id,
                    "candidate_semantic_id": value.candidate.candidate_id if value.candidate else None,
                }
                for value in self.symbol_results
            ],
            "candidate_count": len(self.candidates),
            "finding_codes": [value.code.value for value in self.findings],
            "query_count": self.query_count,
            "rows_read": self.rows_read,
            "duration_ms": round(self.duration_ms, 3),
            "read_only": self.read_only,
            "consistent_snapshot": self.consistent_snapshot,
        }


class CancellationToken(Protocol):
    def is_set(self) -> bool: ...


class _Cancelled(RuntimeError):
    pass


class ReadOnlyPolicyViolation(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class _PersistedDecision:
    run_pk: int
    result_pk: int | None
    run_id: str
    symbol: str
    primary_timeframe: str
    closed_until_ms: int
    status: str
    finished_at: datetime | None
    freshness_deadline_at: datetime | None
    future_bars_used: bool
    is_trade_signal: bool
    is_executable: bool
    order_approved: bool
    execution_approved: bool
    position_opened: bool
    position_size_approved: bool
    analysis_status: str | None
    setup_status: str | None
    strategy_status: str | None
    risk_status: str | None
    paper_status: str | None
    analysis: Mapping[str, Any]
    setup: Mapping[str, Any]
    strategy: Mapping[str, Any]
    risk: Mapping[str, Any]
    paper: Mapping[str, Any]


class _ReadOnlyExecutor:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.query_count = 0

    def execute(self, statement: Any, parameters: Mapping[str, object] | None = None) -> Any:
        if isinstance(statement, Select):
            pass
        elif isinstance(statement, TextClause):
            if " ".join(statement.text.upper().split()) != _TRANSACTION_CONTROL:
                raise ReadOnlyPolicyViolation("APPROVAL_SOURCE_READ_ONLY_VIOLATION")
        else:
            raise ReadOnlyPolicyViolation("APPROVAL_SOURCE_READ_ONLY_VIOLATION")
        self.query_count += 1
        return self.session.execute(statement, parameters or {})


class PaperProductionApprovalReader(Protocol):
    def read_clock_ms(self, executor: _ReadOnlyExecutor) -> int: ...
    def read_recent(
        self,
        executor: _ReadOnlyExecutor,
        symbol: str,
        timeframe: str,
        limit: int,
        start_ms: int | None,
    ) -> Sequence[_PersistedDecision]: ...


class SqlAlchemyPaperProductionApprovalReader:
    """Bounded revision-0008 SELECTs with atomic run/result joins."""

    def read_clock_ms(self, executor: _ReadOnlyExecutor) -> int:
        statement = select(text(
            "CAST(EXTRACT(EPOCH FROM transaction_timestamp()) * 1000 AS BIGINT)"
        ))
        return int(executor.execute(statement).scalar_one())

    def read_recent(
        self,
        executor: _ReadOnlyExecutor,
        symbol: str,
        timeframe: str,
        limit: int,
        start_ms: int | None,
    ) -> Sequence[_PersistedDecision]:
        statement = (
            select(OnlinePipelineRun, OnlinePipelineResultRow)
            .outerjoin(
                OnlinePipelineResultRow,
                OnlinePipelineResultRow.run_id == OnlinePipelineRun.run_id,
            )
            .where(
                OnlinePipelineRun.symbol == symbol,
                OnlinePipelineRun.primary_timeframe == timeframe,
            )
            .order_by(
                OnlinePipelineRun.closed_until_ms.desc(),
                OnlinePipelineRun.id.desc(),
                OnlinePipelineResultRow.id.desc(),
            )
            .limit(limit)
        )
        if start_ms is not None:
            statement = statement.where(OnlinePipelineRun.closed_until_ms >= start_ms)
        return tuple(self._map(run, result) for run, result in executor.execute(statement))

    @staticmethod
    def _map(run: OnlinePipelineRun, result: OnlinePipelineResultRow | None) -> _PersistedDecision:
        mapping = lambda value: value if isinstance(value, Mapping) else {}
        return _PersistedDecision(
            int(run.id), int(result.id) if result is not None else None,
            str(run.run_id), str(run.symbol), str(run.primary_timeframe),
            int(run.closed_until_ms), str(run.status), run.finished_at,
            run.freshness_deadline_at, bool(run.future_bars_used),
            bool(run.is_trade_signal), bool(run.is_executable),
            bool(run.order_approved), bool(run.execution_approved),
            bool(run.position_opened), bool(run.position_size_approved),
            run.analysis_status, run.setup_status, run.strategy_status,
            run.risk_status, run.paper_status,
            mapping(result.analysis_payload_json) if result else {},
            mapping(result.setup_payload_json) if result else {},
            mapping(result.strategy_payload_json) if result else {},
            mapping(result.risk_payload_json) if result else {},
            mapping(result.paper_payload_json) if result else {},
        )


def _canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("timestamp is not timezone-aware")
        return value.astimezone(timezone.utc)
    if not isinstance(value, str):
        raise ValueError("timestamp missing")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp is not timezone-aware")
    return parsed.astimezone(timezone.utc)


def _decimal(value: object) -> Decimal:
    if isinstance(value, bool):
        raise ValueError("boolean is not a quantity")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as error:
        raise ValueError("invalid decimal") from error
    if not result.is_finite():
        raise ValueError("non-finite decimal")
    return result


def _strategy_approval(value: Mapping[str, Any]) -> Any:
    from app.engine_paper.paper_approvals import PaperApprovalReasonCode, PaperStrategyApproval
    from app.engine_safety.paper_domain import PaperInputHealthStatus, PaperSide

    return PaperStrategyApproval(
        approval_id=str(value["approval_id"]), contract_version=str(value["contract_version"]),
        research_strategy_decision_id=str(value["research_strategy_decision_id"]),
        setup_id=str(value["setup_id"]), pipeline_run_id=str(value["pipeline_run_id"]),
        analysis_result_id=str(value["analysis_result_id"]), symbol=str(value["symbol"]),
        side=PaperSide(value["side"]), entry_reference_price=_decimal(value["entry_reference_price"]),
        stop_price=_decimal(value["stop_price"]), target_price=_decimal(value["target_price"]),
        closed_until_ms=int(value["closed_until_ms"]), approved_at=_datetime(value["approved_at"]),
        valid_until_ms=int(value["valid_until_ms"]),
        configuration_fingerprint=str(value["configuration_fingerprint"]),
        symbol_constraints_id=str(value["symbol_constraints_id"]),
        input_health_status=PaperInputHealthStatus(value["input_health_status"]),
        future_bars_used=value["future_bars_used"],
        paper_execution_approved=value["paper_execution_approved"],
        reason_code=PaperApprovalReasonCode(value["reason_code"]),
        correlation_id=str(value["correlation_id"]), causation_id=str(value["causation_id"]),
    )


def _quantity_approval(value: Mapping[str, Any]) -> Any:
    from app.engine_paper.paper_approvals import (
        PaperApprovalReasonCode,
        PaperQuantityApproval,
        PaperQuantityApprovalSource,
    )
    from app.engine_safety.paper_domain import PaperSide

    return PaperQuantityApproval(
        quantity_approval_id=str(value["quantity_approval_id"]),
        contract_version=str(value["contract_version"]),
        paper_strategy_approval_id=str(value["paper_strategy_approval_id"]),
        research_risk_decision_id=str(value["research_risk_decision_id"]),
        symbol=str(value["symbol"]), side=PaperSide(value["side"]),
        approved_quantity=_decimal(value["approved_quantity"]),
        approval_source=PaperQuantityApprovalSource(value["approval_source"]),
        approved_at=_datetime(value["approved_at"]), valid_until_ms=int(value["valid_until_ms"]),
        configuration_fingerprint=str(value["configuration_fingerprint"]),
        symbol_constraints_id=str(value["symbol_constraints_id"]),
        position_size_approved=value["position_size_approved"],
        reason_code=PaperApprovalReasonCode(value["reason_code"]),
        correlation_id=str(value["correlation_id"]), causation_id=str(value["causation_id"]),
    )


def _risk_approval(value: Mapping[str, Any]) -> Any:
    from app.engine_paper.paper_approvals import PaperApprovalReasonCode, PaperRiskApproval
    from app.engine_safety.paper_domain import PaperSide

    return PaperRiskApproval(
        approval_id=str(value["approval_id"]), contract_version=str(value["contract_version"]),
        paper_strategy_approval_id=str(value["paper_strategy_approval_id"]),
        research_risk_decision_id=str(value["research_risk_decision_id"]),
        quantity_approval_id=str(value["quantity_approval_id"]), setup_id=str(value["setup_id"]),
        pipeline_run_id=str(value["pipeline_run_id"]), analysis_result_id=str(value["analysis_result_id"]),
        symbol=str(value["symbol"]), side=PaperSide(value["side"]),
        approved_quantity=_decimal(value["approved_quantity"]), approved_at=_datetime(value["approved_at"]),
        valid_until_ms=int(value["valid_until_ms"]),
        configuration_fingerprint=str(value["configuration_fingerprint"]),
        symbol_constraints_id=str(value["symbol_constraints_id"]),
        order_approved=value["order_approved"], execution_approved=value["execution_approved"],
        position_size_approved=value["position_size_approved"],
        final_paper_approval=value["final_paper_approval"],
        reason_code=PaperApprovalReasonCode(value["reason_code"]),
        correlation_id=str(value["correlation_id"]), causation_id=str(value["causation_id"]),
    )


class PaperProductionApprovalSourceAdapter:
    """Interpret one bounded, consistent, persisted production decision snapshot."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        *,
        reader: PaperProductionApprovalReader | None = None,
        monotonic: Callable[[], float] | None = None,
    ) -> None:
        if session_factory is None:
            raise TypeError("session_factory is required")
        if monotonic is None:
            from time import monotonic as system_monotonic
            monotonic = system_monotonic
        self._session_factory = session_factory
        self._reader = reader or SqlAlchemyPaperProductionApprovalReader()
        self._monotonic = monotonic

    @staticmethod
    def _validate_scope(request: PaperProductionApprovalRequest) -> tuple[str, ...] | PaperProductionApprovalOutcome:
        scope = request.scope
        if not scope.symbols:
            return PaperProductionApprovalOutcome.TARGET_NOT_ALLOWED
        symbols = tuple(str(value).strip().upper() for value in scope.symbols)
        if (
            len(symbols) > MAX_SYMBOLS_PER_REQUEST
            or len(set(symbols)) != len(symbols)
            or any(value not in SYMBOL_ALLOWLIST for value in symbols)
        ):
            return PaperProductionApprovalOutcome.TARGET_NOT_ALLOWED
        if scope.primary_timeframe != PRIMARY_TIMEFRAME:
            return PaperProductionApprovalOutcome.TARGET_NOT_ALLOWED
        if (
            isinstance(scope.max_run_lookback, bool)
            or not 1 <= scope.max_run_lookback <= MAX_RUN_LOOKBACK
            or isinstance(scope.max_results_per_module, bool)
            or not 1 <= scope.max_results_per_module <= MAX_RESULTS_PER_MODULE
            or isinstance(scope.max_candidates, bool)
            or not 1 <= scope.max_candidates <= MAX_CANDIDATES_PER_REQUEST
            or len(symbols) * scope.max_run_lookback > MAX_ROWS_PER_REQUEST
        ):
            return PaperProductionApprovalOutcome.BOUNDED_LIMIT_EXCEEDED
        if scope.start_ms is not None and (
            isinstance(scope.start_ms, bool) or not isinstance(scope.start_ms, int) or scope.start_ms < 0
        ):
            return PaperProductionApprovalOutcome.BOUNDED_LIMIT_EXCEEDED
        if request.as_of_ms is not None and (
            isinstance(request.as_of_ms, bool) or not isinstance(request.as_of_ms, int) or request.as_of_ms <= 0
        ):
            return PaperProductionApprovalOutcome.SAFE_FAILURE
        if scope.start_ms is not None and request.as_of_ms is not None and (
            scope.start_ms > request.as_of_ms
            or request.as_of_ms - scope.start_ms > MAX_TIME_RANGE_MS
        ):
            return PaperProductionApprovalOutcome.BOUNDED_LIMIT_EXCEEDED
        return tuple(sorted(symbols, key=SYMBOL_ALLOWLIST.index))

    @staticmethod
    def _cancelled(token: CancellationToken | None) -> None:
        if token is not None and token.is_set():
            raise _Cancelled("APPROVAL_SOURCE_CANCELLED")

    @staticmethod
    def _readiness(outcome: PaperProductionApprovalOutcome) -> PaperProductionApprovalReadiness:
        if outcome is PaperProductionApprovalOutcome.ELIGIBLE_APPROVAL:
            return PaperProductionApprovalReadiness.READY
        if outcome in {
            PaperProductionApprovalOutcome.NO_ELIGIBLE_APPROVAL,
            PaperProductionApprovalOutcome.NO_TRADE_SIGNAL,
            PaperProductionApprovalOutcome.SETUP_NOT_ELIGIBLE,
            PaperProductionApprovalOutcome.STRATEGY_NOT_EXECUTABLE,
            PaperProductionApprovalOutcome.RISK_REJECTED,
            PaperProductionApprovalOutcome.RISK_DEFERRED,
            PaperProductionApprovalOutcome.APPROVAL_NOT_FINAL,
            PaperProductionApprovalOutcome.EXECUTION_NOT_APPROVED,
            PaperProductionApprovalOutcome.QUANTITY_NOT_APPROVED,
            PaperProductionApprovalOutcome.INVALID_QUANTITY,
            PaperProductionApprovalOutcome.STALE_APPROVAL,
            PaperProductionApprovalOutcome.SUPERSEDED_APPROVAL,
        }:
            return PaperProductionApprovalReadiness.HEALTHY_NO_ELIGIBLE_APPROVAL
        if outcome is PaperProductionApprovalOutcome.CANCELLED:
            return PaperProductionApprovalReadiness.CANCELLED
        return PaperProductionApprovalReadiness.NOT_READY

    def _failure(
        self,
        outcome: PaperProductionApprovalOutcome,
        request: PaperProductionApprovalRequest,
        *,
        as_of_ms: int | None = None,
        query_count: int = 0,
        rows_read: int = 0,
        started: float | None = None,
        read_only: bool = True,
    ) -> PaperProductionApprovalResult:
        return PaperProductionApprovalResult(
            outcome, self._readiness(outcome), request.request_id, as_of_ms,
            (), (PaperProductionApprovalFinding(_FINDING_BY_OUTCOME[outcome]),),
            query_count, rows_read,
            0.0 if started is None else (self._monotonic() - started) * 1000,
            read_only, False,
        )

    @staticmethod
    def _symbol_result(
        row: _PersistedDecision,
        outcome: PaperProductionApprovalOutcome,
        *,
        candidate: PaperProductionApprovalCandidate | None = None,
        lineage_valid: bool = False,
        freshness: str = "NOT_APPLICABLE",
    ) -> PaperProductionApprovalSymbolResult:
        return PaperProductionApprovalSymbolResult(
            row.symbol, outcome,
            "TRADE_SIGNAL" if row.is_trade_signal else "NO_TRADE_SIGNAL",
            str(row.strategy_status or row.strategy.get("decision_status") or "MISSING"),
            str(row.risk_status or row.risk.get("risk_status") or "MISSING"),
            "FINAL" if candidate else "NOT_FINAL",
            "APPROVED" if candidate else "NOT_APPROVED",
            lineage_valid, freshness, row.run_id, candidate,
        )

    def _classify(
        self, row: _PersistedDecision, as_of_ms: int
    ) -> PaperProductionApprovalSymbolResult:
        analysis, setup, strategy, risk, paper = (
            row.analysis, row.setup, row.strategy, row.risk, row.paper
        )
        if row.future_bars_used or bool(analysis.get("future_bars_used")):
            return self._symbol_result(row, PaperProductionApprovalOutcome.FUTURE_DECISION)
        identities = (
            analysis.get("symbol"), setup.get("symbol"), strategy.get("symbol"),
            risk.get("symbol"), paper.get("symbol"),
        )
        if any(value is not None and str(value).upper() != row.symbol for value in identities):
            return self._symbol_result(row, PaperProductionApprovalOutcome.SYMBOL_MISMATCH)
        boundaries = (
            analysis.get("closed_until_ms"), setup.get("closed_until_ms"),
            strategy.get("closed_until_ms"), risk.get("closed_until_ms"),
            paper.get("closed_until_ms"),
        )
        try:
            if any(value is not None and int(value) != row.closed_until_ms for value in boundaries):
                return self._symbol_result(row, PaperProductionApprovalOutcome.CAUSALITY_MISMATCH)
        except (TypeError, ValueError):
            return self._symbol_result(row, PaperProductionApprovalOutcome.CAUSALITY_MISMATCH)
        timestamps = (
            analysis.get("created_at_ms"), setup.get("created_at_ms"),
            strategy.get("created_at_ms"), risk.get("created_at_ms"),
            paper.get("created_at_ms"),
        )
        try:
            if any(value is not None and int(value) > as_of_ms for value in timestamps):
                return self._symbol_result(row, PaperProductionApprovalOutcome.FUTURE_DECISION)
        except (TypeError, ValueError):
            return self._symbol_result(row, PaperProductionApprovalOutcome.CAUSALITY_MISMATCH)

        analysis_id = str(analysis.get("snapshot_id") or "")
        market_snapshot_id = str(analysis.get("source_market_data_snapshot_id") or "")
        setup_id = str(setup.get("setup_id") or "")
        strategy_id = str(strategy.get("decision_id") or "")
        risk_id = str(risk.get("risk_decision_id") or "")
        if analysis and not analysis_id:
            return self._symbol_result(row, PaperProductionApprovalOutcome.CAUSALITY_MISMATCH)
        if setup and str(setup.get("source_analysis_snapshot_id") or "") != analysis_id:
            return self._symbol_result(row, PaperProductionApprovalOutcome.CAUSALITY_MISMATCH)
        if strategy and (
            str(strategy.get("source_setup_id") or "") != setup_id
            or str(strategy.get("source_analysis_snapshot_id") or "") != analysis_id
        ):
            return self._symbol_result(row, PaperProductionApprovalOutcome.CAUSALITY_MISMATCH)
        if risk and (
            str(risk.get("source_strategy_decision_id") or "") != strategy_id
            or str(risk.get("source_setup_id") or "") != setup_id
            or str(risk.get("source_analysis_snapshot_id") or "") != analysis_id
        ):
            return self._symbol_result(row, PaperProductionApprovalOutcome.CAUSALITY_MISMATCH)
        if paper and "paper_plan_id" in paper and (
            str(paper.get("source_risk_decision_id") or "") != risk_id
            or str(paper.get("source_strategy_decision_id") or "") != strategy_id
            or str(paper.get("source_setup_id") or "") != setup_id
            or str(paper.get("source_analysis_snapshot_id") or "") != analysis_id
        ):
            return self._symbol_result(row, PaperProductionApprovalOutcome.CAUSALITY_MISMATCH)

        setup_status = str(row.setup_status or setup.get("status") or "")
        strategy_status = str(row.strategy_status or strategy.get("decision_status") or "")
        risk_status = str(row.risk_status or risk.get("risk_status") or "")
        if not row.is_trade_signal:
            return self._symbol_result(row, PaperProductionApprovalOutcome.NO_TRADE_SIGNAL, lineage_valid=True)
        if setup_status not in _SETUP_ELIGIBLE:
            return self._symbol_result(row, PaperProductionApprovalOutcome.SETUP_NOT_ELIGIBLE, lineage_valid=True)
        if strategy_status not in _STRATEGY_ALLOWED or not row.is_executable:
            return self._symbol_result(row, PaperProductionApprovalOutcome.STRATEGY_NOT_EXECUTABLE, lineage_valid=True)
        if risk_status in _RISK_REJECTED:
            return self._symbol_result(row, PaperProductionApprovalOutcome.RISK_REJECTED, lineage_valid=True)
        if risk_status in _RISK_DEFERRED:
            return self._symbol_result(row, PaperProductionApprovalOutcome.RISK_DEFERRED, lineage_valid=True)
        if risk_status not in _RISK_APPROVED:
            return self._symbol_result(row, PaperProductionApprovalOutcome.NO_ELIGIBLE_APPROVAL, lineage_valid=True)
        if row.position_opened:
            return self._symbol_result(row, PaperProductionApprovalOutcome.CAUSALITY_MISMATCH)

        container = paper.get("persisted_final_approvals")
        if isinstance(container, Sequence) and not isinstance(container, (str, bytes, Mapping)):
            if len(container) != 1 or not isinstance(container[0], Mapping):
                return self._symbol_result(row, PaperProductionApprovalOutcome.AMBIGUOUS_APPROVAL)
            container = container[0]
        if not isinstance(container, Mapping) or any(
            not isinstance(container.get(key), Mapping) for key in _FINAL_APPROVAL_KEYS
        ):
            return self._symbol_result(row, PaperProductionApprovalOutcome.APPROVAL_NOT_FINAL, lineage_valid=True)
        try:
            strategy_approval = _strategy_approval(container[_FINAL_APPROVAL_KEYS[0]])
            quantity_approval = _quantity_approval(container[_FINAL_APPROVAL_KEYS[1]])
            risk_approval = _risk_approval(container[_FINAL_APPROVAL_KEYS[2]])
        except Exception:
            raw_quantity = container.get(_FINAL_APPROVAL_KEYS[1])
            if isinstance(raw_quantity, Mapping):
                try:
                    quantity = _decimal(raw_quantity.get("approved_quantity"))
                    if quantity <= 0:
                        return self._symbol_result(row, PaperProductionApprovalOutcome.INVALID_QUANTITY)
                except ValueError:
                    return self._symbol_result(row, PaperProductionApprovalOutcome.INVALID_QUANTITY)
            return self._symbol_result(row, PaperProductionApprovalOutcome.CAUSALITY_MISMATCH)

        if strategy_approval.symbol != row.symbol or quantity_approval.symbol != row.symbol or risk_approval.symbol != row.symbol:
            return self._symbol_result(row, PaperProductionApprovalOutcome.SYMBOL_MISMATCH)
        if not (strategy_approval.side is quantity_approval.side is risk_approval.side):
            return self._symbol_result(row, PaperProductionApprovalOutcome.SIDE_MISMATCH)
        expected_direction = "BULLISH" if strategy_approval.side.value == "LONG" else "BEARISH"
        persisted_directions = (
            strategy.get("direction_hint"), risk.get("direction_hint"),
            paper.get("paper_direction"),
        )
        if any(
            value not in (None, "NONE", expected_direction)
            for value in persisted_directions
        ):
            return self._symbol_result(row, PaperProductionApprovalOutcome.SIDE_MISMATCH)
        if not market_snapshot_id:
            return self._symbol_result(row, PaperProductionApprovalOutcome.MARKET_DATA_WATERMARK_MISMATCH)
        if (
            strategy_approval.pipeline_run_id != row.run_id
            or strategy_approval.analysis_result_id != analysis_id
            or strategy_approval.setup_id != setup_id
            or strategy_approval.research_strategy_decision_id != strategy_id
            or risk_approval.research_risk_decision_id != risk_id
            or strategy_approval.closed_until_ms != row.closed_until_ms
        ):
            return self._symbol_result(row, PaperProductionApprovalOutcome.CAUSALITY_MISMATCH)
        if not row.order_approved:
            return self._symbol_result(row, PaperProductionApprovalOutcome.APPROVAL_NOT_FINAL, lineage_valid=True)
        if not row.execution_approved:
            return self._symbol_result(row, PaperProductionApprovalOutcome.EXECUTION_NOT_APPROVED, lineage_valid=True)
        if not row.position_size_approved:
            return self._symbol_result(row, PaperProductionApprovalOutcome.QUANTITY_NOT_APPROVED, lineage_valid=True)
        if quantity_approval.approved_quantity <= 0:
            return self._symbol_result(row, PaperProductionApprovalOutcome.INVALID_QUANTITY, lineage_valid=True)
        if max(
            int(strategy_approval.approved_at.timestamp() * 1000),
            int(quantity_approval.approved_at.timestamp() * 1000),
            int(risk_approval.approved_at.timestamp() * 1000),
        ) > as_of_ms:
            return self._symbol_result(row, PaperProductionApprovalOutcome.FUTURE_DECISION, lineage_valid=True)
        prerequisite_ms = max(
            int(value) for value in timestamps if value is not None
        )
        if min(
            int(strategy_approval.approved_at.timestamp() * 1000),
            int(quantity_approval.approved_at.timestamp() * 1000),
            int(risk_approval.approved_at.timestamp() * 1000),
        ) < prerequisite_ms:
            return self._symbol_result(row, PaperProductionApprovalOutcome.CAUSALITY_MISMATCH)
        if as_of_ms > min(
            strategy_approval.valid_until_ms,
            quantity_approval.valid_until_ms,
            risk_approval.valid_until_ms,
        ):
            return self._symbol_result(
                row, PaperProductionApprovalOutcome.STALE_APPROVAL,
                lineage_valid=True, freshness="STALE",
            )
        try:
            from app.engine_paper.paper_approvals import map_final_approvals_to_command_compatibility

            compatibility = map_final_approvals_to_command_compatibility(
                strategy_approval, quantity_approval, risk_approval
            )
        except Exception:
            return self._symbol_result(row, PaperProductionApprovalOutcome.CAUSALITY_MISMATCH)

        watermark_id = _canonical_hash((
            row.symbol, row.primary_timeframe, row.closed_until_ms, market_snapshot_id,
        ))
        watermark = PaperProductionApprovalWatermark(
            row.symbol, row.primary_timeframe, row.closed_until_ms,
            market_snapshot_id, watermark_id,
        )
        lineage_material = (
            row.run_id, analysis_id, setup_id, strategy_id, risk_id,
            strategy_approval.approval_id, quantity_approval.quantity_approval_id,
            risk_approval.approval_id, watermark_id,
        )
        lineage_id = _canonical_hash(lineage_material)
        lineage = PaperProductionApprovalLineage(
            row.run_id, analysis_id, setup_id, strategy_id, risk_id,
            strategy_approval.approval_id, quantity_approval.quantity_approval_id,
            risk_approval.approval_id, lineage_id,
        )
        authority = PaperProductionApprovalQuantityAuthority(
            quantity_approval.quantity_approval_id,
            quantity_approval.approved_quantity,
            quantity_approval.approval_source,
            quantity_approval.approved_at,
            quantity_approval.valid_until_ms,
        )
        candidate_id = "paper:production-approval-candidate:v1:" + _canonical_hash((
            lineage_id, str(authority.approved_quantity), risk_approval.valid_until_ms,
        ))
        try:
            risk_score = _decimal(risk.get("risk_score"))
        except ValueError:
            risk_score = None
        try:
            strategy_score = _decimal(strategy.get("strategy_score"))
        except ValueError:
            strategy_score = None
        risk_distance = abs(
            strategy_approval.entry_reference_price - strategy_approval.stop_price
        )
        reward_distance = abs(
            strategy_approval.target_price - strategy_approval.entry_reference_price
        )
        # Approved geometry already proves a positive risk distance. This is
        # the authoritative production R/R formula, derived once upstream of
        # selection and never recomputed by the ranker.
        planned_risk_reward = reward_distance / risk_distance
        ranking = PaperProductionApprovalRankingInputs(
            risk_score, planned_risk_reward, strategy_score,
            row.closed_until_ms, row.run_id, risk_approval.approval_id,
        )
        candidate = PaperProductionApprovalCandidate(
            candidate_id, AUTHORITATIVE_SOURCE, row.symbol, compatibility.side,
            compatibility.entry_reference_price, compatibility.stop_price,
            compatibility.target_price, risk_approval.approved_at,
            compatibility.valid_until_ms, watermark, lineage, authority,
            compatibility.configuration_fingerprint,
            compatibility.symbol_constraints_id,
            strategy_approval,
            quantity_approval,
            risk_approval,
            ranking,
        )
        return self._symbol_result(
            row, PaperProductionApprovalOutcome.ELIGIBLE_APPROVAL,
            candidate=candidate, lineage_valid=True, freshness="CURRENT",
        )

    def read(
        self,
        request: PaperProductionApprovalRequest,
        *,
        cancellation: CancellationToken | None = None,
    ) -> PaperProductionApprovalResult:
        started = self._monotonic()
        validated = self._validate_scope(request)
        if isinstance(validated, PaperProductionApprovalOutcome):
            return self._failure(validated, request, as_of_ms=request.as_of_ms, started=started)
        executor: _ReadOnlyExecutor | None = None
        rows_read = 0
        as_of_ms = request.as_of_ms
        try:
            self._cancelled(cancellation)
            with self._session_factory() as session:
                executor = _ReadOnlyExecutor(session)
                with session.begin():
                    executor.execute(text(_TRANSACTION_CONTROL))
                    if as_of_ms is None:
                        as_of_ms = self._reader.read_clock_ms(executor)
                    if request.scope.start_ms is not None and as_of_ms - request.scope.start_ms > MAX_TIME_RANGE_MS:
                        return self._failure(
                            PaperProductionApprovalOutcome.BOUNDED_LIMIT_EXCEEDED,
                            request, as_of_ms=as_of_ms, query_count=executor.query_count,
                            rows_read=rows_read, started=started,
                        )
                    results: list[PaperProductionApprovalSymbolResult] = []
                    findings: list[PaperProductionApprovalFinding] = []
                    for symbol in validated:
                        self._cancelled(cancellation)
                        rows = tuple(self._reader.read_recent(
                            executor, symbol, request.scope.primary_timeframe,
                            request.scope.max_run_lookback, request.scope.start_ms,
                        ))
                        rows_read += len(rows)
                        complete = tuple(
                            value for value in rows
                            if value.result_pk is not None and value.status in _COMPLETE_STATUSES
                        )
                        if not complete:
                            empty = _PersistedDecision(
                                0, None, "", symbol, request.scope.primary_timeframe, 0,
                                "", None, None, False, False, False, False, False,
                                False, False, None, None, None, None, None,
                                {}, {}, {}, {}, {},
                            )
                            result = self._symbol_result(
                                empty, PaperProductionApprovalOutcome.NO_ELIGIBLE_APPROVAL
                            )
                        else:
                            latest_rank = (complete[0].closed_until_ms, complete[0].run_pk)
                            tied = tuple(
                                value for value in complete
                                if (value.closed_until_ms, value.run_pk) == latest_rank
                            )
                            if len(tied) != 1:
                                result = self._symbol_result(
                                    complete[0], PaperProductionApprovalOutcome.AMBIGUOUS_APPROVAL
                                )
                            else:
                                result = self._classify(complete[0], as_of_ms)
                        results.append(result)
                        findings.append(PaperProductionApprovalFinding(
                            _FINDING_BY_OUTCOME[result.outcome], symbol, result.source_run_id
                        ))
                    self._cancelled(cancellation)
                    eligible = sum(value.candidate is not None for value in results)
                    if eligible > request.scope.max_candidates:
                        return self._failure(
                            PaperProductionApprovalOutcome.BOUNDED_LIMIT_EXCEEDED,
                            request, as_of_ms=as_of_ms, query_count=executor.query_count,
                            rows_read=rows_read, started=started,
                        )
                    outcomes = {value.outcome for value in results}
                    overall = (
                        PaperProductionApprovalOutcome.ELIGIBLE_APPROVAL
                        if eligible else next(iter(outcomes))
                        if len(outcomes) == 1 else PaperProductionApprovalOutcome.NO_ELIGIBLE_APPROVAL
                    )
                    return PaperProductionApprovalResult(
                        overall, self._readiness(overall), request.request_id,
                        as_of_ms, tuple(results), tuple(findings), executor.query_count,
                        rows_read, (self._monotonic() - started) * 1000, True, True,
                    )
        except _Cancelled:
            return self._failure(
                PaperProductionApprovalOutcome.CANCELLED, request, as_of_ms=as_of_ms,
                query_count=executor.query_count if executor else 0,
                rows_read=rows_read, started=started,
            )
        except ReadOnlyPolicyViolation:
            return self._failure(
                PaperProductionApprovalOutcome.READ_ONLY_POLICY_VIOLATION,
                request, as_of_ms=as_of_ms,
                query_count=executor.query_count if executor else 0,
                rows_read=rows_read, started=started, read_only=False,
            )
        except Exception as exc:
            sqlstate = getattr(getattr(exc, "orig", None), "sqlstate", None)
            outcome = (
                PaperProductionApprovalOutcome.SCHEMA_NOT_SUPPORTED
                if sqlstate in {"42P01", "42703"}
                else PaperProductionApprovalOutcome.SAFE_FAILURE
            )
            return self._failure(
                outcome, request, as_of_ms=as_of_ms,
                query_count=executor.query_count if executor else 0,
                rows_read=rows_read, started=started,
            )
