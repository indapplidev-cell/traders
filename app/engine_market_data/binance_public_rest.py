"""Binance Spot public REST client; no credentials or private endpoints."""

import time
from collections.abc import Callable
from typing import Any, Protocol

import httpx

from app.engine_market_data.candle import Candle
from app.engine_market_data.errors import PublicMarketDataError
from app.engine_market_data.market_symbol import normalize_market_symbol
from app.engine_market_data.timeframe import timeframe_to_milliseconds


class HttpTransport(Protocol):
    def get(self, url: str, *, params: dict[str, Any] | None = None) -> Any: ...


class BinancePublicRestClient:
    BASE_URL = "https://api.binance.com"
    MAX_LIMIT = 1000
    RETRYABLE_STATUS_CODES = frozenset({418, 429, 500, 502, 503, 504})

    def __init__(
        self,
        transport: HttpTransport | None = None,
        *,
        base_url: str = BASE_URL,
        max_retries: int = 3,
        backoff_seconds: float = 0.25,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._transport = transport or httpx.Client(timeout=15.0)
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._backoff_seconds = backoff_seconds
        self._sleep = sleep

    def fetch_klines(
        self,
        symbol: str,
        timeframe: str,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
        limit: int = MAX_LIMIT,
    ) -> list[Candle]:
        symbol = normalize_market_symbol(symbol)
        timeframe_to_milliseconds(timeframe)
        if not 1 <= limit <= self.MAX_LIMIT:
            raise ValueError("limit must be between 1 and 1000")
        if start_time_ms is not None and end_time_ms is not None and start_time_ms > end_time_ms:
            return []
        params: dict[str, Any] = {"symbol": symbol, "interval": timeframe, "limit": limit}
        if start_time_ms is not None:
            params["startTime"] = start_time_ms
        if end_time_ms is not None:
            params["endTime"] = end_time_ms
        payload = self._request_json("/api/v3/klines", params)
        if not isinstance(payload, list):
            raise PublicMarketDataError("Unexpected Binance klines response")
        return [self.map_kline(symbol, timeframe, row) for row in payload]

    def fetch_server_time_ms(self) -> int:
        payload = self._request_json("/api/v3/time", None)
        if not isinstance(payload, dict) or not isinstance(payload.get("serverTime"), int):
            raise PublicMarketDataError("Unexpected Binance time response")
        return payload["serverTime"]

    @staticmethod
    def map_kline(symbol: str, timeframe: str, payload: list[Any]) -> Candle:
        if len(payload) < 9:
            raise PublicMarketDataError("Incomplete Binance kline payload")
        return Candle(
            symbol=symbol,
            timeframe=timeframe,
            open_time_ms=int(payload[0]),
            close_time_ms=int(payload[6]),
            open=payload[1], high=payload[2], low=payload[3], close=payload[4],
            volume=payload[5], quote_volume=payload[7], trades_count=int(payload[8]),
            is_closed=True,
            source="rest",
        )

    def _request_json(self, path: str, params: dict[str, Any] | None) -> Any:
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = self._transport.get(f"{self._base_url}{path}", params=params)
                status = int(getattr(response, "status_code", 200))
                if status in self.RETRYABLE_STATUS_CODES:
                    raise PublicMarketDataError(f"Temporary Binance HTTP status {status}")
                if hasattr(response, "raise_for_status"):
                    response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, PublicMarketDataError, OSError) as exc:
                last_error = exc
                if attempt >= self._max_retries:
                    break
                self._sleep(self._backoff_seconds * (2**attempt))
        raise PublicMarketDataError("Binance public REST request failed") from last_error


BinancePublicRESTClient = BinancePublicRestClient
