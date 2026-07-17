from types import SimpleNamespace

from app.engine_market_data.candle import Candle
from app.engine_market_data.timeframe import timeframe_to_milliseconds
from app.engine_orchestrator.orchestrator_config import OrchestratorConfig


BOUNDARY = 1_800_000_000_000


def config(**changes):
    values = dict(
        symbols=("BTCUSDT",), required_timeframes=("1m", "5m", "15m", "1h", "4h", "1d"),
        minimum_windows={key: 1 for key in ("1m", "5m", "15m", "1h", "4h", "1d")},
        health_report_interval_seconds=1,
    )
    values.update(changes)
    return OrchestratorConfig(**values)


def candle(timeframe="15m", boundary=BOUNDARY):
    duration = timeframe_to_milliseconds(timeframe)
    context_boundary = boundary // duration * duration
    open_ms = context_boundary - duration
    return Candle(
        symbol="BTCUSDT", timeframe=timeframe, open_time_ms=open_ms,
        close_time_ms=context_boundary - 1, open=100, high=102, low=99, close=101,
        volume=10, is_closed=True, source="postgres",
    )


class CandleRepo:
    def __init__(self, enough=True):
        self.enough = enough
        self.calls = []

    def get_candles(self, symbol, timeframe, **kwargs):
        self.calls.append((symbol, timeframe, kwargs))
        return [candle(timeframe)] if self.enough else []

    def get_latest_closed_candle(self, symbol, timeframe):
        return candle(timeframe)


def component(value):
    return lambda _: value


def outputs(*, analysis_action="NO_ACTION", setup_status="NO_SETUP", strategy_status="NO_DECISION",
            risk_status="NO_DECISION", paper_status="NO_PLAN"):
    return (
        SimpleNamespace(status="ANALYZED", action=analysis_action, reason_codes=[], future_bars_used=False),
        SimpleNamespace(status=setup_status, reason_codes=[], future_bars_used=False, is_trade_signal=False),
        SimpleNamespace(decision_status=strategy_status, decision_reasons=[], future_bars_used=False,
                        is_trade_signal=False, is_executable=False),
        SimpleNamespace(risk_status=risk_status, risk_reasons=[], future_bars_used=False,
                        is_trade_signal=False, is_executable=False, order_approved=False,
                        execution_approved=False, position_size_approved=False),
        SimpleNamespace(paper_status=paper_status, plan_reasons=[], future_bars_used=False,
                        is_trade_signal=False, is_executable=False, order_approved=False,
                        execution_approved=False, position_opened=False, position_size_approved=False),
    )
