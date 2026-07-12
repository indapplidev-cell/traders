"""Core schemas for the clean book-based engine_trend module."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EngineTrendRegime(str, Enum):
    """Market state produced by engine_trend."""

    UP = "UP"
    DOWN = "DOWN"
    FLAT = "FLAT"
    UNKNOWN = "UNKNOWN"


class TradeSignal(str, Enum):
    """Safety-locked trade signal enum.

    engine_trend is not allowed to produce trading instructions.
    """

    NOT_EVALUATED = "NOT_EVALUATED"


class BookSource(str, Enum):
    """Book/source group for evidence."""

    NISON = "NISON"
    ALTUNINA = "ALTUNINA"
    SCHWAGER = "SCHWAGER"
    ENGINE_TREND = "ENGINE_TREND"


@dataclass(frozen=True)
class EngineTrendCandle:
    """Single OHLCV candle used by engine_trend."""

    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    def __post_init__(self) -> None:
        numeric_values = {
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }
        for field_name, value in numeric_values.items():
            if not isinstance(value, int | float):
                raise TypeError(f"{field_name} must be numeric")
            if field_name == "volume" and value < 0:
                raise ValueError("volume must be non-negative")

        if self.high < max(self.open, self.close):
            raise ValueError("high must be >= max(open, close)")
        if self.low > min(self.open, self.close):
            raise ValueError("low must be <= min(open, close)")
        if self.high < self.low:
            raise ValueError("high must be >= low")

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "open": float(self.open),
            "high": float(self.high),
            "low": float(self.low),
            "close": float(self.close),
            "volume": float(self.volume),
        }


@dataclass(frozen=True)
class EngineTrendEvidence:
    """Single evidence item used to explain a regime decision."""

    source: BookSource
    code: str
    description: str
    contribution: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("evidence code must not be empty")
        if not -1.0 <= self.contribution <= 1.0:
            raise ValueError("evidence contribution must be within [-1.0, 1.0]")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source.value,
            "code": self.code,
            "description": self.description,
            "contribution": float(self.contribution),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class BookEvidence:
    """Grouped book evidence."""

    nison: tuple[EngineTrendEvidence, ...] = ()
    altunina: tuple[EngineTrendEvidence, ...] = ()
    schwager: tuple[EngineTrendEvidence, ...] = ()
    engine_trend: tuple[EngineTrendEvidence, ...] = ()

    def all_items(self) -> tuple[EngineTrendEvidence, ...]:
        return self.nison + self.altunina + self.schwager + self.engine_trend

    def reason_codes(self) -> tuple[str, ...]:
        return tuple(item.code for item in self.all_items())

    def to_dict(self) -> dict[str, list[dict[str, Any]]]:
        return {
            "nison": [item.to_dict() for item in self.nison],
            "altunina": [item.to_dict() for item in self.altunina],
            "schwager": [item.to_dict() for item in self.schwager],
            "engine_trend": [item.to_dict() for item in self.engine_trend],
        }


@dataclass(frozen=True)
class ConfidenceDecomposition:
    """Explains how final confidence was formed."""

    trend_score: float = 0.0
    range_score: float = 0.0
    candlestick_score: float = 0.0
    level_score: float = 0.0
    breakout_score: float = 0.0
    false_breakout_penalty: float = 0.0
    indicator_score: float = 0.0
    confluence_score: float = 0.0
    conflict_penalty: float = 0.0
    data_quality_penalty: float = 0.0

    def total(self) -> float:
        raw_total = (
            self.trend_score
            + self.range_score
            + self.candlestick_score
            + self.level_score
            + self.breakout_score
            + self.false_breakout_penalty
            + self.indicator_score
            + self.confluence_score
            + self.conflict_penalty
            + self.data_quality_penalty
        )
        return max(0.0, min(1.0, raw_total))

    def to_dict(self) -> dict[str, float]:
        return {
            "trend_score": float(self.trend_score),
            "range_score": float(self.range_score),
            "candlestick_score": float(self.candlestick_score),
            "level_score": float(self.level_score),
            "breakout_score": float(self.breakout_score),
            "false_breakout_penalty": float(self.false_breakout_penalty),
            "indicator_score": float(self.indicator_score),
            "confluence_score": float(self.confluence_score),
            "conflict_penalty": float(self.conflict_penalty),
            "data_quality_penalty": float(self.data_quality_penalty),
            "total": float(self.total()),
        }


@dataclass(frozen=True)
class EngineTrendSafety:
    """Safety contract for engine_trend outputs."""

    trade_signal: TradeSignal = TradeSignal.NOT_EVALUATED
    safe_for_runtime_trading: bool = False
    live_trading_connected: bool = False

    def __post_init__(self) -> None:
        if self.trade_signal is not TradeSignal.NOT_EVALUATED:
            raise ValueError("engine_trend must not emit trading signals")
        if self.safe_for_runtime_trading:
            raise ValueError("engine_trend must not be marked safe for runtime trading")
        if self.live_trading_connected:
            raise ValueError("engine_trend must not connect live trading")

    def to_dict(self) -> dict[str, Any]:
        return {
            "trade_signal": self.trade_signal.value,
            "safe_for_runtime_trading": self.safe_for_runtime_trading,
            "live_trading_connected": self.live_trading_connected,
        }


@dataclass(frozen=True)
class EngineTrendResult:
    """Final result contract for engine_trend."""

    symbol: str
    interval: str
    period_start: str | None
    period_end: str | None
    candle_count: int
    market_regime: EngineTrendRegime
    confidence: float
    book_evidence: BookEvidence = field(default_factory=BookEvidence)
    confidence_decomposition: ConfidenceDecomposition = field(
        default_factory=ConfidenceDecomposition
    )
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    safety: EngineTrendSafety = field(default_factory=EngineTrendSafety)

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("symbol must not be empty")
        if not self.interval:
            raise ValueError("interval must not be empty")
        if self.candle_count < 0:
            raise ValueError("candle_count must be non-negative")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be within [0.0, 1.0]")

    @property
    def reason_codes(self) -> tuple[str, ...]:
        return self.book_evidence.reason_codes()

    def to_dict(self) -> dict[str, Any]:
        return {
            "service": "ENGINE_TREND",
            "contract_version": "engine_trend_result_v1",
            "symbol": self.symbol,
            "interval": self.interval,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "candle_count": self.candle_count,
            "market_regime": self.market_regime.value,
            "confidence": float(self.confidence),
            "book_evidence": self.book_evidence.to_dict(),
            "reason_codes": list(self.reason_codes),
            "confidence_decomposition": self.confidence_decomposition.to_dict(),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "safety": self.safety.to_dict(),
        }