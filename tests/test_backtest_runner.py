from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.backtest.backtest_result import BacktestResult
from app.backtest.backtest_runner import BacktestRunner
from app.db.models import BacktestSession, BacktestSessionMetric, Candle, PaperPosition


def _seed_candles(sqlite_session, count: int = 300) -> None:
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    sqlite_session.add_all(
        [
            Candle(
                symbol="BTCUSDT",
                interval="15m",
                open_time=now - timedelta(minutes=15 * (count - index)),
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100"),
                volume=Decimal("10"),
                close_time=now - timedelta(minutes=15 * (count - index - 1)),
            )
            for index in range(count)
        ]
    )
    sqlite_session.commit()


class FakeEngineSuccess:
    def run(self, *, symbol: str, interval: str, candles):
        _ = (symbol, interval, candles)
        return BacktestResult(
            symbol="BTCUSDT",
            interval="15m",
            candles_used=300,
            initial_balance=Decimal("1000"),
            final_balance=Decimal("1015"),
            total_pnl=Decimal("15"),
            total_pnl_pct=Decimal("1.5"),
            total_trades=2,
            winning_trades=1,
            losing_trades=1,
            winrate_pct=Decimal("50"),
            max_drawdown_pct=Decimal("2"),
            largest_win=Decimal("20"),
            largest_loss=Decimal("-5"),
            trades=[],
        )


class FakeEngineFailure:
    def run(self, *, symbol: str, interval: str, candles):
        _ = (symbol, interval, candles)
        raise RuntimeError("boom")


def test_backtest_runner_creates_completed_session_and_metrics(sqlite_session) -> None:
    _seed_candles(sqlite_session)

    result = BacktestRunner(engine=FakeEngineSuccess()).run(
        strategy_name="simple_trend",
        symbol="BTCUSDT",
        interval="15m",
        candles=300,
        initial_cash=Decimal("1000"),
    )

    session_row = sqlite_session.execute(select(BacktestSession)).scalar_one()
    metric_row = sqlite_session.execute(select(BacktestSessionMetric)).scalar_one()

    assert result.status == "COMPLETED"
    assert session_row.status == "COMPLETED"
    assert session_row.candles_used == 300
    assert metric_row.backtest_session_id == session_row.id
    assert metric_row.total_pnl == Decimal("15")


def test_backtest_runner_marks_failed_and_saves_error(sqlite_session) -> None:
    _seed_candles(sqlite_session)

    result = BacktestRunner(engine=FakeEngineFailure()).run(
        strategy_name="simple_trend",
        symbol="BTCUSDT",
        interval="15m",
        candles=300,
    )

    session_row = sqlite_session.execute(select(BacktestSession)).scalar_one()
    metric_row = sqlite_session.execute(select(BacktestSessionMetric)).scalar_one()

    assert result.status == "FAILED"
    assert result.last_error == "boom"
    assert session_row.status == "FAILED"
    assert session_row.last_error == "boom"
    assert metric_row.data_quality == "UNAVAILABLE"
    assert metric_row.unavailable_reason == "boom"


def test_backtest_runner_does_not_use_live_trading_tables(sqlite_session) -> None:
    _seed_candles(sqlite_session)

    BacktestRunner(engine=FakeEngineSuccess()).run(
        strategy_name="simple_trend",
        symbol="BTCUSDT",
        interval="15m",
        candles=300,
    )

    paper_positions_count = sqlite_session.execute(select(func.count(PaperPosition.id))).scalar_one()
    assert paper_positions_count == 0
