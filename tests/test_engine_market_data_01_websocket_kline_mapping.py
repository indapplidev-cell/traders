import asyncio

from app.engine_market_data.binance_kline_ws import BinanceKlineWebSocketClient, ReconnectPolicy
from app.engine_market_data.candle_store import CandleStore
from app.engine_market_data.candle_stream import CandleStream


def event(closed: bool) -> dict:
    return {"e": "kline", "s": "BTCUSDT", "k": {
        "t": 0, "T": 59_999, "s": "BTCUSDT", "i": "1m",
        "o": "10", "h": "12", "l": "9", "c": "11", "v": "5",
        "q": "52", "n": 3, "x": closed,
    }}


def test_websocket_exchange_flag_is_the_only_closed_signal() -> None:
    assert BinanceKlineWebSocketClient.map_kline_event(event(False)).is_closed is False
    closed = BinanceKlineWebSocketClient.map_kline_event(event(True), 123)
    assert closed.is_closed is True
    assert closed.source == "websocket"
    assert closed.received_at_ms == 123


def test_unclosed_update_is_not_published_or_analysis_ready() -> None:
    store = CandleStore()
    stream = CandleStream(object(), store)
    candle = BinanceKlineWebSocketClient.map_kline_event(event(False))
    assert stream.process_candle(candle) is None
    assert store.get_candles("BTCUSDT", "1m") == []
    assert store.get_raw_candle("BTCUSDT", "1m", 0) == candle


def test_closed_update_is_stored_and_published() -> None:
    store = CandleStore()
    stream = CandleStream(object(), store)
    candle = BinanceKlineWebSocketClient.map_kline_event(event(True))
    published = stream.process_candle(candle)
    assert published is not None and published.candle == candle
    assert store.count("BTCUSDT", "1m") == 1


def test_disconnect_sets_health_and_stops_after_reconnect_policy() -> None:
    class EmptySocket:
        def __aiter__(self): return self
        async def __anext__(self): raise StopAsyncIteration

    client = BinanceKlineWebSocketClient(
        websocket_factory=lambda _: EmptySocket(),
        reconnect_policy=ReconnectPolicy(maximum_attempts=0),
    )

    async def consume() -> None:
        try:
            async for _ in client.listen_klines(["BTCUSDT"], ["1m"]):
                pass
        except Exception:
            pass

    asyncio.run(consume())
    assert client.health.status == "DISCONNECTED"
