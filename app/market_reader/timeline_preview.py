from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.market_reader.candle_window import CandleWindow
from app.market_reader.history_snapshot import HISTORY_TRANSITIONS, classify_regime_transition
from app.market_reader.market_reader import MarketReaderOrchestrator
from app.market_reader.multi_symbol_preview import (
    DEFAULT_MULTI_SYMBOLS,
    TRADE_SIGNAL_NOT_EVALUATED,
    normalize_symbol,
    normalize_symbols,
    parse_symbols,
)


TIMELINE_SAFETY_LOCKED = "LOCKED"
TIMELINE_STATUSES = ("OK", "ERROR", "INSUFFICIENT_DATA")
TIMELINE_STABILITIES = ("STABLE", "CHANGING", "UNSTABLE", "ERROR")
TIMELINE_MIN_WINDOW_COUNT = 2
TIMELINE_MAX_WINDOW_COUNT = 6


@dataclass(frozen=True)
class TimelinePreviewConfig:
    symbols: tuple[str, ...] = DEFAULT_MULTI_SYMBOLS
    interval: str = "15m"
    window_size: int = 300
    window_count: int = 4
    min_candles: int = 50
    reference_mode: str = "latest"

    def __post_init__(self) -> None:
        symbols = normalize_symbols(self.symbols)
        if not symbols:
            raise ValueError("symbols must not be empty")
        if not self.interval or not self.interval.strip():
            raise ValueError("interval must not be empty")
        if self.window_size <= 0:
            raise ValueError("window_size must be positive")
        if self.window_count < TIMELINE_MIN_WINDOW_COUNT or self.window_count > TIMELINE_MAX_WINDOW_COUNT:
            raise ValueError("window_count must be between 2 and 6")
        if self.min_candles <= 0:
            raise ValueError("min_candles must be positive")
        if self.window_size < self.min_candles:
            raise ValueError("window_size must be greater than or equal to min_candles")

        reference_mode = self.reference_mode.strip().lower()
        if reference_mode != "latest":
            raise ValueError("BOOK-L1 timeline preview currently supports latest reference mode only")

        object.__setattr__(self, "symbols", symbols)
        object.__setattr__(self, "interval", self.interval.strip())
        object.__setattr__(self, "reference_mode", reference_mode)

    @property
    def required_candles(self) -> int:
        return self.window_size * self.window_count


@dataclass(frozen=True)
class TimelineWindowSnapshot:
    symbol: str
    window_label: str
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
        object.__setattr__(self, "window_label", str(self.window_label).strip())
        object.__setattr__(self, "market_regime", _normalize_token(self.market_regime))
        object.__setattr__(self, "directional_bias", _normalize_token(self.directional_bias))
        object.__setattr__(self, "trend_strength", _normalize_token(self.trend_strength))
        object.__setattr__(self, "trade_signal", _normalize_token(self.trade_signal))
        object.__setattr__(self, "reason_codes", tuple(str(item) for item in self.reason_codes))

        if self.trade_signal != TRADE_SIGNAL_NOT_EVALUATED:
            raise ValueError("BOOK-L1 timeline preview must not expose trading signals")
        if self.safe_for_runtime_trading is not False:
            raise ValueError("BOOK-L1 timeline preview must not approve runtime trading")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if self.candle_count < 0:
            raise ValueError("candle_count must be non-negative")


@dataclass(frozen=True)
class TimelineSymbolRow:
    symbol: str
    status: str
    windows: tuple[TimelineWindowSnapshot, ...]
    regimes: tuple[str, ...]
    transitions: tuple[str, ...]
    last_transition: str
    stability: str
    current_confidence: float
    current_trend_strength: str
    trade_signal: str
    safe_for_runtime_trading: bool
    warning: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", normalize_symbol(self.symbol))
        object.__setattr__(self, "status", _normalize_token(self.status))
        object.__setattr__(self, "windows", tuple(self.windows))
        object.__setattr__(self, "regimes", tuple(_normalize_token(item) for item in self.regimes))
        object.__setattr__(self, "transitions", tuple(_normalize_token(item) for item in self.transitions))
        object.__setattr__(self, "last_transition", _normalize_token(self.last_transition))
        object.__setattr__(self, "stability", _normalize_token(self.stability))
        object.__setattr__(self, "current_trend_strength", _normalize_token(self.current_trend_strength))
        object.__setattr__(self, "trade_signal", _normalize_token(self.trade_signal))

        if self.status not in TIMELINE_STATUSES:
            raise ValueError(f"unsupported timeline row status: {self.status}")
        if self.last_transition not in HISTORY_TRANSITIONS:
            raise ValueError(f"unsupported transition: {self.last_transition}")
        for transition in self.transitions:
            if transition not in HISTORY_TRANSITIONS:
                raise ValueError(f"unsupported transition: {transition}")
        if self.stability not in TIMELINE_STABILITIES:
            raise ValueError(f"unsupported timeline stability: {self.stability}")
        if self.trade_signal != TRADE_SIGNAL_NOT_EVALUATED:
            raise ValueError("BOOK-L1 timeline preview must not expose trading signals")
        if self.safe_for_runtime_trading is not False:
            raise ValueError("BOOK-L1 timeline preview must not approve runtime trading")
        if not 0.0 <= float(self.current_confidence) <= 1.0:
            raise ValueError("current_confidence must be between 0.0 and 1.0")


@dataclass(frozen=True)
class TimelinePreviewResult:
    config: TimelinePreviewConfig
    rows: tuple[TimelineSymbolRow, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "rows", tuple(self.rows))
        object.__setattr__(self, "warnings", tuple(str(item) for item in self.warnings))


class TimelinePreviewRunner:
    def __init__(
        self,
        *,
        candle_repository: Any,
        market_reader: Any | None = None,
    ) -> None:
        self._candle_repository = candle_repository
        self._market_reader = market_reader or MarketReaderOrchestrator()

    def run(self, config: TimelinePreviewConfig) -> TimelinePreviewResult:
        rows: list[TimelineSymbolRow] = []
        warnings: list[str] = []

        for symbol in config.symbols:
            row = self._build_row(symbol=symbol, config=config)
            rows.append(row)
            if row.warning:
                warnings.append(f"{row.symbol}: {row.warning}")

        return TimelinePreviewResult(
            config=config,
            rows=tuple(rows),
            warnings=tuple(warnings),
        )

    def _build_row(self, *, symbol: str, config: TimelinePreviewConfig) -> TimelineSymbolRow:
        required = config.required_candles

        try:
            candles = tuple(
                self._candle_repository.get_last_n(
                    symbol=symbol,
                    interval=config.interval,
                    limit=required,
                )
            )
        except Exception as exc:
            return _problem_row(symbol=symbol, config=config, status="ERROR", warning=str(exc) or "failed to read candles.")

        candles = _sort_candles_chronologically(candles)
        if len(candles) < required:
            return _problem_row(
                symbol=symbol,
                config=config,
                status="INSUFFICIENT_DATA",
                warning=f"required {required} candles, found {len(candles)}.",
            )

        candles = candles[-required:]
        labels = build_window_labels(config.window_count)
        chunks = tuple(
            candles[index * config.window_size : (index + 1) * config.window_size]
            for index in range(config.window_count)
        )

        try:
            candle_windows = tuple(
                CandleWindow.from_candles(
                    symbol=symbol,
                    interval=config.interval,
                    candles=chunk,
                    min_size=config.min_candles,
                )
                for chunk in chunks
            )
            _validate_non_overlapping_windows(candle_windows)
            snapshots = tuple(
                self._analyze_window(window, window_label=label)
                for label, window in zip(labels, candle_windows)
            )
        except Exception as exc:
            return _problem_row(symbol=symbol, config=config, status="ERROR", warning=str(exc) or "timeline preview failed.")

        regimes = tuple(snapshot.market_regime for snapshot in snapshots)
        transitions = tuple(
            classify_regime_transition(previous, current)
            for previous, current in zip(regimes, regimes[1:])
        )
        current = snapshots[-1]
        return TimelineSymbolRow(
            symbol=symbol,
            status="OK",
            windows=snapshots,
            regimes=regimes,
            transitions=transitions,
            last_transition=transitions[-1] if transitions else "ERROR",
            stability=classify_timeline_stability(regimes),
            current_confidence=current.confidence,
            current_trend_strength=current.trend_strength,
            trade_signal=TRADE_SIGNAL_NOT_EVALUATED,
            safe_for_runtime_trading=False,
        )

    def _analyze_window(self, window: CandleWindow, *, window_label: str) -> TimelineWindowSnapshot:
        analysis = self._market_reader.analyze(window)
        return TimelineWindowSnapshot(
            symbol=window.symbol,
            window_label=window_label,
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


class TimelinePreviewTableFormatter:
    def format_result(self, result: TimelinePreviewResult, *, show_details: bool = False) -> str:
        config = result.config
        lines = [
            "BOOK-L1 Market Regime Timeline Preview",
            "",
            f"Interval: {config.interval}",
            f"Window size: {config.window_size} candles",
            f"Windows: {config.window_count}",
            f"Required candles per symbol: {config.required_candles}",
            "",
            self.format_table(result),
            "",
            self.format_summary(result),
        ]

        if result.warnings:
            lines.extend(["", self.format_warnings(result.warnings)])

        lines.extend(["", self.format_safety()])

        if show_details:
            lines.extend(["", self.format_details(result.rows)])

        return "\n".join(lines)

    def format_table(self, result: TimelinePreviewResult) -> str:
        labels = build_window_labels(result.config.window_count)
        headers = (
            "Symbol",
            "Status",
            *labels,
            "Stability",
            "Last Change",
            "Trend",
            "Curr Conf",
            "Safety",
        )
        body = [
            (
                row.symbol,
                row.status,
                *row.regimes,
                row.stability,
                row.last_transition,
                row.current_trend_strength,
                f"{row.current_confidence:.2f}",
                TIMELINE_SAFETY_LOCKED,
            )
            for row in result.rows
        ]
        return _format_grid(headers, body)

    def format_summary(self, result: TimelinePreviewResult) -> str:
        summary = summarize_timeline_result(result)
        lines = [
            "Summary:",
            "",
            f"Symbols: {summary['Symbols']}",
            f"OK: {summary['OK']}",
            f"Errors: {summary['Errors']}",
        ]
        if summary["INSUFFICIENT_DATA"] > 0:
            lines.append(f"INSUFFICIENT_DATA: {summary['INSUFFICIENT_DATA']}")

        lines.extend(
            [
                "",
                "Current regimes:",
                f"UP: {summary['current_UP']}",
                f"DOWN: {summary['current_DOWN']}",
                f"FLAT: {summary['current_FLAT']}",
                f"UNKNOWN: {summary['current_UNKNOWN']}",
                "",
                "Last transitions:",
            ]
        )
        for transition in HISTORY_TRANSITIONS:
            value = summary.get(f"last_transition_{transition}", 0)
            if value > 0:
                lines.append(f"{transition}: {value}")

        lines.extend(["", "Stability:"])
        for stability in TIMELINE_STABILITIES:
            value = summary.get(f"stability_{stability}", 0)
            if value > 0:
                lines.append(f"{stability}: {value}")
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

    def format_details(self, rows: Sequence[TimelineSymbolRow]) -> str:
        return "\n\n".join(self.format_symbol_details(row) for row in rows)

    def format_symbol_details(self, row: TimelineSymbolRow) -> str:
        lines = [f"{row.symbol} timeline details", ""]
        if row.warning:
            lines.extend(["Warning:", row.warning, ""])
        for index, snapshot in enumerate(row.windows):
            if index > 0:
                lines.append("")
            lines.extend(self._format_window(snapshot))
        return "\n".join(lines)

    def _format_window(self, snapshot: TimelineWindowSnapshot) -> list[str]:
        lines = [
            f"{snapshot.window_label}:",
            f"Window: {_format_open_time(snapshot.first_open_time)} -> {_format_open_time(snapshot.last_open_time)}",
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


def build_window_labels(window_count: int) -> tuple[str, ...]:
    if window_count < TIMELINE_MIN_WINDOW_COUNT or window_count > TIMELINE_MAX_WINDOW_COUNT:
        raise ValueError("window_count must be between 2 and 6")
    return tuple(f"W-{offset}" for offset in range(window_count - 1, 0, -1)) + ("Current",)


def classify_timeline_stability(regimes: tuple[str, ...]) -> str:
    normalized = tuple(_normalize_token(item) for item in regimes)
    if not normalized:
        return "ERROR"
    if len(set(normalized)) == 1 and normalized[0] != "UNKNOWN":
        return "STABLE"
    if normalized[-1] == "UNKNOWN":
        return "UNSTABLE"
    if len(set(normalized)) <= 2:
        return "CHANGING"
    return "UNSTABLE"


def summarize_timeline_result(result: TimelinePreviewResult) -> dict[str, int]:
    summary: dict[str, int] = {
        "Symbols": len(result.rows),
        "OK": sum(1 for row in result.rows if row.status == "OK"),
        "Errors": sum(1 for row in result.rows if row.status != "OK"),
        "ERROR": sum(1 for row in result.rows if row.status == "ERROR"),
        "INSUFFICIENT_DATA": sum(1 for row in result.rows if row.status == "INSUFFICIENT_DATA"),
    }

    current_regimes = Counter(_current_regime(row) for row in result.rows)
    for regime in ("UP", "DOWN", "FLAT", "UNKNOWN"):
        summary[f"current_{regime}"] = current_regimes.get(regime, 0)

    last_transitions = Counter(row.last_transition for row in result.rows)
    for transition in HISTORY_TRANSITIONS:
        summary[f"last_transition_{transition}"] = last_transitions.get(transition, 0)

    stabilities = Counter(row.stability for row in result.rows)
    for stability in TIMELINE_STABILITIES:
        summary[f"stability_{stability}"] = stabilities.get(stability, 0)

    return summary


def _problem_row(*, symbol: str, config: TimelinePreviewConfig, status: str, warning: str) -> TimelineSymbolRow:
    windows = tuple(_unknown_snapshot(symbol=symbol, window_label=label) for label in build_window_labels(config.window_count))
    regimes = tuple(snapshot.market_regime for snapshot in windows)
    transitions = tuple("ERROR" for _ in range(max(config.window_count - 1, 0)))
    return TimelineSymbolRow(
        symbol=symbol,
        status=status,
        windows=windows,
        regimes=regimes,
        transitions=transitions,
        last_transition="ERROR",
        stability="ERROR",
        current_confidence=0.0,
        current_trend_strength="UNKNOWN",
        trade_signal=TRADE_SIGNAL_NOT_EVALUATED,
        safe_for_runtime_trading=False,
        warning=warning,
    )


def _unknown_snapshot(*, symbol: str, window_label: str) -> TimelineWindowSnapshot:
    return TimelineWindowSnapshot(
        symbol=symbol,
        window_label=window_label,
        market_regime="UNKNOWN",
        directional_bias="UNKNOWN",
        confidence=0.0,
        trend_strength="UNKNOWN",
        trade_signal=TRADE_SIGNAL_NOT_EVALUATED,
        safe_for_runtime_trading=False,
        candle_count=0,
    )


def _validate_non_overlapping_windows(windows: Sequence[CandleWindow]) -> None:
    for previous, current in zip(windows, windows[1:]):
        if current.first_open_time <= previous.last_open_time:
            raise ValueError("timeline windows must not overlap")


def _sort_candles_chronologically(candles: Sequence[Any]) -> tuple[Any, ...]:
    return tuple(sorted(candles, key=lambda candle: _read_field(candle, "open_time", None)))


def _current_regime(row: TimelineSymbolRow) -> str:
    if not row.regimes:
        return "UNKNOWN"
    regime = row.regimes[-1]
    return regime if regime in {"UP", "DOWN", "FLAT"} else "UNKNOWN"


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
    "TimelinePreviewConfig",
    "TimelineWindowSnapshot",
    "TimelineSymbolRow",
    "TimelinePreviewResult",
    "TimelinePreviewRunner",
    "TimelinePreviewTableFormatter",
    "build_window_labels",
    "classify_timeline_stability",
    "parse_symbols",
    "summarize_timeline_result",
]
