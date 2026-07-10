import pytest

from app.market_reader.schemas import (
    DirectionalBias,
    MarketAnalysisResult,
    MarketRegime,
    TradeSignal,
    TrendStrength,
)


def test_market_analysis_result_defaults_are_safe() -> None:
    result = MarketAnalysisResult(
        symbol="BTCUSDT",
        interval="15m",
        market_regime=MarketRegime.UNKNOWN,
        directional_bias=DirectionalBias.UNKNOWN,
        confidence=0.0,
        trend_strength=TrendStrength.UNKNOWN,
    )

    assert result.trade_signal == TradeSignal.NOT_EVALUATED
    assert result.safe_for_runtime_trading is False
    assert result.reason_codes == ()


def test_market_analysis_result_to_dict_uses_plain_values() -> None:
    result = MarketAnalysisResult(
        symbol="SOLUSDT",
        interval="15m",
        market_regime=MarketRegime.UP,
        directional_bias=DirectionalBias.BULLISH,
        confidence=0.71,
        trend_strength=TrendStrength.MODERATE,
        reason_codes=("HIGHER_HIGHS_HIGHER_LOWS", "EMA_SLOPE_UP"),
    )

    assert result.to_dict() == {
        "symbol": "SOLUSDT",
        "interval": "15m",
        "market_regime": "UP",
        "directional_bias": "BULLISH",
        "confidence": 0.71,
        "trend_strength": "MODERATE",
        "reason_codes": ["HIGHER_HIGHS_HIGHER_LOWS", "EMA_SLOPE_UP"],
        "trade_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": False,
    }


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_market_analysis_result_rejects_invalid_confidence(confidence: float) -> None:
    with pytest.raises(ValueError, match="confidence"):
        MarketAnalysisResult(
            symbol="BTCUSDT",
            interval="15m",
            market_regime=MarketRegime.UNKNOWN,
            directional_bias=DirectionalBias.UNKNOWN,
            confidence=confidence,
            trend_strength=TrendStrength.UNKNOWN,
        )


def test_market_analysis_result_rejects_runtime_trading_approval() -> None:
    with pytest.raises(ValueError, match="runtime trading"):
        MarketAnalysisResult(
            symbol="BTCUSDT",
            interval="15m",
            market_regime=MarketRegime.UP,
            directional_bias=DirectionalBias.BULLISH,
            confidence=0.8,
            trend_strength=TrendStrength.STRONG,
            safe_for_runtime_trading=True,
        )


def test_market_analysis_result_rejects_trading_signal_values() -> None:
    with pytest.raises(ValueError, match="trading signals"):
        MarketAnalysisResult(
            symbol="BTCUSDT",
            interval="15m",
            market_regime=MarketRegime.UP,
            directional_bias=DirectionalBias.BULLISH,
            confidence=0.8,
            trend_strength=TrendStrength.STRONG,
            trade_signal="LONG",
        )
