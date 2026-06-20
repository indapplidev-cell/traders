from __future__ import annotations

from dataclasses import dataclass

from app.diagnostics.real_feature_diagnostics_service import RealFeatureDiagnosticsService
from app.features.book_setup_context_features import (
    BookSetupContextFeatureBuilder,
    SCHWAGER_TRAP_INVALIDATION_FEATURE_NAMES,
)
from app.features.feature_models import FV4_BOOK_SETUP_CONTEXT_FEATURE_NAMES


@dataclass(slots=True)
class Candle:
    open: float
    high: float
    low: float
    close: float
    volume: float


def _base_features() -> dict[str, float]:
    return {
        "atr_14": 2.0,
        "regime_trend_up": 0.3,
        "regime_trend_down": 0.1,
        "regime_range": 0.6,
        "trend_strength": 0.01,
        "trend_slope_short": 0.0,
        "trend_slope_medium": 0.0,
        "trend_slope_long": 0.0,
        "volume_confirmation": 0.2,
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


def test_schwager_trap_feature_names_are_part_of_fv4() -> None:
    for name in SCHWAGER_TRAP_INVALIDATION_FEATURE_NAMES:
        assert name in FV4_BOOK_SETUP_CONTEXT_FEATURE_NAMES


def test_false_breakout_up_creates_bull_trap_risk() -> None:
    candles = [Candle(open=95.0, high=100.0, low=90.0, close=95.0, volume=100.0) for _ in range(24)]
    candles.append(Candle(open=99.0, high=105.0, low=97.0, close=99.0, volume=260.0))

    features = BookSetupContextFeatureBuilder().build(
        candles=candles,
        index=len(candles) - 1,
        base_features=_base_features(),
    )

    assert features["schwager_false_breakout_risk_score"] > 0.40
    assert features["schwager_bull_trap_risk_score"] > 0.30
    assert features["schwager_failed_breakout_return_inside_range_score"] > 0.30
    assert features["schwager_stop_hunt_like_move_score"] > 0.25
    assert features["schwager_invalidation_quality_score"] < 0.80


def test_real_feature_diagnostics_requires_new_trap_feature_for_fv4_refresh() -> None:
    assert "schwager_false_breakout_risk_score" in RealFeatureDiagnosticsService.FV4_REQUIRED_FEATURES
