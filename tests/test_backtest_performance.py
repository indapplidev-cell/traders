from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.analytics.backtest_performance import BacktestPerformanceService
from app.db.models import BacktestSession, BacktestSessionMetric


def _create_backtest_session(sqlite_session, *, status: str = "COMPLETED") -> BacktestSession:
    item = BacktestSession(
        strategy_name="simple_trend",
        strategy_version="1.0",
        symbol="BTCUSDT",
        interval="15m",
        status=status,
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        candles_requested=300,
        candles_used=300,
        initial_cash=Decimal("1000"),
        final_equity=Decimal("1005"),
        last_error=None,
    )
    sqlite_session.add(item)
    sqlite_session.commit()
    return item


def test_session_without_metrics_returns_unavailable_report(sqlite_session) -> None:
    item = _create_backtest_session(sqlite_session)

    report = BacktestPerformanceService(sqlite_session).get_backtest_performance(item.id)

    assert report.session_id == item.id
    assert report.equity_metrics.data_quality == "UNAVAILABLE"
    assert report.equity_metrics.unavailable_reason == "No metrics recorded"


def test_save_or_update_metrics_does_not_create_duplicate(sqlite_session) -> None:
    item = _create_backtest_session(sqlite_session)
    service = BacktestPerformanceService(sqlite_session)

    service.save_or_update_metrics(session_id=item.id)
    metric = sqlite_session.execute(
        select(BacktestSessionMetric).where(BacktestSessionMetric.backtest_session_id == item.id)
    ).scalar_one()
    metric.total_trades = 2
    metric.total_pnl = Decimal("7")
    metric.return_pct = Decimal("0.7")
    metric.data_quality = "COMPLETE"

    first = service.get_backtest_performance(item.id)
    second = service.save_or_update_metrics(session_id=item.id)

    metrics = sqlite_session.execute(
        select(BacktestSessionMetric).where(BacktestSessionMetric.backtest_session_id == item.id)
    ).scalars().all()

    assert first.session_id == second.session_id
    assert len(metrics) == 1
    assert metrics[0].total_trades == 2
    assert metrics[0].total_pnl == Decimal("7")


def test_list_backtest_performance_empty_db_returns_empty_list(sqlite_session) -> None:
    items = BacktestPerformanceService(sqlite_session).list_backtest_performance(limit=10)

    assert items == []


def test_unknown_session_id_returns_clear_error(sqlite_session) -> None:
    with pytest.raises(ValueError, match="Backtest session 999 not found"):
        BacktestPerformanceService(sqlite_session).get_backtest_performance(999)
