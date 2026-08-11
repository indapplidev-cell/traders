"""Authoritative realized-only PAPER accounting and reporting projections.

The existing fill and position lifecycle remains the sole fee/PnL engine.  This
module validates and projects those persisted facts; it never prices a fill or
calculates a configured fee.  Revision 0011 has no account/session baseline
table, so the persistence boundary is deliberately a port rather than an
unrelated-table fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from enum import Enum
from hashlib import sha256
from typing import Protocol, Sequence, runtime_checkable

from app.engine_execution.paper_models import PaperFill
from app.engine_journal.paper_events import PaperDomainEvent
from app.engine_position.paper_accounting import gross_realized_pnl
from app.engine_position.paper_models import PaperPosition
from app.engine_safety.paper_domain import (
    ExecutionMode,
    PaperEventType,
    PaperPositionState,
    PaperSide,
)


ACCOUNTING_SEMANTIC_VERSION = "PAPER_ACCOUNTING/1.0"
SUPPORTED_CURRENCY = "USDT"
CURRENT_0011_BASELINE_PERSISTENCE_CAPABILITY = (
    "UNSUPPORTED_REQUIRES_SCHEMA_EXTENSION"
)


class PaperAccountingFinding(str, Enum):
    ACCOUNTING_HEALTHY = "ACCOUNTING_HEALTHY"
    BASELINE_MISSING = "BASELINE_MISSING"
    BASELINE_DUPLICATE = "BASELINE_DUPLICATE"
    BASELINE_INVALID = "BASELINE_INVALID"
    BASELINE_IMMUTABILITY_VIOLATION = "BASELINE_IMMUTABILITY_VIOLATION"
    BASELINE_AFTER_ECONOMIC_ACTIVITY_DENIED = "BASELINE_AFTER_ECONOMIC_ACTIVITY_DENIED"
    UNSUPPORTED_CURRENCY = "UNSUPPORTED_CURRENCY"
    TRADE_NOT_CLOSED = "TRADE_NOT_CLOSED"
    ENTRY_FILL_MISSING = "ENTRY_FILL_MISSING"
    CLOSE_FILL_MISSING = "CLOSE_FILL_MISSING"
    FILL_IDENTITY_CONFLICT = "FILL_IDENTITY_CONFLICT"
    FEE_MISMATCH = "FEE_MISMATCH"
    PNL_MISMATCH = "PNL_MISMATCH"
    DUPLICATE_TRADE = "DUPLICATE_TRADE"
    BALANCE_CHAIN_MISMATCH = "BALANCE_CHAIN_MISMATCH"
    AMBIGUOUS_CLOSE_ORDER = "AMBIGUOUS_CLOSE_ORDER"
    SCHEMA_PERSISTENCE_UNAVAILABLE = "SCHEMA_PERSISTENCE_UNAVAILABLE"
    SAFE_FAILURE = "SAFE_FAILURE"


class PaperAccountingOutcome(str, Enum):
    HEALTHY = "HEALTHY"
    DENIED = "DENIED"
    FINAL_REPORT_NOT_AVAILABLE = "FINAL_REPORT_NOT_AVAILABLE"
    ACCOUNT_SUMMARY_NOT_AUTHORITATIVE = "ACCOUNT_SUMMARY_NOT_AUTHORITATIVE"
    SAFE_FAILURE = "SAFE_FAILURE"


class PaperAccountBaselineGate(str, Enum):
    PASS = "PASS"
    MISSING = "MISSING"
    INVALID = "INVALID"


class PaperAccountingError(ValueError):
    def __init__(self, finding: PaperAccountingFinding, message: str) -> None:
        super().__init__(message)
        self.finding = finding


def _identity(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 128:
        raise PaperAccountingError(PaperAccountingFinding.BASELINE_INVALID, field)
    return value.strip()


def _money(
    value: object,
    field: str,
    *,
    positive: bool = False,
    nonnegative: bool = False,
    finding: PaperAccountingFinding = PaperAccountingFinding.BASELINE_INVALID,
) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise PaperAccountingError(finding, f"{field} must be a finite Decimal")
    if positive and value <= 0:
        raise PaperAccountingError(finding, f"{field} must be positive")
    if nonnegative and value < 0:
        raise PaperAccountingError(finding, f"{field} must be nonnegative")
    return Decimal("0") if value == 0 else value


def _currency(value: object) -> str:
    normalized = str(value).strip().upper()
    if normalized != SUPPORTED_CURRENCY:
        raise PaperAccountingError(
            PaperAccountingFinding.UNSUPPORTED_CURRENCY,
            "PAPER accounting V1 supports USDT only",
        )
    return normalized


def _utc(value: datetime, field: str) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() != timedelta(0)
    ):
        raise PaperAccountingError(PaperAccountingFinding.BASELINE_INVALID, field)
    return value


@dataclass(frozen=True, slots=True)
class PaperAccountIdentity:
    account_id: str
    accounting_session_id: str
    currency: str = SUPPORTED_CURRENCY
    mode: ExecutionMode = ExecutionMode.PAPER

    def __post_init__(self) -> None:
        object.__setattr__(self, "account_id", _identity(self.account_id, "account_id"))
        object.__setattr__(
            self,
            "accounting_session_id",
            _identity(self.accounting_session_id, "accounting_session_id"),
        )
        object.__setattr__(self, "currency", _currency(self.currency))
        if self.mode is not ExecutionMode.PAPER:
            raise PaperAccountingError(
                PaperAccountingFinding.BASELINE_INVALID, "mode must be PAPER"
            )


@dataclass(frozen=True, slots=True)
class PaperAccountBaseline:
    baseline_id: str
    identity: PaperAccountIdentity
    initial_balance: Decimal
    initialized_at: datetime
    semantic_version: str = ACCOUNTING_SEMANTIC_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "baseline_id", _identity(self.baseline_id, "baseline_id"))
        _money(self.initial_balance, "initial_balance", positive=True)
        _utc(self.initialized_at, "initialized_at")
        object.__setattr__(
            self, "semantic_version", _identity(self.semantic_version, "semantic_version")
        )


@runtime_checkable
class PaperAccountBaselinePersistence(Protocol):
    """Transactional port required from a future account-baseline schema task."""

    def list_for_identity(self, identity: PaperAccountIdentity) -> Sequence[PaperAccountBaseline]: ...

    def has_economic_activity(self, identity: PaperAccountIdentity) -> bool: ...

    def insert_once(self, baseline: PaperAccountBaseline) -> PaperAccountBaseline: ...


class PaperAccountBaselineService:
    def __init__(self, persistence: PaperAccountBaselinePersistence) -> None:
        self._persistence = persistence

    def status(self, identity: PaperAccountIdentity) -> PaperAccountBaselineGate:
        try:
            rows = tuple(self._persistence.list_for_identity(identity))
        except Exception as exc:
            raise PaperAccountingError(PaperAccountingFinding.SAFE_FAILURE, "baseline read failed") from exc
        if not rows:
            return PaperAccountBaselineGate.MISSING
        if len(rows) != 1:
            return PaperAccountBaselineGate.INVALID
        try:
            PaperAccountBaseline(**{
                "baseline_id": rows[0].baseline_id,
                "identity": rows[0].identity,
                "initial_balance": rows[0].initial_balance,
                "initialized_at": rows[0].initialized_at,
                "semantic_version": rows[0].semantic_version,
            })
        except (PaperAccountingError, TypeError):
            return PaperAccountBaselineGate.INVALID
        return PaperAccountBaselineGate.PASS

    def initialize(
        self,
        *,
        baseline_id: str,
        identity: PaperAccountIdentity,
        initial_balance: Decimal,
        initialized_at: datetime,
        semantic_version: str = ACCOUNTING_SEMANTIC_VERSION,
    ) -> PaperAccountBaseline:
        requested = PaperAccountBaseline(
            baseline_id=baseline_id,
            identity=identity,
            initial_balance=initial_balance,
            initialized_at=initialized_at,
            semantic_version=semantic_version,
        )
        try:
            existing = tuple(self._persistence.list_for_identity(identity))
            if len(existing) > 1:
                raise PaperAccountingError(
                    PaperAccountingFinding.BASELINE_DUPLICATE, "multiple baselines"
                )
            if existing:
                current = existing[0]
                if (
                    current.initial_balance == requested.initial_balance
                    and current.identity == requested.identity
                    and current.semantic_version == requested.semantic_version
                ):
                    return current
                raise PaperAccountingError(
                    PaperAccountingFinding.BASELINE_IMMUTABILITY_VIOLATION,
                    "an established baseline cannot be rewritten",
                )
            if self._persistence.has_economic_activity(identity):
                raise PaperAccountingError(
                    PaperAccountingFinding.BASELINE_AFTER_ECONOMIC_ACTIVITY_DENIED,
                    "baseline initialization after economic activity is denied",
                )
            return self._persistence.insert_once(requested)
        except PaperAccountingError:
            raise
        except Exception as exc:
            raise PaperAccountingError(PaperAccountingFinding.SAFE_FAILURE, "baseline write failed") from exc


@dataclass(frozen=True, slots=True)
class PaperClosedTradeFacts:
    """Causally complete authoritative facts for one finalized position."""

    position: PaperPosition
    entry_fill: PaperFill | None
    exit_fill: PaperFill | None
    exit_reason: str
    journal_events: tuple[PaperDomainEvent, ...]


@dataclass(frozen=True, slots=True)
class PaperTradeFinancialReport:
    position_id: str
    symbol: str
    side: PaperSide
    entry_time: datetime
    exit_time: datetime
    exit_reason: str
    quantity: Decimal
    entry_price: Decimal
    exit_price: Decimal
    entry_notional: Decimal
    exit_notional: Decimal
    capital_used: Decimal
    entry_fee: Decimal
    exit_fee: Decimal
    total_fees: Decimal
    gross_pnl: Decimal
    net_pnl: Decimal
    roi_percent: Decimal
    balance_before: Decimal
    balance_after: Decimal
    currency: str
    accounting_session_id: str
    report_semantic_id: str


class PaperTradeReportingService:
    """Project CLOSED lifecycle facts without creating new economics."""

    def project(
        self,
        identity: PaperAccountIdentity,
        facts: PaperClosedTradeFacts,
        balance_before: Decimal,
    ) -> PaperTradeFinancialReport:
        before = _money(balance_before, "balance_before", finding=PaperAccountingFinding.BALANCE_CHAIN_MISMATCH)
        position = facts.position
        if position.state is not PaperPositionState.CLOSED:
            raise PaperAccountingError(PaperAccountingFinding.TRADE_NOT_CLOSED, "final report unavailable")
        if facts.entry_fill is None:
            raise PaperAccountingError(PaperAccountingFinding.ENTRY_FILL_MISSING, "entry fill missing")
        if facts.exit_fill is None:
            raise PaperAccountingError(PaperAccountingFinding.CLOSE_FILL_MISSING, "close fill missing")
        entry, exit_fill = facts.entry_fill, facts.exit_fill
        if (
            entry.fill_id == exit_fill.fill_id
            or position.entry_fill_id != entry.fill_id
            or position.exit_fill_id != exit_fill.fill_id
            or entry.order_id == exit_fill.order_id
            or entry.symbol != position.symbol
            or exit_fill.symbol != position.symbol
            or entry.side is not position.side
            or exit_fill.side is not position.side
            or entry.quantity != position.entry_quantity
            or exit_fill.quantity != position.entry_quantity
            or entry.price != position.average_entry_price
            or exit_fill.price != position.average_exit_price
        ):
            raise PaperAccountingError(PaperAccountingFinding.FILL_IDENTITY_CONFLICT, "fill/position identity conflict")
        _currency(entry.fee_asset)
        _currency(exit_fill.fee_asset)
        if position.entry_fees != entry.fee_amount or position.exit_fees != exit_fill.fee_amount:
            raise PaperAccountingError(PaperAccountingFinding.FEE_MISMATCH, "position fees differ from fills")
        gross = gross_realized_pnl(position.side, entry.price, exit_fill.price, entry.quantity)
        total_fees = entry.fee_amount + exit_fill.fee_amount
        expected_net = gross - total_fees
        if position.realized_pnl != expected_net:
            raise PaperAccountingError(PaperAccountingFinding.PNL_MISMATCH, "finalized net PnL mismatch")
        self._validate_journal(facts, entry, exit_fill)
        entry_notional = abs(entry.price * entry.quantity)
        exit_notional = abs(exit_fill.price * exit_fill.quantity)
        if entry_notional <= 0:
            raise PaperAccountingError(PaperAccountingFinding.PNL_MISMATCH, "entry notional invalid")
        net = Decimal("0") if position.realized_pnl == 0 else position.realized_pnl
        after = before + net
        semantic_payload = "|".join(
            (
                ACCOUNTING_SEMANTIC_VERSION,
                identity.account_id,
                identity.accounting_session_id,
                position.position_id,
                entry.fill_id,
                exit_fill.fill_id,
                position.closed_at.isoformat(),
            )
        )
        semantic_id = "paper-report-" + sha256(semantic_payload.encode("utf-8")).hexdigest()
        return PaperTradeFinancialReport(
            position_id=position.position_id,
            symbol=position.symbol,
            side=position.side,
            entry_time=entry.filled_at,
            exit_time=exit_fill.filled_at,
            exit_reason=_identity(facts.exit_reason, "exit_reason"),
            quantity=entry.quantity,
            entry_price=entry.price,
            exit_price=exit_fill.price,
            entry_notional=entry_notional,
            exit_notional=exit_notional,
            capital_used=entry_notional,
            entry_fee=entry.fee_amount,
            exit_fee=exit_fill.fee_amount,
            total_fees=total_fees,
            gross_pnl=Decimal("0") if gross == 0 else gross,
            net_pnl=net,
            roi_percent=Decimal("0") if net == 0 else net / entry_notional * Decimal("100"),
            balance_before=before,
            balance_after=Decimal("0") if after == 0 else after,
            currency=identity.currency,
            accounting_session_id=identity.accounting_session_id,
            report_semantic_id=semantic_id,
        )

    @staticmethod
    def _validate_journal(
        facts: PaperClosedTradeFacts, entry: PaperFill, exit_fill: PaperFill
    ) -> None:
        opened = tuple(
            event for event in facts.journal_events
            if event.event_type is PaperEventType.PAPER_POSITION_OPENED
            and event.aggregate_id == facts.position.position_id
        )
        closed = tuple(
            event for event in facts.journal_events
            if event.event_type is PaperEventType.PAPER_POSITION_CLOSED
            and event.aggregate_id == facts.position.position_id
        )
        if len(opened) != 1 or opened[0].causation_id != entry.fill_id:
            raise PaperAccountingError(PaperAccountingFinding.ENTRY_FILL_MISSING, "entry journal causality invalid")
        if len(closed) != 1 or closed[0].causation_id != exit_fill.fill_id:
            finding = PaperAccountingFinding.DUPLICATE_TRADE if len(closed) > 1 else PaperAccountingFinding.CLOSE_FILL_MISSING
            raise PaperAccountingError(finding, "close journal causality invalid")


@dataclass(frozen=True, slots=True)
class PaperAccountSummary:
    account_id: str
    accounting_session_id: str
    currency: str
    initial_balance: Decimal
    current_balance: Decimal
    realized_gross_pnl: Decimal
    total_fees: Decimal
    realized_net_pnl: Decimal
    return_percent: Decimal
    closed_trade_count: int
    winning_trade_count: int
    losing_trade_count: int
    breakeven_trade_count: int
    win_rate_percent: Decimal
    gross_profit: Decimal
    gross_loss: Decimal
    profit_factor: Decimal | None
    average_net_pnl: Decimal | None
    average_win: Decimal | None
    average_loss: Decimal | None
    largest_win: Decimal | None
    largest_loss: Decimal | None


class PaperAccountAccountingService:
    def __init__(self, reporting: PaperTradeReportingService | None = None) -> None:
        self._reporting = reporting or PaperTradeReportingService()

    def project(
        self,
        baseline: PaperAccountBaseline,
        trades: Sequence[PaperClosedTradeFacts],
    ) -> tuple[tuple[PaperTradeFinancialReport, ...], PaperAccountSummary]:
        if len({item.position.position_id for item in trades}) != len(trades):
            raise PaperAccountingError(PaperAccountingFinding.DUPLICATE_TRADE, "duplicate position")
        # A zero-balance projection obtains semantic IDs without changing economics,
        # then close time + semantic ID provides a total deterministic order.
        unordered = tuple(self._reporting.project(baseline.identity, item, Decimal("0")) for item in trades)
        ordered_ids = tuple(
            report.position_id for report in sorted(
                unordered, key=lambda item: (item.exit_time, item.report_semantic_id)
            )
        )
        facts_by_id = {item.position.position_id: item for item in trades}
        balance = baseline.initial_balance
        reports: list[PaperTradeFinancialReport] = []
        for position_id in ordered_ids:
            report = self._reporting.project(baseline.identity, facts_by_id[position_id], balance)
            reports.append(report)
            balance = report.balance_after
        return tuple(reports), self._summary(baseline, tuple(reports))

    @staticmethod
    def _summary(
        baseline: PaperAccountBaseline, reports: tuple[PaperTradeFinancialReport, ...]
    ) -> PaperAccountSummary:
        gross = sum((item.gross_pnl for item in reports), Decimal("0"))
        fees = sum((item.total_fees for item in reports), Decimal("0"))
        net = sum((item.net_pnl for item in reports), Decimal("0"))
        wins = tuple(item.net_pnl for item in reports if item.net_pnl > 0)
        losses = tuple(item.net_pnl for item in reports if item.net_pnl < 0)
        breakeven = len(reports) - len(wins) - len(losses)
        gross_profit = sum(wins, Decimal("0"))
        gross_loss = abs(sum(losses, Decimal("0")))
        count = len(reports)
        current = baseline.initial_balance + net
        return PaperAccountSummary(
            account_id=baseline.identity.account_id,
            accounting_session_id=baseline.identity.accounting_session_id,
            currency=baseline.identity.currency,
            initial_balance=baseline.initial_balance,
            current_balance=current,
            realized_gross_pnl=gross,
            total_fees=fees,
            realized_net_pnl=net,
            return_percent=net / baseline.initial_balance * Decimal("100"),
            closed_trade_count=count,
            winning_trade_count=len(wins),
            losing_trade_count=len(losses),
            breakeven_trade_count=breakeven,
            win_rate_percent=(Decimal(len(wins)) / Decimal(count) * Decimal("100") if count else Decimal("0")),
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            profit_factor=(gross_profit / gross_loss if gross_loss else None),
            average_net_pnl=(net / Decimal(count) if count else None),
            average_win=(gross_profit / Decimal(len(wins)) if wins else None),
            average_loss=(sum(losses, Decimal("0")) / Decimal(len(losses)) if losses else None),
            largest_win=(max(wins) if wins else None),
            largest_loss=(min(losses) if losses else None),
        )


@dataclass(frozen=True, slots=True)
class PaperAccountingReconciliationResult:
    outcome: PaperAccountingOutcome
    findings: tuple[PaperAccountingFinding, ...]
    reports: tuple[PaperTradeFinancialReport, ...] = ()
    summary: PaperAccountSummary | None = None


class PaperAccountingReconciliationService:
    def __init__(self, accounting: PaperAccountAccountingService | None = None) -> None:
        self._accounting = accounting or PaperAccountAccountingService()

    def reconcile(
        self,
        baselines: Sequence[PaperAccountBaseline],
        trades: Sequence[PaperClosedTradeFacts],
    ) -> PaperAccountingReconciliationResult:
        if not baselines:
            return self._failed(PaperAccountingFinding.BASELINE_MISSING, PaperAccountingOutcome.ACCOUNT_SUMMARY_NOT_AUTHORITATIVE)
        if len(baselines) != 1:
            return self._failed(PaperAccountingFinding.BASELINE_DUPLICATE)
        try:
            reports, summary = self._accounting.project(baselines[0], trades)
            balance = baselines[0].initial_balance
            for report in reports:
                if report.balance_before != balance or report.balance_after != balance + report.net_pnl:
                    raise PaperAccountingError(PaperAccountingFinding.BALANCE_CHAIN_MISMATCH, "broken balance chain")
                balance = report.balance_after
            if summary.current_balance != balance or summary.closed_trade_count != len(reports):
                raise PaperAccountingError(PaperAccountingFinding.BALANCE_CHAIN_MISMATCH, "summary mismatch")
            return PaperAccountingReconciliationResult(
                PaperAccountingOutcome.HEALTHY,
                (PaperAccountingFinding.ACCOUNTING_HEALTHY,),
                reports,
                summary,
            )
        except PaperAccountingError as exc:
            outcome = (
                PaperAccountingOutcome.FINAL_REPORT_NOT_AVAILABLE
                if exc.finding is PaperAccountingFinding.TRADE_NOT_CLOSED
                else PaperAccountingOutcome.SAFE_FAILURE
            )
            return self._failed(exc.finding, outcome)
        except (ArithmeticError, InvalidOperation, TypeError, ValueError):
            return self._failed(PaperAccountingFinding.SAFE_FAILURE)

    @staticmethod
    def _failed(
        finding: PaperAccountingFinding,
        outcome: PaperAccountingOutcome = PaperAccountingOutcome.SAFE_FAILURE,
    ) -> PaperAccountingReconciliationResult:
        return PaperAccountingReconciliationResult(outcome, (finding,))


def render_paper_trade_report(report: PaperTradeFinancialReport) -> str:
    """Render only safe business fields; no persistence payload or environment."""
    return "\n".join(
        (
            "PAPER TRADE REPORT",
            "",
            f"Symbol: {report.symbol}",
            f"Side: {report.side.value}",
            "",
            f"Capital used / Entry notional: {report.capital_used} {report.currency}",
            f"Exit notional: {report.exit_notional} {report.currency}",
            f"Entry price: {report.entry_price}",
            f"Exit price: {report.exit_price}",
            f"Quantity: {report.quantity}",
            f"Entry fee: {report.entry_fee}",
            f"Exit fee: {report.exit_fee}",
            f"Total fees: {report.total_fees}",
            f"Gross PnL: {report.gross_pnl}",
            f"Net PnL: {report.net_pnl}",
            f"ROI: {report.roi_percent}%",
            f"Balance before: {report.balance_before}",
            f"Balance after: {report.balance_after}",
            f"Exit reason: {report.exit_reason}",
        )
    )
