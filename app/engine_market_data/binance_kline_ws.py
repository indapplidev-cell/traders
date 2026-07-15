"""Binance public combined kline stream mapping and reconnect loop."""

import asyncio
import inspect
import json
import time
from collections.abc import AsyncIterator, Callable, Iterable
from dataclasses import dataclass
from typing import Any

from app.engine_market_data.candle import Candle
from app.engine_market_data.errors import WebSocketDisconnectedError
from app.engine_market_data.market_data_health import MarketDataHealth
from app.engine_market_data.market_symbol import normalize_market_symbol
from app.engine_market_data.timeframe import timeframe_to_milliseconds


@dataclass(frozen=True, slots=True)
class ReconnectPolicy:
    initial_delay_seconds: float = 0.25
    maximum_delay_seconds: float = 10.0
    maximum_attempts: int | None = None


class BinanceKlineWebSocketClient:
    BASE_URL = "wss://stream.binance.com:9443/stream?streams="

    def __init__(
        self,
        websocket_factory: Callable[[str], Any] | None = None,
        *,
        health: MarketDataHealth | None = None,
        reconnect_policy: ReconnectPolicy | None = None,
        sleep: Callable[[float], Any] = asyncio.sleep,
        clock_ms: Callable[[], int] = lambda: int(time.time() * 1000),
    ) -> None:
        self._factory = websocket_factory
        self.health = health or MarketDataHealth()
        self.reconnect_policy = reconnect_policy or ReconnectPolicy()
        self._sleep = sleep
        self._clock_ms = clock_ms

    @staticmethod
    def map_kline_event(payload: dict[str, Any], received_at_ms: int | None = None) -> Candle:
        event = payload.get("data", payload)
        if not isinstance(event, dict) or not isinstance(event.get("k"), dict):
            raise ValueError("Not a Binance kline event")
        kline = event["k"]
        symbol = kline.get("s") or event.get("s")
        timeframe = kline.get("i")
        required = ("t", "T", "o", "h", "l", "c", "v", "x")
        if symbol is None or timeframe is None or any(key not in kline for key in required):
            raise ValueError("Incomplete Binance kline event")
        return Candle(
            symbol=symbol, timeframe=timeframe,
            open_time_ms=int(kline["t"]), close_time_ms=int(kline["T"]),
            open=kline["o"], high=kline["h"], low=kline["l"], close=kline["c"],
            volume=kline["v"], quote_volume=kline.get("q"),
            trades_count=int(kline["n"]) if kline.get("n") is not None else None,
            is_closed=kline["x"] is True,
            source="websocket", received_at_ms=received_at_ms,
        )

    async def listen_klines(self, symbols: Iterable[str], timeframes: Iterable[str]) -> AsyncIterator[Candle]:
        if self._factory is None:
            raise RuntimeError("A websocket_factory is required; install/inject a websocket adapter")
        normalized_symbols = sorted({normalize_market_symbol(symbol).lower() for symbol in symbols})
        normalized_timeframes = sorted(set(timeframes))
        for timeframe in normalized_timeframes:
            timeframe_to_milliseconds(timeframe)
        if not normalized_symbols or not normalized_timeframes:
            raise ValueError("At least one symbol and timeframe are required")
        streams = "/".join(f"{symbol}@kline_{tf}" for symbol in normalized_symbols for tf in normalized_timeframes)
        url = f"{self.BASE_URL}{streams}"
        attempts = 0
        while True:
            try:
                connection = self._factory(url)
                if inspect.isawaitable(connection):
                    connection = await connection
                self.health.ok()
                async for raw in self._iterate_connection(connection):
                    payload = json.loads(raw) if isinstance(raw, (str, bytes, bytearray)) else raw
                    yield self.map_kline_event(payload, self._clock_ms())
                raise WebSocketDisconnectedError("Public websocket stream ended")
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.health.disconnected()
                attempts += 1
                maximum = self.reconnect_policy.maximum_attempts
                if maximum is not None and attempts > maximum:
                    raise WebSocketDisconnectedError("Reconnect attempts exhausted") from exc
                delay = min(
                    self.reconnect_policy.initial_delay_seconds * (2 ** (attempts - 1)),
                    self.reconnect_policy.maximum_delay_seconds,
                )
                result = self._sleep(delay)
                if inspect.isawaitable(result):
                    await result

    @staticmethod
    async def _iterate_connection(connection: Any) -> AsyncIterator[Any]:
        if hasattr(connection, "__aenter__"):
            async with connection as websocket:
                async for message in BinanceKlineWebSocketClient._iterate_connection(websocket):
                    yield message
            return
        if hasattr(connection, "__aiter__"):
            async for message in connection:
                yield message
            return
        while True:
            yield await connection.recv()


BinanceKlineWsClient = BinanceKlineWebSocketClient
parse_binance_kline_event = BinanceKlineWebSocketClient.map_kline_event
