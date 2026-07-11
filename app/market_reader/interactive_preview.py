from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from app.market_reader.api_response import build_book_l1_api_response_payload


def build_book_l1_interactive_preview_report(
    *,
    symbol: str,
    interval: str,
    candle_repository: Any,
    limit: int = 300,
    min_candles: int = 50,
    reader: Any | None = None,
) -> str:
    """Build a human-readable BOOK-L1 terminal report from stored candles."""

    payload = build_book_l1_api_response_payload(
        symbol=symbol,
        interval=interval,
        limit=limit,
        min_candles=min_candles,
        candle_repository=candle_repository,
        reader=reader,
    )
    return format_book_l1_interactive_preview_report(payload)


def format_book_l1_interactive_preview_report(payload: Mapping[str, Any]) -> str:
    """Format the BOOK-L1 API preview payload as deterministic terminal tables."""

    if not isinstance(payload, Mapping):
        raise ValueError("payload must be a mapping")

    request = _mapping_or_empty(payload.get("request"))
    preview = _mapping_or_empty(payload.get("preview"))
    analysis = _mapping_or_empty(preview.get("analysis"))
    safety = _mapping_or_empty(payload.get("safety"))

    sections = [
        "BOOK-L1 Interactive Preview / Human Table Report",
        "Preview only. This report is not a trading signal and cannot approve orders.",
        _format_table(
            "Response",
            [
                ("status", _stringify(payload.get("status"))),
                ("service", _stringify(payload.get("service"))),
                ("contract_version", _stringify(payload.get("contract_version"))),
            ],
        ),
        _format_table(
            "Request",
            [
                ("symbol", _stringify(request.get("symbol"))),
                ("interval", _stringify(request.get("interval"))),
                ("limit", _stringify(request.get("limit"))),
                ("min_candles", _stringify(request.get("min_candles"))),
            ],
        ),
        _format_table(
            "Candle Window",
            [
                ("candle_count", _stringify(preview.get("candle_count"))),
                ("requested_limit", _stringify(preview.get("requested_limit"))),
                ("first_open_time", _stringify(preview.get("first_open_time"))),
                ("last_open_time", _stringify(preview.get("last_open_time"))),
            ],
        ),
        _format_table(
            "Market Analysis",
            [
                ("market_regime", _stringify(analysis.get("market_regime"))),
                ("directional_bias", _stringify(analysis.get("directional_bias"))),
                ("confidence", _format_confidence(analysis.get("confidence"))),
                ("trend_strength", _stringify(analysis.get("trend_strength"))),
                ("trade_signal", _stringify(analysis.get("trade_signal"))),
                (
                    "safe_for_runtime_trading",
                    _stringify(analysis.get("safe_for_runtime_trading")),
                ),
            ],
        ),
        _format_table(
            "Safety",
            [
                ("api_preview_only", _stringify(safety.get("api_preview_only"))),
                ("trade_signal", _stringify(safety.get("trade_signal"))),
                (
                    "safe_for_runtime_trading",
                    _stringify(safety.get("safe_for_runtime_trading")),
                ),
                ("orders_enabled", _stringify(safety.get("orders_enabled"))),
                ("live_trading_connected", _stringify(safety.get("live_trading_connected"))),
                ("traders_core_connected", _stringify(safety.get("traders_core_connected"))),
                ("approved_for_live_trading", _stringify(safety.get("approved_for_live_trading"))),
                (
                    "approved_for_auto_activation",
                    _stringify(safety.get("approved_for_auto_activation")),
                ),
                ("model_training_executed", _stringify(safety.get("model_training_executed"))),
                ("binance_download_executed", _stringify(safety.get("binance_download_executed"))),
            ],
        ),
        _format_list_table("Reason Codes", _sequence_or_empty(analysis.get("reason_codes"))),
        _format_list_table("Warnings", _sequence_or_empty(payload.get("warnings"))),
        _format_list_table("Errors", _sequence_or_empty(payload.get("errors"))),
    ]

    return "\n\n".join(section for section in sections if section)


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


def _format_table(title: str, rows: Sequence[tuple[str, str]]) -> str:
    normalized_rows = [(str(key), str(value)) for key, value in rows]
    field_width = max([len("Field"), *(len(key) for key, _ in normalized_rows)])
    value_width = max([len("Value"), *(len(value) for _, value in normalized_rows)])

    border = f"+-{'-' * field_width}-+-{'-' * value_width}-+"
    lines = [
        title,
        border,
        f"| {'Field'.ljust(field_width)} | {'Value'.ljust(value_width)} |",
        border,
    ]

    for key, value in normalized_rows:
        lines.append(f"| {key.ljust(field_width)} | {value.ljust(value_width)} |")

    lines.append(border)
    return "\n".join(lines)


def _format_list_table(title: str, values: Sequence[Any]) -> str:
    if not values:
        return f"{title}\n(no items)"

    rows = [(str(index), _stringify(value)) for index, value in enumerate(values, start=1)]
    index_width = max([len("#"), *(len(index) for index, _ in rows)])
    value_width = max([len("Value"), *(len(value) for _, value in rows)])
    border = f"+-{'-' * index_width}-+-{'-' * value_width}-+"

    lines = [
        title,
        border,
        f"| {'#'.ljust(index_width)} | {'Value'.ljust(value_width)} |",
        border,
    ]
    for index, value in rows:
        lines.append(f"| {index.ljust(index_width)} | {value.ljust(value_width)} |")
    lines.append(border)
    return "\n".join(lines)


def _format_confidence(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return _stringify(value)
    return f"{confidence:.4f} ({confidence * 100:.2f}%)"


def _stringify(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
