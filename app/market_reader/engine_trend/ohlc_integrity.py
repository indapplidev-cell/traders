"""OHLC integrity checks for engine_trend input candles."""

from __future__ import annotations

from dataclasses import dataclass

from app.market_reader.engine_trend.schemas import EngineTrendCandle


@dataclass(frozen=True)
class OHLCIntegrityResult:
    """Result of checking input candle integrity."""

    is_valid: bool
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def status(self) -> str:
        if self.errors:
            return "FAIL"
        if self.warnings:
            return "PASS_WITH_WARNINGS"
        return "PASS"

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "is_valid": self.is_valid,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


def validate_ohlc_integrity(
    candles: tuple[EngineTrendCandle, ...] | list[EngineTrendCandle],
) -> OHLCIntegrityResult:
    """Validate basic OHLC integrity."""

    errors: list[str] = []
    warnings: list[str] = []

    if not candles:
        return OHLCIntegrityResult(
            is_valid=False,
            errors=("NO_CANDLES_PROVIDED",),
        )

    seen_timestamps: set[str] = set()
    previous_timestamp: str | None = None

    for index, candle in enumerate(candles):
        if candle.timestamp in seen_timestamps:
            warnings.append(f"DUPLICATE_TIMESTAMP:{candle.timestamp}")
        seen_timestamps.add(candle.timestamp)

        if previous_timestamp is not None and candle.timestamp < previous_timestamp:
            errors.append(f"TIMESTAMP_ORDER_ERROR:index={index}")

        previous_timestamp = candle.timestamp

        if candle.high < max(candle.open, candle.close):
            errors.append(f"HIGH_BELOW_BODY:index={index}")

        if candle.low > min(candle.open, candle.close):
            errors.append(f"LOW_ABOVE_BODY:index={index}")

        if candle.high < candle.low:
            errors.append(f"HIGH_BELOW_LOW:index={index}")

        if candle.volume < 0:
            errors.append(f"NEGATIVE_VOLUME:index={index}")

    return OHLCIntegrityResult(
        is_valid=not errors,
        warnings=tuple(warnings),
        errors=tuple(errors),
    )
