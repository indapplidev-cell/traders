"""Read-only PAPER reporting orchestration.

The service delegates every financial value to ``engine_paper.accounting`` and
contains no trading, baseline-initialization, repair, or control transition.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import re

from app.engine_paper.accounting import (
    PaperAccountAccountingService,
    PaperAccountingOutcome,
    PaperAccountingReconciliationService,
    PaperTradeFinancialReport,
)
from app.engine_paper.production_preparation import PaperProductionAccountIdentityBinding
from app.server_api.errors import ApiError
from app.server_api.mapping.contract import decimal_text, utc_text
from app.server_api.pagination import decode_cursor, encode_cursor
from app.server_api.repositories.protocols import PaperReportingReadRepository
from app.server_api.repositories.records import (
    CursorPosition,
    PaperPositionQuery,
    PaperPositionRecordView,
    PaperTradeQuery,
    PaperListQuery,
    PaperOrderRecordView,
    PaperFillRecordView,
    PaperJournalRecordView,
)
from app.server_api.schemas.paper import (
    PaperAccount,
    PaperControlStatus,
    PaperList,
    PaperPositionDetail,
    PaperPositionItem,
    PaperReadiness,
    PaperReconciliation,
    PaperReconciliationSection,
    PaperRuntimeStatus,
    PaperTradeItem,
    PaperTradeReport, TradingCriteriaSnapshot, PaperOrderItem, PaperFillItem,
    PaperJournalItem,
)
from app.engine_paper.trading_criteria import build_trading_criteria_snapshot
from app.engine_paper.performance import scalp_v2_performance
from app.server_api.schema_compatibility import (
    PAPER_SCHEMA_COMPATIBILITY_LABEL,
    revision_is_supported,
)


PAPER_SCHEMA_EXPECTED = PAPER_SCHEMA_COMPATIBILITY_LABEL
PAPER_REPORTING_API_VERSION = 1
MAX_RECONCILIATION_CLOSED_TRADES = 10_000
MAX_TRADE_DATE_RANGE = timedelta(days=365)
_SYMBOL = re.compile(r"^[A-Z0-9]{5,20}$")
_EXIT_REASON = re.compile(r"^[A-Z0-9_]{1,64}$")


@dataclass(frozen=True, slots=True)
class PaperRuntimeObservation:
    environment: str = "NOT_DEPLOYED"
    runtime_enabled: bool = False
    daemon_enabled: bool = False
    scheduler_enabled: bool = False
    dry_run: bool = True
    mutation_enabled: bool = False
    worker_running: bool | None = None
    operator_runner_running: bool | None = None
    market_data_adapter_ready: bool | None = None
    approval_source_adapter_ready: bool | None = None
    wal_ready: bool | None = None
    pitr_ready: bool | None = None
    pitr_lineage_valid: bool | None = None
    pitr_lineage_start: datetime | None = None
    pitr_lineage_end: datetime | None = None
    pitr_contiguous_duration_seconds: int | None = None
    pitr_physical_gap: bool | None = None
    current_approval_availability: str = "NOT_AVAILABLE"
    paper_principal_ready: bool = False
    production_identity_binding_ready: bool | None = None
    runtime_credential_binding_ready: bool | None = None
    runtime_grants_ready: bool | None = None
    readonly_grants_ready: bool | None = None
    runtime_config_ready: bool = False
    kill_switch_ready: bool = False
    canary_scope_valid: bool = False
    live_enabled: bool = False
    current_execution: dict[str, object] | None = None


def _default_control_status() -> PaperControlStatus:
    return PaperControlStatus(
        state="NOT_AVAILABLE",
        effective_state="FAIL_CLOSED",
        generation=None,
        health="FAIL_CLOSED",
        emergency_stop_available=False,
        audit_health="NOT_APPLICABLE",
        state_audit_reconciliation="NOT_APPLICABLE",
    )


def _timestamp(value: str | None, field: str) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if not value.endswith("Z") or parsed.tzinfo is None:
            raise ValueError
        return parsed.astimezone(timezone.utc)
    except ValueError:
        raise ApiError(422, "INVALID_FILTER", "A PAPER reporting filter is invalid.", {"field": field}) from None


class PaperReadonlyReportingService:
    def __init__(
        self,
        repository: PaperReportingReadRepository | None,
        *,
        runtime: PaperRuntimeObservation | Callable[[], PaperRuntimeObservation] | None = None,
        control_status: Callable[[], PaperControlStatus] = _default_control_status,
        max_closed_trades: int = MAX_RECONCILIATION_CLOSED_TRADES,
        production_identity: PaperProductionAccountIdentityBinding | None = None,
    ) -> None:
        self._repository = repository
        self._runtime_source = runtime or PaperRuntimeObservation()
        self._control_status = control_status
        self._max_closed_trades = max_closed_trades
        self._production_identity = production_identity
        self._accounting = PaperAccountAccountingService()
        self._reconciliation = PaperAccountingReconciliationService(self._accounting)

    def _runtime(self) -> PaperRuntimeObservation:
        value = self._runtime_source
        return value() if callable(value) else value

    def trading_criteria(self) -> TradingCriteriaSnapshot:
        repository = self._repo()
        active = getattr(repository, "active_trading_universe", None)
        symbols = active().symbols if callable(active) else None
        return TradingCriteriaSnapshot.model_validate(build_trading_criteria_snapshot(symbols))

    def _repo(self) -> PaperReportingReadRepository:
        if self._repository is None:
            raise ApiError(503, "PAPER_REPORTING_SAFE_FAILURE", "PAPER reporting is not configured.")
        return self._repository

    @staticmethod
    def _filters(*, limit: int, symbol: str | None = None, state: str | None = None,
                 side: str | None = None, exit_reason: str | None = None) -> None:
        if limit < 1 or limit > 100:
            raise ApiError(422, "LIMIT_EXCEEDED", "The PAPER reporting limit must be between 1 and 100.")
        invalid = ((symbol is not None and _SYMBOL.fullmatch(symbol) is None)
                   or (state is not None and state not in {"OPEN", "CLOSING", "CLOSED", "FAILED"})
                   or (side is not None and side not in {"LONG", "SHORT"})
                   or (exit_reason is not None and _EXIT_REASON.fullmatch(exit_reason) is None))
        if invalid:
            raise ApiError(422, "INVALID_FILTER", "A PAPER reporting filter is invalid.")

    def _schema_ready(self) -> bool:
        try:
            repository = self._repo()
            capabilities_source = getattr(repository, "readonly_schema_capabilities", None)
            if callable(capabilities_source):
                return bool(getattr(capabilities_source(), "compatible", False))
            revisions_source = getattr(repository, "schema_revisions", None)
            revisions = tuple(revisions_source()) if callable(revisions_source) else (repository.schema_revision(),)
            contract_source = getattr(repository, "paper_schema_contract", None)
            revision_ready = revision_is_supported(
                tuple(str(value) for value in revisions if value)
            )
            if not callable(contract_source):
                # Inert/test adapters can expose only the historical revision
                # protocol. The production adapter always takes the capability
                # branch above, which validates the complete physical shape.
                return revision_ready
            return bool(revision_ready and getattr(contract_source(), "compatible", False))
        except Exception:
            return False

    def _require_schema(self) -> None:
        if not self._schema_ready():
            raise ApiError(409, "PAPER_SCHEMA_NOT_DEPLOYED", "The PAPER reporting schema is not deployed.")

    def _authoritative(self, *, schema_checked: bool = False):
        if not schema_checked:
            self._require_schema()
        baselines = self._repo().list_account_baselines(2)
        if not baselines:
            raise ApiError(409, "BASELINE_MISSING", "The immutable PAPER account baseline is missing.")
        if len(baselines) != 1:
            raise ApiError(409, "ACCOUNTING_NOT_AUTHORITATIVE", "PAPER accounting is not authoritative.")
        if (self._production_identity is not None
                and baselines[0].identity != self._production_identity.account_identity()):
            raise ApiError(409, "PRODUCTION_IDENTITY_MISMATCH", "PAPER production identity does not match the baseline.")
        facts = self._repo().list_closed_trade_facts(self._max_closed_trades + 1)
        if len(facts) > self._max_closed_trades:
            raise ApiError(409, "RECONCILIATION_SCOPE_EXCEEDED", "The bounded reconciliation scope was exceeded.")
        result = self._reconciliation.reconcile(baselines, facts)
        if result.outcome is not PaperAccountingOutcome.HEALTHY or result.summary is None:
            raise ApiError(409, "ACCOUNTING_NOT_AUTHORITATIVE", "PAPER accounting is not authoritative.")
        return baselines[0], result

    def readiness(self) -> PaperReadiness:
        runtime = self._runtime()
        ready = self._schema_ready()
        control = self.control_status()
        baseline_exists: bool | None = None
        baseline_valid: bool | None = None
        accounting_status = "NOT_DEPLOYED"
        paper_status = "NOT_DEPLOYED"
        if ready:
            baselines = self._repo().list_account_baselines(2)
            baseline_exists = bool(baselines)
            baseline_valid = len(baselines) == 1
            if not baselines:
                accounting_status = "BASELINE_MISSING"
                paper_status = "UNHEALTHY"
            elif len(baselines) != 1:
                accounting_status = "ACCOUNTING_NOT_AUTHORITATIVE"
                paper_status = "UNHEALTHY"
            else:
                facts = self._repo().list_closed_trade_facts(self._max_closed_trades + 1)
                if len(facts) > self._max_closed_trades:
                    accounting_status = "SCOPE_EXCEEDED"
                    paper_status = "SCOPE_EXCEEDED"
                else:
                    result = self._reconciliation.reconcile(baselines, facts)
                    accounting_status = result.outcome.value
                    paper_status = "HEALTHY" if result.outcome is PaperAccountingOutcome.HEALTHY else "UNHEALTHY"
        denials = []
        if not ready:
            denials.append("PAPER_SCHEMA_NOT_DEPLOYED")
        preparation_gates = (
            ("PRODUCTION_IDENTITY_BINDING_MISSING", runtime.production_identity_binding_ready),
            ("RUNTIME_CREDENTIAL_BINDING_MISSING", runtime.runtime_credential_binding_ready),
            ("RUNTIME_GRANTS_NOT_READY", runtime.runtime_grants_ready),
            ("READONLY_GRANTS_NOT_READY", runtime.readonly_grants_ready),
        )
        denials.extend(code for code, passed in preparation_gates if passed is False)
        gates = (
            ("PITR_NOT_READY", runtime.pitr_ready is True),
            ("WAL_NOT_READY", runtime.wal_ready is True),
            ("MARKET_DATA_NOT_READY", runtime.market_data_adapter_ready is True),
            ("APPROVAL_SOURCE_NOT_READY", runtime.approval_source_adapter_ready is True),
            ("BASELINE_PERSISTENCE_NOT_READY", ready),
            ("BASELINE_MISSING", baseline_exists is True),
            ("BASELINE_INVALID", baseline_valid is True),
            ("ACCOUNTING_NOT_HEALTHY", accounting_status == "HEALTHY"),
            ("PAPER_RECONCILIATION_NOT_HEALTHY", paper_status == "HEALTHY"),
            ("PAPER_PRINCIPAL_NOT_READY", runtime.paper_principal_ready),
            ("RUNTIME_CONFIG_NOT_READY", runtime.runtime_config_ready),
            ("PAPER_RUNTIME_DISABLED", runtime.runtime_enabled),
            ("KILL_SWITCH_NOT_READY", runtime.kill_switch_ready),
            (
                "CONTROL_NOT_ELIGIBLE",
                control.state in {"DISABLED", "ARMED", "CONTINUOUS_ARMED", "PAUSED_BY_RISK"}
                and control.effective_state == control.state
                and control.health == "HEALTHY"
                and control.audit_health == "PASS"
                and control.state_audit_reconciliation == "PASS"
                and control.emergency_stop_available,
            ),
            ("CANARY_SCOPE_INVALID", runtime.canary_scope_valid),
            ("LIVE_NOT_DENIED", not runtime.live_enabled),
        )
        denials.extend(code for code, passed in gates if not passed and code not in denials)
        if control.risk_pause_reason and control.risk_pause_reason not in denials:
            denials.append(control.risk_pause_reason)
        mutation_ready = ready and not denials
        return PaperReadiness(
            environment=runtime.environment,
            paper_schema_ready=ready,
            status="READY" if ready and baseline_valid and accounting_status == "HEALTHY" else ("PAPER_SCHEMA_NOT_DEPLOYED" if not ready else accounting_status),
            paper_runtime_enabled=runtime.runtime_enabled,
            paper_daemon_enabled=runtime.daemon_enabled,
            paper_scheduler_enabled=runtime.scheduler_enabled,
            paper_control_state=control.state,
            paper_control_effective_state=control.effective_state,
            paper_control_generation=control.generation,
            paper_control_health=control.health,
            paper_canary_id=control.canary_id,
            paper_canary_status=control.canary_status,
            account_baseline_persistence_ready=ready,
            account_baseline_exists=baseline_exists,
            account_baseline_valid=baseline_valid,
            accounting_reconciliation_status=accounting_status,
            paper_reconciliation_status=paper_status,
            market_data_adapter_ready=runtime.market_data_adapter_ready,
            approval_source_adapter_ready=runtime.approval_source_adapter_ready,
            wal_ready=runtime.wal_ready,
            pitr_ready=runtime.pitr_ready,
            pitr_lineage_valid=runtime.pitr_lineage_valid,
            pitr_lineage_start=utc_text(runtime.pitr_lineage_start) if runtime.pitr_lineage_start else None,
            pitr_lineage_end=utc_text(runtime.pitr_lineage_end) if runtime.pitr_lineage_end else None,
            pitr_contiguous_duration_seconds=runtime.pitr_contiguous_duration_seconds,
            pitr_physical_gap=runtime.pitr_physical_gap,
            canary_command_limit=control.canary_command_limit,
            canary_command_count=control.canary_command_count,
            canary_command_remaining=control.canary_command_remaining,
            canary_command_budget_exhausted=control.canary_command_budget_exhausted,
            canary_open_position_limit=control.canary_open_position_limit,
            canary_open_position_count=control.canary_open_position_count,
            canary_open_position_remaining=control.canary_open_position_remaining,
            canary_open_position_budget_exhausted=control.canary_open_position_budget_exhausted,
            canary_closed_trade_count=control.canary_closed_trade_count,
            current_approval_availability=runtime.current_approval_availability,
            current_mutation_ready=mutation_ready,
            current_mutation_denial_reasons=denials,
            authority_mode=control.authority_mode,
            control_mode_version=control.control_mode_version,
            budget_day=control.budget_day,
            daily_command_budget=control.daily_command_budget,
            commands_used_today=control.commands_used_today,
            daily_realized_loss_budget=control.daily_realized_loss_budget,
            realized_pnl_today=control.realized_pnl_today,
            realized_loss_today=control.realized_loss_today,
            daily_risk_budget_bps=control.daily_risk_budget_bps,
            risk_used_today_bps=control.risk_used_today_bps,
            max_consecutive_losses=control.max_consecutive_losses,
            loss_streak=control.loss_streak,
            risk_pause_reason=control.risk_pause_reason,
        )

    def account(self) -> PaperAccount:
        baseline, result = self._authoritative()
        value = result.summary
        assert value is not None
        unrealized_source = getattr(self._repo(), "total_unrealized_pnl", None)
        open_count_source = getattr(self._repo(), "count_open_paper_positions", None)
        unrealized = unrealized_source() if callable(unrealized_source) else None
        open_count = open_count_source() if callable(open_count_source) else None
        profile_source = getattr(self._repo(), "paper_trade_profile_context", None)
        profile_context = profile_source(
            tuple(report.position_id for report in result.reports)
        ) if callable(profile_source) else {}
        performance = {
            key: decimal_text(metric) if isinstance(metric, Decimal) else metric
            for key, metric in scalp_v2_performance(result.reports, profile_context).items()
        }
        return PaperAccount(
            account_id=value.account_id, accounting_session_id=value.accounting_session_id,
            currency=value.currency, baseline_id=baseline.baseline_id,
            initial_balance=decimal_text(value.initial_balance), initialized_at=utc_text(baseline.initialized_at),
            baseline_semantic_version=baseline.semantic_version, current_balance=decimal_text(value.current_balance),
            realized_gross_pnl=decimal_text(value.realized_gross_pnl), total_fees=decimal_text(value.total_fees),
            realized_net_pnl=decimal_text(value.realized_net_pnl), return_percent=decimal_text(value.return_percent),
            closed_trade_count=value.closed_trade_count, winning_trade_count=value.winning_trade_count,
            losing_trade_count=value.losing_trade_count, breakeven_trade_count=value.breakeven_trade_count,
            win_rate_percent=decimal_text(value.win_rate_percent), gross_profit=decimal_text(value.gross_profit),
            gross_loss=decimal_text(value.gross_loss), profit_factor=decimal_text(value.profit_factor),
            average_net_pnl=decimal_text(value.average_net_pnl), average_win=decimal_text(value.average_win),
            average_loss=decimal_text(value.average_loss), largest_win=decimal_text(value.largest_win),
            largest_loss=decimal_text(value.largest_loss), accounting_reconciliation_status=result.outcome.value,
            unrealized_pnl=decimal_text(unrealized),
            global_open_position_count=open_count,
            scalping_v2_performance=performance,
        )

    @staticmethod
    def _position(value: PaperPositionRecordView) -> PaperPositionItem:
        item = value.position
        closed = getattr(item.state, "value", item.state) == "CLOSED"
        return PaperPositionItem(
            position_id=item.position_id, command_id=value.command_id,
            symbol=item.symbol, side=getattr(item.side, "value", item.side),
            state=getattr(item.state, "value", item.state), quantity=decimal_text(item.entry_quantity),
            entry_price=decimal_text(item.average_entry_price), entry_time=utc_text(value.entry_time),
            stop_price=decimal_text(item.stop_price), target_price=decimal_text(item.target_price),
            exit_reason=value.exit_reason, closed_at=utc_text(item.closed_at) if item.closed_at else None,
            realized_pnl=decimal_text(item.realized_pnl) if closed else None,
        )

    def positions(self, *, limit: int, cursor: str | None, state: str | None, symbol: str | None) -> PaperList[PaperPositionItem]:
        self._filters(limit=limit, state=state, symbol=symbol)
        self._require_schema()
        page = self._repo().list_paper_positions(PaperPositionQuery(limit, decode_cursor(cursor, "paper_positions"), state, symbol))
        records = tuple(item for item in page.items if isinstance(item, PaperPositionRecordView))[:limit]
        next_cursor = None
        if page.has_more and records:
            last = records[-1]
            next_cursor = encode_cursor("paper_positions", CursorPosition(last.updated_at, last.position.position_id))
        return PaperList[PaperPositionItem](items=[self._position(item) for item in records], next_cursor=next_cursor, has_more=bool(next_cursor))

    def position(self, position_id: str) -> PaperPositionDetail:
        self._require_schema()
        value = self._repo().get_paper_position(position_id)
        if value is None:
            raise ApiError(404, "POSITION_NOT_FOUND", "The PAPER position was not found.")
        base = self._position(value).model_dump()
        return PaperPositionDetail(**base, entry_order_id=value.entry_order_id, entry_fill_id=value.entry_fill_id,
            close_order_id=value.close_order_id, close_fill_id=value.close_fill_id,
            exit_cursor_status=value.exit_cursor_status, exit_decision=value.exit_decision,
            lifecycle_events=list(value.lifecycle_events))

    @staticmethod
    def _trade(report: PaperTradeFinancialReport) -> PaperTradeItem:
        return PaperTradeItem(
            position_id=report.position_id, trade_id=report.position_id, symbol=report.symbol,
            side=report.side.value, entry_time=utc_text(report.entry_time), exit_time=utc_text(report.exit_time),
            exit_reason=report.exit_reason, capital_used=decimal_text(report.capital_used),
            entry_notional=decimal_text(report.entry_notional), exit_notional=decimal_text(report.exit_notional),
            total_fees=decimal_text(report.total_fees), net_pnl=decimal_text(report.net_pnl),
            roi_percent=decimal_text(report.roi_percent), balance_before=decimal_text(report.balance_before),
            balance_after=decimal_text(report.balance_after),
        )

    def trades(self, *, limit: int, cursor: str | None, symbol: str | None, side: str | None,
               exit_reason: str | None, from_value: str | None, to_value: str | None) -> PaperList[PaperTradeItem]:
        self._filters(limit=limit, symbol=symbol, side=side, exit_reason=exit_reason)
        from_at, to_at = _timestamp(from_value, "from"), _timestamp(to_value, "to")
        if from_at and to_at and (from_at >= to_at or to_at - from_at > MAX_TRADE_DATE_RANGE):
            code = "DATE_RANGE_EXCEEDED" if to_at > from_at else "INVALID_FILTER"
            raise ApiError(422, code, "The PAPER trade date range is invalid.")
        self._require_schema()
        page = self._repo().list_paper_trades(PaperTradeQuery(limit, decode_cursor(cursor, "paper_trades"), symbol, side, exit_reason, from_at, to_at))
        if not page.items:
            return PaperList[PaperTradeItem](items=[], next_cursor=None, has_more=False)
        _, result = self._authoritative(schema_checked=True)
        selected_ids = {item.position.position_id for item in page.items}
        reports = [item for item in reversed(result.reports) if item.position_id in selected_ids][:limit]
        next_cursor = None
        if page.has_more and reports:
            last = reports[-1]
            next_cursor = encode_cursor("paper_trades", CursorPosition(last.exit_time, last.position_id))
        return PaperList[PaperTradeItem](items=[self._trade(item) for item in reports], next_cursor=next_cursor, has_more=bool(next_cursor))

    def trade_report(self, position_id: str) -> PaperTradeReport:
        self._require_schema()
        position = self._repo().get_paper_position(position_id)
        if position is None:
            raise ApiError(404, "POSITION_NOT_FOUND", "The PAPER position was not found.")
        if getattr(position.position.state, "value", position.position.state) != "CLOSED":
            raise ApiError(409, "FINAL_REPORT_NOT_AVAILABLE", "The final PAPER trade report is not available.")
        _, result = self._authoritative(schema_checked=True)
        report = next((item for item in result.reports if item.position_id == position_id), None)
        if report is None:
            raise ApiError(409, "ACCOUNTING_NOT_AUTHORITATIVE", "PAPER accounting is not authoritative.")
        return PaperTradeReport(**self._trade(report).model_dump(), accounting_session_id=report.accounting_session_id,
            currency=report.currency, quantity=decimal_text(report.quantity), entry_price=decimal_text(report.entry_price),
            exit_price=decimal_text(report.exit_price), entry_fee=decimal_text(report.entry_fee),
            exit_fee=decimal_text(report.exit_fee), gross_pnl=decimal_text(report.gross_pnl),
            report_semantic_id=report.report_semantic_id)

    def reconciliation(self) -> PaperReconciliation:
        self._require_schema()
        try:
            _, result = self._authoritative(schema_checked=True)
            status = "HEALTHY"
            findings = [item.value for item in result.findings]
            rows = len(result.reports)
        except ApiError as error:
            if error.code == "RECONCILIATION_SCOPE_EXCEEDED":
                raise
            status, findings, rows = "UNHEALTHY", [error.code], 0
        section = PaperReconciliationSection(status=status, findings=findings, rows_scanned=rows)
        return PaperReconciliation(overall_status=status, paper_reconciliation=section, accounting_reconciliation=section)

    def runtime_status(self) -> PaperRuntimeStatus:
        value = self._runtime()
        return PaperRuntimeStatus(runtime_enabled=value.runtime_enabled, daemon_enabled=value.daemon_enabled,
            scheduler_enabled=value.scheduler_enabled, dry_run=value.dry_run, mutation_enabled=value.mutation_enabled,
            worker_running=value.worker_running, operator_runner_running=value.operator_runner_running,
            current_execution=value.current_execution)

    def control_status(self) -> PaperControlStatus:
        try:
            return self._control_status()
        except Exception:
            return _default_control_status()

    def orders(self, *, limit: int, cursor: str | None, symbol: str | None) -> PaperList[PaperOrderItem]:
        self._filters(limit=limit, symbol=symbol)
        self._require_schema()
        page = self._repo().list_paper_orders(PaperListQuery(limit, decode_cursor(cursor, "paper_orders"), symbol))
        records = tuple(item for item in page.items if isinstance(item, PaperOrderRecordView))[:limit]
        next_cursor = None
        if page.has_more and records:
            last = records[-1]
            next_cursor = encode_cursor("paper_orders", CursorPosition(last.updated_at, last.order_id))
        items = [PaperOrderItem(
            order_id=item.order_id, command_id=item.command_id, symbol=item.symbol, side=item.side,
            role=item.order_role, order_type=item.order_type, state=item.state,
            quantity=decimal_text(item.requested_quantity), filled_quantity=decimal_text(item.filled_quantity),
            average_fill_price=decimal_text(item.average_fill_price), reason_code=item.reason_code,
            created_at=utc_text(item.created_at), updated_at=utc_text(item.updated_at),
        ) for item in records]
        return PaperList[PaperOrderItem](items=items, next_cursor=next_cursor, has_more=bool(next_cursor))

    def fills(self, *, limit: int, cursor: str | None, symbol: str | None) -> PaperList[PaperFillItem]:
        self._filters(limit=limit, symbol=symbol)
        self._require_schema()
        page = self._repo().list_paper_fills(PaperListQuery(limit, decode_cursor(cursor, "paper_fills"), symbol))
        records = tuple(item for item in page.items if isinstance(item, PaperFillRecordView))[:limit]
        next_cursor = None
        if page.has_more and records:
            last = records[-1]
            next_cursor = encode_cursor("paper_fills", CursorPosition(last.filled_at, last.fill_id))
        items = [PaperFillItem(
            fill_id=item.fill_id, order_id=item.order_id, symbol=item.symbol, side=item.side,
            role=item.fill_role, quantity=decimal_text(item.quantity), price=decimal_text(item.price),
            fee=decimal_text(item.fee_amount), fee_asset=item.fee_asset, timestamp=utc_text(item.filled_at),
        ) for item in records]
        return PaperList[PaperFillItem](items=items, next_cursor=next_cursor, has_more=bool(next_cursor))

    def journal(self, *, limit: int, cursor: str | None) -> PaperList[PaperJournalItem]:
        self._filters(limit=limit)
        self._require_schema()
        page = self._repo().list_paper_journal(PaperListQuery(limit, decode_cursor(cursor, "paper_journal")))
        records = tuple(item for item in page.items if isinstance(item, PaperJournalRecordView))[:limit]
        next_cursor = None
        if page.has_more and records:
            last = records[-1]
            next_cursor = encode_cursor("paper_journal", CursorPosition(last.occurred_at, last.event_id))
        items = [PaperJournalItem(
            event_id=item.event_id, entity_type=item.entity_type, entity_id=item.entity_id,
            event_type=item.event_type, state_version=item.state_version, reason_code=item.reason_code,
            causation_id=item.causation_id, correlation_id=item.correlation_id,
            timestamp=utc_text(item.occurred_at),
        ) for item in records]
        return PaperList[PaperJournalItem](items=items, next_cursor=next_cursor, has_more=bool(next_cursor))
