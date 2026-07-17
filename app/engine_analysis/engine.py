"""Public Python facade for the clean engine_analysis composer."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from app.engine_analysis.json_export import (
    build_engine_analysis_json_payload,
    build_engine_analysis_preview,
)
from app.engine_analysis.regime_composer import (
    RegimeComposerOutput,
    compose_engine_analysis_result,
)
from app.engine_analysis.schemas import EngineAnalysisCandle
from app.engine_analysis.analysis_contract import AnalysisWindowConfig


@dataclass(frozen=True)
class EngineAnalysisFacadeOutput:
    """Composer output together with presentation-ready representations."""

    symbol: str
    interval: str
    composer_output: RegimeComposerOutput
    preview: dict[str, object]
    json_payload: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "composer_output": self.composer_output.to_dict(),
            "preview": self.preview,
            "json_payload": self.json_payload,
        }


def _value(row: dict[str, object], canonical: str, *aliases: str) -> object:
    for key in (canonical, *aliases):
        if key in row:
            return row[key]
    raise ValueError(f"missing required candle field: {canonical}")


def normalize_candle_row(row: dict[str, object]) -> EngineAnalysisCandle:
    """Convert one canonical or aliased mapping into an engine candle."""
    if not isinstance(row, dict):
        raise ValueError("candle row must be a mapping")
    timestamp = _value(row, "timestamp", "time", "open_time")
    if timestamp is None or str(timestamp) == "":
        raise ValueError("timestamp must not be empty")
    try:
        candle = EngineAnalysisCandle(
            timestamp=str(timestamp),
            open=float(_value(row, "open", "o")),
            high=float(_value(row, "high", "h")),
            low=float(_value(row, "low", "l")),
            close=float(_value(row, "close", "c")),
            volume=float(row.get("volume", row.get("v", 0.0))),
        )
        # Real market rows must use a positive price scale. Low-level pattern
        # tests may still instantiate EngineAnalysisCandle directly with a
        # normalized zero baseline.
        values = (candle.open, candle.high, candle.low, candle.close, candle.volume)
        if not all(isfinite(value) for value in values):
            raise ValueError("market OHLCV values must be finite")
        if min(candle.open, candle.high, candle.low, candle.close) <= 0.0:
            raise ValueError("market prices must be positive")
        return candle
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid candle row: {exc}") from exc


def normalize_candles(
    rows: tuple[dict[str, object], ...] | list[dict[str, object]],
) -> tuple[EngineAnalysisCandle, ...]:
    """Normalize a candle sequence while preserving its order."""
    return tuple(normalize_candle_row(row) for row in rows)


def run_engine_analysis(
    symbol: str,
    interval: str,
    candles: tuple[EngineAnalysisCandle, ...] | list[EngineAnalysisCandle],
    *,
    config: AnalysisWindowConfig | None = None,
    strict_market_series: bool = True,
) -> EngineAnalysisFacadeOutput:
    """Run the composer and build its two presentation forms."""
    contract = config or AnalysisWindowConfig()
    composer_output = compose_engine_analysis_result(
        symbol,
        interval,
        candles,
        config=contract,
        strict_timestamps=strict_market_series,
    )
    return EngineAnalysisFacadeOutput(
        symbol=composer_output.result.symbol,
        interval=composer_output.result.interval,
        composer_output=composer_output,
        preview=build_engine_analysis_preview(composer_output),
        json_payload=build_engine_analysis_json_payload(composer_output),
    )


def run_engine_analysis_from_rows(
    symbol: str,
    interval: str,
    rows: tuple[dict[str, object], ...] | list[dict[str, object]],
    *,
    config: AnalysisWindowConfig | None = None,
) -> EngineAnalysisFacadeOutput:
    """Normalize mapping rows and run the engine facade."""
    return run_engine_analysis(
        symbol,
        interval,
        normalize_candles(rows),
        config=config,
        strict_market_series=True,
    )
