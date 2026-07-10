from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from app.market_reader.candle_window import CandleWindow
from app.market_reader.market_reader import (
    MarketReaderConfig,
    MarketReaderOrchestrator,
    MarketReaderPipelineResult,
    TechnicalContextComposerInput,
)
from app.market_reader.schemas import (
    DirectionalBias,
    MarketAnalysisResult,
    MarketRegime,
    TradeSignal,
    TrendStrength,
)


def _window(rows: list[dict[str, Any]], *, symbol: str = "BTCUSDT", interval: str = "15m") -> CandleWindow:
    candles: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        open_price = float(row.get("open", row["close"]))
        close_price = float(row["close"])
        high = float(row.get("high", max(open_price, close_price) + 1.0))
        low = float(row.get("low", min(open_price, close_price) - 1.0))
        candles.append(
            {
                "open_time": datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=15 * index),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close_price,
                "volume": float(row.get("volume", 10.0)),
            }
        )
    return CandleWindow.from_candles(symbol=symbol, interval=interval, candles=candles)


def _sample_window(size: int = 36) -> CandleWindow:
    rows: list[dict[str, Any]] = []
    close = 100.0
    for index in range(size):
        close += 0.35
        pullback = 1.0 if index % 6 == 3 else 0.0
        rows.append(
            {
                "open": close - 0.20,
                "high": close + 1.00 + pullback,
                "low": close - 1.20 - pullback,
                "close": close,
                "volume": 10.0 + index,
            }
        )
    return _window(rows)


class RecordingMorphologyAnalyzer:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def analyze_window(self, window: CandleWindow) -> tuple[SimpleNamespace, ...]:
        self.calls.append("morphology")
        return (SimpleNamespace(reason_codes=("MORPHOLOGY_READY",)),)


class RecordingSwingDetector:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def detect(self, window: CandleWindow) -> tuple[SimpleNamespace, ...]:
        self.calls.append("swing")
        return (
            SimpleNamespace(point_type="HIGH", index=1, price=110.0, reason_codes=("SWING_HIGH",)),
            SimpleNamespace(point_type="LOW", index=0, price=100.0, reason_codes=("SWING_LOW",)),
        )

    @staticmethod
    def highs(points: tuple[SimpleNamespace, ...]) -> tuple[SimpleNamespace, ...]:
        return tuple(point for point in points if point.point_type == "HIGH")

    @staticmethod
    def lows(points: tuple[SimpleNamespace, ...]) -> tuple[SimpleNamespace, ...]:
        return tuple(point for point in points if point.point_type == "LOW")


class RecordingTrendAnalyzer:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def analyze(
        self,
        *,
        swing_highs: tuple[SimpleNamespace, ...],
        swing_lows: tuple[SimpleNamespace, ...],
        tolerance_pct: float,
    ) -> SimpleNamespace:
        self.calls.append("trend")
        assert len(swing_highs) == 1
        assert len(swing_lows) == 1
        assert tolerance_pct == pytest.approx(0.01)
        return SimpleNamespace(direction="UP", strength_score=0.80, reason_codes=("UP_TREND_STRUCTURE",))


class RecordingRangeAnalyzer:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def analyze(self, window: CandleWindow, **kwargs: Any) -> SimpleNamespace:
        self.calls.append("range")
        assert kwargs["lookback"] == 12
        return SimpleNamespace(
            classification="NOT_RANGE",
            range_score=0.20,
            support_level=99.0,
            resistance_level=111.0,
            reason_codes=("NO_RANGE_STRUCTURE",),
        )


class RecordingBreakoutAnalyzer:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def analyze(self, window: CandleWindow, **kwargs: Any) -> SimpleNamespace:
        self.calls.append("breakout")
        assert kwargs["range_result"].support_level == 99.0
        assert kwargs["lookback"] == 12
        return SimpleNamespace(classification="NO_BREAKOUT", reason_codes=("NO_CLOSE_BREAKOUT",))


class RecordingTechnicalAnalyzer:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def analyze(self, window: CandleWindow, **kwargs: Any) -> SimpleNamespace:
        self.calls.append("technical")
        assert kwargs["fast_ema_period"] == 5
        assert kwargs["slow_ema_period"] == 9
        return SimpleNamespace(
            ema_direction="UP",
            price_ema_position="ABOVE_FAST_ABOVE_SLOW",
            technical_score=0.90,
            reason_codes=("EMA_TREND_UP", "PRICE_ABOVE_EMAS"),
        )


class RecordingComposer:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def compose(self, **kwargs: Any) -> MarketAnalysisResult:
        self.calls.append("composer")
        assert kwargs["symbol"] == "BTCUSDT"
        assert kwargs["interval"] == "15m"
        assert kwargs["technical_context"].technical_bias == DirectionalBias.BULLISH
        return MarketAnalysisResult(
            symbol=kwargs["symbol"],
            interval=kwargs["interval"],
            market_regime=MarketRegime.UP,
            directional_bias=DirectionalBias.BULLISH,
            confidence=0.70,
            trend_strength=TrendStrength.MODERATE,
            reason_codes=("MARKET_REGIME_COMPOSED",),
        )


def test_market_reader_orchestrator_runs_components_in_order() -> None:
    calls: list[str] = []
    window = _sample_window()

    result = MarketReaderOrchestrator(
        morphology_analyzer=RecordingMorphologyAnalyzer(calls),
        swing_detector=RecordingSwingDetector(calls),
        trend_structure_analyzer=RecordingTrendAnalyzer(calls),
        range_structure_analyzer=RecordingRangeAnalyzer(calls),
        breakout_retest_analyzer=RecordingBreakoutAnalyzer(calls),
        technical_context_analyzer=RecordingTechnicalAnalyzer(calls),
        market_regime_composer=RecordingComposer(calls),
    ).analyze_detailed(
        window,
        config=MarketReaderConfig(
            trend_tolerance_pct=0.01,
            range_lookback=12,
            breakout_lookback=12,
            fast_ema_period=5,
            slow_ema_period=9,
            atr_period=5,
            technical_slope_lookback=2,
        ),
    )

    assert calls == [
        "morphology",
        "swing",
        "trend",
        "range",
        "breakout",
        "technical",
        "composer",
    ]
    assert isinstance(result, MarketReaderPipelineResult)
    assert result.final_result.market_regime == MarketRegime.UP
    assert result.technical_context_for_composer.technical_bias == DirectionalBias.BULLISH
    assert "MARKET_READER_ORCHESTRATED" in result.final_result.reason_codes
    assert result.final_result.trade_signal == TradeSignal.NOT_EVALUATED
    assert result.final_result.safe_for_runtime_trading is False


def test_market_reader_analyze_returns_final_result_only() -> None:
    window = _sample_window()

    result = MarketReaderOrchestrator().analyze(
        window,
        config=MarketReaderConfig(
            fast_ema_period=5,
            slow_ema_period=9,
            atr_period=5,
            technical_slope_lookback=2,
        ),
    )

    assert isinstance(result, MarketAnalysisResult)
    assert result.symbol == "BTCUSDT"
    assert result.interval == "15m"
    assert result.trade_signal == TradeSignal.NOT_EVALUATED
    assert result.safe_for_runtime_trading is False
    assert "MARKET_READER_ORCHESTRATED" in result.reason_codes


def test_market_reader_detailed_result_can_be_serialized_to_dict() -> None:
    window = _sample_window()

    result = MarketReaderOrchestrator().analyze_detailed(
        window,
        config=MarketReaderConfig(
            fast_ema_period=5,
            slow_ema_period=9,
            atr_period=5,
            technical_slope_lookback=2,
        ),
    )

    payload = result.to_dict()

    assert payload["final_result"]["symbol"] == "BTCUSDT"
    assert payload["final_result"]["trade_signal"] == "NOT_EVALUATED"
    assert payload["final_result"]["safe_for_runtime_trading"] is False
    assert "trend_structure" in payload
    assert "range_structure" in payload
    assert "breakout_retest" in payload
    assert "technical_context" in payload
    assert "technical_context_for_composer" in payload


@pytest.mark.parametrize(
    ("ema_direction", "price_position", "expected_bias"),
    [
        ("UP", "ABOVE_FAST_ABOVE_SLOW", DirectionalBias.BULLISH),
        ("DOWN", "BELOW_FAST_BELOW_SLOW", DirectionalBias.BEARISH),
        ("FLAT", "AROUND_EMAS", DirectionalBias.NEUTRAL),
        ("UNKNOWN", "UNKNOWN", DirectionalBias.UNKNOWN),
    ],
)
def test_market_reader_derives_technical_bias_for_composer(
    ema_direction: str,
    price_position: str,
    expected_bias: DirectionalBias,
) -> None:
    calls: list[str] = []

    class TechnicalAnalyzer:
        def analyze(self, window: CandleWindow, **kwargs: Any) -> SimpleNamespace:
            return SimpleNamespace(
                ema_direction=ema_direction,
                price_ema_position=price_position,
                technical_score=0.5,
                reason_codes=("TECHNICAL_CONTEXT",),
            )

    class Composer:
        def compose(self, **kwargs: Any) -> MarketAnalysisResult:
            calls.append(kwargs["technical_context"].technical_bias.value)
            return MarketAnalysisResult(
                symbol=kwargs["symbol"],
                interval=kwargs["interval"],
                market_regime=MarketRegime.UNKNOWN,
                directional_bias=DirectionalBias.UNKNOWN,
                confidence=0.0,
                trend_strength=TrendStrength.UNKNOWN,
                reason_codes=("MARKET_REGIME_COMPOSED",),
            )

    MarketReaderOrchestrator(
        technical_context_analyzer=TechnicalAnalyzer(),
        market_regime_composer=Composer(),
    ).analyze(
        _sample_window(),
        config=MarketReaderConfig(
            fast_ema_period=5,
            slow_ema_period=9,
            atr_period=5,
            technical_slope_lookback=2,
        ),
    )

    assert calls == [expected_bias.value]


def test_technical_context_composer_input_rejects_invalid_score() -> None:
    with pytest.raises(ValueError, match="technical_score"):
        TechnicalContextComposerInput(
            technical_bias=DirectionalBias.UNKNOWN,
            technical_score=1.01,
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"trend_tolerance_pct": -0.01},
        {"range_lookback": 0},
        {"range_min_size": 0},
        {"range_boundary_tolerance_pct": -0.01},
        {"range_max_width_pct": 0.0},
        {"range_max_close_drift_ratio": 0.0},
        {"range_min_boundary_touch_count": 0},
        {"breakout_lookback": 0},
        {"breakout_tolerance_pct": -0.01},
        {"retest_tolerance_pct": -0.01},
        {"breakout_min_follow_through_count": -1},
        {"fast_ema_period": 0},
        {"slow_ema_period": 0},
        {"atr_period": 0},
        {"technical_slope_lookback": 0},
        {"flat_slope_tolerance_pct": -0.01},
        {"around_ema_tolerance_pct": -0.01},
        {"high_volatility_atr_pct": 0.0},
        {"low_volatility_atr_pct": -0.01},
        {"fast_ema_period": 9, "slow_ema_period": 9},
        {"low_volatility_atr_pct": 0.05, "high_volatility_atr_pct": 0.03},
    ],
)
def test_market_reader_config_rejects_invalid_values(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        MarketReaderConfig(**kwargs)
