from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from app.market_reader.breakout_retest import BreakoutRetestAnalyzer
from app.market_reader.candle_morphology import CandleMorphologyAnalyzer
from app.market_reader.candle_window import CandleWindow
from app.market_reader.market_regime_composer import (
    MarketRegimeComposer,
    MarketRegimeCompositionConfig,
)
from app.market_reader.range_structure import RangeStructureAnalyzer
from app.market_reader.schemas import DirectionalBias, MarketAnalysisResult
from app.market_reader.swing_detector import SwingDetector
from app.market_reader.technical_context import TechnicalContextAnalyzer
from app.market_reader.trend_structure import TrendStructureAnalyzer


@dataclass(frozen=True)
class MarketReaderConfig:
    trend_tolerance_pct: float = 0.0

    range_lookback: int = 20
    range_min_size: int = 5
    range_boundary_tolerance_pct: float = 0.01
    range_max_width_pct: float = 0.08
    range_max_close_drift_ratio: float = 0.60
    range_min_boundary_touch_count: int = 2

    breakout_lookback: int = 20
    breakout_tolerance_pct: float = 0.001
    retest_tolerance_pct: float = 0.005
    breakout_min_follow_through_count: int = 1

    fast_ema_period: int = 9
    slow_ema_period: int = 21
    atr_period: int = 14
    technical_slope_lookback: int = 3
    flat_slope_tolerance_pct: float = 0.0005
    around_ema_tolerance_pct: float = 0.001
    high_volatility_atr_pct: float = 0.03
    low_volatility_atr_pct: float = 0.003

    composition_config: MarketRegimeCompositionConfig | None = None

    def __post_init__(self) -> None:
        _validate_non_negative(self.trend_tolerance_pct, "trend_tolerance_pct")

        _validate_positive_int(self.range_lookback, "range_lookback")
        _validate_positive_int(self.range_min_size, "range_min_size")
        _validate_non_negative(self.range_boundary_tolerance_pct, "range_boundary_tolerance_pct")
        _validate_positive(self.range_max_width_pct, "range_max_width_pct")
        _validate_positive(self.range_max_close_drift_ratio, "range_max_close_drift_ratio")
        _validate_positive_int(self.range_min_boundary_touch_count, "range_min_boundary_touch_count")

        _validate_positive_int(self.breakout_lookback, "breakout_lookback")
        _validate_non_negative(self.breakout_tolerance_pct, "breakout_tolerance_pct")
        _validate_non_negative(self.retest_tolerance_pct, "retest_tolerance_pct")
        _validate_non_negative_int(self.breakout_min_follow_through_count, "breakout_min_follow_through_count")

        _validate_positive_int(self.fast_ema_period, "fast_ema_period")
        _validate_positive_int(self.slow_ema_period, "slow_ema_period")
        _validate_positive_int(self.atr_period, "atr_period")
        _validate_positive_int(self.technical_slope_lookback, "technical_slope_lookback")
        _validate_non_negative(self.flat_slope_tolerance_pct, "flat_slope_tolerance_pct")
        _validate_non_negative(self.around_ema_tolerance_pct, "around_ema_tolerance_pct")
        _validate_positive(self.high_volatility_atr_pct, "high_volatility_atr_pct")
        _validate_non_negative(self.low_volatility_atr_pct, "low_volatility_atr_pct")

        if self.fast_ema_period >= self.slow_ema_period:
            raise ValueError("fast_ema_period must be less than slow_ema_period")

        if self.low_volatility_atr_pct >= self.high_volatility_atr_pct:
            raise ValueError("low_volatility_atr_pct must be less than high_volatility_atr_pct")


@dataclass(frozen=True)
class TechnicalContextComposerInput:
    technical_bias: DirectionalBias
    technical_score: float
    reason_codes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not 0.0 <= self.technical_score <= 1.0:
            raise ValueError("technical_score must be between 0.0 and 1.0")
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))

    def to_dict(self) -> dict[str, object]:
        return {
            "technical_bias": self.technical_bias.value,
            "technical_score": self.technical_score,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class MarketReaderPipelineResult:
    final_result: MarketAnalysisResult
    morphologies: tuple[Any, ...]
    swing_points: tuple[Any, ...]
    trend_structure: Any
    range_structure: Any
    breakout_retest: Any
    technical_context: Any
    technical_context_for_composer: TechnicalContextComposerInput

    def to_dict(self) -> dict[str, object]:
        return {
            "final_result": self.final_result.to_dict(),
            "morphologies": [_to_plain_value(item) for item in self.morphologies],
            "swing_points": [_to_plain_value(item) for item in self.swing_points],
            "trend_structure": _to_plain_value(self.trend_structure),
            "range_structure": _to_plain_value(self.range_structure),
            "breakout_retest": _to_plain_value(self.breakout_retest),
            "technical_context": _to_plain_value(self.technical_context),
            "technical_context_for_composer": self.technical_context_for_composer.to_dict(),
        }


class MarketReaderOrchestrator:
    def __init__(
        self,
        *,
        morphology_analyzer: Any | None = None,
        swing_detector: Any | None = None,
        trend_structure_analyzer: Any | None = None,
        range_structure_analyzer: Any | None = None,
        breakout_retest_analyzer: Any | None = None,
        technical_context_analyzer: Any | None = None,
        market_regime_composer: Any | None = None,
    ) -> None:
        self.morphology_analyzer = morphology_analyzer or CandleMorphologyAnalyzer()
        self.swing_detector = swing_detector or SwingDetector()
        self.trend_structure_analyzer = trend_structure_analyzer or TrendStructureAnalyzer()
        self.range_structure_analyzer = range_structure_analyzer or RangeStructureAnalyzer()
        self.breakout_retest_analyzer = breakout_retest_analyzer or BreakoutRetestAnalyzer()
        self.technical_context_analyzer = technical_context_analyzer or TechnicalContextAnalyzer()
        self.market_regime_composer = market_regime_composer or MarketRegimeComposer()

    def analyze(
        self,
        window: CandleWindow,
        *,
        config: MarketReaderConfig | None = None,
    ) -> MarketAnalysisResult:
        return self.analyze_detailed(window, config=config).final_result

    def analyze_detailed(
        self,
        window: CandleWindow,
        *,
        config: MarketReaderConfig | None = None,
    ) -> MarketReaderPipelineResult:
        active_config = config or MarketReaderConfig()

        morphologies = tuple(self.morphology_analyzer.analyze_window(window))

        swing_points = tuple(self.swing_detector.detect(window))
        swing_highs = tuple(self.swing_detector.highs(swing_points))
        swing_lows = tuple(self.swing_detector.lows(swing_points))

        trend_structure = self.trend_structure_analyzer.analyze(
            swing_highs=swing_highs,
            swing_lows=swing_lows,
            tolerance_pct=active_config.trend_tolerance_pct,
        )

        range_structure = self.range_structure_analyzer.analyze(
            window,
            lookback=active_config.range_lookback,
            min_size=active_config.range_min_size,
            boundary_tolerance_pct=active_config.range_boundary_tolerance_pct,
            max_range_width_pct=active_config.range_max_width_pct,
            max_close_drift_ratio=active_config.range_max_close_drift_ratio,
            min_boundary_touch_count=active_config.range_min_boundary_touch_count,
        )

        breakout_retest = self.breakout_retest_analyzer.analyze(
            window,
            range_result=range_structure,
            lookback=active_config.breakout_lookback,
            breakout_tolerance_pct=active_config.breakout_tolerance_pct,
            retest_tolerance_pct=active_config.retest_tolerance_pct,
            min_follow_through_count=active_config.breakout_min_follow_through_count,
        )

        technical_context = self.technical_context_analyzer.analyze(
            window,
            fast_ema_period=active_config.fast_ema_period,
            slow_ema_period=active_config.slow_ema_period,
            atr_period=active_config.atr_period,
            slope_lookback=active_config.technical_slope_lookback,
            flat_slope_tolerance_pct=active_config.flat_slope_tolerance_pct,
            around_ema_tolerance_pct=active_config.around_ema_tolerance_pct,
            high_volatility_atr_pct=active_config.high_volatility_atr_pct,
            low_volatility_atr_pct=active_config.low_volatility_atr_pct,
        )
        technical_context_for_composer = _build_technical_context_for_composer(technical_context)

        final_result = self.market_regime_composer.compose(
            symbol=window.symbol,
            interval=window.interval,
            trend_structure=trend_structure,
            range_structure=range_structure,
            breakout_retest=breakout_retest,
            technical_context=technical_context_for_composer,
            config=active_config.composition_config,
        )

        return MarketReaderPipelineResult(
            final_result=_with_orchestrator_reason(final_result),
            morphologies=morphologies,
            swing_points=swing_points,
            trend_structure=trend_structure,
            range_structure=range_structure,
            breakout_retest=breakout_retest,
            technical_context=technical_context,
            technical_context_for_composer=technical_context_for_composer,
        )


def _build_technical_context_for_composer(technical_context: Any) -> TechnicalContextComposerInput:
    return TechnicalContextComposerInput(
        technical_bias=_derive_technical_bias(technical_context),
        technical_score=_clamp(_read_float(technical_context, "technical_score", default=0.0)),
        reason_codes=_read_reason_codes(technical_context),
    )


def _derive_technical_bias(technical_context: Any) -> DirectionalBias:
    ema_direction = _read_token(technical_context, "ema_direction", default="UNKNOWN")
    price_position = _read_token(technical_context, "price_ema_position", default="UNKNOWN")

    if ema_direction == "UP" and price_position != "BELOW_FAST_BELOW_SLOW":
        return DirectionalBias.BULLISH

    if ema_direction == "DOWN" and price_position != "ABOVE_FAST_ABOVE_SLOW":
        return DirectionalBias.BEARISH

    if price_position == "ABOVE_FAST_ABOVE_SLOW":
        return DirectionalBias.BULLISH

    if price_position == "BELOW_FAST_BELOW_SLOW":
        return DirectionalBias.BEARISH

    if ema_direction == "FLAT" or price_position in {"AROUND_EMAS", "BETWEEN_EMAS"}:
        return DirectionalBias.NEUTRAL

    return DirectionalBias.UNKNOWN


def _with_orchestrator_reason(result: MarketAnalysisResult) -> MarketAnalysisResult:
    return MarketAnalysisResult(
        symbol=result.symbol,
        interval=result.interval,
        market_regime=result.market_regime,
        directional_bias=result.directional_bias,
        confidence=result.confidence,
        trend_strength=result.trend_strength,
        reason_codes=_merge_reason_codes(("MARKET_READER_ORCHESTRATED",), result.reason_codes),
    )


def _read_reason_codes(source: Any) -> tuple[str, ...]:
    reason_codes = _read_field(source, "reason_codes", default=())
    if reason_codes is None:
        return ()
    return tuple(str(reason_code) for reason_code in reason_codes)


def _read_token(source: Any, field_name: str, *, default: str) -> str:
    return _normalize_token(_read_field(source, field_name, default=default))


def _read_float(source: Any, field_name: str, *, default: float) -> float:
    return _to_finite_float(_read_field(source, field_name, default=default), field_name)


def _read_field(source: Any, field_name: str, *, default: Any) -> Any:
    if source is None:
        return default

    if isinstance(source, Mapping):
        return source.get(field_name, default)

    return getattr(source, field_name, default)


def _normalize_token(value: Any) -> str:
    if isinstance(value, Enum):
        value = value.value
    return str(value).strip().upper()


def _to_finite_float(value: Any, field_name: str) -> float:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc

    if not math.isfinite(numeric_value):
        raise ValueError(f"{field_name} must be finite")

    return numeric_value


def _to_plain_value(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, Mapping):
        return {str(key): _to_plain_value(item) for key, item in value.items()}

    if isinstance(value, tuple | list):
        return [_to_plain_value(item) for item in value]

    return value


def _validate_positive(value: float, field_name: str) -> None:
    if value <= 0.0:
        raise ValueError(f"{field_name} must be positive")


def _validate_non_negative(value: float, field_name: str) -> None:
    if value < 0.0:
        raise ValueError(f"{field_name} must be non-negative")


def _validate_positive_int(value: int, field_name: str) -> None:
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")


def _validate_non_negative_int(value: int, field_name: str) -> None:
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _merge_reason_codes(*groups: tuple[str, ...]) -> tuple[str, ...]:
    merged: list[str] = []
    seen: set[str] = set()

    for group in groups:
        for reason_code in group:
            normalized = str(reason_code)
            if normalized not in seen:
                seen.add(normalized)
                merged.append(normalized)

    return tuple(merged)
