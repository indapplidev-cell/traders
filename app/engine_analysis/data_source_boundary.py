"""Storage-neutral candle provider boundary for engine_analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

from app.engine_analysis.engine import (
    EngineAnalysisFacadeOutput,
    normalize_candles,
    run_engine_analysis,
)
from app.engine_analysis.analysis_contract import (
    MIN_FULL_ANALYSIS_CANDLES,
    AnalysisWindowConfig,
)
from app.engine_analysis.ohlc_integrity import validate_ohlc_integrity
from app.engine_analysis.schemas import EngineAnalysisCandle


class CandleDataBoundaryStatus(str, Enum):
    READY = "READY"
    EMPTY = "EMPTY"
    INVALID_REQUEST = "INVALID_REQUEST"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    VALIDATION_FAILED = "VALIDATION_FAILED"


class CandleDataQualityFlag(str, Enum):
    EMPTY_BATCH = "EMPTY_BATCH"
    SYMBOL_MISMATCH = "SYMBOL_MISMATCH"
    INTERVAL_MISMATCH = "INTERVAL_MISMATCH"
    UNSORTED_TIMESTAMPS = "UNSORTED_TIMESTAMPS"
    DUPLICATE_TIMESTAMPS = "DUPLICATE_TIMESTAMPS"
    CANDLE_NORMALIZATION_FAILED = "CANDLE_NORMALIZATION_FAILED"
    MIN_CANDLE_COUNT_NOT_MET = "MIN_CANDLE_COUNT_NOT_MET"
    INVALID_TIMESTAMP = "INVALID_TIMESTAMP"
    IRREGULAR_CADENCE = "IRREGULAR_CADENCE"
    MISSING_CANDLES = "MISSING_CANDLES"
    NON_FINITE_VALUE = "NON_FINITE_VALUE"
    NON_POSITIVE_PRICE = "NON_POSITIVE_PRICE"


@dataclass(frozen=True)
class CandleDataRequest:
    symbol: str
    interval: str
    limit: int
    start_time: str | None = None
    end_time: str | None = None
    source_name: str = "external_provider"

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "limit": self.limit,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "source_name": self.source_name,
        }


@dataclass(frozen=True)
class CandleDataBatch:
    request: CandleDataRequest
    rows: tuple[dict[str, object], ...] = ()
    candles: tuple[EngineAnalysisCandle, ...] = ()
    status: CandleDataBoundaryStatus = CandleDataBoundaryStatus.EMPTY
    quality_flags: tuple[CandleDataQualityFlag, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "request": self.request.to_dict(),
            "rows": [dict(row) for row in self.rows],
            "candles": [candle.to_dict() for candle in self.candles],
            "status": self.status.value,
            "quality_flags": [flag.value for flag in self.quality_flags],
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class CandleDataBoundaryResult:
    request: CandleDataRequest
    batch: CandleDataBatch
    engine_output: EngineAnalysisFacadeOutput
    status: CandleDataBoundaryStatus
    quality_flags: tuple[CandleDataQualityFlag, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "request": self.request.to_dict(),
            "batch": self.batch.to_dict(),
            "engine_output": self.engine_output.to_dict(),
            "status": self.status.value,
            "quality_flags": [flag.value for flag in self.quality_flags],
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


class CandleDataProvider(Protocol):
    def load_rows(
        self, request: CandleDataRequest
    ) -> tuple[dict[str, object], ...]: ...


def validate_candle_data_request(request: CandleDataRequest) -> tuple[str, ...]:
    errors: list[str] = []
    if not request.symbol.strip():
        errors.append("REQUEST_SYMBOL_EMPTY")
    if not request.interval.strip():
        errors.append("REQUEST_INTERVAL_EMPTY")
    if request.limit <= 0:
        errors.append("REQUEST_LIMIT_NOT_POSITIVE")
    return tuple(errors)


def _metadata(
    request: CandleDataRequest,
    rows: tuple[dict[str, object], ...],
    candles: tuple[EngineAnalysisCandle, ...],
    min_candle_count: int,
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "row_count": len(rows),
        "candle_count": len(candles),
        "source_name": request.source_name,
        "min_candle_count": min_candle_count,
    }
    if candles:
        metadata["period_start"] = candles[0].timestamp
        metadata["period_end"] = candles[-1].timestamp
    return metadata


def build_candle_data_batch(
    request: CandleDataRequest,
    rows: tuple[dict[str, object], ...] | list[dict[str, object]],
    *,
    min_candle_count: int = 1,
    strict_market_series: bool = True,
) -> CandleDataBatch:
    raw_rows = tuple(rows)
    request_errors = validate_candle_data_request(request)
    if request_errors:
        return CandleDataBatch(
            request=request,
            rows=raw_rows,
            status=CandleDataBoundaryStatus.INVALID_REQUEST,
            errors=request_errors,
            metadata=_metadata(request, raw_rows, (), min_candle_count),
        )

    try:
        candles = normalize_candles(raw_rows)
    except (TypeError, ValueError, KeyError) as exc:
        return CandleDataBatch(
            request=request,
            rows=raw_rows,
            status=CandleDataBoundaryStatus.VALIDATION_FAILED,
            quality_flags=(CandleDataQualityFlag.CANDLE_NORMALIZATION_FAILED,),
            errors=("CANDLE_NORMALIZATION_FAILED", str(exc)),
            metadata=_metadata(request, raw_rows, (), min_candle_count),
        )

    flags: list[CandleDataQualityFlag] = []
    warnings: list[str] = []
    if not candles:
        flags.append(CandleDataQualityFlag.EMPTY_BATCH)
        warnings.append("EMPTY_BATCH")
    if len(candles) < min_candle_count:
        flags.append(CandleDataQualityFlag.MIN_CANDLE_COUNT_NOT_MET)
        warnings.append("MIN_CANDLE_COUNT_NOT_MET")

    timestamps = tuple(candle.timestamp for candle in candles)
    if timestamps != tuple(sorted(timestamps)):
        flags.append(CandleDataQualityFlag.UNSORTED_TIMESTAMPS)
        warnings.append("UNSORTED_TIMESTAMPS")
    if len(timestamps) != len(set(timestamps)):
        flags.append(CandleDataQualityFlag.DUPLICATE_TIMESTAMPS)
        warnings.append("DUPLICATE_TIMESTAMPS")

    for row in raw_rows:
        row_symbol = row.get("symbol")
        if row_symbol is not None and str(row_symbol) != request.symbol:
            flags.append(CandleDataQualityFlag.SYMBOL_MISMATCH)
            warnings.append("SYMBOL_MISMATCH")
            break

    integrity = validate_ohlc_integrity(
        candles,
        interval=request.interval,
        config=AnalysisWindowConfig(
            minimum_candles=max(8, min_candle_count),
            context_candles=max(96, max(8, min_candle_count)),
        ),
        strict_timestamps=strict_market_series,
    )
    for error in integrity.errors:
        if error.startswith("TIMESTAMP_PARSE_ERROR"):
            flags.append(CandleDataQualityFlag.INVALID_TIMESTAMP)
        elif error.startswith("CANDLE_GAP"):
            flags.append(CandleDataQualityFlag.MISSING_CANDLES)
        elif error.startswith("IRREGULAR_CADENCE"):
            flags.append(CandleDataQualityFlag.IRREGULAR_CADENCE)
        elif error.startswith("NON_FINITE"):
            flags.append(CandleDataQualityFlag.NON_FINITE_VALUE)
        elif error.startswith("NON_POSITIVE"):
            flags.append(CandleDataQualityFlag.NON_POSITIVE_PRICE)
    if integrity.errors:
        warnings.extend(integrity.errors)
    for row in raw_rows:
        row_interval = row.get("interval")
        if row_interval is not None and str(row_interval) != request.interval:
            flags.append(CandleDataQualityFlag.INTERVAL_MISMATCH)
            warnings.append("INTERVAL_MISMATCH")
            break

    return CandleDataBatch(
        request=request,
        rows=raw_rows,
        candles=candles,
        status=(
            CandleDataBoundaryStatus.EMPTY
            if not candles
            else CandleDataBoundaryStatus.VALIDATION_FAILED
            if strict_market_series and integrity.errors
            else CandleDataBoundaryStatus.READY
        ),
        quality_flags=tuple(flags),
        warnings=tuple(warnings),
        errors=integrity.errors if strict_market_series else (),
        metadata=_metadata(request, raw_rows, candles, min_candle_count),
    )


def _run_batch(batch: CandleDataBatch) -> EngineAnalysisFacadeOutput:
    symbol = batch.request.symbol or "UNKNOWN"
    interval = batch.request.interval or "UNKNOWN"
    return run_engine_analysis(symbol, interval, batch.candles)


def run_engine_analysis_from_batch(
    batch: CandleDataBatch,
) -> CandleDataBoundaryResult:
    return CandleDataBoundaryResult(
        request=batch.request,
        batch=batch,
        engine_output=_run_batch(batch),
        status=batch.status,
        quality_flags=batch.quality_flags,
        warnings=batch.warnings,
        errors=batch.errors,
    )


def run_engine_analysis_from_provider(
    provider: CandleDataProvider,
    request: CandleDataRequest,
    *,
    min_candle_count: int = MIN_FULL_ANALYSIS_CANDLES,
) -> CandleDataBoundaryResult:
    try:
        rows = provider.load_rows(request)
    except Exception as exc:
        batch = CandleDataBatch(
            request=request,
            status=CandleDataBoundaryStatus.PROVIDER_ERROR,
            errors=("PROVIDER_ERROR", str(exc)),
            metadata=_metadata(request, (), (), min_candle_count),
        )
        return run_engine_analysis_from_batch(batch)
    batch = build_candle_data_batch(
        request, rows, min_candle_count=min_candle_count
    )
    return run_engine_analysis_from_batch(batch)
