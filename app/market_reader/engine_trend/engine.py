"""Public Python facade for the clean engine_trend composer."""

from __future__ import annotations

from dataclasses import dataclass

from app.market_reader.engine_trend.json_export import (
    build_engine_trend_json_payload,
    build_engine_trend_preview,
)
from app.market_reader.engine_trend.regime_composer import (
    RegimeComposerOutput,
    compose_engine_trend_result,
)
from app.market_reader.engine_trend.schemas import EngineTrendCandle


@dataclass(frozen=True)
class EngineTrendFacadeOutput:
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


def normalize_candle_row(row: dict[str, object]) -> EngineTrendCandle:
    """Convert one canonical or aliased mapping into an engine candle."""
    if not isinstance(row, dict):
        raise ValueError("candle row must be a mapping")
    timestamp = _value(row, "timestamp", "time", "open_time")
    if timestamp is None or str(timestamp) == "":
        raise ValueError("timestamp must not be empty")
    try:
        return EngineTrendCandle(
            timestamp=str(timestamp),
            open=float(_value(row, "open", "o")),
            high=float(_value(row, "high", "h")),
            low=float(_value(row, "low", "l")),
            close=float(_value(row, "close", "c")),
            volume=float(row.get("volume", row.get("v", 0.0))),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid candle row: {exc}") from exc


def normalize_candles(
    rows: tuple[dict[str, object], ...] | list[dict[str, object]],
) -> tuple[EngineTrendCandle, ...]:
    """Normalize a candle sequence while preserving its order."""
    return tuple(normalize_candle_row(row) for row in rows)


def run_engine_trend(
    symbol: str,
    interval: str,
    candles: tuple[EngineTrendCandle, ...] | list[EngineTrendCandle],
) -> EngineTrendFacadeOutput:
    """Run the composer and build its two presentation forms."""
    composer_output = compose_engine_trend_result(symbol, interval, candles)
    return EngineTrendFacadeOutput(
        symbol=composer_output.result.symbol,
        interval=composer_output.result.interval,
        composer_output=composer_output,
        preview=build_engine_trend_preview(composer_output),
        json_payload=build_engine_trend_json_payload(composer_output),
    )


def run_engine_trend_from_rows(
    symbol: str,
    interval: str,
    rows: tuple[dict[str, object], ...] | list[dict[str, object]],
) -> EngineTrendFacadeOutput:
    """Normalize mapping rows and run the engine facade."""
    return run_engine_trend(symbol, interval, normalize_candles(rows))
