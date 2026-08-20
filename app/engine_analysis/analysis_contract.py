"""Production analysis contract for candle-series market reading."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from re import fullmatch


MIN_FULL_ANALYSIS_CANDLES = 64
RECOMMENDED_CONTEXT_CANDLES = 96


class AnalysisReadiness(str, Enum):
    INVALID = "INVALID"
    PARTIAL = "PARTIAL"
    FULL = "FULL"


@dataclass(frozen=True)
class AnalysisWindowConfig:
    """Separates structural history from recent decisions and confirmation."""

    minimum_candles: int = MIN_FULL_ANALYSIS_CANDLES
    context_candles: int = RECOMMENDED_CONTEXT_CANDLES
    decision_candles: int = 24
    confirmation_candles: int = 3
    atr_lookback_candles: int = 14
    impulse_lookback_candles: int = RECOMMENDED_CONTEXT_CANDLES
    structure_lookback_candles: int = RECOMMENDED_CONTEXT_CANDLES
    volume_baseline_candles: int = RECOMMENDED_CONTEXT_CANDLES - 3
    breakout_volume_baseline_candles: int = 20

    def __post_init__(self) -> None:
        if self.minimum_candles < 8:
            raise ValueError("minimum_candles must be at least 8")
        if self.context_candles < self.minimum_candles:
            raise ValueError("context_candles must be >= minimum_candles")
        if self.decision_candles < 1:
            raise ValueError("decision_candles must be positive")
        if self.confirmation_candles < 1:
            raise ValueError("confirmation_candles must be positive")
        if self.decision_candles + self.confirmation_candles > self.context_candles:
            raise ValueError("decision and confirmation windows exceed context")
        if min(
            self.atr_lookback_candles,
            self.impulse_lookback_candles,
            self.structure_lookback_candles,
            self.volume_baseline_candles,
            self.breakout_volume_baseline_candles,
        ) < 1:
            raise ValueError("analysis runtime lookbacks must be positive")
        if self.structure_lookback_candles > self.context_candles:
            raise ValueError("structure lookback exceeds context")

    def to_dict(self) -> dict[str, int]:
        return {
            "minimum_candles": self.minimum_candles,
            "context_candles": self.context_candles,
            "decision_candles": self.decision_candles,
            "confirmation_candles": self.confirmation_candles,
            "atr_lookback_candles": self.atr_lookback_candles,
            "impulse_lookback_candles": self.impulse_lookback_candles,
            "structure_lookback_candles": self.structure_lookback_candles,
            "volume_baseline_candles": self.volume_baseline_candles,
            "breakout_volume_baseline_candles": self.breakout_volume_baseline_candles,
        }


@dataclass(frozen=True)
class ResolvedAnalysisWindow:
    candle_count: int
    context_start_index: int
    decision_start_index: int
    decision_end_index: int
    confirmation_lookahead: int
    readiness: AnalysisReadiness

    def contains_decision_event(self, index: int | None) -> bool:
        return index is not None and self.decision_start_index <= index <= self.decision_end_index

    def to_dict(self) -> dict[str, int | str]:
        return {
            "candle_count": self.candle_count,
            "context_start_index": self.context_start_index,
            "decision_start_index": self.decision_start_index,
            "decision_end_index": self.decision_end_index,
            "confirmation_lookahead": self.confirmation_lookahead,
            "readiness": self.readiness.value,
        }


def resolve_analysis_window(
    candle_count: int,
    config: AnalysisWindowConfig,
) -> ResolvedAnalysisWindow:
    readiness = analysis_readiness(candle_count, config)
    context_start = max(0, candle_count - config.context_candles)
    # Short synthetic fixtures remain fully observable for isolated rule tests.
    decision_start = (
        context_start
        if readiness is not AnalysisReadiness.FULL
        else max(context_start, candle_count - config.decision_candles)
    )
    return ResolvedAnalysisWindow(
        candle_count=candle_count,
        context_start_index=context_start,
        decision_start_index=decision_start,
        decision_end_index=max(0, candle_count - 1),
        confirmation_lookahead=config.confirmation_candles,
        readiness=readiness,
    )


def parse_market_timestamp(value: str) -> datetime:
    """Parse ISO-8601 or unix-second/millisecond timestamps as aware UTC."""

    text = str(value).strip()
    if not text:
        raise ValueError("timestamp is empty")
    if fullmatch(r"\d{10}(?:\.\d+)?", text):
        return datetime.fromtimestamp(float(text), tz=timezone.utc)
    if fullmatch(r"\d{13}", text):
        return datetime.fromtimestamp(int(text) / 1000.0, tz=timezone.utc)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"timestamp is not ISO-8601 or unix time: {text}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def interval_duration(interval: str) -> timedelta:
    """Convert canonical exchange intervals such as 15m, 1h, or 1d."""

    match = fullmatch(r"([1-9]\d*)([smhdw])", interval.strip().lower())
    if match is None:
        raise ValueError(f"unsupported interval: {interval}")
    value = int(match.group(1))
    unit = match.group(2)
    seconds = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400,
        "w": 604800,
    }[unit]
    return timedelta(seconds=value * seconds)


def analysis_readiness(candle_count: int, config: AnalysisWindowConfig) -> AnalysisReadiness:
    if candle_count <= 0:
        return AnalysisReadiness.INVALID
    if candle_count < config.minimum_candles:
        return AnalysisReadiness.PARTIAL
    return AnalysisReadiness.FULL
