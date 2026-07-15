import pytest

from app.engine_market_data.candle import Candle
from app.engine_market_data.candle_store import CandleStore
from app.engine_market_data.errors import DuplicateCandleConflict


def make(open_time: int, *, closed: bool = True, close: str = "11", source: str = "rest") -> Candle:
    return Candle("BTCUSDT", "1m", open_time, open_time + 59_999, "10", "12", "9", close, "5", "52", 3, closed, source)


def test_upsert_is_idempotent_sorted_and_symbol_scoped() -> None:
    store = CandleStore()
    store.upsert_candle(make(60_000))
    store.upsert_candle(make(0))
    store.upsert_candle(make(0, source="websocket"))
    assert [item.open_time_ms for item in store.get_candles("BTCUSDT", "1m")] == [0, 60_000]
    assert store.count("ETHUSDT", "1m") == 0


def test_closed_candle_cannot_be_overwritten_by_unclosed() -> None:
    store = CandleStore()
    closed = make(0)
    store.upsert_candle(closed)
    store.upsert_candle(make(0, closed=False, close="10"))
    assert store.get_latest_closed_candle("BTCUSDT", "1m") == closed


def test_conflicting_closed_duplicate_is_rejected() -> None:
    store = CandleStore()
    store.upsert_candle(make(0))
    with pytest.raises(DuplicateCandleConflict):
        store.upsert_candle(make(0, close="10"))
    assert store.health.status == "DEGRADED"
