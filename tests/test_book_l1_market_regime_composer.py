from __future__ import annotations

from enum import Enum
from types import SimpleNamespace

import pytest

from app.market_reader.market_regime_composer import (
    MarketRegimeComponentSnapshot,
    MarketRegimeCompositionConfig,
    MarketRegimeComposer,
)
from app.market_reader.schemas import (
    DirectionalBias,
    MarketRegime,
    TradeSignal,
    TrendStrength,
)


class DummyEnum(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    RANGE = "RANGE"
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    BULLISH_BREAKOUT_RETEST = "BULLISH_BREAKOUT_RETEST"


def _trend(direction: object, strength_score: float, *reason_codes: str) -> SimpleNamespace:
    return SimpleNamespace(
        direction=direction,
        strength_score=strength_score,
        reason_codes=reason_codes,
    )


def _range(classification: object, range_score: float, *reason_codes: str) -> SimpleNamespace:
    return SimpleNamespace(
        classification=classification,
        range_score=range_score,
        reason_codes=reason_codes,
    )


def _breakout(classification: object, *reason_codes: str) -> SimpleNamespace:
    return SimpleNamespace(
        classification=classification,
        reason_codes=reason_codes,
    )


def _technical(bias: object, score: float, *reason_codes: str) -> SimpleNamespace:
    return SimpleNamespace(
        directional_bias=bias,
        technical_score=score,
        reason_codes=reason_codes,
    )


def test_composer_returns_up_when_bullish_context_dominates() -> None:
    result = MarketRegimeComposer().compose(
        symbol="BTCUSDT",
        interval="15m",
        trend_structure=_trend("UP", 0.80, "UP_TREND_STRUCTURE"),
        range_structure=_range("NOT_RANGE", 0.20, "NO_RANGE_STRUCTURE"),
        breakout_retest=_breakout("NO_BREAKOUT"),
        technical_context=_technical("BULLISH", 0.80, "PRICE_ABOVE_EMA", "EMA_SLOPE_UP"),
    )

    assert result.market_regime == MarketRegime.UP
    assert result.directional_bias == DirectionalBias.BULLISH
    assert result.trend_strength == TrendStrength.MODERATE
    assert result.confidence == pytest.approx(0.60)
    assert result.trade_signal == TradeSignal.NOT_EVALUATED
    assert result.safe_for_runtime_trading is False
    assert "MARKET_REGIME_COMPOSED" in result.reason_codes
    assert "COMPOSER_BULLISH_SCORE_DOMINANT" in result.reason_codes
    assert "UP_TREND_STRUCTURE" in result.reason_codes
    assert "PRICE_ABOVE_EMA" in result.reason_codes


def test_composer_returns_down_when_bearish_context_dominates() -> None:
    result = MarketRegimeComposer().compose(
        symbol="BTCUSDT",
        interval="15m",
        trend_structure=_trend("DOWN", 0.85, "DOWN_TREND_STRUCTURE"),
        range_structure=_range("NOT_RANGE", 0.10),
        breakout_retest=_breakout("NO_BREAKOUT"),
        technical_context=_technical("BEARISH", 0.90, "PRICE_BELOW_EMA", "EMA_SLOPE_DOWN"),
    )

    assert result.market_regime == MarketRegime.DOWN
    assert result.directional_bias == DirectionalBias.BEARISH
    assert result.confidence == pytest.approx(0.6475)
    assert result.trend_strength == TrendStrength.MODERATE
    assert "COMPOSER_BEARISH_SCORE_DOMINANT" in result.reason_codes
    assert "DOWN_TREND_STRUCTURE" in result.reason_codes


def test_composer_returns_flat_when_range_is_dominant_without_active_breakout() -> None:
    result = MarketRegimeComposer().compose(
        symbol="BTCUSDT",
        interval="15m",
        trend_structure=_trend("MIXED", 0.30, "MIXED_SWING_STRUCTURE"),
        range_structure=_range("RANGE", 0.82, "RANGE_STRUCTURE_DETECTED"),
        breakout_retest=_breakout("NO_BREAKOUT"),
        technical_context=_technical("NEUTRAL", 0.50, "PRICE_NEAR_EMA"),
    )

    assert result.market_regime == MarketRegime.FLAT
    assert result.directional_bias == DirectionalBias.NEUTRAL
    assert result.trend_strength == TrendStrength.NONE
    assert result.confidence == pytest.approx(0.82)
    assert "COMPOSER_FLAT_RANGE_DOMINANT" in result.reason_codes
    assert "RANGE_STRUCTURE_DETECTED" in result.reason_codes


def test_composer_allows_active_bullish_breakout_to_override_range_context() -> None:
    result = MarketRegimeComposer().compose(
        symbol="BTCUSDT",
        interval="15m",
        trend_structure=_trend("MIXED", 0.30, "MIXED_SWING_STRUCTURE"),
        range_structure=_range("RANGE", 0.82, "RANGE_STRUCTURE_DETECTED"),
        breakout_retest=_breakout("BULLISH_BREAKOUT_RETEST", "BULLISH_BREAKOUT_RETEST"),
        technical_context=_technical("BULLISH", 0.80, "PRICE_ABOVE_EMA"),
    )

    assert result.market_regime == MarketRegime.UP
    assert result.directional_bias == DirectionalBias.BULLISH
    assert result.confidence == pytest.approx(0.61)
    assert "COMPOSER_BULLISH_SCORE_DOMINANT" in result.reason_codes
    assert "BULLISH_BREAKOUT_RETEST" in result.reason_codes


def test_composer_returns_unknown_when_context_is_conflicting() -> None:
    result = MarketRegimeComposer().compose(
        symbol="BTCUSDT",
        interval="15m",
        trend_structure=_trend("UP", 0.80, "UP_TREND_STRUCTURE"),
        range_structure=_range("NOT_RANGE", 0.10),
        breakout_retest=_breakout("BEARISH_BREAKOUT_RETEST", "BEARISH_BREAKOUT_RETEST"),
        technical_context=_technical("NEUTRAL", 0.50),
    )

    assert result.market_regime == MarketRegime.UNKNOWN
    assert result.directional_bias == DirectionalBias.UNKNOWN
    assert result.trend_strength == TrendStrength.UNKNOWN
    assert result.confidence == 0.0
    assert "COMPOSER_MIXED_OR_WEAK_CONTEXT" in result.reason_codes


def test_composer_returns_unknown_when_context_is_too_weak() -> None:
    result = MarketRegimeComposer().compose(
        symbol="BTCUSDT",
        interval="15m",
        trend_structure=_trend("UP", 0.30),
        range_structure=_range("NOT_RANGE", 0.10),
        breakout_retest=_breakout("NO_BREAKOUT"),
        technical_context=_technical("NEUTRAL", 0.50),
    )

    assert result.market_regime == MarketRegime.UNKNOWN
    assert result.confidence == 0.0
    assert "COMPOSER_MIXED_OR_WEAK_CONTEXT" in result.reason_codes


def test_composer_accepts_mapping_inputs_and_enum_values() -> None:
    result = MarketRegimeComposer().compose(
        symbol="ETHUSDT",
        interval="15m",
        trend_structure={
            "direction": DummyEnum.UP,
            "strength_score": 0.80,
            "reason_codes": ["UP_TREND_STRUCTURE"],
        },
        range_structure={
            "classification": "NOT_RANGE",
            "range_score": 0.10,
            "reason_codes": [],
        },
        breakout_retest={
            "classification": "NO_BREAKOUT",
            "reason_codes": [],
        },
        technical_context={
            "directional_bias": DummyEnum.BULLISH,
            "technical_score": 0.80,
            "reason_codes": ["PRICE_ABOVE_EMA"],
        },
    )

    assert result.symbol == "ETHUSDT"
    assert result.interval == "15m"
    assert result.market_regime == MarketRegime.UP
    assert "UP_TREND_STRUCTURE" in result.reason_codes
    assert "PRICE_ABOVE_EMA" in result.reason_codes


def test_composer_deduplicates_reason_codes() -> None:
    result = MarketRegimeComposer().compose(
        symbol="BTCUSDT",
        interval="15m",
        trend_structure=_trend("UP", 0.80, "SHARED_REASON", "UP_TREND_STRUCTURE"),
        range_structure=_range("NOT_RANGE", 0.10, "SHARED_REASON"),
        breakout_retest=_breakout("NO_BREAKOUT", "SHARED_REASON"),
        technical_context=_technical("BULLISH", 0.80, "SHARED_REASON"),
    )

    assert result.reason_codes.count("SHARED_REASON") == 1


def test_component_snapshot_normalizes_values() -> None:
    snapshot = MarketRegimeComponentSnapshot(
        trend_direction=DummyEnum.UP,
        trend_strength_score=2.0,
        range_classification=DummyEnum.RANGE,
        range_score=2.0,
        breakout_classification=DummyEnum.BULLISH_BREAKOUT_RETEST,
        technical_bias=DummyEnum.BULLISH,
        technical_score=2.0,
        reason_codes=["A", "B"],
    )

    assert snapshot.trend_direction == "UP"
    assert snapshot.trend_strength_score == 1.0
    assert snapshot.range_classification == "RANGE"
    assert snapshot.range_score == 1.0
    assert snapshot.has_active_bullish_breakout is True
    assert snapshot.technical_bias == "BULLISH"
    assert snapshot.technical_score == 1.0
    assert snapshot.reason_codes == ("A", "B")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min_directional_score": -0.01},
        {"min_directional_score": 1.01},
        {"min_range_score": -0.01},
        {"trend_weight": 1.01},
        {"technical_bias_weight": -0.01},
        {"breakout_weight": 1.01},
        {"breakout_retest_bonus": -0.01},
        {"min_score_gap": -0.01},
    ],
)
def test_config_rejects_invalid_values(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        MarketRegimeCompositionConfig(**kwargs)


def test_config_rejects_invalid_threshold_order() -> None:
    with pytest.raises(ValueError, match="trend thresholds"):
        MarketRegimeCompositionConfig(
            strong_trend_threshold=0.50,
            moderate_trend_threshold=0.60,
            weak_trend_threshold=0.30,
        )
