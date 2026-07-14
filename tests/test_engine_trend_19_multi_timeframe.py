from dataclasses import replace

import pytest

from app.market_reader.engine_trend.engine import EngineTrendFacadeOutput
from app.market_reader.engine_trend.multi_timeframe import (
    TimeframeAlignment,
    run_multi_timeframe_engine_trend,
)
from app.market_reader.engine_trend.schemas import EngineTrendCandle, EngineTrendRegime


def candles(interval_minutes: int, direction: int, count: int = 96) -> list[EngineTrendCandle]:
    items = []
    for index in range(count):
        close = 100 + direction * index * 0.5 + (index % 4) * 0.1
        total_minutes = index * interval_minutes
        day = 1 + total_minutes // 1440
        minute_of_day = total_minutes % 1440
        items.append(
            EngineTrendCandle(
                f"2026-01-{day:02d}T{minute_of_day // 60:02d}:{minute_of_day % 60:02d}:00Z",
                close - direction * 0.2,
                close + 0.7,
                close - 0.7,
                close,
                100 + index,
            )
        )
    return items


def test_multi_timeframe_requires_decision_interval() -> None:
    with pytest.raises(ValueError):
        run_multi_timeframe_engine_trend(
            "TEST", {"1h": candles(60, 1)}, decision_interval="15m"
        )


def test_multi_timeframe_returns_one_safe_answer() -> None:
    result = run_multi_timeframe_engine_trend(
        "TEST",
        {"15m": candles(15, 1), "1h": candles(60, 1), "4h": candles(240, 1)},
        decision_interval="15m",
    )
    assert result.market_regime in set(EngineTrendRegime)
    assert result.alignment in set(TimeframeAlignment)
    assert result.interval_regimes.keys() == {"15m", "1h", "4h"}
    assert result.safety.live_trading_connected is False
    assert result.to_dict()["contract_version"] == "engine_trend_mtf_v1"
