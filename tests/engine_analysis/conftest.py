from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import sin

import pytest

from app.engine_analysis import EngineAnalysisCandle
from app.engine_market_data.candle import Candle
from app.engine_market_data.market_data_snapshot import MarketDataSnapshot


@pytest.fixture
def candle_factory():
    def build(kind: str = "up", count: int = 120) -> list[EngineAnalysisCandle]:
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        result: list[EngineAnalysisCandle] = []
        for index in range(count):
            if kind == "up":
                price = 100.0 + index * 0.4
                close = price + 0.2
            elif kind == "down":
                price = 200.0 - index * 0.4
                close = price - 0.2
            elif kind == "range":
                price = 100.0 + 3.0 * sin(index / 3.0)
                close = price + (0.3 if index % 2 else -0.3)
            elif kind == "unknown":
                price = 100.0 + (2.0 if index % 2 else -2.0)
                close = price + (0.3 if index % 2 else -0.3)
            else:
                raise ValueError(kind)
            result.append(
                EngineAnalysisCandle(
                    timestamp=(start + timedelta(minutes=15 * index)).isoformat(),
                    open=price,
                    high=max(price, close) + 0.5,
                    low=min(price, close) - 0.5,
                    close=close,
                    volume=10.0 + index % 3,
                )
            )
        return result

    return build


@pytest.fixture
def market_snapshot_factory():
    def build(*, count: int = 4, timeframe: str = "1m", closed_until_ms: int | None = None):
        duration = 3_600_000 if timeframe == "1h" else 60_000
        rows = [
            Candle(
                symbol="BTCUSDT",
                timeframe=timeframe,
                open_time_ms=index * duration,
                close_time_ms=(index + 1) * duration - 1,
                open=100 + index,
                high=102 + index,
                low=99 + index,
                close=101 + index,
                volume=10 + index,
                is_closed=True,
                source="test",
            )
            for index in range(count)
        ]
        boundary = rows[-1].close_time_ms if closed_until_ms is None and rows else int(closed_until_ms or 0)
        return MarketDataSnapshot(
            symbol="BTCUSDT",
            timeframe=timeframe,
            closed_until_ms=boundary,
            candles=rows,
            source="test",
            has_gaps=False,
            future_bars_used=False,
            health_status="OK",
            enough_data=True,
        )

    return build
