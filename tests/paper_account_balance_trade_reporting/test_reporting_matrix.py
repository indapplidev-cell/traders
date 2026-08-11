from __future__ import annotations

from decimal import Decimal

import pytest

from app.engine_paper.accounting import (
    PaperAccountAccountingService,
    PaperAccountingFinding,
    PaperAccountingOutcome,
    PaperAccountingReconciliationService,
    PaperTradeReportingService,
    render_paper_trade_report,
)
from app.engine_safety.paper_domain import PaperSide
from tests.paper_account_balance_trade_reporting.conftest import make_trade


@pytest.mark.parametrize("case", range(1000))
def test_decimal_long_short_authoritative_projection_matrix(case, identity):
    side = PaperSide.LONG if case % 2 == 0 else PaperSide.SHORT
    entry = Decimal("100") + Decimal(case % 37) / Decimal("7")
    delta = Decimal("0.000000001") + Decimal(case % 19) / Decimal("11")
    exit_price = entry + delta if side is PaperSide.LONG else entry - delta
    quantity = Decimal(case % 23 + 1) / Decimal("13")
    facts = make_trade(
        case + 1, side=side, entry_price=entry, exit_price=exit_price,
        quantity=quantity, fee_bps=Decimal(case % 17) / Decimal("10"),
    )
    report = PaperTradeReportingService().project(identity, facts, Decimal("100"))
    expected_gross = abs(exit_price - entry) * quantity
    assert report.gross_pnl == expected_gross
    assert report.net_pnl == facts.position.realized_pnl
    assert report.total_fees == facts.entry_fill.fee_amount + facts.exit_fill.fee_amount
    assert report.entry_notional == abs(entry * quantity)
    assert report.capital_used == report.entry_notional
    assert report.exit_notional == abs(exit_price * quantity)
    assert report.balance_after == report.balance_before + report.net_pnl
    assert report.roi_percent == report.net_pnl / report.entry_notional * Decimal("100")
    assert report.currency == "USDT"


@pytest.mark.parametrize("case", range(400))
def test_replay_ordering_and_summary_determinism_matrix(case, baseline):
    first = make_trade(case * 2 + 1, exit_price=Decimal("11"), close_offset_seconds=60)
    second = make_trade(
        case * 2 + 2, side=PaperSide.SHORT, entry_price=Decimal("10"),
        exit_price=Decimal("10.5"), close_offset_seconds=59,
    )
    service = PaperAccountAccountingService()
    reports_a, summary_a = service.project(baseline, (first, second))
    reports_b, summary_b = service.project(baseline, (second, first))
    assert reports_a == reports_b
    assert summary_a == summary_b
    assert len({item.report_semantic_id for item in reports_a}) == 2
    assert reports_a[0].balance_before == baseline.initial_balance
    assert reports_a[1].balance_before == reports_a[0].balance_after
    assert summary_a.current_balance == reports_a[-1].balance_after
    assert summary_a.realized_net_pnl == sum((item.net_pnl for item in reports_a), Decimal("0"))
    result = PaperAccountingReconciliationService(service).reconcile((baseline,), (second, first))
    assert result.outcome is PaperAccountingOutcome.HEALTHY
    assert result.findings == (PaperAccountingFinding.ACCOUNTING_HEALTHY,)


def test_safe_report_rendering(identity):
    report = PaperTradeReportingService().project(identity, make_trade(2001), Decimal("100"))
    rendered = render_paper_trade_report(report)
    assert "PAPER TRADE REPORT" in rendered
    assert "Capital used / Entry notional" in rendered
    assert "Gross PnL" in rendered and "Net PnL" in rendered
    assert "DATABASE_URL" not in rendered and "password" not in rendered.lower()

