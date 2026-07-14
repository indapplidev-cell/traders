"""OHLC integrity checks for engine_trend input candles."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from app.market_reader.engine_trend.analysis_contract import (
    AnalysisReadiness,
    AnalysisWindowConfig,
    analysis_readiness,
    interval_duration,
    parse_market_timestamp,
)
from app.market_reader.engine_trend.schemas import EngineTrendCandle


@dataclass(frozen=True)
class OHLCIntegrityResult:
    """Result of checking input candle integrity."""

    is_valid: bool
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    readiness: AnalysisReadiness = AnalysisReadiness.FULL
    expected_interval_seconds: float | None = None
    missing_candle_count: int = 0

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
            "readiness": self.readiness.value,
            "expected_interval_seconds": self.expected_interval_seconds,
            "missing_candle_count": self.missing_candle_count,
        }


def validate_ohlc_integrity(
    candles: tuple[EngineTrendCandle, ...] | list[EngineTrendCandle],
    *,
    interval: str | None = None,
    config: AnalysisWindowConfig | None = None,
    strict_timestamps: bool = False,
) -> OHLCIntegrityResult:
    """Validate basic OHLC integrity."""

    errors: list[str] = []
    warnings: list[str] = []

    if not candles:
        return OHLCIntegrityResult(
            is_valid=False,
            errors=("NO_CANDLES_PROVIDED",),
        )

    contract = config
    readiness = (
        analysis_readiness(len(candles), contract)
        if contract is not None
        else AnalysisReadiness.FULL
    )
    if contract is not None and readiness is AnalysisReadiness.PARTIAL:
        warnings.append(
            f"MIN_FULL_ANALYSIS_CANDLES_NOT_MET:{len(candles)}<{contract.minimum_candles}"
        )

    seen_timestamps: set[str] = set()
    previous_timestamp: str | None = None
    parsed_timestamps = []

    for index, candle in enumerate(candles):
        if candle.timestamp in seen_timestamps:
            warnings.append(f"DUPLICATE_TIMESTAMP:{candle.timestamp}")
        seen_timestamps.add(candle.timestamp)

        if previous_timestamp is not None and candle.timestamp < previous_timestamp:
            errors.append(f"TIMESTAMP_ORDER_ERROR:index={index}")

        previous_timestamp = candle.timestamp

        values = {
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume,
        }
        for field_name, value in values.items():
            if not isfinite(float(value)):
                errors.append(f"NON_FINITE_{field_name.upper()}:index={index}")
        for field_name in ("open", "high", "low", "close"):
            if float(values[field_name]) <= 0.0:
                errors.append(f"NON_POSITIVE_{field_name.upper()}:index={index}")

        if strict_timestamps:
            try:
                parsed_timestamps.append(parse_market_timestamp(candle.timestamp))
            except ValueError:
                errors.append(f"TIMESTAMP_PARSE_ERROR:index={index}")

        if candle.high < max(candle.open, candle.close):
            errors.append(f"HIGH_BELOW_BODY:index={index}")

        if candle.low > min(candle.open, candle.close):
            errors.append(f"LOW_ABOVE_BODY:index={index}")

        if candle.high < candle.low:
            errors.append(f"HIGH_BELOW_LOW:index={index}")

        if candle.volume < 0:
            errors.append(f"NEGATIVE_VOLUME:index={index}")

    expected_seconds: float | None = None
    missing_count = 0
    if strict_timestamps and interval is not None:
        try:
            expected_seconds = interval_duration(interval).total_seconds()
        except ValueError:
            errors.append(f"INTERVAL_PARSE_ERROR:{interval}")
        if expected_seconds is not None and len(parsed_timestamps) == len(candles):
            for index, (previous, current) in enumerate(
                zip(parsed_timestamps, parsed_timestamps[1:]), start=1
            ):
                delta = (current - previous).total_seconds()
                if delta <= 0:
                    errors.append(f"TIMESTAMP_ORDER_ERROR:index={index}")
                elif delta != expected_seconds:
                    if delta > expected_seconds:
                        missing = max(0, round(delta / expected_seconds) - 1)
                        missing_count += missing
                        errors.append(
                            f"CANDLE_GAP:index={index}:seconds={delta}:missing={missing}"
                        )
                    else:
                        errors.append(
                            f"IRREGULAR_CADENCE:index={index}:seconds={delta}"
                        )

    return OHLCIntegrityResult(
        is_valid=not errors,
        warnings=tuple(warnings),
        errors=tuple(errors),
        readiness=readiness,
        expected_interval_seconds=expected_seconds,
        missing_candle_count=missing_count,
    )
