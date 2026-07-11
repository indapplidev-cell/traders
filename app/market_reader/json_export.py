from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any


CONTRACT_VERSION = "book_l1_json_export_v1"
SERVICE_NAME = "BOOK_L1_MARKET_READER"
DEFAULT_BOOK_L1_EXPORT_DIR = Path("reports") / "book_l1"

REPORT_TYPES = (
    "current_preview",
    "multi_preview",
    "history_preview",
    "timeline_preview",
)

EXPORT_FILE_NAMES = {
    "current_preview": "current_preview.json",
    "multi_preview": "multi_preview.json",
    "history_preview": "history_preview.json",
    "timeline_preview": "timeline_preview.json",
}


@dataclass(frozen=True)
class BookL1JsonExportSafety:
    trade_signal: str = "NOT_EVALUATED"
    safe_for_runtime_trading: bool = False
    orders_enabled: bool = False
    live_trading_connected: bool = False
    traders_core_connected: bool = False
    approved_for_live_trading: bool = False
    approved_for_auto_activation: bool = False
    model_training_executed: bool = False
    binance_download_executed: bool = False

    def __post_init__(self) -> None:
        if self.trade_signal != "NOT_EVALUATED":
            raise ValueError("BOOK-L1 JSON export must not produce trading signals")
        if self.safe_for_runtime_trading is not False:
            raise ValueError("BOOK-L1 JSON export must not approve runtime trading")
        if self.orders_enabled is not False:
            raise ValueError("BOOK-L1 JSON export must not enable orders")
        if self.live_trading_connected is not False:
            raise ValueError("BOOK-L1 JSON export must not connect live trading")
        if self.traders_core_connected is not False:
            raise ValueError("BOOK-L1 JSON export must not connect traders-core")
        if self.approved_for_live_trading is not False:
            raise ValueError("BOOK-L1 JSON export must not approve live trading")
        if self.approved_for_auto_activation is not False:
            raise ValueError("BOOK-L1 JSON export must not approve auto activation")
        if self.model_training_executed is not False:
            raise ValueError("BOOK-L1 JSON export must not execute model training")
        if self.binance_download_executed is not False:
            raise ValueError("BOOK-L1 JSON export must not execute Binance download")

    def to_dict(self) -> dict[str, object]:
        return {
            "trade_signal": self.trade_signal,
            "safe_for_runtime_trading": self.safe_for_runtime_trading,
            "orders_enabled": self.orders_enabled,
            "live_trading_connected": self.live_trading_connected,
            "traders_core_connected": self.traders_core_connected,
            "approved_for_live_trading": self.approved_for_live_trading,
            "approved_for_auto_activation": self.approved_for_auto_activation,
            "model_training_executed": self.model_training_executed,
            "binance_download_executed": self.binance_download_executed,
        }


@dataclass(frozen=True)
class BookL1JsonExportEnvelope:
    report_type: str
    request: dict[str, object]
    result: dict[str, object]
    summary: dict[str, object]
    status: str = "ok"
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
    safety: BookL1JsonExportSafety = field(default_factory=BookL1JsonExportSafety)

    def __post_init__(self) -> None:
        if self.report_type not in REPORT_TYPES:
            raise ValueError(f"unsupported BOOK-L1 report_type: {self.report_type}")
        if self.status not in {"ok", "partial", "error"}:
            raise ValueError("status must be one of: ok, partial, error")

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "service": SERVICE_NAME,
            "report_type": self.report_type,
            "contract_version": CONTRACT_VERSION,
            "request": self.request,
            "result": self.result,
            "summary": self.summary,
            "safety": self.safety.to_dict(),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


def resolve_export_path(report_type: str, output_dir: str | Path | None = None) -> Path:
    if report_type not in EXPORT_FILE_NAMES:
        raise ValueError(f"unsupported BOOK-L1 report_type: {report_type}")
    base_dir = Path(output_dir) if output_dir is not None else DEFAULT_BOOK_L1_EXPORT_DIR
    return base_dir / EXPORT_FILE_NAMES[report_type]


def write_book_l1_json_export(
    envelope: BookL1JsonExportEnvelope,
    *,
    output_dir: str | Path | None = None,
) -> Path:
    path = resolve_export_path(envelope.report_type, output_dir=output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(envelope.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def build_current_preview_export_payload(
    *,
    request: dict[str, object],
    preview_payload: dict[str, object],
) -> BookL1JsonExportEnvelope:
    analysis = _mapping_or_empty(preview_payload.get("analysis"))
    summary = {
        "market_regime": _string_field(analysis, "market_regime", "UNKNOWN"),
        "directional_bias": _string_field(analysis, "directional_bias", "UNKNOWN"),
        "confidence": _float_field(analysis, "confidence", 0.0),
        "trend_strength": _string_field(analysis, "trend_strength", "UNKNOWN"),
        "trade_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": False,
    }
    return BookL1JsonExportEnvelope(
        report_type="current_preview",
        request=dict(request),
        result=dict(preview_payload),
        summary=summary,
    )


def build_multi_preview_export_payload(
    *,
    request: dict[str, object],
    result: Any,
) -> BookL1JsonExportEnvelope:
    rows = tuple(getattr(result, "rows", ()))
    summary = _multi_summary(rows)
    errors = _row_errors(rows)
    return BookL1JsonExportEnvelope(
        report_type="multi_preview",
        request=dict(request),
        result={
            "config": _config_to_dict(getattr(result, "config", None)),
            "rows": [_multi_row_to_dict(row) for row in rows],
        },
        summary=summary,
        status=_status_from_counts(ok=int(summary["ok"]), errors=int(summary["errors"])),
        warnings=tuple(str(item) for item in getattr(result, "warnings", ())),
        errors=errors,
    )


def build_history_preview_export_payload(
    *,
    request: dict[str, object],
    result: Any,
) -> BookL1JsonExportEnvelope:
    rows = tuple(getattr(result, "rows", ()))
    summary = _history_summary(rows)
    errors = _row_errors(rows)
    return BookL1JsonExportEnvelope(
        report_type="history_preview",
        request=dict(request),
        result={
            "config": _config_to_dict(getattr(result, "config", None)),
            "rows": [_history_row_to_dict(row) for row in rows],
        },
        summary=summary,
        status=_status_from_counts(ok=int(summary["ok"]), errors=int(summary["errors"])),
        warnings=tuple(str(item) for item in getattr(result, "warnings", ())),
        errors=errors,
    )


def build_timeline_preview_export_payload(
    *,
    request: dict[str, object],
    result: Any,
) -> BookL1JsonExportEnvelope:
    rows = tuple(getattr(result, "rows", ()))
    summary = _timeline_summary(rows)
    errors = _row_errors(rows)
    return BookL1JsonExportEnvelope(
        report_type="timeline_preview",
        request=dict(request),
        result={
            "config": _config_to_dict(getattr(result, "config", None)),
            "rows": [_timeline_row_to_dict(row) for row in rows],
        },
        summary=summary,
        status=_status_from_counts(ok=int(summary["ok"]), errors=int(summary["errors"])),
        warnings=tuple(str(item) for item in getattr(result, "warnings", ())),
        errors=errors,
    )


def _multi_summary(rows: tuple[Any, ...]) -> dict[str, object]:
    regime_counts = Counter(_known_regime(_read_field(row, "market_regime", "UNKNOWN")) for row in rows)
    errors = sum(1 for row in rows if _read_status(row) != "OK")
    return {
        "total_symbols": len(rows),
        "ok": sum(1 for row in rows if _read_status(row) == "OK"),
        "errors": errors,
        "up": regime_counts.get("UP", 0),
        "down": regime_counts.get("DOWN", 0),
        "flat": regime_counts.get("FLAT", 0),
        "unknown": regime_counts.get("UNKNOWN", 0),
    }


def _history_summary(rows: tuple[Any, ...]) -> dict[str, object]:
    transition_counts = Counter(_read_token(row, "transition", "ERROR") for row in rows)
    current_counts = Counter(_known_regime(_read_field(row, "current_regime", "UNKNOWN")) for row in rows)
    errors = sum(1 for row in rows if _read_status(row) != "OK")
    return {
        "total_symbols": len(rows),
        "ok": sum(1 for row in rows if _read_status(row) == "OK"),
        "errors": errors,
        "insufficient_data": sum(1 for row in rows if _read_status(row) == "INSUFFICIENT_DATA"),
        "transition_counts": dict(sorted(transition_counts.items())),
        "current_regime_counts": _regime_counts_dict(current_counts),
    }


def _timeline_summary(rows: tuple[Any, ...]) -> dict[str, object]:
    current_counts = Counter(_current_timeline_regime(row) for row in rows)
    transition_counts = Counter(_read_token(row, "last_transition", "ERROR") for row in rows)
    stability_counts = Counter(_read_token(row, "stability", "ERROR") for row in rows)
    errors = sum(1 for row in rows if _read_status(row) != "OK")
    return {
        "total_symbols": len(rows),
        "ok": sum(1 for row in rows if _read_status(row) == "OK"),
        "errors": errors,
        "insufficient_data": sum(1 for row in rows if _read_status(row) == "INSUFFICIENT_DATA"),
        "current_regime_counts": _regime_counts_dict(current_counts),
        "last_transition_counts": dict(sorted(transition_counts.items())),
        "stability_counts": dict(sorted(stability_counts.items())),
    }


def _status_from_counts(*, ok: int, errors: int) -> str:
    if errors == 0:
        return "ok"
    if ok > 0:
        return "partial"
    return "error"


def _row_errors(rows: tuple[Any, ...]) -> tuple[str, ...]:
    messages: list[str] = []
    for row in rows:
        if _read_status(row) == "OK":
            continue
        symbol = _read_field(row, "symbol", "UNKNOWN")
        warning = _read_field(row, "warning", None) or _read_status(row)
        messages.append(f"{symbol}: {warning}")
    return tuple(messages)


def _config_to_dict(config: Any) -> dict[str, object]:
    if config is None:
        return {}
    return {
        field: _json_value(_read_field(config, field, None))
        for field in (
            "symbols",
            "symbol",
            "interval",
            "limit",
            "min_candles",
            "window_size",
            "window_count",
            "required_candles",
            "required_candles_per_symbol",
            "reference_mode",
            "reference_date",
        )
        if _has_field(config, field)
    }


def _multi_row_to_dict(row: Any) -> dict[str, object]:
    return {
        "symbol": _read_field(row, "symbol", "UNKNOWN"),
        "status": _read_status(row),
        "market_regime": _read_token(row, "market_regime", "UNKNOWN"),
        "directional_bias": _read_token(row, "directional_bias", "UNKNOWN"),
        "confidence": _read_float(row, "confidence", 0.0),
        "trend_strength": _read_token(row, "trend_strength", "UNKNOWN"),
        "volatility_context": _read_token(row, "volatility_context", "UNKNOWN"),
        "trade_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": False,
        "candle_count": int(_read_field(row, "candle_count", 0) or 0),
        "first_open_time": _read_field(row, "first_open_time", None),
        "last_open_time": _read_field(row, "last_open_time", None),
        "reason_codes": list(_sequence_or_empty(_read_field(row, "reason_codes", ()))),
        "warning": _read_field(row, "warning", None),
    }


def _history_row_to_dict(row: Any) -> dict[str, object]:
    return {
        "symbol": _read_field(row, "symbol", "UNKNOWN"),
        "status": _read_status(row),
        "previous_regime": _read_token(row, "previous_regime", "UNKNOWN"),
        "current_regime": _read_token(row, "current_regime", "UNKNOWN"),
        "transition": _read_token(row, "transition", "ERROR"),
        "previous_confidence": _read_float(row, "previous_confidence", 0.0),
        "current_confidence": _read_float(row, "current_confidence", 0.0),
        "current_trend_strength": _read_token(row, "current_trend_strength", "UNKNOWN"),
        "trade_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": False,
        "previous_snapshot": _snapshot_to_dict(_read_field(row, "previous_snapshot", None)),
        "current_snapshot": _snapshot_to_dict(_read_field(row, "current_snapshot", None)),
        "warning": _read_field(row, "warning", None),
    }


def _timeline_row_to_dict(row: Any) -> dict[str, object]:
    return {
        "symbol": _read_field(row, "symbol", "UNKNOWN"),
        "status": _read_status(row),
        "regimes": list(_sequence_or_empty(_read_field(row, "regimes", ()))),
        "transitions": list(_sequence_or_empty(_read_field(row, "transitions", ()))),
        "last_transition": _read_token(row, "last_transition", "ERROR"),
        "stability": _read_token(row, "stability", "ERROR"),
        "current_confidence": _read_float(row, "current_confidence", 0.0),
        "current_trend_strength": _read_token(row, "current_trend_strength", "UNKNOWN"),
        "trade_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": False,
        "windows": [_snapshot_to_dict(window) for window in _sequence_or_empty(_read_field(row, "windows", ()))],
        "warning": _read_field(row, "warning", None),
    }


def _snapshot_to_dict(snapshot: Any) -> dict[str, object] | None:
    if snapshot is None:
        return None
    return {
        "symbol": _read_field(snapshot, "symbol", "UNKNOWN"),
        "window_name": _read_field(snapshot, "window_name", None),
        "label": _read_field(snapshot, "window_label", None),
        "market_regime": _read_token(snapshot, "market_regime", "UNKNOWN"),
        "directional_bias": _read_token(snapshot, "directional_bias", "UNKNOWN"),
        "confidence": _read_float(snapshot, "confidence", 0.0),
        "trend_strength": _read_token(snapshot, "trend_strength", "UNKNOWN"),
        "trade_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": False,
        "candle_count": int(_read_field(snapshot, "candle_count", 0) or 0),
        "first_open_time": _read_field(snapshot, "first_open_time", None),
        "last_open_time": _read_field(snapshot, "last_open_time", None),
        "reason_codes": list(_sequence_or_empty(_read_field(snapshot, "reason_codes", ()))),
    }


def _current_timeline_regime(row: Any) -> str:
    regimes = tuple(_sequence_or_empty(_read_field(row, "regimes", ())))
    if not regimes:
        return "UNKNOWN"
    return _known_regime(regimes[-1])


def _regime_counts_dict(counts: Counter[str]) -> dict[str, int]:
    return {
        "up": counts.get("UP", 0),
        "down": counts.get("DOWN", 0),
        "flat": counts.get("FLAT", 0),
        "unknown": counts.get("UNKNOWN", 0),
    }


def _known_regime(value: Any) -> str:
    token = _normalize_token(value)
    return token if token in {"UP", "DOWN", "FLAT"} else "UNKNOWN"


def _has_field(source: Any, field_name: str) -> bool:
    if isinstance(source, Mapping):
        return field_name in source
    return hasattr(source, field_name)


def _read_status(row: Any) -> str:
    return _read_token(row, "status", "ERROR")


def _read_field(source: Any, field_name: str, default: Any) -> Any:
    if source is None:
        return default
    if isinstance(source, Mapping):
        return source.get(field_name, default)
    return getattr(source, field_name, default)


def _read_token(source: Any, field_name: str, default: str) -> str:
    return _normalize_token(_read_field(source, field_name, default))


def _normalize_token(value: Any) -> str:
    if isinstance(value, Enum):
        value = value.value
    return str(value or "").strip().upper()


def _string_field(source: Mapping[str, Any], field_name: str, default: str) -> str:
    return str(source.get(field_name) or default)


def _float_field(source: Mapping[str, Any], field_name: str, default: float) -> float:
    try:
        return float(source.get(field_name, default))
    except (TypeError, ValueError):
        return default


def _read_float(source: Any, field_name: str, default: float) -> float:
    try:
        return float(_read_field(source, field_name, default))
    except (TypeError, ValueError):
        return default


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


def _json_value(value: Any) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str):
        return [_json_value(item) for item in value]
    if is_dataclass(value):
        return {
            name: _json_value(_read_field(value, name, None))
            for name in getattr(value, "__dataclass_fields__", {})
        }
    return value


__all__ = [
    "CONTRACT_VERSION",
    "SERVICE_NAME",
    "DEFAULT_BOOK_L1_EXPORT_DIR",
    "EXPORT_FILE_NAMES",
    "BookL1JsonExportSafety",
    "BookL1JsonExportEnvelope",
    "resolve_export_path",
    "write_book_l1_json_export",
    "build_current_preview_export_payload",
    "build_multi_preview_export_payload",
    "build_history_preview_export_payload",
    "build_timeline_preview_export_payload",
]
