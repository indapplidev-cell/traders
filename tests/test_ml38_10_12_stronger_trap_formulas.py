from __future__ import annotations

from dataclasses import dataclass

from app.features.book_setup_context_features import BookSetupContextFeatureBuilder


@dataclass(slots=True)
class Candle:
    open: float
    high: float
    low: float
    close: float
    volume: float


def _base_features(*, volume_confirmation: float = 0.2, regime_range: float = 0.6) -> dict[str, float]:
    return {
        "atr_14": 2.0,
        "regime_trend_up": 0.3,
        "regime_trend_down": 0.1,
        "regime_range": regime_range,
        "trend_strength": 0.01,
        "trend_slope_short": 0.0,
        "trend_slope_medium": 0.0,
        "trend_slope_long": 0.0,
        "volume_confirmation": volume_confirmation,
        "volume_ratio_20": 1.8,
        "volume_zscore": 2.0,
        "rsi_14": 55.0,
        "macd_histogram": 0.0,
        "stochastic_k": 55.0,
        "roc": 0.0,
        "momentum": 0.0,
        "volatility_regime_score": 1.0,
        "breakout_candidate": 1.0,
        "breakdown_candidate": 0.0,
        "false_breakout_candidate": 0.0,
        "false_breakdown_candidate": 0.0,
        "near_support": 0.0,
        "near_resistance": 1.0,
        "distance_to_support": 1.2,
        "distance_to_resistance": 0.2,
    }


def _previous_range() -> list[Candle]:
    return [Candle(open=95.0, high=100.0, low=90.0, close=95.0, volume=100.0) for _ in range(24)]


def test_ml38_10_12_stronger_formula_flags_failed_up_breakout_trap() -> None:
    candles = _previous_range()
    candles.append(Candle(open=99.0, high=105.0, low=97.0, close=99.0, volume=280.0))

    features = BookSetupContextFeatureBuilder().build(
        candles=candles,
        index=len(candles) - 1,
        base_features=_base_features(volume_confirmation=0.15, regime_range=0.75),
    )

    assert features["schwager_false_breakout_risk_score"] > 0.45
    assert features["schwager_bull_trap_risk_score"] > 0.40
    assert features["schwager_failed_breakout_return_inside_range_score"] > 0.45
    assert features["schwager_stop_hunt_like_move_score"] > 0.35
    assert features["schwager_trap_safe_setup_score"] < 0.65


def test_ml38_10_12_stronger_formula_flags_failed_down_breakout_trap() -> None:
    candles = _previous_range()
    candles.append(Candle(open=91.0, high=93.0, low=85.0, close=91.5, volume=280.0))

    features = BookSetupContextFeatureBuilder().build(
        candles=candles,
        index=len(candles) - 1,
        base_features=_base_features(volume_confirmation=0.15, regime_range=0.75),
    )

    assert features["schwager_false_breakout_risk_score"] > 0.45
    assert features["schwager_bear_trap_risk_score"] > 0.40
    assert features["schwager_failed_breakout_return_inside_range_score"] > 0.45
    assert features["schwager_range_reentry_after_breakout_score"] > 0.45
    assert features["schwager_trap_safe_setup_score"] < 0.65


def test_ml38_10_12_clean_breakout_scores_safer_than_failed_breakout() -> None:
    failed = _previous_range()
    failed.append(Candle(open=99.0, high=105.0, low=97.0, close=99.0, volume=280.0))
    clean = _previous_range()
    clean.append(Candle(open=100.5, high=106.0, low=99.5, close=105.7, volume=280.0))

    builder = BookSetupContextFeatureBuilder()
    failed_features = builder.build(
        candles=failed,
        index=len(failed) - 1,
        base_features=_base_features(volume_confirmation=0.15, regime_range=0.75),
    )
    clean_features = builder.build(
        candles=clean,
        index=len(clean) - 1,
        base_features=_base_features(volume_confirmation=0.90, regime_range=0.15),
    )

    assert clean_features["schwager_false_breakout_risk_score"] < failed_features["schwager_false_breakout_risk_score"]
    assert clean_features["schwager_bull_trap_risk_score"] < failed_features["schwager_bull_trap_risk_score"]
    assert clean_features["schwager_trap_safe_setup_score"] > failed_features["schwager_trap_safe_setup_score"]
    assert clean_features["schwager_invalidation_quality_score"] > failed_features["schwager_invalidation_quality_score"]
