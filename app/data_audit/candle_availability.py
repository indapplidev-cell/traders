from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Protocol


DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
DEFAULT_INTERVALS = ("15m", "1h", "4h")
DEFAULT_OUTPUT_JSON = Path("reports/book_data/candle_availability_audit.json")
DEFAULT_OUTPUT_MD = Path("reports/book_data/candle_availability_audit.md")
CONTRACT_VERSION = "book_data_candle_availability_v1"
SERVICE_NAME = "BOOK_DATA_AUDIT"
REPORT_TYPE = "candle_availability_audit"

READY = "READY"
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
MISSING = "MISSING"
ERROR = "ERROR"
ROW_STATUSES = (READY, INSUFFICIENT_DATA, MISSING, ERROR)
PASS = "PASS"
PASS_WITH_DATA_GAPS = "PASS_WITH_DATA_GAPS"
FAIL = "FAIL"


class CandleAvailabilityRepository(Protocol):
    def count_by_symbol_interval(self, symbol: str, interval: str) -> int:
        ...

    def get_open_time_bounds(self, symbol: str, interval: str) -> tuple[object | None, object | None]:
        ...


@dataclass(frozen=True)
class CandleAvailabilityAuditConfig:
    symbols: tuple[str, ...] = DEFAULT_SYMBOLS
    intervals: tuple[str, ...] = DEFAULT_INTERVALS
    window_size: int = 300
    window_count: int = 4
    required_candles: int | None = None
    output_json: Path = DEFAULT_OUTPUT_JSON
    output_md: Path = DEFAULT_OUTPUT_MD
    strict: bool = False
    show_details: bool = False

    def __post_init__(self) -> None:
        symbols = normalize_symbols(self.symbols)
        intervals = normalize_intervals(self.intervals)
        object.__setattr__(self, "symbols", symbols or DEFAULT_SYMBOLS)
        object.__setattr__(self, "intervals", intervals or DEFAULT_INTERVALS)
        object.__setattr__(self, "output_json", Path(self.output_json))
        object.__setattr__(self, "output_md", Path(self.output_md))

    @property
    def effective_required_candles(self) -> int:
        return self.required_candles or self.window_size * self.window_count


@dataclass(frozen=True)
class CandleAvailabilityRow:
    symbol: str
    interval: str
    available_candles: int
    required_candles: int
    status: str
    first_open_time: str | None = None
    last_open_time: str | None = None
    message: str | None = None


@dataclass(frozen=True)
class CandleAvailabilityAuditResult:
    status: str
    rows: tuple[CandleAvailabilityRow, ...] = field(default_factory=tuple)
    summary: dict[str, int] = field(default_factory=dict)
    output_json: str | None = None
    output_md: str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        return self.status == PASS


class CandleAvailabilityAuditor:
    def __init__(self, repository: CandleAvailabilityRepository) -> None:
        self._repository = repository

    def run(self, config: CandleAvailabilityAuditConfig | None = None) -> CandleAvailabilityAuditResult:
        active_config = config or CandleAvailabilityAuditConfig()
        required = active_config.effective_required_candles
        rows = tuple(
            self._read_row(symbol=symbol, interval=interval, required_candles=required)
            for symbol in active_config.symbols
            for interval in active_config.intervals
        )
        summary = summarize_rows(rows)
        errors = tuple(row.message or f"{row.symbol} {row.interval} read error" for row in rows if row.status == ERROR)
        status = resolve_result_status(rows, strict=active_config.strict)
        output_json = write_candle_availability_json(active_config, rows, summary, status, errors=errors)
        output_md = write_candle_availability_markdown(active_config, rows, summary, status, errors=errors)
        return CandleAvailabilityAuditResult(
            status=status,
            rows=rows,
            summary=summary,
            output_json=output_json.as_posix(),
            output_md=output_md.as_posix(),
            errors=errors,
        )

    def _read_row(self, *, symbol: str, interval: str, required_candles: int) -> CandleAvailabilityRow:
        try:
            available = self._repository.count_by_symbol_interval(symbol, interval)
            first_open_time, last_open_time = self._repository.get_open_time_bounds(symbol, interval)
            status = resolve_row_status(available, required_candles)
            return CandleAvailabilityRow(
                symbol=symbol,
                interval=interval,
                available_candles=available,
                required_candles=required_candles,
                status=status,
                first_open_time=format_open_time(first_open_time),
                last_open_time=format_open_time(last_open_time),
                message=coverage_note(status, available_candles=available, required_candles=required_candles),
            )
        except Exception as exc:
            return CandleAvailabilityRow(
                symbol=symbol,
                interval=interval,
                available_candles=0,
                required_candles=required_candles,
                status=ERROR,
                message=f"read error: {exc}",
            )


class CandleAvailabilityAuditFormatter:
    def format(self, result: CandleAvailabilityAuditResult, *, config: CandleAvailabilityAuditConfig) -> str:
        lines = [
            "BOOK-DATA-01 Candle Data Availability Audit",
            "",
            "Request:",
            f"Symbols: {', '.join(config.symbols)}",
            f"Intervals: {', '.join(config.intervals)}",
            f"Required candles per symbol/interval: {config.effective_required_candles}",
            "",
            "Availability:",
            format_availability_table(result.rows),
            "",
            "Summary:",
        ]
        for status in ROW_STATUSES:
            lines.append(f"{status}: {result.summary.get(status, 0)}")
        lines.extend(["", "Conclusion:", *terminal_conclusion_lines(result.rows), "No data was downloaded or modified."])
        if config.show_details:
            lines.extend(["", "Details:"])
            lines.extend(
                f"{row.symbol} {row.interval}: {row.message or 'ready'}"
                for row in result.rows
            )
        if result.errors:
            lines.extend(["", "Errors:"])
            lines.extend(f"- {error}" for error in result.errors)
        lines.extend(
            [
                "",
                f"JSON evidence: {result.output_json or config.output_json.as_posix()}",
                f"Markdown evidence: {result.output_md or config.output_md.as_posix()}",
                "",
                f"Result: {result.status}",
            ]
        )
        return "\n".join(lines)


def parse_audit_symbols(symbols: str | None, symbol_options: tuple[str, ...] = ()) -> tuple[str, ...]:
    values: list[str] = []
    if symbols:
        values.extend(item.strip() for item in symbols.split(",") if item.strip())
    values.extend(item.strip() for item in symbol_options if item.strip())
    return normalize_symbols(tuple(values)) or DEFAULT_SYMBOLS


def parse_audit_intervals(intervals: str | None) -> tuple[str, ...]:
    if not intervals:
        return DEFAULT_INTERVALS
    return normalize_intervals(tuple(item.strip() for item in intervals.split(",") if item.strip())) or DEFAULT_INTERVALS


def normalize_symbols(symbols: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()))


def normalize_intervals(intervals: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(interval).strip() for interval in intervals if str(interval).strip()))


def resolve_row_status(available_candles: int, required_candles: int) -> str:
    if available_candles >= required_candles:
        return READY
    if available_candles > 0:
        return INSUFFICIENT_DATA
    return MISSING


def resolve_result_status(rows: tuple[CandleAvailabilityRow, ...], *, strict: bool) -> str:
    if any(row.status == ERROR for row in rows):
        return FAIL
    if all(row.status == READY for row in rows):
        return PASS
    if strict:
        return FAIL
    return PASS_WITH_DATA_GAPS


def summarize_rows(rows: tuple[CandleAvailabilityRow, ...]) -> dict[str, int]:
    counts = Counter(row.status for row in rows)
    return {status: counts.get(status, 0) for status in ROW_STATUSES}


def coverage_note(status: str, *, available_candles: int, required_candles: int) -> str:
    if status == READY:
        return "ready for L1-L2 report"
    if status == INSUFFICIENT_DATA:
        missing = required_candles - available_candles
        return f"insufficient candles: missing {missing}"
    if status == MISSING:
        return "no candles found"
    return "read error"


def format_open_time(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def build_json_payload(
    config: CandleAvailabilityAuditConfig,
    rows: tuple[CandleAvailabilityRow, ...],
    summary: dict[str, int],
    status: str,
    *,
    errors: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
) -> dict[str, object]:
    return {
        "status": status,
        "service": SERVICE_NAME,
        "report_type": REPORT_TYPE,
        "contract_version": CONTRACT_VERSION,
        "request": {
            "symbols": list(config.symbols),
            "intervals": list(config.intervals),
            "window_size": config.window_size,
            "window_count": config.window_count,
            "required_candles": config.effective_required_candles,
        },
        "summary": summary,
        "rows": [asdict(row) for row in rows],
        "safety": build_safety_payload(),
        "warnings": list(warnings),
        "errors": list(errors),
    }


def build_safety_payload() -> dict[str, object]:
    return {
        "read_only": True,
        "download_executed": False,
        "db_write_executed": False,
        "market_analysis_changed": False,
        "trading_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": False,
    }


def write_candle_availability_json(
    config: CandleAvailabilityAuditConfig,
    rows: tuple[CandleAvailabilityRow, ...],
    summary: dict[str, int],
    status: str,
    *,
    errors: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
) -> Path:
    payload = build_json_payload(config, rows, summary, status, errors=errors, warnings=warnings)
    config.output_json.parent.mkdir(parents=True, exist_ok=True)
    config.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return config.output_json


def build_markdown(
    config: CandleAvailabilityAuditConfig,
    rows: tuple[CandleAvailabilityRow, ...],
    summary: dict[str, int],
    status: str,
    *,
    errors: tuple[str, ...] = (),
) -> str:
    lines = [
        "# BOOK-DATA-01 - Candle Data Availability Audit",
        "",
        "## Status",
        "",
        f"`{status}`",
        "",
        "## Request",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Symbols | {_md(', '.join(config.symbols))} |",
        f"| Intervals | {_md(', '.join(config.intervals))} |",
        f"| Window size | {config.window_size} |",
        f"| Window count | {config.window_count} |",
        f"| Required candles | {config.effective_required_candles} |",
        "",
        "## Availability",
        "",
        "| Symbol | Interval | Available | Required | Status | First open time | Last open time | Message |",
        "|---|---|---:|---:|---|---|---|---|",
        *[_markdown_row(row) for row in rows],
        "",
        "## Summary",
        "",
        "| Status | Count |",
        "|---|---:|",
        *[f"| {row_status} | {summary.get(row_status, 0)} |" for row_status in ROW_STATUSES],
        "",
        "## Conclusion",
        "",
        *[f"- {_md(line)}" for line in markdown_conclusion_lines(rows)],
        "",
        "## Safety",
        "",
        "- read_only: `true`",
        "- download_executed: `false`",
        "- db_write_executed: `false`",
        "- safe_for_runtime_trading: `false`",
        "",
    ]
    if errors:
        lines.extend(["## Errors", "", *[f"- {_md(error)}" for error in errors], ""])
    return "\n".join(lines)


def write_candle_availability_markdown(
    config: CandleAvailabilityAuditConfig,
    rows: tuple[CandleAvailabilityRow, ...],
    summary: dict[str, int],
    status: str,
    *,
    errors: tuple[str, ...] = (),
) -> Path:
    config.output_md.parent.mkdir(parents=True, exist_ok=True)
    config.output_md.write_text(build_markdown(config, rows, summary, status, errors=errors), encoding="utf-8")
    return config.output_md


def format_availability_table(rows: tuple[CandleAvailabilityRow, ...]) -> str:
    headers = ("Symbol", "Interval", "Available", "Required", "Status", "First open time", "Last open time")
    values = tuple(
        (
            row.symbol,
            row.interval,
            str(row.available_candles),
            str(row.required_candles),
            row.status,
            row.first_open_time or "N/A",
            row.last_open_time or "N/A",
        )
        for row in rows
    )
    widths = [len(header) for header in headers]
    for row in values:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))
    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"
    lines = [border, _table_row(headers, widths), border]
    lines.extend(_table_row(row, widths) for row in values)
    lines.append(border)
    return "\n".join(lines)


def terminal_conclusion_lines(rows: tuple[CandleAvailabilityRow, ...]) -> list[str]:
    ready_intervals = intervals_for_status(rows, READY)
    missing_intervals = intervals_for_status(rows, MISSING)
    insufficient_intervals = intervals_for_status(rows, INSUFFICIENT_DATA)
    lines: list[str] = []
    if ready_intervals:
        lines.append(f"{', '.join(ready_intervals)} ready for L1-L2 interval answer smoke.")
    if missing_intervals:
        lines.append(f"{', '.join(missing_intervals)} missing candles in the local database.")
    if insufficient_intervals:
        lines.append(f"{', '.join(insufficient_intervals)} have candles but not enough for the requested timeline.")
    if not lines:
        lines.append("No ready intervals found.")
    return lines


def markdown_conclusion_lines(rows: tuple[CandleAvailabilityRow, ...]) -> list[str]:
    ready_intervals = intervals_for_status(rows, READY)
    missing_intervals = intervals_for_status(rows, MISSING)
    insufficient_intervals = intervals_for_status(rows, INSUFFICIENT_DATA)
    blocking = tuple(dict.fromkeys((*missing_intervals, *insufficient_intervals)))
    return [
        f"Ready intervals: {_join_or_none(ready_intervals)}",
        f"Missing intervals: {_join_or_none(missing_intervals)}",
        f"Insufficient intervals: {_join_or_none(insufficient_intervals)}",
        f"Intervals that currently block L1-L2 multi-interval smoke: {_join_or_none(blocking)}",
    ]


def intervals_for_status(rows: tuple[CandleAvailabilityRow, ...], status: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(row.interval for row in rows if row.status == status))


def _table_row(values: tuple[str, ...], widths: list[int]) -> str:
    return "|" + "|".join(f" {value:<{widths[index]}} " for index, value in enumerate(values)) + "|"


def _markdown_row(row: CandleAvailabilityRow) -> str:
    return (
        f"| {_md(row.symbol)} | {_md(row.interval)} | {row.available_candles} | {row.required_candles} | "
        f"{row.status} | {_md(row.first_open_time or 'N/A')} | {_md(row.last_open_time or 'N/A')} | "
        f"{_md(row.message or '')} |"
    )


def _join_or_none(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "none"


def _md(value: str) -> str:
    return str(value).replace("|", "\\|")


__all__ = [
    "CandleAvailabilityAuditConfig",
    "CandleAvailabilityAuditFormatter",
    "CandleAvailabilityAuditResult",
    "CandleAvailabilityAuditor",
    "CandleAvailabilityRow",
    "build_json_payload",
    "build_markdown",
    "parse_audit_intervals",
    "parse_audit_symbols",
    "resolve_result_status",
    "resolve_row_status",
    "summarize_rows",
    "write_candle_availability_json",
    "write_candle_availability_markdown",
]
