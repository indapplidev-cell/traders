from __future__ import annotations

from dataclasses import replace

from app.engine_analysis.analysis_snapshot_store import AnalysisSnapshotStore
from app.engine_analysis.market_data_adapter import MarketDataAdapter
from app.engine_analysis.online_config import OnlineAnalysisConfig
from app.engine_analysis.online_runner import OnlineAnalysisRunner
from app.engine_market_data.candle import Candle
from app.engine_market_data.market_data_snapshot import MarketDataSnapshot


def candles(count: int = 3, *, symbol: str = "BTCUSDT", timeframe: str = "1m") -> list[Candle]:
    result = []
    for index in range(count):
        opened = index * 60_000
        price = 100 + index
        result.append(Candle(
            symbol=symbol, timeframe=timeframe, open_time_ms=opened,
            close_time_ms=opened + 59_999, open=price, high=price + 2,
            low=price - 1, close=price + 1, volume=10 + index,
            is_closed=True, source="test",
        ))
    return result


def snapshot(
    count: int = 3,
    *,
    health: str = "OK",
    has_gaps: bool = False,
    enough_data: bool = True,
    symbol: str = "BTCUSDT",
    timeframe: str = "1m",
) -> MarketDataSnapshot:
    rows = candles(count, symbol=symbol, timeframe=timeframe)
    return MarketDataSnapshot(
        symbol=symbol, timeframe=timeframe,
        closed_until_ms=rows[-1].close_time_ms if rows else 0,
        candles=rows, source="test", has_gaps=has_gaps,
        future_bars_used=False, health_status=health, enough_data=enough_data,
    )


class PipelineSpy:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.calls = 0
        self.error = error

    def __call__(self, symbol, timeframe, analysis_candles):
        self.calls += 1
        if self.error:
            raise self.error
        return {
            "model_regime": "UP",
            "model_confidence": 0.8,
            "model_final_action": "NO_ACTION",
            "model_impulse_phase": "IMPULSE_DETECTED",
            "model_entry_quality": "ACCEPTABLE",
            "model_reason_codes": ["TEST_ANALYSIS"],
            "analysis_context": {"candle_count": len(analysis_candles)},
            "human_explanation": "Closed-window analysis.",
        }


def runner(*, pipeline=None, store=None, **config_values):
    config = OnlineAnalysisConfig(required_history_candles=3, max_snapshot_age_ms=0, **config_values)
    active_store = store or AnalysisSnapshotStore()
    active_pipeline = pipeline or PipelineSpy()
    return OnlineAnalysisRunner(config, MarketDataAdapter(), active_store, active_pipeline)
