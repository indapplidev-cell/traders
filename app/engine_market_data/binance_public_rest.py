"""Binance Spot public REST client; no credentials or private endpoints."""

import time
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

import httpx

from app.engine_market_data.candle import Candle
from app.engine_market_data.errors import PublicMarketDataError
from app.engine_market_data.market_symbol import normalize_market_symbol
from app.engine_market_data.timeframe import timeframe_to_milliseconds


class HttpTransport(Protocol):
    def get(self, url: str, *, params: dict[str, Any] | None = None) -> Any: ...


@dataclass(frozen=True, slots=True)
class PublicBookTicker:
    symbol: str
    bid_price: Decimal
    bid_quantity: Decimal
    ask_price: Decimal
    ask_quantity: Decimal

    @property
    def spread_bps(self) -> float:
        midpoint = (self.bid_price + self.ask_price) / Decimal("2")
        return float((self.ask_price - self.bid_price) / midpoint * Decimal("10000"))


@dataclass(frozen=True, slots=True)
class PublicDepthEstimate:
    symbol: str
    reference_quantity: Decimal
    buy_vwap: Decimal
    sell_vwap: Decimal
    entry_impact_bps: float
    exit_impact_bps: float
    depth_impact_bps: float
    source: str = "BINANCE_PUBLIC_MARKET_DATA_DEPTH"


class BinancePublicRestClient:
    # Binance's public market-data-only origin remains usable from production
    # locations where the trading API origin rejects even unauthenticated
    # market-data requests.  This client never calls private/order endpoints.
    BASE_URL = "https://data-api.binance.vision"
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

    def fetch_book_ticker(self, symbol: str) -> PublicBookTicker:
        symbol = normalize_market_symbol(symbol)
        payload = self._request_json("/api/v3/ticker/bookTicker", {"symbol": symbol})
        if not isinstance(payload, dict):
            raise PublicMarketDataError("Unexpected Binance book ticker response")
        try:
            ticker = PublicBookTicker(
                symbol=symbol,
                bid_price=Decimal(str(payload["bidPrice"])),
                bid_quantity=Decimal(str(payload["bidQty"])),
                ask_price=Decimal(str(payload["askPrice"])),
                ask_quantity=Decimal(str(payload["askQty"])),
            )
        except (KeyError, ValueError, ArithmeticError) as exc:
            raise PublicMarketDataError("Invalid Binance book ticker response") from exc
        if ticker.bid_price <= 0 or ticker.ask_price <= ticker.bid_price:
            raise PublicMarketDataError("Invalid Binance bid/ask geometry")
        return ticker

    def estimate_round_trip_depth_impact(
        self, symbol: str, reference_quantity: Decimal | str, *, limit: int = 100
    ) -> PublicDepthEstimate:
        """Bounded diagnostic VWAP; it grants no execution quantity authority."""
        symbol = normalize_market_symbol(symbol)
        quantity = Decimal(str(reference_quantity))
        if quantity <= 0 or limit not in {5, 10, 20, 50, 100, 500, 1000, 5000}:
            raise ValueError("positive reference quantity and a Binance depth limit are required")
        payload = self._request_json("/api/v3/depth", {"symbol": symbol, "limit": limit})
        if not isinstance(payload, dict):
            raise PublicMarketDataError("Unexpected Binance depth response")
        asks = self._depth_levels(payload.get("asks"))
        bids = self._depth_levels(payload.get("bids"))
        buy_vwap = self._vwap(asks, quantity)
        sell_vwap = self._vwap(bids, quantity)
        best_ask, best_bid = asks[0][0], bids[0][0]
        entry_impact = float((buy_vwap - best_ask) / best_ask * Decimal("10000"))
        exit_impact = float((best_bid - sell_vwap) / best_bid * Decimal("10000"))
        return PublicDepthEstimate(
            symbol=symbol, reference_quantity=quantity, buy_vwap=buy_vwap,
            sell_vwap=sell_vwap, entry_impact_bps=entry_impact,
            exit_impact_bps=exit_impact, depth_impact_bps=entry_impact + exit_impact,
        )

    @staticmethod
    def _depth_levels(payload: Any) -> list[tuple[Decimal, Decimal]]:
        if not isinstance(payload, list) or not payload:
            raise PublicMarketDataError("Missing Binance depth levels")
        try:
            levels = [(Decimal(str(row[0])), Decimal(str(row[1]))) for row in payload]
        except (IndexError, TypeError, ValueError, ArithmeticError) as exc:
            raise PublicMarketDataError("Invalid Binance depth level") from exc
        if any(price <= 0 or quantity <= 0 for price, quantity in levels):
            raise PublicMarketDataError("Non-positive Binance depth level")
        return levels

    @staticmethod
    def _vwap(levels: list[tuple[Decimal, Decimal]], quantity: Decimal) -> Decimal:
        remaining, notional = quantity, Decimal("0")
        for price, available in levels:
            taken = min(remaining, available)
            notional += taken * price
            remaining -= taken
            if remaining == 0:
                return notional / quantity
        raise PublicMarketDataError("Insufficient bounded depth for reference quantity")

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
