from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from app.engine_paper.accounting import (
    ACCOUNTING_SEMANTIC_VERSION,
    ACCOUNT_BASELINE_PERSISTENCE_CAPABILITY,
    PaperAccountAccountingService,
    PaperAccountBaseline,
    PaperAccountBaselineGate,
    PaperAccountBaselineService,
    PaperAccountIdentity,
    PaperAccountingError,
    PaperAccountingFinding,
    PaperAccountingOutcome,
    PaperAccountingReconciliationService,
    PaperTradeReportingService,
)
from app.engine_safety.paper_domain import ExecutionMode, PaperEventType, PaperPositionState, PaperSide
from tests.paper_account_balance_trade_reporting.conftest import make_trade


UTC = timezone.utc


class MemoryBaselinePort:
    def __init__(self, rows=(), *, activity=False, fault=None):
        self.rows = list(rows)
        self.activity = activity
        self.fault = fault

    def list_for_identity(self, identity):
        if self.fault == "read":
            raise TimeoutError("statement timeout")
        return tuple(row for row in self.rows if row.identity == identity)

    def has_economic_activity(self, identity):
        if self.fault == "activity":
            raise RuntimeError("db unavailable")
        return self.activity

    def create_if_absent(self, baseline):
        if self.fault in {"read", "activity", "insert"}:
            raise RuntimeError("cancelled")
        if self.rows:
            current = self.rows[0]
            if (current.identity == baseline.identity
                    and current.initial_balance == baseline.initial_balance
                    and current.semantic_version == baseline.semantic_version):
                return current
            raise PaperAccountingError(
                PaperAccountingFinding.BASELINE_IMMUTABILITY_VIOLATION,
                "immutable conflict",
            )
        if self.activity:
            raise PaperAccountingError(
                PaperAccountingFinding.BASELINE_AFTER_ECONOMIC_ACTIVITY_DENIED,
                "activity exists",
            )
        self.rows.append(baseline)
        return baseline


def test_0012_persistence_decision_is_narrow_and_present():
    assert ACCOUNT_BASELINE_PERSISTENCE_CAPABILITY == "READY_REVISION_0012"
    assert Path("alembic/versions/0012_paper_account_baseline.py").is_file()


def test_baseline_validation_usdt_paper_and_positive(identity):
    with pytest.raises(PaperAccountingError) as invalid:
        PaperAccountBaseline("b", identity, Decimal("0"), datetime.now(UTC))
    assert invalid.value.finding is PaperAccountingFinding.BASELINE_INVALID
    with pytest.raises(PaperAccountingError) as currency:
        PaperAccountIdentity("account", "session", "BTC")
    assert currency.value.finding is PaperAccountingFinding.UNSUPPORTED_CURRENCY
    with pytest.raises(PaperAccountingError):
        PaperAccountIdentity("account", "session", mode=ExecutionMode.LIVE)


def test_baseline_initialize_replay_immutability_and_gate(identity):
    port = MemoryBaselinePort()
    service = PaperAccountBaselineService(port)
    assert service.status(identity) is PaperAccountBaselineGate.MISSING
    initial = service.initialize(
        baseline_id="baseline", identity=identity, initial_balance=Decimal("100"),
        initialized_at=datetime(2026, 8, 11, tzinfo=UTC),
    )
    replay = service.initialize(
        baseline_id="different-request-id", identity=identity,
        initial_balance=Decimal("100"), initialized_at=datetime(2026, 8, 12, tzinfo=UTC),
    )
    assert replay is initial
    assert service.status(identity) is PaperAccountBaselineGate.PASS
    with pytest.raises(PaperAccountingError) as changed:
        service.initialize(
            baseline_id="changed", identity=identity, initial_balance=Decimal("101"),
            initialized_at=datetime.now(UTC),
        )
    assert changed.value.finding is PaperAccountingFinding.BASELINE_IMMUTABILITY_VIOLATION
    assert port.rows == [initial]


def test_baseline_after_activity_and_db_failures_fail_closed(identity):
    service = PaperAccountBaselineService(MemoryBaselinePort(activity=True))
    with pytest.raises(PaperAccountingError) as denied:
        service.initialize(
            baseline_id="baseline", identity=identity, initial_balance=Decimal("100"),
            initialized_at=datetime.now(UTC),
        )
    assert denied.value.finding is PaperAccountingFinding.BASELINE_AFTER_ECONOMIC_ACTIVITY_DENIED
    for fault in ("read", "activity", "insert"):
        with pytest.raises(PaperAccountingError) as failure:
            PaperAccountBaselineService(MemoryBaselinePort(fault=fault)).initialize(
                baseline_id="baseline", identity=identity, initial_balance=Decimal("100"),
                initialized_at=datetime.now(UTC),
            )
        assert failure.value.finding is PaperAccountingFinding.SAFE_FAILURE


def test_missing_and_duplicate_baseline_fail_closed(baseline):
    service = PaperAccountingReconciliationService()
    assert service.reconcile((), ()).findings == (PaperAccountingFinding.BASELINE_MISSING,)
    duplicate = service.reconcile((baseline, baseline), ())
    assert duplicate.findings == (PaperAccountingFinding.BASELINE_DUPLICATE,)


def test_open_and_closing_reports_not_available(identity):
    facts = make_trade(3001)
    for state in (PaperPositionState.OPEN, PaperPositionState.CLOSING):
        active = replace(
            facts.position, state=state, remaining_quantity=facts.position.entry_quantity,
            average_exit_price=None, exit_fees=Decimal("0"),
            realized_pnl=-facts.position.entry_fees, closed_at=None, exit_fill_id=None,
        )
        with pytest.raises(PaperAccountingError) as failure:
            PaperTradeReportingService().project(identity, replace(facts, position=active), Decimal("100"))
        assert failure.value.finding is PaperAccountingFinding.TRADE_NOT_CLOSED


@pytest.mark.parametrize(
    "mutation,finding",
    (
        (lambda f: replace(f, entry_fill=None), PaperAccountingFinding.ENTRY_FILL_MISSING),
        (lambda f: replace(f, exit_fill=None), PaperAccountingFinding.CLOSE_FILL_MISSING),
        (lambda f: replace(f, exit_fill=replace(f.exit_fill, fill_id="conflict")), PaperAccountingFinding.FILL_IDENTITY_CONFLICT),
        (lambda f: replace(f, position=replace(f.position, entry_fees=f.position.entry_fees + Decimal("1"))), PaperAccountingFinding.FEE_MISMATCH),
        (lambda f: replace(f, position=replace(f.position, realized_pnl=f.position.realized_pnl + Decimal("1"))), PaperAccountingFinding.PNL_MISMATCH),
        (lambda f: replace(f, entry_fill=replace(f.entry_fill, fee_asset="BTC")), PaperAccountingFinding.UNSUPPORTED_CURRENCY),
        (lambda f: replace(f, journal_events=()), PaperAccountingFinding.ENTRY_FILL_MISSING),
        (lambda f: replace(f, journal_events=(*f.journal_events, f.journal_events[-1])), PaperAccountingFinding.DUPLICATE_TRADE),
    ),
)
def test_fault_matrix_fails_closed(mutation, finding, baseline):
    result = PaperAccountingReconciliationService().reconcile((baseline,), (mutation(make_trade(3100)),))
    assert result.outcome is not PaperAccountingOutcome.HEALTHY
    assert result.findings == (finding,)


def test_duplicate_trade_replay_not_double_counted(baseline):
    trade = make_trade(3200)
    result = PaperAccountingReconciliationService().reconcile((baseline,), (trade, trade))
    assert result.findings == (PaperAccountingFinding.DUPLICATE_TRADE,)


def test_same_close_timestamp_has_stable_semantic_tie_breaker(baseline):
    first = make_trade(3301, close_offset_seconds=100)
    second = make_trade(3302, close_offset_seconds=99)
    assert first.position.closed_at == second.position.closed_at
    service = PaperAccountAccountingService()
    reports_a, summary_a = service.project(baseline, (first, second))
    reports_b, summary_b = service.project(baseline, (second, first))
    assert reports_a == reports_b and summary_a == summary_b
    assert tuple(item.report_semantic_id for item in reports_a) == tuple(sorted(item.report_semantic_id for item in reports_a))


def test_isolated_three_trade_realized_accounting_lifecycle(baseline):
    profitable_long = make_trade(3401, side=PaperSide.LONG, entry_price=Decimal("10"), exit_price=Decimal("12"))
    losing_short = make_trade(3402, side=PaperSide.SHORT, entry_price=Decimal("10"), exit_price=Decimal("11"))
    breakeven_after_fees = make_trade(
        3403, side=PaperSide.LONG, entry_price=Decimal("10"),
        # 50% per fill is intentionally extreme but gives an exact Decimal
        # equality: gross 20 - entry fee 5 - exit fee 15 == 0.
        exit_price=Decimal("30"), quantity=Decimal("1"), fee_bps=Decimal("5000"),
    )
    result = PaperAccountingReconciliationService().reconcile(
        (baseline,), (breakeven_after_fees, losing_short, profitable_long)
    )
    assert result.outcome is PaperAccountingOutcome.HEALTHY
    assert result.summary.closed_trade_count == 3
    assert result.summary.winning_trade_count == 1
    assert result.summary.losing_trade_count == 1
    assert result.summary.breakeven_trade_count == 1
    assert result.summary.current_balance == baseline.initial_balance + result.summary.realized_net_pnl
    assert result.summary.total_fees == sum((r.total_fees for r in result.reports), Decimal("0"))
    assert result.summary.profit_factor == result.summary.gross_profit / result.summary.gross_loss


def test_profit_factor_not_applicable_without_losses(baseline):
    _, summary = PaperAccountAccountingService().project(baseline, (make_trade(3501),))
    assert summary.profit_factor is None
    assert summary.win_rate_percent == Decimal("100")


def test_empty_summary_is_exact_and_realized_only(baseline):
    reports, summary = PaperAccountAccountingService().project(baseline, ())
    assert reports == ()
    assert summary.current_balance == summary.initial_balance == Decimal("100")
    assert summary.realized_net_pnl == summary.total_fees == Decimal("0")
    assert summary.profit_factor is None


def test_contract_source_has_no_float_or_host_financial_fallback():
    source = Path("app/engine_paper/accounting.py").read_text(encoding="utf-8")
    assert "float(" not in source
    for forbidden in ("production_control", ".env", "online_trader.md", "DATABASE_URL"):
        assert forbidden not in source
    assert "PaperAccountBaselinePersistence" in source
    assert ACCOUNTING_SEMANTIC_VERSION == "PAPER_ACCOUNTING/1.0"


def test_first_canary_gate_contract(identity, baseline):
    missing = PaperAccountBaselineService(MemoryBaselinePort())
    ready = PaperAccountBaselineService(MemoryBaselinePort((baseline,)))
    assert missing.status(identity) is PaperAccountBaselineGate.MISSING
    assert ready.status(identity) is PaperAccountBaselineGate.PASS
