from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping

from app.market_reader.schemas import (
    DirectionalBias,
    MarketAnalysisResult,
    MarketRegime,
    TrendStrength,
)


class ComposerDecisionReason(str, Enum):
    FLAT_RANGE_DOMINANT = "COMPOSER_FLAT_RANGE_DOMINANT"
    BULLISH_SCORE_DOMINANT = "COMPOSER_BULLISH_SCORE_DOMINANT"
    BEARISH_SCORE_DOMINANT = "COMPOSER_BEARISH_SCORE_DOMINANT"
    MIXED_OR_WEAK_CONTEXT = "COMPOSER_MIXED_OR_WEAK_CONTEXT"


@dataclass(frozen=True)
class MarketRegimeCompositionConfig:
    min_directional_score: float = 0.55
    min_score_gap: float = 0.15
    min_range_score: float = 0.55
    trend_weight: float = 0.55
    technical_bias_weight: float = 0.20
    breakout_weight: float = 0.35
    breakout_retest_bonus: float = 0.10
    strong_trend_threshold: float = 0.75
    moderate_trend_threshold: float = 0.55
    weak_trend_threshold: float = 0.35

    def __post_init__(self) -> None:
        _validate_unit_interval(self.min_directional_score, "min_directional_score")
        _validate_unit_interval(self.min_range_score, "min_range_score")
        _validate_unit_interval(self.trend_weight, "trend_weight")
        _validate_unit_interval(self.technical_bias_weight, "technical_bias_weight")
        _validate_unit_interval(self.breakout_weight, "breakout_weight")
        _validate_unit_interval(self.breakout_retest_bonus, "breakout_retest_bonus")
        _validate_unit_interval(self.strong_trend_threshold, "strong_trend_threshold")
        _validate_unit_interval(self.moderate_trend_threshold, "moderate_trend_threshold")
        _validate_unit_interval(self.weak_trend_threshold, "weak_trend_threshold")

        if self.min_score_gap < 0.0:
            raise ValueError("min_score_gap must be non-negative")

        if not self.strong_trend_threshold >= self.moderate_trend_threshold >= self.weak_trend_threshold:
            raise ValueError(
                "trend thresholds must satisfy strong >= moderate >= weak"
            )


@dataclass(frozen=True)
class MarketRegimeComponentSnapshot:
    trend_direction: str
    trend_strength_score: float
    range_classification: str
    range_score: float
    breakout_classification: str
    technical_bias: str
    technical_score: float
    reason_codes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "trend_direction", _normalize_token(self.trend_direction))
        object.__setattr__(self, "range_classification", _normalize_token(self.range_classification))
        object.__setattr__(self, "breakout_classification", _normalize_token(self.breakout_classification))
        object.__setattr__(self, "technical_bias", _normalize_token(self.technical_bias))
        object.__setattr__(self, "trend_strength_score", _clamp(self.trend_strength_score))
        object.__setattr__(self, "range_score", _clamp(self.range_score))
        object.__setattr__(self, "technical_score", _clamp(self.technical_score))
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))

    @property
    def has_active_bullish_breakout(self) -> bool:
        return self.breakout_classification.startswith("BULLISH_") and "FALSE" not in self.breakout_classification

    @property
    def has_active_bearish_breakout(self) -> bool:
        return self.breakout_classification.startswith("BEARISH_") and "FALSE" not in self.breakout_classification

    @property
    def has_active_directional_breakout(self) -> bool:
        return self.has_active_bullish_breakout or self.has_active_bearish_breakout


class MarketRegimeComposer:
    def compose(
        self,
        *,
        symbol: str,
        interval: str,
        trend_structure: Any,
        range_structure: Any,
        breakout_retest: Any,
        technical_context: Any,
        config: MarketRegimeCompositionConfig | None = None,
    ) -> MarketAnalysisResult:
        active_config = config or MarketRegimeCompositionConfig()
        snapshot = _build_snapshot(
            trend_structure=trend_structure,
            range_structure=range_structure,
            breakout_retest=breakout_retest,
            technical_context=technical_context,
        )

        if _is_range_dominant(snapshot=snapshot, config=active_config):
            return _build_result(
                symbol=symbol,
                interval=interval,
                market_regime=MarketRegime.FLAT,
                directional_bias=DirectionalBias.NEUTRAL,
                confidence=snapshot.range_score,
                trend_strength=TrendStrength.NONE,
                decision_reason=ComposerDecisionReason.FLAT_RANGE_DOMINANT,
                snapshot=snapshot,
            )

        bullish_score = _bullish_score(snapshot=snapshot, config=active_config)
        bearish_score = _bearish_score(snapshot=snapshot, config=active_config)

        if (
            bullish_score >= active_config.min_directional_score
            and bullish_score - bearish_score >= active_config.min_score_gap
        ):
            return _build_result(
                symbol=symbol,
                interval=interval,
                market_regime=MarketRegime.UP,
                directional_bias=DirectionalBias.BULLISH,
                confidence=bullish_score,
                trend_strength=_trend_strength_from_score(bullish_score, active_config),
                decision_reason=ComposerDecisionReason.BULLISH_SCORE_DOMINANT,
                snapshot=snapshot,
            )

        if (
            bearish_score >= active_config.min_directional_score
            and bearish_score - bullish_score >= active_config.min_score_gap
        ):
            return _build_result(
                symbol=symbol,
                interval=interval,
                market_regime=MarketRegime.DOWN,
                directional_bias=DirectionalBias.BEARISH,
                confidence=bearish_score,
                trend_strength=_trend_strength_from_score(bearish_score, active_config),
                decision_reason=ComposerDecisionReason.BEARISH_SCORE_DOMINANT,
                snapshot=snapshot,
            )

        return _build_result(
            symbol=symbol,
            interval=interval,
            market_regime=MarketRegime.UNKNOWN,
            directional_bias=DirectionalBias.UNKNOWN,
            confidence=0.0,
            trend_strength=TrendStrength.UNKNOWN,
            decision_reason=ComposerDecisionReason.MIXED_OR_WEAK_CONTEXT,
            snapshot=snapshot,
        )


def _build_snapshot(
    *,
    trend_structure: Any,
    range_structure: Any,
    breakout_retest: Any,
    technical_context: Any,
) -> MarketRegimeComponentSnapshot:
    return MarketRegimeComponentSnapshot(
        trend_direction=_read_token(trend_structure, "direction", default="UNKNOWN"),
        trend_strength_score=_read_float(trend_structure, "strength_score", default=0.0),
        range_classification=_read_token(range_structure, "classification", default="UNKNOWN"),
        range_score=_read_float(range_structure, "range_score", default=0.0),
        breakout_classification=_read_token(breakout_retest, "classification", default="UNKNOWN"),
        technical_bias=_read_first_token(
            technical_context,
            field_names=("directional_bias", "technical_bias", "bias"),
            default="UNKNOWN",
        ),
        technical_score=_read_first_float(
            technical_context,
            field_names=("technical_score", "confidence", "score", "context_score"),
            default=0.0,
        ),
        reason_codes=_merge_reason_codes(
            _read_reason_codes(trend_structure),
            _read_reason_codes(range_structure),
            _read_reason_codes(breakout_retest),
            _read_reason_codes(technical_context),
        ),
    )


def _is_range_dominant(
    *,
    snapshot: MarketRegimeComponentSnapshot,
    config: MarketRegimeCompositionConfig,
) -> bool:
    return (
        snapshot.range_classification == "RANGE"
        and snapshot.range_score >= config.min_range_score
        and not snapshot.has_active_directional_breakout
    )


def _bullish_score(
    *,
    snapshot: MarketRegimeComponentSnapshot,
    config: MarketRegimeCompositionConfig,
) -> float:
    score = 0.0

    if snapshot.trend_direction == "UP":
        score += snapshot.trend_strength_score * config.trend_weight

    if snapshot.has_active_bullish_breakout:
        score += config.breakout_weight
        if "RETEST" in snapshot.breakout_classification:
            score += config.breakout_retest_bonus

    if snapshot.technical_bias == "BULLISH":
        score += _signal_strength(snapshot.technical_score) * config.technical_bias_weight

    return _clamp(score)


def _bearish_score(
    *,
    snapshot: MarketRegimeComponentSnapshot,
    config: MarketRegimeCompositionConfig,
) -> float:
    score = 0.0

    if snapshot.trend_direction == "DOWN":
        score += snapshot.trend_strength_score * config.trend_weight

    if snapshot.has_active_bearish_breakout:
        score += config.breakout_weight
        if "RETEST" in snapshot.breakout_classification:
            score += config.breakout_retest_bonus

    if snapshot.technical_bias == "BEARISH":
        score += _signal_strength(snapshot.technical_score) * config.technical_bias_weight

    return _clamp(score)


def _signal_strength(value: float) -> float:
    if value <= 0.0:
        return 0.5
    return _clamp(value)


def _build_result(
    *,
    symbol: str,
    interval: str,
    market_regime: MarketRegime,
    directional_bias: DirectionalBias,
    confidence: float,
    trend_strength: TrendStrength,
    decision_reason: ComposerDecisionReason,
    snapshot: MarketRegimeComponentSnapshot,
) -> MarketAnalysisResult:
    return MarketAnalysisResult(
        symbol=symbol,
        interval=interval,
        market_regime=market_regime,
        directional_bias=directional_bias,
        confidence=_clamp(confidence),
        trend_strength=trend_strength,
        reason_codes=_merge_reason_codes(
            ("MARKET_REGIME_COMPOSED", decision_reason.value),
            snapshot.reason_codes,
        ),
    )


def _trend_strength_from_score(
    score: float,
    config: MarketRegimeCompositionConfig,
) -> TrendStrength:
    if score >= config.strong_trend_threshold:
        return TrendStrength.STRONG
    if score >= config.moderate_trend_threshold:
        return TrendStrength.MODERATE
    if score >= config.weak_trend_threshold:
        return TrendStrength.WEAK
    return TrendStrength.UNKNOWN


def _read_token(source: Any, field_name: str, *, default: str) -> str:
    return _normalize_token(_read_field(source, field_name, default=default))


def _read_first_token(
    source: Any,
    *,
    field_names: Iterable[str],
    default: str,
) -> str:
    for field_name in field_names:
        value = _read_field(source, field_name, default=None)
        if value is not None:
            return _normalize_token(value)
    return _normalize_token(default)


def _read_float(source: Any, field_name: str, *, default: float) -> float:
    return _to_finite_float(_read_field(source, field_name, default=default), field_name)


def _read_first_float(
    source: Any,
    *,
    field_names: Iterable[str],
    default: float,
) -> float:
    for field_name in field_names:
        value = _read_field(source, field_name, default=None)
        if value is not None:
            return _to_finite_float(value, field_name)
    return default


def _read_reason_codes(source: Any) -> tuple[str, ...]:
    reason_codes = _read_field(source, "reason_codes", default=())
    if reason_codes is None:
        return ()
    return tuple(str(reason_code) for reason_code in reason_codes)


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


def _validate_unit_interval(value: float, field_name: str) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0")


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _merge_reason_codes(*groups: Iterable[str]) -> tuple[str, ...]:
    merged: list[str] = []
    seen: set[str] = set()

    for group in groups:
        for reason_code in group:
            normalized = str(reason_code)
            if normalized not in seen:
                seen.add(normalized)
                merged.append(normalized)

    return tuple(merged)
