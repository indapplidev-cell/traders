from datetime import datetime, timezone
from typing import Any

from app.data.binance_client import BinanceClient
from app.db.repositories.candle_repository import CandleRepository


class HistoricalLoader:
    def __init__(self, client: BinanceClient, repository: CandleRepository) -> None:
        self._client = client
        self._repository = repository

    def load_range(
        self,
        symbol: str,
        interval: str,
        start_at: datetime,
        end_at: datetime,
    ) -> dict[str, Any]:
        normalized_start = self._normalize_datetime(start_at)
        normalized_end = self._normalize_datetime(end_at)
        candles = self._client.load_klines(symbol, interval, normalized_start, normalized_end)
        inserted_or_updated = self._repository.upsert_many(candles)

        first_open_time = candles[0]["open_time"].isoformat() if candles else None
        last_open_time = candles[-1]["open_time"].isoformat() if candles else None

        return {
            "symbol": symbol,
            "interval": interval,
            "start_at": normalized_start.isoformat(),
            "end_at": normalized_end.isoformat(),
            "loaded": len(candles),
            "inserted_or_updated": inserted_or_updated,
            "first_open_time": first_open_time,
            "last_open_time": last_open_time,
        }

    @staticmethod
    def _normalize_datetime(value: datetime) -> datetime:
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
