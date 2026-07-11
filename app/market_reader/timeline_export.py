from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.market_reader.timeline_preview import build_window_labels, summarize_timeline_result


DEFAULT_TIMELINE_EXPORT_DIR = Path("reports/book_l1")
DEFAULT_TIMELINE_JSON_FILENAME = "timeline_preview.json"
DEFAULT_TIMELINE_MARKDOWN_FILENAME = "timeline_preview.md"
TIMELINE_EXPORT_SERVICE = "BOOK_L1_MARKET_READER"
TIMELINE_EXPORT_TYPE = "timeline_preview"
TIMELINE_EXPORT_CONTRACT_VERSION = "book_l1_timeline_export_v1"
TIMELINE_EXPORT_FORMATS = ("all", "json", "md")

TIMELINE_EXPORT_SAFETY: dict[str, bool | str] = {
    "trade_signal": "NOT_EVALUATED",
    "safe_for_runtime_trading": False,
    "orders_enabled": False,
    "live_trading_connected": False,
    "traders_core_connected": False,
    "approved_for_live_trading": False,
    "approved_for_auto_activation": False,
    "model_training_executed": False,
    "binance_download_executed": False,
}


@dataclass(frozen=True)
class TimelineExportConfig:
    output_dir: Path = DEFAULT_TIMELINE_EXPORT_DIR
    export_format: str = "all"

    def __post_init__(self) -> None:
        output_dir = Path(self.output_dir)
        export_format = str(self.export_format).strip().lower()
        if export_format not in TIMELINE_EXPORT_FORMATS:
            raise ValueError("export_format must be one of: all, json, md")

        object.__setattr__(self, "output_dir", output_dir)
        object.__setattr__(self, "export_format", export_format)


@dataclass(frozen=True)
class TimelineExportPaths:
    json_path: Path | None
    markdown_path: Path | None


@dataclass(frozen=True)
class TimelineExportResult:
    paths: TimelineExportPaths
    written_files: tuple[Path, ...]


class TimelinePreviewExporter:
    def export(self, result: Any, config: TimelineExportConfig) -> TimelineExportResult:
        paths = _build_export_paths(config)
        written_files: list[Path] = []

        if paths.json_path is not None:
            payload = timeline_result_to_dict(result)
            write_text_overwrite(
                paths.json_path,
                json.dumps(payload, ensure_ascii=False, indent=2),
            )
            written_files.append(paths.json_path)

        if paths.markdown_path is not None:
            write_text_overwrite(paths.markdown_path, timeline_result_to_markdown(result))
            written_files.append(paths.markdown_path)

        return TimelineExportResult(paths=paths, written_files=tuple(written_files))


def timeline_result_to_dict(result: Any) -> dict[str, Any]:
    config = result.config
    rows = tuple(result.rows)
    summary = summarize_timeline_result(result)

    return {
        "service": TIMELINE_EXPORT_SERVICE,
        "export_type": TIMELINE_EXPORT_TYPE,
        "contract_version": TIMELINE_EXPORT_CONTRACT_VERSION,
        "config": {
            "symbols": list(config.symbols),
            "interval": config.interval,
            "window_size": config.window_size,
            "window_count": config.window_count,
            "required_candles": config.required_candles,
            "min_candles": config.min_candles,
            "reference_mode": config.reference_mode,
        },
        "summary": {
            "symbols": summary["Symbols"],
            "ok": summary["OK"],
            "errors": summary["Errors"],
            "insufficient_data": summary["INSUFFICIENT_DATA"],
            "current_up": summary["current_UP"],
            "current_down": summary["current_DOWN"],
            "current_flat": summary["current_FLAT"],
            "current_unknown": summary["current_UNKNOWN"],
        },
        "rows": [_row_to_dict(row) for row in rows],
        "warnings": list(result.warnings),
        "safety": dict(TIMELINE_EXPORT_SAFETY),
    }


def timeline_result_to_markdown(result: Any) -> str:
    payload = timeline_result_to_dict(result)
    config = payload["config"]
    summary = payload["summary"]
    labels = build_window_labels(config["window_count"])

    header = (
        "| Symbol | Status | "
        + " | ".join(labels)
        + " | Stability | Last transition | Current confidence | Safety |"
    )
    separator = "|---|---|" + "|".join("---" for _ in labels) + "|---|---|---:|---|"
    rows = [
        _markdown_table_row(row, labels)
        for row in payload["rows"]
    ]

    warning_lines = ["No warnings."] if not payload["warnings"] else [f"- {_md_escape(warning)}" for warning in payload["warnings"]]
    safety_lines = [f"{key} = {_safety_value(value)}" for key, value in payload["safety"].items()]

    lines = [
        "# BOOK-L1 Timeline Preview",
        "",
        "## Config",
        "",
        f"- Symbols: {_format_markdown_symbols(config['symbols'])}",
        f"- Interval: `{config['interval']}`",
        f"- Window size: `{config['window_size']}`",
        f"- Window count: `{config['window_count']}`",
        f"- Required candles per symbol: `{config['required_candles']}`",
        f"- Min candles per window: `{config['min_candles']}`",
        f"- Reference mode: `{config['reference_mode']}`",
        "",
        "## Timeline",
        "",
        header,
        separator,
        *rows,
        "",
        "## Summary",
        "",
        f"- Symbols: `{summary['symbols']}`",
        f"- OK: `{summary['ok']}`",
        f"- Errors: `{summary['errors']}`",
        f"- Insufficient data: `{summary['insufficient_data']}`",
        f"- Current UP: `{summary['current_up']}`",
        f"- Current DOWN: `{summary['current_down']}`",
        f"- Current FLAT: `{summary['current_flat']}`",
        f"- Current UNKNOWN: `{summary['current_unknown']}`",
        "",
        "## Warnings",
        "",
        *warning_lines,
        "",
        "## Safety",
        "",
        "```text",
        *safety_lines,
        "```",
        "",
        "## Conclusion",
        "",
        "This report is a read-only BOOK-L1 market-regime timeline preview. "
        "It does not produce trading signals and does not approve runtime trading.",
        "",
    ]
    return "\n".join(lines)


def write_text_overwrite(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _build_export_paths(config: TimelineExportConfig) -> TimelineExportPaths:
    json_path = config.output_dir / DEFAULT_TIMELINE_JSON_FILENAME if config.export_format in {"all", "json"} else None
    markdown_path = (
        config.output_dir / DEFAULT_TIMELINE_MARKDOWN_FILENAME
        if config.export_format in {"all", "md"}
        else None
    )
    return TimelineExportPaths(json_path=json_path, markdown_path=markdown_path)


def _row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "symbol": row.symbol,
        "status": row.status,
        "regimes": list(row.regimes),
        "transitions": list(row.transitions),
        "last_transition": row.last_transition,
        "stability": row.stability,
        "current_confidence": row.current_confidence,
        "current_trend_strength": row.current_trend_strength,
        "trade_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": False,
        "windows": [_window_to_dict(window) for window in row.windows],
        "warning": row.warning,
    }


def _window_to_dict(window: Any) -> dict[str, Any]:
    return {
        "label": window.window_label,
        "market_regime": window.market_regime,
        "directional_bias": window.directional_bias,
        "confidence": window.confidence,
        "trend_strength": window.trend_strength,
        "first_open_time": window.first_open_time,
        "last_open_time": window.last_open_time,
        "reason_codes": list(window.reason_codes),
    }


def _markdown_table_row(row: dict[str, Any], labels: tuple[str, ...]) -> str:
    regimes_by_label = {
        window["label"]: window["market_regime"]
        for window in row["windows"]
    }
    values = [
        row["symbol"],
        row["status"],
        *(regimes_by_label.get(label, "UNKNOWN") for label in labels),
        row["stability"],
        row["last_transition"],
        f"{row['current_confidence']:.2f}",
        "LOCKED",
    ]
    return "| " + " | ".join(_md_escape(str(value)) for value in values) + " |"


def _format_markdown_symbols(symbols: list[str]) -> str:
    return ", ".join(f"`{symbol}`" for symbol in symbols)


def _md_escape(value: str) -> str:
    return value.replace("|", "\\|")


def _safety_value(value: bool | str) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return value


__all__ = [
    "DEFAULT_TIMELINE_EXPORT_DIR",
    "DEFAULT_TIMELINE_JSON_FILENAME",
    "DEFAULT_TIMELINE_MARKDOWN_FILENAME",
    "TimelineExportConfig",
    "TimelineExportPaths",
    "TimelineExportResult",
    "TimelinePreviewExporter",
    "timeline_result_to_dict",
    "timeline_result_to_markdown",
    "write_text_overwrite",
]
