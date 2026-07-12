"""Read-only operational smoke for engine_trend and PostgreSQL market_candles."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine, text

from app.market_reader.engine_trend.data_source_boundary import (
    CandleDataBoundaryStatus,
    CandleDataRequest,
    run_engine_trend_from_provider,
)
from app.market_reader.engine_trend.json_export import save_engine_trend_json
from app.market_reader.engine_trend.postgres_candle_adapter import (
    PostgresMarketCandlesProvider,
)

DB_ENV_NAMES = (
    "TRADERS_ML_DATABASE_URL",
    "TRADERS_ML_POSTGRES_URL",
    "DATABASE_URL",
    "POSTGRES_URL",
)
DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
AVAILABILITY_SQL = text(
    """
    select symbol, interval, count(*) as candle_count,
           min(open_time) as min_open_time, max(open_time) as max_open_time
    from market_candles
    where symbol in (:symbol_1, :symbol_2, :symbol_3)
      and interval = :interval
    group by symbol, interval
    order by symbol, interval
    """
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS))
    parser.add_argument("--interval", default="15m")
    parser.add_argument("--max-candles", type=int, default=96)
    parser.add_argument(
        "--output-dir", default="reports/engine_trend/manual_smoke"
    )
    return parser.parse_args()


def _db_config() -> tuple[str | None, str | None]:
    for name in DB_ENV_NAMES:
        value = os.getenv(name)
        if value:
            return name, value
    return None, None


def _json_safe(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _artifact_stem(symbol: str, interval: str) -> str:
    return f"engine_trend_11_{symbol.lower()}_{interval.lower()}"


def main() -> int:
    args = _arguments()
    if args.max_candles < 1 or args.max_candles > 96:
        print("max-candles must be between 1 and 96", file=sys.stderr)
        return 2
    if tuple(args.symbols) != DEFAULT_SYMBOLS or args.interval != "15m":
        print("this smoke is restricted to BTCUSDT ETHUSDT SOLUSDT at 15m", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    source_name, database_url = _db_config()
    if not database_url:
        print("smoke_status: SKIPPED_DB_CONFIG_MISSING")
        print("db_source: none")
        return 0

    engine = create_engine(database_url, pool_pre_ping=True)
    connected = False
    try:
        with engine.connect() as connection:
            connected = True
            availability = connection.execute(
                AVAILABILITY_SQL,
                {
                    "symbol_1": DEFAULT_SYMBOLS[0],
                    "symbol_2": DEFAULT_SYMBOLS[1],
                    "symbol_3": DEFAULT_SYMBOLS[2],
                    "interval": args.interval,
                },
            ).mappings().all()
            by_symbol = {str(row["symbol"]): row for row in availability}
            print(f"db_source: {source_name}")
            print("smoke_status: CONNECTED")

            successes = 0
            for symbol in args.symbols:
                available = by_symbol.get(symbol)
                if not available or available["max_open_time"] is None:
                    print(f"{symbol} {args.interval}: no rows")
                    continue
                period_end = available["max_open_time"]
                period_start = period_end - timedelta(
                    minutes=15 * (args.max_candles - 1)
                )
                request = CandleDataRequest(
                    symbol=symbol,
                    interval=args.interval,
                    limit=args.max_candles,
                    start_time=period_start.isoformat(),
                    end_time=period_end.isoformat(),
                    source_name="postgres_market_candles",
                )
                boundary = run_engine_trend_from_provider(
                    PostgresMarketCandlesProvider(connection), request
                )
                facade = boundary.engine_output
                stem = _artifact_stem(symbol, args.interval)
                preview_path = output_dir / f"{stem}_preview.json"
                result_path = output_dir / f"{stem}_result.json"
                save_engine_trend_json(facade.preview, preview_path)
                save_engine_trend_json(facade.json_payload, result_path)

                safety = facade.preview["safety"]
                if not isinstance(safety, dict):
                    raise RuntimeError("engine safety payload is not a mapping")
                valid_safety = (
                    safety.get("trade_signal") == "NOT_EVALUATED"
                    and safety.get("safe_for_runtime_trading") is False
                    and safety.get("live_trading_connected") is False
                )
                if boundary.status is CandleDataBoundaryStatus.READY and valid_safety:
                    successes += 1
                print(f"{symbol} {args.interval}:")
                print(f"  candles_loaded: {len(boundary.batch.candles)}")
                print(f"  period_start: {_json_safe(facade.preview['period_start'])}")
                print(f"  period_end: {_json_safe(facade.preview['period_end'])}")
                print(f"  market_regime: {facade.preview['market_regime']}")
                print(f"  confidence: {facade.preview['confidence']}")
                print(f"  safety.trade_signal: {safety.get('trade_signal')}")
                print(
                    "  safety.safe_for_runtime_trading: "
                    f"{str(safety.get('safe_for_runtime_trading')).lower()}"
                )

            print(f"successful_symbols: {successes}")
            return 0 if successes else 1
    except Exception as exc:
        status = (
            "SMOKE_EXECUTION_FAILED" if connected else "SKIPPED_DB_CONNECTION_FAILED"
        )
        print(f"smoke_status: {status}")
        print(f"db_source: {source_name}")
        print(f"error_type: {type(exc).__name__}")
        return 1 if connected else 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
