from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.analytics.session_comparison import SessionComparisonService
from app.db.models import BacktestSession, BacktestSessionMetric, RunnerSession, RunnerSessionMetric


def _runner_session(
    sqlite_session,
    *,
    strategy_name: str = "simple_trend",
    symbol: str = "BTCUSDT",
    interval: str = "15m",
    data_quality: str = "COMPLETE",
    total_pnl: Decimal | None = Decimal("10"),
) -> RunnerSession:
    now = datetime.now(UTC)
    item = RunnerSession(
        strategy_name=strategy_name,
        strategy_version="1.0",
        symbol=symbol,
        interval=interval,
        status="STOPPED",
        started_at=now,
        stopped_at=now,
        ticks_requested=3,
        ticks_completed=3,
        last_error=None,
    )
    sqlite_session.add(item)
    sqlite_session.flush()
    sqlite_session.add(
        RunnerSessionMetric(
            runner_session_id=item.id,
            ticks_requested=3,
            ticks_completed=3,
            audit_ticks_count=3,
            error_ticks_count=0,
            success_rate=1.0,
            strategy_buy_count=1,
            strategy_sell_count=1,
            strategy_hold_count=1,
            final_buy_count=1,
            final_sell_count=1,
            final_hold_count=1,
            risk_approved_count=2,
            risk_rejected_count=1,
            risk_rejection_rate=0.3333,
            execution_executed_count=2,
            execution_skipped_count=1,
            average_confidence=Decimal("0.70"),
            min_confidence=Decimal("0.55"),
            max_confidence=Decimal("0.80"),
            candles_used_min=300,
            candles_used_max=300,
            candles_used_average=300.0,
            realized_pnl=total_pnl,
            unrealized_pnl=Decimal("0") if total_pnl is not None else None,
            total_pnl=total_pnl,
            return_pct=Decimal("1.0") if total_pnl is not None else None,
            data_quality=data_quality,
            unavailable_reason=None if data_quality != "UNAVAILABLE" else "missing data",
        )
    )
    sqlite_session.commit()
    return item


def _backtest_session(
    sqlite_session,
    *,
    strategy_name: str = "simple_trend",
    symbol: str = "BTCUSDT",
    interval: str = "15m",
    data_quality: str = "COMPLETE",
    total_pnl: Decimal | None = Decimal("8"),
) -> BacktestSession:
    now = datetime.now(UTC)
    item = BacktestSession(
        strategy_name=strategy_name,
        strategy_version="1.0",
        symbol=symbol,
        interval=interval,
        status="COMPLETED",
        started_at=now,
        finished_at=now,
        candles_requested=300,
        candles_used=300,
        initial_cash=Decimal("1000"),
        final_equity=Decimal("1008"),
        last_error=None,
    )
    sqlite_session.add(item)
    sqlite_session.flush()
    sqlite_session.add(
        BacktestSessionMetric(
            backtest_session_id=item.id,
            candles_used=300,
            strategy_buy_count=1,
            strategy_sell_count=1,
            strategy_hold_count=10,
            executed_buy_count=1,
            executed_sell_count=1,
            skipped_count=0,
            total_trades=1,
            winning_trades=1,
            losing_trades=0,
            win_rate=Decimal("100"),
            initial_cash=Decimal("1000"),
            final_equity=Decimal("1008"),
            realized_pnl=total_pnl,
            unrealized_pnl=Decimal("0") if total_pnl is not None else None,
            total_pnl=total_pnl,
            return_pct=Decimal("0.8") if total_pnl is not None else None,
            max_drawdown=Decimal("2.5"),
            average_confidence=None,
            min_confidence=None,
            max_confidence=None,
            data_quality=data_quality,
            unavailable_reason=None if data_quality != "UNAVAILABLE" else "missing data",
        )
    )
    sqlite_session.commit()
    return item


def test_runner_vs_runner_is_comparable(sqlite_session) -> None:
    left = _runner_session(sqlite_session)
    right = _runner_session(sqlite_session, total_pnl=Decimal("12"))

    result = SessionComparisonService(sqlite_session).compare("runner", left.id, "runner", right.id)

    assert result.comparable is True
    assert result.same_strategy is True
    assert result.same_symbol is True
    assert result.same_interval is True


def test_backtest_vs_backtest_is_comparable(sqlite_session) -> None:
    left = _backtest_session(sqlite_session)
    right = _backtest_session(sqlite_session, total_pnl=Decimal("9"))

    result = SessionComparisonService(sqlite_session).compare("backtest", left.id, "backtest", right.id)

    assert result.comparable is True
    assert result.pnl_delta == Decimal("-1")


def test_runner_vs_backtest_adds_execution_mode_warning(sqlite_session) -> None:
    left = _runner_session(sqlite_session)
    right = _backtest_session(sqlite_session)

    result = SessionComparisonService(sqlite_session).compare("runner", left.id, "backtest", right.id)

    assert "RUNNER and BACKTEST are different execution modes" in result.warnings


def test_different_strategy_makes_comparison_not_comparable(sqlite_session) -> None:
    left = _runner_session(sqlite_session, strategy_name="simple_trend")
    right = _backtest_session(sqlite_session, strategy_name="other_strategy")

    result = SessionComparisonService(sqlite_session).compare("runner", left.id, "backtest", right.id)

    assert result.comparable is False
    assert "Different strategies" in result.warnings


def test_different_symbol_makes_comparison_not_comparable(sqlite_session) -> None:
    left = _runner_session(sqlite_session, symbol="BTCUSDT")
    right = _backtest_session(sqlite_session, symbol="ETHUSDT")

    result = SessionComparisonService(sqlite_session).compare("runner", left.id, "backtest", right.id)

    assert result.comparable is False
    assert "Different symbols" in result.warnings


def test_different_interval_makes_comparison_not_comparable(sqlite_session) -> None:
    left = _runner_session(sqlite_session, interval="15m")
    right = _backtest_session(sqlite_session, interval="1h")

    result = SessionComparisonService(sqlite_session).compare("runner", left.id, "backtest", right.id)

    assert result.comparable is False
    assert "Different intervals" in result.warnings


def test_unavailable_data_quality_makes_comparison_not_comparable(sqlite_session) -> None:
    left = _runner_session(sqlite_session, data_quality="UNAVAILABLE")
    right = _backtest_session(sqlite_session)

    result = SessionComparisonService(sqlite_session).compare("runner", left.id, "backtest", right.id)

    assert result.comparable is False
    assert "Unavailable data quality" in result.warnings


def test_missing_pnl_does_not_break_comparison(sqlite_session) -> None:
    left = _runner_session(sqlite_session, total_pnl=None)
    right = _backtest_session(sqlite_session)

    result = SessionComparisonService(sqlite_session).compare("runner", left.id, "backtest", right.id)

    assert result.pnl_delta is None
    assert "PnL delta unavailable" in result.warnings
