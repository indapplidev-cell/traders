from datetime import datetime, timezone
from typing import Any

import httpx

from app.data.candle_normalizer import CandleNormalizer


class BinanceClient:
    BASE_URL = "https://data-api.binance.vision/api/v3/klines"
    PAGE_LIMIT = 1000

    def __init__(
        self,
        http_client: httpx.Client | None = None,
        normalizer: CandleNormalizer | None = None,
        base_url: str | None = None,
    ) -> None:
        self._http_client = http_client or httpx.Client(timeout=30.0)
        self._normalizer = normalizer or CandleNormalizer()
        self._base_url = base_url or self.BASE_URL

    def load_klines(
        self,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        start_ms = self._to_milliseconds(start_time)
        end_ms = self._to_milliseconds(end_time)
        if start_ms >= end_ms:
            return []

        normalized: list[dict[str, Any]] = []
        cursor_ms = start_ms
        last_allowed_ms = end_ms - 1

        while cursor_ms <= last_allowed_ms:
            page = self._fetch_page(
                symbol=symbol,
                interval=interval,
                start_time_ms=cursor_ms,
                end_time_ms=last_allowed_ms,
            )
            if not page:
                break

            normalized.extend(self._normalizer.normalize_many(symbol, interval, page))
            cursor_ms = int(page[-1][0]) + 1

            if len(page) < self.PAGE_LIMIT:
                break

        return normalized

    def _fetch_page(
        self,
        symbol: str,
        interval: str,
        start_time_ms: int,
        end_time_ms: int,
    ) -> list[list[Any]]:
        response = self._http_client.get(
            self._base_url,
            params={
                "symbol": symbol,
                "interval": interval,
                "startTime": start_time_ms,
                "endTime": end_time_ms,
                "limit": self.PAGE_LIMIT,
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("Unexpected Binance response payload.")
        return payload

    @staticmethod
    def _to_milliseconds(value: datetime) -> int:
        normalized = value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return int(normalized.timestamp() * 1000)
