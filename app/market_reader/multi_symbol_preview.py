from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from app.market_reader.api_response import build_book_l1_api_response_payload


DEFAULT_MULTI_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
TRADE_SIGNAL_NOT_EVALUATED = "NOT_EVALUATED"
MANUAL_REFERENCE_DATE_UNSUPPORTED = "Manual reference date is not supported yet by repository method"

_SYMBOL_ALIASES = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
}


@dataclass(frozen=True)
class MultiSymbolPreviewConfig:
    symbols: tuple[str, ...] = DEFAULT_MULTI_SYMBOLS
    interval: str = "15m"
    limit: int = 300
    min_candles: int = 50
    reference_mode: str = "latest"
    reference_date: str | None = None

    def __post_init__(self) -> None:
        symbols = normalize_symbols(self.symbols)
        if not symbols:
            raise ValueError("symbols must not be empty")
        if not self.interval or not self.interval.strip():
            raise ValueError("interval must not be empty")
        if self.limit <= 0:
            raise ValueError("limit must be positive")
        if self.min_candles <= 0:
            raise ValueError("min_candles must be positive")
        if self.limit < self.min_candles:
            raise ValueError("limit must be greater than or equal to min_candles")

        reference_mode = self.reference_mode.strip().lower()
        if reference_mode not in {"latest", "manual"}:
            raise ValueError("reference_mode must be latest or manual")
        if reference_mode == "manual" and not self.reference_date:
            raise ValueError("reference_date is required for manual reference mode")

        object.__setattr__(self, "symbols", symbols)
        object.__setattr__(self, "interval", self.interval.strip())
        object.__setattr__(self, "reference_mode", reference_mode)


@dataclass(frozen=True)
class SymbolPreviewRow:
    symbol: str
    status: str
    market_regime: str
    directional_bias: str
    confidence: float
    trend_strength: str
    volatility_context: str
    trade_signal: str
    safe_for_runtime_trading: bool
    candle_count: int = 0
    first_open_time: str | None = None
    last_open_time: str | None = None
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    warning: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", normalize_symbol(self.symbol))
        object.__setattr__(self, "status", self.status.strip().upper())
        object.__setattr__(self, "market_regime", self.market_regime.strip().upper())
        object.__setattr__(self, "directional_bias", self.directional_bias.strip().upper())
        object.__setattr__(self, "trend_strength", self.trend_strength.strip().upper())
        object.__setattr__(self, "volatility_context", self.volatility_context.strip().upper())
        object.__setattr__(self, "trade_signal", self.trade_signal.strip().upper())
        object.__setattr__(self, "reason_codes", tuple(str(item) for item in self.reason_codes))

        if self.trade_signal != TRADE_SIGNAL_NOT_EVALUATED:
            raise ValueError("BOOK-L1 multi-symbol preview must not expose trading signals")
        if self.safe_for_runtime_trading is not False:
            raise ValueError("BOOK-L1 multi-symbol preview must not approve runtime trading")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")


@dataclass(frozen=True)
class MultiSymbolPreviewResult:
    config: MultiSymbolPreviewConfig
    rows: tuple[SymbolPreviewRow, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "rows", tuple(self.rows))
        object.__setattr__(self, "warnings", tuple(str(item) for item in self.warnings))


class MultiSymbolPreviewRunner:
    def __init__(self, *, candle_repository: Any, reader: Any | None = None) -> None:
        self._candle_repository = candle_repository
        self._reader = reader

    def run(self, config: MultiSymbolPreviewConfig) -> MultiSymbolPreviewResult:
        rows: list[SymbolPreviewRow] = []
        warnings: list[str] = []

        for symbol in config.symbols:
            row = self._build_row(symbol=symbol, config=config)
            rows.append(row)
            if row.warning:
                warnings.append(f"{row.symbol}: {row.warning}")

        return MultiSymbolPreviewResult(
            config=config,
            rows=tuple(rows),
            warnings=tuple(warnings),
        )

    def _build_row(self, *, symbol: str, config: MultiSymbolPreviewConfig) -> SymbolPreviewRow:
        if config.reference_mode != "latest":
            return _error_row(symbol, MANUAL_REFERENCE_DATE_UNSUPPORTED)

        try:
            payload = build_book_l1_api_response_payload(
                symbol=symbol,
                interval=config.interval,
                limit=config.limit,
                min_candles=config.min_candles,
                candle_repository=self._candle_repository,
                reader=self._reader,
            )
        except Exception as exc:
            message = str(exc)
            if "not enough candles" in message:
                message = "not enough candles or no local candles found."
            return _error_row(symbol, message or "preview failed.")

        if payload.get("status") != "ok":
            return _error_row(symbol, _join_messages(payload.get("errors")) or "preview returned error status.")

        preview = _mapping_or_empty(payload.get("preview"))
        analysis = _mapping_or_empty(preview.get("analysis"))

        return SymbolPreviewRow(
            symbol=symbol,
            status="OK",
            market_regime=_string_field(analysis, "market_regime", "UNKNOWN"),
            directional_bias=_string_field(analysis, "directional_bias", "UNKNOWN"),
            confidence=_float_field(analysis, "confidence", 0.0),
            trend_strength=_string_field(analysis, "trend_strength", "UNKNOWN"),
            volatility_context=_derive_volatility_context(analysis.get("reason_codes")),
            trade_signal=_string_field(analysis, "trade_signal", TRADE_SIGNAL_NOT_EVALUATED),
            safe_for_runtime_trading=bool(analysis.get("safe_for_runtime_trading")),
            candle_count=int(preview.get("candle_count") or 0),
            first_open_time=_optional_string(preview.get("first_open_time")),
            last_open_time=_optional_string(preview.get("last_open_time")),
            reason_codes=tuple(str(item) for item in _sequence_or_empty(analysis.get("reason_codes"))),
        )


class MultiSymbolTableFormatter:
    def format_result(self, result: MultiSymbolPreviewResult) -> str:
        config = result.config
        lines = [
            "BOOK-L1 Multi-Symbol Market Reader - Result",
            "",
            f"Interval: {config.interval}",
            f"Range: last {config.limit} candles",
            f"Reference date: {_format_reference_date(config)}",
            "",
            self.format_table(result.rows),
            "",
            self.format_summary(result),
        ]

        if result.warnings:
            lines.extend(["", self.format_warnings(result.warnings)])

        lines.extend(["", self.format_safety()])
        return "\n".join(lines)

    def format_table(self, rows: Sequence[SymbolPreviewRow]) -> str:
        headers = (
            "Symbol",
            "Status",
            "Regime",
            "Bias",
            "Confidence",
            "Trend",
            "Vol",
            "Trade signal",
            "Runtime trading",
        )
        body = [
            (
                row.symbol,
                row.status,
                row.market_regime,
                row.directional_bias,
                f"{row.confidence:.2f}",
                row.trend_strength,
                row.volatility_context,
                row.trade_signal,
                _format_bool(row.safe_for_runtime_trading),
            )
            for row in rows
        ]
        return _format_grid(headers, body)

    def format_summary(self, result: MultiSymbolPreviewResult) -> str:
        summary = calculate_summary(result.rows)
        return "\n".join(
            [
                "Summary:",
                "",
                f"UP: {summary['UP']}",
                f"DOWN: {summary['DOWN']}",
                f"FLAT: {summary['FLAT']}",
                f"UNKNOWN: {summary['UNKNOWN']}",
                f"Errors: {summary['Errors']}",
            ]
        )

    def format_warnings(self, warnings: Sequence[str]) -> str:
        lines = ["Warnings:", ""]
        lines.extend(f"- {warning}" for warning in warnings)
        return "\n".join(lines)

    def format_safety(self) -> str:
        return "\n".join(
            [
                "Safety:",
                "",
                "trade_signal: NOT_EVALUATED",
                "safe_for_runtime_trading: false",
                "orders_enabled: false",
                "live_trading_connected: false",
                "approved_for_live_trading: false",
                "approved_for_auto_activation: false",
            ]
        )

    def format_details(self, rows: Sequence[SymbolPreviewRow]) -> str:
        return "\n\n".join(self.format_symbol_details(row) for row in rows)

    def format_symbol_details(self, row: SymbolPreviewRow) -> str:
        lines = [
            f"{row.symbol} details",
            "",
            "Window:",
            f"{_format_open_time(row.first_open_time)} -> {_format_open_time(row.last_open_time)}",
            f"Candles: {row.candle_count}",
            "",
            "Main result:",
            f"Market regime: {row.market_regime}",
            f"Directional bias: {row.directional_bias}",
            f"Confidence: {row.confidence:.2f}",
            f"Trend strength: {row.trend_strength}",
        ]

        if row.warning:
            lines.extend(["", f"Warning: {row.warning}"])

        lines.extend(["", "Reason codes:"])
        if row.reason_codes:
            lines.extend(f"- {reason_code}" for reason_code in row.reason_codes)
        else:
            lines.append("- N/A")

        return "\n".join(lines)


def normalize_symbol(value: str) -> str:
    token = str(value).strip().upper().replace(" ", "")
    if not token:
        raise ValueError("symbol must not be empty")
    return _SYMBOL_ALIASES.get(token, token)


def parse_symbols(value: str) -> tuple[str, ...]:
    return normalize_symbols(tuple(item for item in value.split(",")))


def normalize_symbols(values: Sequence[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        symbol = normalize_symbol(value)
        if symbol not in seen:
            seen.add(symbol)
            normalized.append(symbol)
    return tuple(normalized)


def calculate_summary(rows: Sequence[SymbolPreviewRow]) -> dict[str, int]:
    summary = {
        "UP": 0,
        "DOWN": 0,
        "FLAT": 0,
        "UNKNOWN": 0,
        "Errors": 0,
    }
    for row in rows:
        regime = row.market_regime if row.market_regime in {"UP", "DOWN", "FLAT"} else "UNKNOWN"
        summary[regime] += 1
        if row.status != "OK":
            summary["Errors"] += 1
    return summary


def _error_row(symbol: str, warning: str) -> SymbolPreviewRow:
    return SymbolPreviewRow(
        symbol=symbol,
        status="ERROR",
        market_regime="UNKNOWN",
        directional_bias="UNKNOWN",
        confidence=0.0,
        trend_strength="UNKNOWN",
        volatility_context="N/A",
        trade_signal=TRADE_SIGNAL_NOT_EVALUATED,
        safe_for_runtime_trading=False,
        warning=warning,
    )


def _derive_volatility_context(reason_codes: Any) -> str:
    reasons = {str(item).upper() for item in _sequence_or_empty(reason_codes)}
    if "ATR_HIGH_VOLATILITY" in reasons:
        return "HIGH"
    if "ATR_LOW_VOLATILITY" in reasons:
        return "LOW"
    if "ATR_NORMAL_VOLATILITY" in reasons:
        return "NORMAL"
    return "UNKNOWN"


def _format_reference_date(config: MultiSymbolPreviewConfig) -> str:
    if config.reference_mode == "manual":
        return config.reference_date or "manual"
    return "latest available candle"


def _format_grid(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    widths = [
        max(len(header), *(len(str(row[index])) for row in rows)) if rows else len(header)
        for index, header in enumerate(headers)
    ]
    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"
    lines = [
        border,
        "| " + " | ".join(header.ljust(widths[index]) for index, header in enumerate(headers)) + " |",
        border,
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value).ljust(widths[index]) for index, value in enumerate(row)) + " |")
    lines.append(border)
    return "\n".join(lines)


def _mapping_or_empty(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _sequence_or_empty(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Sequence):
        return tuple(value)
    return (value,)


def _join_messages(value: Any) -> str:
    return "; ".join(str(item) for item in _sequence_or_empty(value))


def _string_field(source: Mapping[str, Any], field_name: str, default: str) -> str:
    return str(source.get(field_name) or default)


def _float_field(source: Mapping[str, Any], field_name: str, default: float) -> float:
    try:
        return float(source.get(field_name, default))
    except (TypeError, ValueError):
        return default


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _format_bool(value: bool) -> str:
    return "true" if value else "false"


def _format_open_time(value: str | None) -> str:
    if value is None:
        return "N/A"
    return value.replace("T", " ").replace("+00:00", "")
