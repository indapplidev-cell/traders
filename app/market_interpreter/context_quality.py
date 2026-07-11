from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Iterable


class ContextQualityGrade(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    SKIP = "SKIP"
    ERROR = "ERROR"


@dataclass(frozen=True)
class ContextQualityConfig:
    high_threshold: float = 0.75
    medium_threshold: float = 0.50
    low_threshold: float = 0.25


@dataclass(frozen=True)
class ContextQualityScore:
    symbol: str
    score: float
    grade: str
    rank: int | None
    reason_codes: tuple[str, ...] = field(default_factory=tuple)


class ContextQualityScorer:
    def __init__(self, config: ContextQualityConfig | None = None) -> None:
        self.config = config or ContextQualityConfig()

    def score(self, symbol_context: object) -> ContextQualityScore:
        symbol = _read_token(symbol_context, "symbol", "UNKNOWN")
        status = _read_token(symbol_context, "status", "ERROR")
        bucket = _read_token(symbol_context, "bucket", "UNKNOWN")
        skip_candidate = _read_bool(_read_field(symbol_context, "skip_candidate", False))
        stability = _read_token(symbol_context, "stability", "UNKNOWN")
        current_regime = _read_token(symbol_context, "current_regime", "UNKNOWN")
        confidence = _read_float(
            _read_field(symbol_context, "current_confidence", _read_field(symbol_context, "confidence", 0.0)),
            0.0,
        )
        last_transition = _read_token(symbol_context, "last_transition", "UNKNOWN")
        trend_strength = _read_token(
            symbol_context,
            "current_trend_strength",
            _read_token(symbol_context, "trend_strength", "UNKNOWN"),
        )

        reason_codes: list[str] = ["CONTEXT_QUALITY_SCORED"]
        if _is_error_context(status=status, bucket=bucket):
            reason_codes.extend(("QUALITY_STATUS_NOT_OK", "QUALITY_GRADE_ERROR"))
            return ContextQualityScore(
                symbol=symbol,
                score=0.0,
                grade=ContextQualityGrade.ERROR.value,
                rank=None,
                reason_codes=tuple(reason_codes),
            )

        score = 0.50
        if _is_clean_bucket(bucket):
            score += 0.20
            reason_codes.append("QUALITY_BUCKET_CLEAN")
        if stability == "STABLE":
            score += 0.15
            reason_codes.append("QUALITY_STABLE_CONTEXT")
        if stability == "CHANGING" and current_regime != "UNKNOWN":
            score += 0.10
            reason_codes.append("QUALITY_CHANGING_CONTEXT_READABLE")
        if confidence >= 0.75:
            score += 0.10
            reason_codes.append("QUALITY_CURRENT_CONFIDENCE_HIGH")
        elif confidence >= 0.60:
            score += 0.05
            reason_codes.append("QUALITY_CURRENT_CONFIDENCE_ACCEPTABLE")
        if current_regime in {"UP", "DOWN"} and bucket != "TRANSITIONING":
            score += 0.10
            reason_codes.append("QUALITY_DIRECTIONAL_REGIME")
        if current_regime == "FLAT" and stability == "STABLE":
            score += 0.05
            reason_codes.append("QUALITY_STABLE_FLAT_REGIME")
        if last_transition == "NO_CHANGE":
            score += 0.05
            reason_codes.append("QUALITY_LAST_TRANSITION_NO_CHANGE")
        if trend_strength in {"MODERATE", "STRONG"}:
            score += 0.05
            reason_codes.append("QUALITY_TREND_STRENGTH_SUPPORTED")

        if skip_candidate:
            score -= 0.30
            reason_codes.append("QUALITY_SKIP_CANDIDATE_PENALTY")
        if bucket == "UNSTABLE":
            score -= 0.25
            reason_codes.append("QUALITY_BUCKET_UNSTABLE")
        if bucket in {"UNKNOWN", "INSUFFICIENT_DATA"}:
            score -= 0.25
            reason_codes.append("QUALITY_BUCKET_UNKNOWN")
        if current_regime == "UNKNOWN":
            score -= 0.20
            reason_codes.append("QUALITY_CURRENT_REGIME_UNKNOWN")
        if stability == "UNSTABLE":
            score -= 0.15
            reason_codes.append("QUALITY_UNSTABLE_CONTEXT")
        if last_transition == "TO_UNKNOWN":
            score -= 0.10
            reason_codes.append("QUALITY_TRANSITION_TO_UNKNOWN")
        if confidence < 0.50:
            score -= 0.10
            reason_codes.append("QUALITY_LOW_CONFIDENCE")
        if status != "OK":
            score -= 0.20
            reason_codes.append("QUALITY_STATUS_NOT_OK")

        score = round(_clamp(score), 2)
        grade = self.grade_for_score(score)
        reason_codes.append(f"QUALITY_GRADE_{grade.value}")
        return ContextQualityScore(
            symbol=symbol,
            score=score,
            grade=grade.value,
            rank=None,
            reason_codes=tuple(reason_codes),
        )

    def grade_for_score(self, score: float) -> ContextQualityGrade:
        score = _clamp(score)
        if score >= self.config.high_threshold:
            return ContextQualityGrade.HIGH
        if score >= self.config.medium_threshold:
            return ContextQualityGrade.MEDIUM
        if score >= self.config.low_threshold:
            return ContextQualityGrade.LOW
        return ContextQualityGrade.SKIP


def rank_symbol_contexts(
    symbol_contexts: Iterable[object],
    *,
    scorer: ContextQualityScorer | None = None,
) -> tuple[ContextQualityScore, ...]:
    active_scorer = scorer or ContextQualityScorer()
    contexts = tuple(symbol_contexts)
    scores = tuple(active_scorer.score(symbol_context) for symbol_context in contexts)
    by_symbol = {score.symbol: score for score in scores}
    rankable_symbols = sorted(
        (
            score.symbol
            for score, symbol_context in zip(scores, contexts, strict=True)
            if _is_rankable(score=score, symbol_context=symbol_context)
        ),
        key=lambda symbol: (-by_symbol[symbol].score, symbol),
    )
    ranks = {symbol: index for index, symbol in enumerate(rankable_symbols, start=1)}
    return tuple(replace(score, rank=ranks.get(score.symbol)) for score in scores)


def summarize_quality_distribution(scores: Iterable[ContextQualityScore]) -> dict[str, int]:
    summary = {grade.value: 0 for grade in ContextQualityGrade}
    for score in scores:
        grade = score.grade if score.grade in summary else ContextQualityGrade.ERROR.value
        summary[grade] += 1
    return summary


def _is_rankable(*, score: ContextQualityScore, symbol_context: object) -> bool:
    status = _read_token(symbol_context, "status", "ERROR")
    skip_candidate = _read_bool(_read_field(symbol_context, "skip_candidate", False))
    return status == "OK" and not skip_candidate and score.grade != ContextQualityGrade.ERROR.value


def _is_error_context(*, status: str, bucket: str) -> bool:
    return status == "ERROR" or bucket == "ERROR"


def _is_clean_bucket(bucket: str) -> bool:
    return bucket in {"CLEAN", "CLEAN_TREND"}


def _read_field(row: object, field_name: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(field_name, default)
    return getattr(row, field_name, default)


def _read_token(row: object, field_name: str, default: str) -> str:
    value = _read_field(row, field_name, default)
    if value is None:
        return default
    text = str(value).strip().upper()
    return text or default


def _read_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


def _read_float(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return _clamp(number)


def _clamp(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value
