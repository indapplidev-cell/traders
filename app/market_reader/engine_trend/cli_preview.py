"""Command-line preview for candle data supplied in a JSON file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.market_reader.engine_trend.engine import run_engine_trend_from_rows
from app.market_reader.engine_trend.json_export import save_engine_trend_json


def load_candle_payload(
    input_path: str | Path,
) -> tuple[str | None, str | None, list[dict[str, object]]]:
    """Load either an envelope or a direct list of candle mappings."""
    data = json.loads(Path(input_path).read_text(encoding="utf-8-sig"))
    symbol: str | None = None
    interval: str | None = None
    if isinstance(data, dict):
        if "candles" not in data or not isinstance(data["candles"], list):
            raise ValueError("JSON object must contain a candles list")
        symbol = str(data["symbol"]) if data.get("symbol") else None
        interval = str(data["interval"]) if data.get("interval") else None
        rows = data["candles"]
    elif isinstance(data, list):
        rows = data
    else:
        raise ValueError("JSON root must be an object or list")
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("each candle must be an object")
    return symbol, interval, rows


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preview an engine_trend market reading")
    parser.add_argument("--input", required=True, help="JSON candle file")
    parser.add_argument("--symbol", help="Symbol used when absent from the file")
    parser.add_argument("--interval", help="Interval used when absent from the file")
    parser.add_argument("--output", help="Optional JSON result path")
    parser.add_argument("--print-json", action="store_true", help="Print the full JSON result")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        file_symbol, file_interval, rows = load_candle_payload(args.input)
        symbol = args.symbol or file_symbol
        interval = args.interval or file_interval
        if not symbol or not interval:
            raise ValueError("symbol and interval are required")
        facade = run_engine_trend_from_rows(symbol, interval, rows)
        if args.output:
            save_engine_trend_json(facade.json_payload, args.output)
        if args.print_json:
            print(json.dumps(facade.json_payload, ensure_ascii=False, indent=2))
        else:
            preview = facade.preview
            print(f"symbol: {preview['symbol']}")
            print(f"interval: {preview['interval']}")
            print(f"market_regime: {preview['market_regime']}")
            print(f"confidence: {preview['confidence']}")
            print(f"status: {preview['status']}")
            codes = preview["reason_codes_top"]
            print(f"top reason codes: {', '.join(codes) if isinstance(codes, list) else codes}")
        return 0
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"engine_trend preview error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
