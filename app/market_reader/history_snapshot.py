from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.market_reader.candle_window import CandleWindow
from app.market_reader.market_reader import MarketReaderOrchestrator
from app.market_reader.multi_symbol_preview import (
    DEFAULT_MULTI_SYMBOLS,
    TRADE_SIGNAL_NOT_EVALUATED,
    normalize_symbol,
    normalize_symbols,
    parse_symbols,
)


HISTORY_SAFETY_LOCKED = "LOCKED"
HISTORY_TRANSITIONS = (
    "NO_CHANGE",
    "FLAT_TO_UP",
    "FLAT_TO_DOWN",
    "UP_TO_FLAT",
    "DOWN_TO_FLAT",
    "UP_TO_DOWN",
    "DOWN_TO_UP",
    "UNKNOWN_TO_UP",
    "UNKNOWN_TO_DOWN",
    "UNKNOWN_TO_FLAT",
    "TO_UNKNOWN",
    "OTHER_CHANGE",
    "ERROR",
)


@dataclass(frozen=True)
class HistorySnapshotConfig:
    symbols: tuple[str, ...] = DEFAULT_MULTI_SYMBOLS
    interval: str = "15m"
    limit: int = 300
    min_candles: int = 50
    reference_mode: str = "latest"

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
        if reference_mode != "latest":
            raise ValueError("BOOK-L1 history snapshot currently supports latest reference mode only")

        object.__setattr__(self, "symbols", symbols)
        object.__setattr__(self, "interval", self.interval.strip())
        object.__setattr__(self, "reference_mode", reference_mode)

    @property
    def required_candles_per_symbol(self) -> int:
        return self.limit * 2


@dataclass(frozen=True)
class RegimeWindowSnapshot:
    symbol: str
    window_name: str
    market_regime: str
    directional_bias: str
    confidence: float
    trend_strength: str
    trade_signal: str
    safe_for_runtime_trading: bool
    candle_count: int
    first_open_time: str | None = None
    last_open_time: str | None = None
    reason_codes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", normalize_symbol(self.symbol))
        object.__setattr__(self, "window_name", self.window_name.strip().lower())
        object.__setattr__(self, "market_regime", _normalize_token(self.market_regime))
        object.__setattr__(self, "directional_bias", _normalize_token(self.directional_bias))
        object.__setattr__(self, "trend_strength", _normalize_token(self.trend_strength))
        object.__setattr__(self, "trade_signal", _normalize_token(self.trade_signal))
        object.__setattr__(self, "reason_codes", tuple(str(item) for item in self.reason_codes))

        if self.trade_signal != TRADE_SIGNAL_NOT_EVALUATED:
            raise ValueError("BOOK-L1 history snapshot must not expose trading signals")
        if self.safe_for_runtime_trading is not False:
            raise ValueError("BOOK-L1 history snapshot must not approve runtime trading")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if self.candle_count < 0:
            raise ValueError("candle_count must be non-negative")


@dataclass(frozen=True)
class RegimeTransitionRow:
    symbol: str
    status: str
    previous_regime: str
    current_regime: str
    transition: str
    previous_confidence: float
    current_confidence: float
    current_trend_strength: str
    trade_signal: str
    safe_for_runtime_trading: bool
    warning: str | None = None
    previous_snapshot: RegimeWindowSnapshot | None = None
    current_snapshot: RegimeWindowSnapshot | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", normalize_symbol(self.symbol))
        object.__setattr__(self, "status", _normalize_token(self.status))
        object.__setattr__(self, "previous_regime", _normalize_token(self.previous_regime))
        object.__setattr__(self, "current_regime", _normalize_token(self.current_regime))
        object.__setattr__(self, "transition", _normalize_token(self.transition))
        object.__setattr__(self, "current_trend_strength", _normalize_token(self.current_trend_strength))
        object.__setattr__(self, "trade_signal", _normalize_token(self.trade_signal))

        if self.transition not in HISTORY_TRANSITIONS:
            raise ValueError(f"unsupported transition: {self.transition}")
        if self.trade_signal != TRADE_SIGNAL_NOT_EVALUATED:
            raise ValueError("BOOK-L1 history snapshot must not expose trading signals")
        if self.safe_for_runtime_trading is not False:
            raise ValueError("BOOK-L1 history snapshot must not approve runtime trading")
        if not 0.0 <= float(self.previous_confidence) <= 1.0:
            raise ValueError("previous_confidence must be between 0.0 and 1.0")
        if not 0.0 <= float(self.current_confidence) <= 1.0:
            raise ValueError("current_confidence must be between 0.0 and 1.0")


@dataclass(frozen=True)
class HistorySnapshotResult:
    config: HistorySnapshotConfig
    rows: tuple[RegimeTransitionRow, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "rows", tuple(self.rows))
        object.__setattr__(self, "warnings", tuple(str(item) for item in self.warnings))


class HistorySnapshotRunner:
    def __init__(
        self,
        *,
        candle_repository: Any,
        market_reader: Any | None = None,
    ) -> None:
        self._candle_repository = candle_repository
        self._market_reader = market_reader or MarketReaderOrchestrator()

    def run(self, config: HistorySnapshotConfig) -> HistorySnapshotResult:
        rows: list[RegimeTransitionRow] = []
        warnings: list[str] = []

        for symbol in config.symbols:
            row = self._build_row(symbol=symbol, config=config)
            rows.append(row)
            if row.warning:
                warnings.append(f"{row.symbol}: {row.warning}")

        return HistorySnapshotResult(
            config=config,
            rows=tuple(rows),
            warnings=tuple(warnings),
        )

    def _build_row(self, *, symbol: str, config: HistorySnapshotConfig) -> RegimeTransitionRow:
        required = config.required_candles_per_symbol

        try:
            candles = tuple(
                self._candle_repository.get_last_n(
                    symbol=symbol,
                    interval=config.interval,
                    limit=required,
                )
            )
        except Exception as exc:
            return _error_row(symbol, str(exc) or "failed to read candles.")

        candles = _sort_candles_chronologically(candles)
        if len(candles) < required:
            return _insufficient_data_row(
                symbol=symbol,
                warning=f"required {required} candles, found {len(candles)}.",
            )

        candles = candles[-required:]
        previous_candles = candles[: config.limit]
        current_candles = candles[config.limit :]

        try:
            previous_window = CandleWindow.from_candles(
                symbol=symbol,
                interval=config.interval,
                candles=previous_candles,
                min_size=config.min_candles,
            )
            current_window = CandleWindow.from_candles(
                symbol=symbol,
                interval=config.interval,
                candles=current_candles,
                min_size=config.min_candles,
            )
            if current_window.first_open_time <= previous_window.last_open_time:
                raise ValueError("previous and current windows must not overlap")

            previous_snapshot = self._analyze_window(previous_window, window_name="previous")
            current_snapshot = self._analyze_window(current_window, window_name="current")
        except Exception as exc:
            return _error_row(symbol, str(exc) or "history snapshot failed.")

        transition = classify_regime_transition(
            previous_snapshot.market_regime,
            current_snapshot.market_regime,
        )
        return RegimeTransitionRow(
            symbol=symbol,
            status="OK",
            previous_regime=previous_snapshot.market_regime,
            current_regime=current_snapshot.market_regime,
            transition=transition,
            previous_confidence=previous_snapshot.confidence,
            current_confidence=current_snapshot.confidence,
            current_trend_strength=current_snapshot.trend_strength,
            trade_signal=TRADE_SIGNAL_NOT_EVALUATED,
            safe_for_runtime_trading=False,
            previous_snapshot=previous_snapshot,
            current_snapshot=current_snapshot,
        )

    def _analyze_window(self, window: CandleWindow, *, window_name: str) -> RegimeWindowSnapshot:
        analysis = self._market_reader.analyze(window)
        return RegimeWindowSnapshot(
            symbol=window.symbol,
            window_name=window_name,
            market_regime=_read_token(analysis, "market_regime", "UNKNOWN"),
            directional_bias=_read_token(analysis, "directional_bias", "UNKNOWN"),
            confidence=_read_float(analysis, "confidence", 0.0),
            trend_strength=_read_token(analysis, "trend_strength", "UNKNOWN"),
            trade_signal=_read_token(analysis, "trade_signal", TRADE_SIGNAL_NOT_EVALUATED),
            safe_for_runtime_trading=bool(_read_field(analysis, "safe_for_runtime_trading", False)),
            candle_count=window.size,
            first_open_time=window.first_open_time.isoformat(),
            last_open_time=window.last_open_time.isoformat(),
            reason_codes=tuple(str(item) for item in _sequence_or_empty(_read_field(analysis, "reason_codes", ()))),
        )


class HistorySnapshotTableFormatter:
    def format_result(self, result: HistorySnapshotResult, *, show_details: bool = False) -> str:
        config = result.config
        lines = [
            "BOOK-L1 History Snapshot - Current vs Previous Window",
            "",
            f"Interval: {config.interval}",
            f"Current window: last {config.limit} candles",
            f"Previous window: previous {config.limit} candles",
            "",
            self.format_table(result.rows),
            "",
            self.format_summary(result),
        ]

        if result.warnings:
            lines.extend(["", self.format_warnings(result.warnings)])

        lines.extend(["", self.format_safety()])

        if show_details:
            lines.extend(["", self.format_details(result.rows)])

        return "\n".join(lines)

    def format_table(self, rows: Sequence[RegimeTransitionRow]) -> str:
        headers = (
            "Symbol",
            "Status",
            "Previous",
            "Current",
            "Transition",
            "Prev Conf",
            "Curr Conf",
            "Trend Now",
            "Safety",
        )
        body = [
            (
                row.symbol,
                row.status,
                row.previous_regime,
                row.current_regime,
                row.transition,
                f"{row.previous_confidence:.2f}",
                f"{row.current_confidence:.2f}",
                row.current_trend_strength,
                HISTORY_SAFETY_LOCKED,
            )
            for row in rows
        ]
        return _format_grid(headers, body)

    def format_summary(self, result: HistorySnapshotResult) -> str:
        summary = summarize_history_result(result)
        lines = ["Summary:", ""]
        for transition in HISTORY_TRANSITIONS:
            if summary[transition] > 0:
                lines.append(f"{transition}: {summary[transition]}")
        lines.append(f"Errors: {summary['Errors']}")
        return "\n".join(lines)

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
                "traders_core_connected: false",
                "approved_for_live_trading: false",
                "approved_for_auto_activation: false",
                "model_training_executed: false",
                "binance_download_executed: false",
            ]
        )

    def format_details(self, rows: Sequence[RegimeTransitionRow]) -> str:
        return "\n\n".join(self.format_symbol_details(row) for row in rows)

    def format_symbol_details(self, row: RegimeTransitionRow) -> str:
        lines = [f"{row.symbol} details", ""]
        if row.warning:
            lines.extend(["Warning:", row.warning, ""])
        lines.extend(self._format_window("Previous window", row.previous_snapshot))
        lines.extend([""])
        lines.extend(self._format_window("Current window", row.current_snapshot))
        return "\n".join(lines)

    def _format_window(self, title: str, snapshot: RegimeWindowSnapshot | None) -> list[str]:
        if snapshot is None:
            return [
                f"{title}:",
                "N/A",
                "Regime: UNKNOWN",
                "Bias: UNKNOWN",
                "Confidence: 0.00",
                "Reason codes:",
                "- N/A",
            ]

        lines = [
            f"{title}:",
            f"{_format_open_time(snapshot.first_open_time)} -> {_format_open_time(snapshot.last_open_time)}",
            f"Regime: {snapshot.market_regime}",
            f"Bias: {snapshot.directional_bias}",
            f"Confidence: {snapshot.confidence:.2f}",
            "Reason codes:",
        ]
        if snapshot.reason_codes:
            lines.extend(f"- {reason_code}" for reason_code in snapshot.reason_codes)
        else:
            lines.append("- N/A")
        return lines


def classify_regime_transition(previous_regime: str, current_regime: str) -> str:
    previous = _normalize_token(previous_regime)
    current = _normalize_token(current_regime)

    if previous == "ERROR" or current == "ERROR":
        return "ERROR"
    if previous == current:
        return "NO_CHANGE"
    if current == "UNKNOWN":
        return "TO_UNKNOWN"

    mapping = {
        ("FLAT", "UP"): "FLAT_TO_UP",
        ("FLAT", "DOWN"): "FLAT_TO_DOWN",
        ("UP", "FLAT"): "UP_TO_FLAT",
        ("DOWN", "FLAT"): "DOWN_TO_FLAT",
        ("UP", "DOWN"): "UP_TO_DOWN",
        ("DOWN", "UP"): "DOWN_TO_UP",
        ("UNKNOWN", "UP"): "UNKNOWN_TO_UP",
        ("UNKNOWN", "DOWN"): "UNKNOWN_TO_DOWN",
        ("UNKNOWN", "FLAT"): "UNKNOWN_TO_FLAT",
    }
    return mapping.get((previous, current), "OTHER_CHANGE")


def summarize_history_result(result: HistorySnapshotResult) -> dict[str, int]:
    counts = Counter(row.transition for row in result.rows)
    summary = {transition: counts.get(transition, 0) for transition in HISTORY_TRANSITIONS}
    summary["Errors"] = sum(1 for row in result.rows if row.status != "OK")
    return summary


def _error_row(symbol: str, warning: str) -> RegimeTransitionRow:
    return RegimeTransitionRow(
        symbol=symbol,
        status="ERROR",
        previous_regime="UNKNOWN",
        current_regime="UNKNOWN",
        transition="ERROR",
        previous_confidence=0.0,
        current_confidence=0.0,
        current_trend_strength="UNKNOWN",
        trade_signal=TRADE_SIGNAL_NOT_EVALUATED,
        safe_for_runtime_trading=False,
        warning=warning,
    )


def _insufficient_data_row(symbol: str, warning: str) -> RegimeTransitionRow:
    return RegimeTransitionRow(
        symbol=symbol,
        status="INSUFFICIENT_DATA",
        previous_regime="UNKNOWN",
        current_regime="UNKNOWN",
        transition="ERROR",
        previous_confidence=0.0,
        current_confidence=0.0,
        current_trend_strength="UNKNOWN",
        trade_signal=TRADE_SIGNAL_NOT_EVALUATED,
        safe_for_runtime_trading=False,
        warning=warning,
    )


def _sort_candles_chronologically(candles: Sequence[Any]) -> tuple[Any, ...]:
    return tuple(sorted(candles, key=lambda candle: _read_field(candle, "open_time", None)))


def _read_field(source: Any, field_name: str, default: Any) -> Any:
    if source is None:
        return default
    if isinstance(source, Mapping):
        return source.get(field_name, default)
    return getattr(source, field_name, default)


def _read_token(source: Any, field_name: str, default: str) -> str:
    return _normalize_token(_read_field(source, field_name, default))


def _read_float(source: Any, field_name: str, default: float) -> float:
    try:
        return float(_read_field(source, field_name, default))
    except (TypeError, ValueError):
        return default


def _normalize_token(value: Any) -> str:
    if isinstance(value, Enum):
        value = value.value
    return str(value or "").strip().upper()


def _sequence_or_empty(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Sequence):
        return tuple(value)
    return (value,)


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


def _format_open_time(value: str | None) -> str:
    if value is None:
        return "N/A"
    return value.replace("T", " ").replace("+00:00", "")


__all__ = [
    "HistorySnapshotConfig",
    "RegimeWindowSnapshot",
    "RegimeTransitionRow",
    "HistorySnapshotResult",
    "HistorySnapshotRunner",
    "HistorySnapshotTableFormatter",
    "classify_regime_transition",
    "parse_symbols",
    "summarize_history_result",
]
