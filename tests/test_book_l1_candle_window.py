from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest

from app.market_reader.candle_window import CandleBar, CandleWindow


@dataclass(frozen=True)
class DummyCandle:
    open_time: datetime
    open: Any
    high: Any
    low: Any
    close: Any
    volume: Any


def _candle(index: int, **overrides: Any) -> DummyCandle:
    values: dict[str, Any] = {
        "open_time": datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=15 * index),
        "open": Decimal("100.0") + Decimal(index),
        "high": Decimal("105.0") + Decimal(index),
        "low": Decimal("95.0") + Decimal(index),
        "close": Decimal("102.0") + Decimal(index),
        "volume": Decimal("10.0") + Decimal(index),
    }
    values.update(overrides)
    return DummyCandle(**values)


def test_candle_bar_converts_decimal_values_to_float() -> None:
    bar = CandleBar.from_candle(_candle(0))

    assert bar.open_time == datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert bar.open == 100.0
    assert bar.high == 105.0
    assert bar.low == 95.0
    assert bar.close == 102.0
    assert bar.volume == 10.0


def test_candle_window_preserves_input_order_and_exposes_series() -> None:
    window = CandleWindow.from_candles(
        symbol="BTCUSDT",
        interval="15m",
        candles=[_candle(0), _candle(1), _candle(2)],
        min_size=3,
    )

    assert window.symbol == "BTCUSDT"
    assert window.interval == "15m"
    assert window.size == 3
    assert window.first_open_time == datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert window.last_open_time == datetime(2026, 1, 1, 0, 30, tzinfo=timezone.utc)
    assert window.opens == (100.0, 101.0, 102.0)
    assert window.highs == (105.0, 106.0, 107.0)
    assert window.lows == (95.0, 96.0, 97.0)
    assert window.closes == (102.0, 103.0, 104.0)
    assert window.volumes == (10.0, 11.0, 12.0)
    assert window.latest.close == 104.0


def test_candle_window_accepts_mapping_candles() -> None:
    source = {
        "open_time": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "open": "100.0",
        "high": "105.0",
        "low": "95.0",
        "close": "102.0",
        "volume": "10.0",
    }

    window = CandleWindow.from_candles(symbol="ETHUSDT", interval="15m", candles=[source])

    assert window.closes == (102.0,)


def test_candle_window_rejects_too_few_candles() -> None:
    with pytest.raises(ValueError, match="not enough candles"):
        CandleWindow.from_candles(
            symbol="BTCUSDT",
            interval="15m",
            candles=[_candle(0)],
            min_size=2,
        )


@pytest.mark.parametrize(
    "bad_candles",
    [
        [_candle(1), _candle(0)],
        [_candle(0), _candle(0)],
    ],
)
def test_candle_window_rejects_non_increasing_open_time(bad_candles: list[DummyCandle]) -> None:
    with pytest.raises(ValueError, match="strictly increasing open_time"):
        CandleWindow.from_candles(
            symbol="BTCUSDT",
            interval="15m",
            candles=bad_candles,
            min_size=2,
        )


def test_candle_bar_rejects_high_lower_than_low() -> None:
    with pytest.raises(ValueError, match="high"):
        CandleBar.from_candle(_candle(0, high=Decimal("90.0"), low=Decimal("95.0")))


def test_candle_bar_rejects_open_outside_high_low_range() -> None:
    with pytest.raises(ValueError, match="open"):
        CandleBar.from_candle(_candle(0, open=Decimal("110.0")))


def test_candle_bar_rejects_close_outside_high_low_range() -> None:
    with pytest.raises(ValueError, match="close"):
        CandleBar.from_candle(_candle(0, close=Decimal("90.0")))


def test_candle_bar_rejects_negative_volume() -> None:
    with pytest.raises(ValueError, match="volume"):
        CandleBar.from_candle(_candle(0, volume=Decimal("-1.0")))


def test_candle_bar_rejects_missing_required_field() -> None:
    with pytest.raises(ValueError, match="missing field: close"):
        CandleBar.from_candle(
            {
                "open_time": datetime(2026, 1, 1, tzinfo=timezone.utc),
                "open": 100.0,
                "high": 105.0,
                "low": 95.0,
                "volume": 10.0,
            }
        )
