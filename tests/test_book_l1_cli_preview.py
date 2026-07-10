from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from app.market_reader.cli_preview import (
    MarketReaderPreview,
    MarketReaderPreviewBuilder,
    build_market_reader_preview_payload,
)
from app.market_reader.schemas import (
    DirectionalBias,
    MarketAnalysisResult,
    MarketRegime,
    TrendStrength,
)


@dataclass(frozen=True)
class DummyCandle:
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


def _candle(index: int, close: float = 100.0) -> DummyCandle:
    return DummyCandle(
        open_time=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=15 * index),
        open=close - 0.5,
        high=close + 1.0,
        low=close - 1.0,
        close=close,
        volume=10.0,
    )


def _candles(count: int) -> list[DummyCandle]:
    return [_candle(index, close=100.0 + index) for index in range(count)]


def _analysis() -> MarketAnalysisResult:
    return MarketAnalysisResult(
        symbol="BTCUSDT",
        interval="15m",
        market_regime=MarketRegime.UP,
        directional_bias=DirectionalBias.BULLISH,
        confidence=0.72,
        trend_strength=TrendStrength.MODERATE,
        reason_codes=("UP_TREND_STRUCTURE", "PRICE_ABOVE_EMA"),
    )


class DummyReader:
    def __init__(self) -> None:
        self.last_window_size: int | None = None

    def analyze(self, window: Any) -> MarketAnalysisResult:
        self.last_window_size = window.size
        return _analysis()


class DummyRepository:
    def __init__(self, candles: list[DummyCandle]) -> None:
        self._candles = candles
        self.calls: list[dict[str, object]] = []

    def get_last_n(self, *, symbol: str, interval: str, limit: int) -> list[DummyCandle]:
        self.calls.append({"symbol": symbol, "interval": interval, "limit": limit})
        return self._candles[-limit:]


def test_market_reader_preview_to_dict_uses_plain_values() -> None:
    preview = MarketReaderPreview(
        symbol="BTCUSDT",
        interval="15m",
        requested_limit=100,
        candle_count=50,
        first_open_time="2026-01-01T00:00:00+00:00",
        last_open_time="2026-01-01T12:15:00+00:00",
        analysis=_analysis(),
    )

    assert preview.to_dict() == {
        "symbol": "BTCUSDT",
        "interval": "15m",
        "requested_limit": 100,
        "candle_count": 50,
        "first_open_time": "2026-01-01T00:00:00+00:00",
        "last_open_time": "2026-01-01T12:15:00+00:00",
        "analysis": {
            "symbol": "BTCUSDT",
            "interval": "15m",
            "market_regime": "UP",
            "directional_bias": "BULLISH",
            "confidence": 0.72,
            "trend_strength": "MODERATE",
            "reason_codes": ["UP_TREND_STRUCTURE", "PRICE_ABOVE_EMA"],
            "trade_signal": "NOT_EVALUATED",
            "safe_for_runtime_trading": False,
        },
    }


def test_market_reader_preview_builder_runs_reader_on_candle_window() -> None:
    reader = DummyReader()

    preview = MarketReaderPreviewBuilder(reader=reader, min_candles=5).build(
        symbol="BTCUSDT",
        interval="15m",
        candles=_candles(6),
        requested_limit=6,
    )

    assert preview.symbol == "BTCUSDT"
    assert preview.interval == "15m"
    assert preview.requested_limit == 6
    assert preview.candle_count == 6
    assert preview.first_open_time == "2026-01-01T00:00:00+00:00"
    assert preview.last_open_time == "2026-01-01T01:15:00+00:00"
    assert preview.analysis.market_regime == MarketRegime.UP
    assert reader.last_window_size == 6


def test_market_reader_preview_builder_rejects_invalid_min_candles() -> None:
    with pytest.raises(ValueError, match="min_candles"):
        MarketReaderPreviewBuilder(reader=DummyReader(), min_candles=0)


def test_market_reader_preview_builder_rejects_invalid_requested_limit() -> None:
    with pytest.raises(ValueError, match="requested_limit"):
        MarketReaderPreviewBuilder(reader=DummyReader(), min_candles=1).build(
            symbol="BTCUSDT",
            interval="15m",
            candles=_candles(1),
            requested_limit=0,
        )


def test_market_reader_preview_builder_rejects_not_enough_candles() -> None:
    with pytest.raises(ValueError, match="not enough candles"):
        MarketReaderPreviewBuilder(reader=DummyReader(), min_candles=5).build(
            symbol="BTCUSDT",
            interval="15m",
            candles=_candles(2),
            requested_limit=2,
        )


def test_market_reader_preview_builder_rejects_reader_with_wrong_return_type() -> None:
    class BadReader:
        def analyze(self, window: Any) -> dict[str, object]:
            return {"market_regime": "UP"}

    with pytest.raises(ValueError, match="MarketReader must return MarketAnalysisResult"):
        MarketReaderPreviewBuilder(reader=BadReader(), min_candles=1).build(
            symbol="BTCUSDT",
            interval="15m",
            candles=_candles(1),
            requested_limit=1,
        )


def test_build_market_reader_preview_payload_reads_repository_and_returns_dict() -> None:
    repository = DummyRepository(_candles(10))

    payload = build_market_reader_preview_payload(
        symbol="ETHUSDT",
        interval="15m",
        limit=7,
        min_candles=5,
        candle_repository=repository,
        reader=DummyReader(),
    )

    assert repository.calls == [{"symbol": "ETHUSDT", "interval": "15m", "limit": 7}]
    assert payload["symbol"] == "ETHUSDT"
    assert payload["interval"] == "15m"
    assert payload["requested_limit"] == 7
    assert payload["candle_count"] == 7
    assert isinstance(payload["analysis"], dict)


def test_build_market_reader_preview_payload_rejects_invalid_limit() -> None:
    with pytest.raises(ValueError, match="limit"):
        build_market_reader_preview_payload(
            symbol="BTCUSDT",
            interval="15m",
            limit=0,
            candle_repository=DummyRepository(_candles(1)),
            reader=DummyReader(),
            min_candles=1,
        )
