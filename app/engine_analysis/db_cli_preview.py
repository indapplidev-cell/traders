"""Read-only CLI preview for confirmed PostgreSQL ``market_candles`` data."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.engine_analysis.data_source_boundary import (
    CandleDataRequest,
    run_engine_analysis_from_provider,
)
from app.engine_analysis.json_export import save_engine_analysis_json
from app.engine_analysis.postgres_candle_adapter import (
    PostgresMarketCandlesProvider,
)

STAGE = "ENGINE-ANALYSIS-12"
CONFIRMED_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
CONFIRMED_INTERVAL = "15m"
DEFAULT_DB_ENV_NAMES = (
    "TRADERS_ML_DATABASE_URL",
    "TRADERS_ML_POSTGRES_URL",
    "DATABASE_URL",
    "POSTGRES_URL",
)
MAX_CANDLES_HARD_CAP = 500
AVAILABILITY_SQL = """
SELECT
    symbol,
    interval,
    COUNT(*) AS candle_count,
    MIN(open_time) AS min_open_time,
    MAX(open_time) AS max_open_time
FROM public.market_candles
WHERE symbol IN ('BTCUSDT', 'ETHUSDT', 'SOLUSDT')
  AND interval = '15m'
GROUP BY symbol, interval
ORDER BY symbol, interval
""".strip()


class CliError(RuntimeError):
    """Expected operational CLI failure with a stable public error code."""

    def __init__(self, code: str, detail: str | None = None) -> None:
        super().__init__(detail or code)
        self.code = code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preview engine_analysis from read-only PostgreSQL market_candles"
    )
    parser.add_argument("--symbol", choices=CONFIRMED_SYMBOLS)
    parser.add_argument("--interval", choices=(CONFIRMED_INTERVAL,), default=CONFIRMED_INTERVAL)
    parser.add_argument("--period-start", help="ISO datetime; requires --period-end")
    parser.add_argument(
        "--period-end",
        help="ISO datetime, inclusive; requires --period-start",
    )
    parser.add_argument("--max-candles", type=int, default=96)
    parser.add_argument("--output", help="Optional full JSON result path")
    parser.add_argument("--preview-output", help="Optional compact preview JSON path")
    parser.add_argument("--print-json", action="store_true")
    parser.add_argument("--db-env", help="Read the DB URL only from this env var")
    parser.add_argument("--availability", action="store_true")
    return parser


def validate_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if not args.availability and not args.symbol:
        parser.error("--symbol is required unless --availability is used")
    if args.max_candles <= 0:
        parser.error("--max-candles must be positive")
    if args.max_candles > MAX_CANDLES_HARD_CAP:
        parser.error(f"--max-candles must not exceed {MAX_CANDLES_HARD_CAP}")
    if bool(args.period_start) != bool(args.period_end):
        parser.error("--period-start and --period-end must be provided together")


def resolve_db_url(
    environment: Mapping[str, str], explicit_name: str | None = None
) -> tuple[str, str]:
    names = (explicit_name,) if explicit_name else DEFAULT_DB_ENV_NAMES
    for name in names:
        value = environment.get(name)
        if value:
            return name, value
    raise CliError("DB_CONFIG_MISSING")


def mask_db_url(db_url: str) -> str:
    """Return useful connection coordinates without credentials or database name."""
    try:
        parsed = make_url(db_url)
        host = parsed.host or "<host>"
        port = f":{parsed.port}" if parsed.port is not None else ""
        return f"{parsed.drivername}://<user>:<password>@{host}{port}/<db>"
    except Exception:
        return "<invalid-database-url>"


def parse_iso_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CliError("INVALID_PERIOD", "period bounds must be ISO datetimes") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def iso_datetime(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def resolve_period_bounds(
    connection: Any,
    symbol: str,
    interval: str,
    max_candles: int,
    period_start: str | None = None,
    period_end: str | None = None,
) -> tuple[str, str]:
    if period_start is not None and period_end is not None:
        start = parse_iso_datetime(period_start)
        end = parse_iso_datetime(period_end)
        if start > end:
            raise CliError("INVALID_PERIOD", "period_start must not exceed period_end")
        return start.isoformat(), end.isoformat()

    statement = text(
        "SELECT MAX(open_time) AS max_open_time FROM public.market_candles "
        "WHERE symbol = :symbol AND interval = :interval"
    )
    row = connection.execute(
        statement, {"symbol": symbol, "interval": interval}
    ).mappings().one()
    max_open_time = row["max_open_time"]
    if max_open_time is None:
        raise CliError("DB_DATA_MISSING")
    end = (
        max_open_time
        if isinstance(max_open_time, datetime)
        else parse_iso_datetime(str(max_open_time))
    )
    start = end - timedelta(minutes=15 * (max_candles - 1))
    return start.isoformat(), end.isoformat()


def availability_rows(connection: Any) -> list[dict[str, object]]:
    rows = connection.execute(text(AVAILABILITY_SQL)).mappings().all()
    return [
        {
            "symbol": row["symbol"],
            "interval": row["interval"],
            "candle_count": int(row["candle_count"]),
            "min_open_time": iso_datetime(row["min_open_time"]),
            "max_open_time": iso_datetime(row["max_open_time"]),
        }
        for row in rows
    ]


def ensure_market_candles_table(connection: Any) -> None:
    result = connection.execute(
        text("SELECT to_regclass('public.market_candles') AS table_name")
    ).mappings().one()
    if result["table_name"] is None:
        raise CliError("DB_TABLE_MISSING")


def build_cli_payload(
    engine_payload: dict[str, object], db_env_name: str, db_url: str
) -> dict[str, object]:
    return {
        "cli": {
            "stage": STAGE,
            "db_env_var_name": db_env_name,
            "db_url_masked": mask_db_url(db_url),
            "source": "postgresql.public.market_candles",
            "period_end_boundary": "inclusive",
        },
        "payload": engine_payload,
    }


def build_cli_preview(
    boundary_result: Any,
    db_env_name: str,
    db_url: str,
    output: str | None,
    preview_output: str | None,
) -> dict[str, object]:
    preview = boundary_result.engine_output.preview
    safety = preview["safety"]
    if safety != {
        "trade_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": False,
        "live_trading_connected": False,
    }:
        raise CliError("SAFETY_CONTRACT_VIOLATION")
    return {
        "service": "ENGINE_ANALYSIS",
        "stage": STAGE,
        "symbol": preview["symbol"],
        "interval": preview["interval"],
        "period_start": preview["period_start"],
        "period_end": preview["period_end"],
        "period_end_boundary": "inclusive",
        "candles_loaded": boundary_result.batch.metadata.get("candle_count", 0),
        "market_regime": preview["market_regime"],
        "confidence": preview["confidence"],
        "top_reason_codes": preview["reason_codes_top"],
        "warnings_count": len(boundary_result.warnings),
        "errors_count": len(boundary_result.errors),
        "boundary_status": boundary_result.status.value,
        "safety": safety,
        "db_env_var_name": db_env_name,
        "db_url_masked": mask_db_url(db_url),
        "output_path": output,
        "preview_output_path": preview_output,
    }


def save_json(payload: dict[str, object], output_path: str | Path) -> Path:
    return save_engine_analysis_json(payload, output_path)


def print_human_preview(preview: Mapping[str, object]) -> None:
    safety = preview["safety"]
    assert isinstance(safety, Mapping)
    keys = (
        "service", "stage", "symbol", "interval", "period_start", "period_end",
        "candles_loaded", "market_regime", "confidence", "warnings_count",
        "errors_count", "boundary_status",
    )
    for key in keys:
        print(f"{key}: {preview[key]}")
    codes = preview["top_reason_codes"]
    print(f"top reason codes: {', '.join(codes) if isinstance(codes, list) else codes}")
    for key in (
        "trade_signal", "safe_for_runtime_trading", "live_trading_connected"
    ):
        print(f"safety.{key}: {str(safety[key]).lower() if isinstance(safety[key], bool) else safety[key]}")
    print(f"output: {preview['output_path'] or 'not saved'}")
    print(f"preview_output: {preview['preview_output_path'] or 'not saved'}")


def _is_table_missing(exc: BaseException) -> bool:
    current: BaseException | None = exc
    while current is not None:
        code = getattr(current, "pgcode", None) or getattr(current, "sqlstate", None)
        message = str(current).lower()
        if code == "42P01" or "undefined table" in message or (
            "relation" in message and "market_candles" in message and "does not exist" in message
        ):
            return True
        current = current.__cause__
    return False


def _run(args: argparse.Namespace, db_env_name: str, db_url: str) -> int:
    engine = None
    try:
        engine = create_engine(db_url)
        with engine.connect() as connection:
            ensure_market_candles_table(connection)
            if args.availability:
                rows = availability_rows(connection)
                print("symbol interval candle_count min_open_time max_open_time")
                for row in rows:
                    print(
                        f"{row['symbol']} {row['interval']} {row['candle_count']} "
                        f"{row['min_open_time']} {row['max_open_time']}"
                    )
                return 0

            start, end = resolve_period_bounds(
                connection, args.symbol, args.interval, args.max_candles,
                args.period_start, args.period_end,
            )
            request = CandleDataRequest(
                symbol=args.symbol,
                interval=args.interval,
                limit=args.max_candles,
                start_time=start,
                end_time=end,
                source_name="postgresql.public.market_candles",
            )
            result = run_engine_analysis_from_provider(
                PostgresMarketCandlesProvider(connection), request
            )
            full_payload = build_cli_payload(
                result.engine_output.json_payload, db_env_name, db_url
            )
            preview = build_cli_preview(
                result, db_env_name, db_url, args.output, args.preview_output
            )
            if args.output:
                save_json(full_payload, args.output)
            if args.preview_output:
                save_json(preview, args.preview_output)
            if args.print_json:
                print(json.dumps(full_payload, ensure_ascii=False, indent=2))
            else:
                print_human_preview(preview)
            return 0
    except CliError:
        raise
    except Exception as exc:
        if _is_table_missing(exc):
            raise CliError("DB_TABLE_MISSING") from exc
        raise CliError("DB_CONNECTION_FAILED") from exc
    finally:
        if engine is not None:
            engine.dispose()


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    validate_args(args, parser)
    try:
        db_env_name, db_url = resolve_db_url(os.environ, args.db_env)
        return _run(args, db_env_name, db_url)
    except CliError as exc:
        print(f"error: {exc.code}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
