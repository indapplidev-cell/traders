"""Read-only PostgreSQL adapter for ``market_candles``."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.market_reader.engine_trend.data_source_boundary import CandleDataRequest


class PostgresCandleAdapterError(RuntimeError):
    """Raised when ``market_candles`` cannot be read."""


class PostgresMarketCandlesProvider:
    """Load engine-neutral candle rows through an injected DB connection."""

    def __init__(self, connection: Any) -> None:
        if connection is None:
            raise TypeError("connection is required")
        self._connection = connection

    def load_rows(self, request: CandleDataRequest) -> list[dict[str, object]]:
        conditions = ["symbol = :symbol", "interval = :interval"]
        parameters: dict[str, object] = {
            "symbol": request.symbol,
            "interval": request.interval,
            "limit": request.limit,
        }
        if request.start_time is not None:
            conditions.append("open_time >= :period_start")
            parameters["period_start"] = request.start_time
        if request.end_time is not None:
            conditions.append("open_time <= :period_end")
            parameters["period_end"] = request.end_time

        statement = text(
            "SELECT open_time, open, high, low, close, volume, symbol, interval "
            "FROM market_candles WHERE "
            + " AND ".join(conditions)
            + " ORDER BY open_time ASC LIMIT :limit"
        )
        try:
            result = self._connection.execute(statement, parameters)
            records = result.mappings().all()
        except Exception as exc:
            raise PostgresCandleAdapterError(
                "failed to read candles from market_candles"
            ) from exc

        return [
            {
                "timestamp": row["open_time"],
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "volume": row["volume"],
                "symbol": row["symbol"],
                "interval": row["interval"],
            }
            for row in records
        ]
