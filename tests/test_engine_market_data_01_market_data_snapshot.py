from app.engine_market_data.candle import Candle
from app.engine_market_data.candle_store import CandleStore
from app.engine_market_data.market_data_snapshot import MarketDataSnapshot


def make(open_time: int, closed: bool = True) -> Candle:
    return Candle("BTCUSDT", "1m", open_time, open_time + 59_999, 10, 12, 9, 11, 5, None, None, closed, "websocket")


def test_snapshot_is_closed_only_causal_and_enough_data_aware() -> None:
    store = CandleStore()
    store.upsert_candle(make(0))
    store.upsert_candle(make(60_000, False))
    snapshot = MarketDataSnapshot.from_store(store, "BTCUSDT", "1m", minimum_candles=2)
    assert [c.open_time_ms for c in snapshot.candles] == [0]
    assert snapshot.closed_until_ms == 59_999
    assert snapshot.future_bars_used is False
    assert snapshot.enough_data is False
    assert snapshot.health_status == "DEGRADED"


def test_snapshot_reports_internal_gap() -> None:
    store = CandleStore()
    store.upsert_candle(make(0))
    store.upsert_candle(make(120_000))
    snapshot = MarketDataSnapshot.from_store(store, "BTCUSDT", "1m")
    assert snapshot.has_gaps is True
    assert snapshot.health_status == "DEGRADED"


def test_snapshot_identity_is_versioned_deterministic_and_causal() -> None:
    first = MarketDataSnapshot(
        "BTCUSDT", "1m", 120_000, [make(0), make(60_000)], "websocket",
        False, False, "OK", True,
    )
    same = MarketDataSnapshot(
        "btcusdt", "1m", 120_000,
        [replace(make(0), received_at_ms=10), replace(make(60_000), received_at_ms=20)],
        "websocket", False, False, "DEGRADED", False,
    )
    changed = replace(
        first,
        candles=[make(0), replace(make(60_000), close=Decimal("11.5"))],
    )
    assert first.snapshot_id.startswith("market-data-snapshot:v1:")
    assert len(first.snapshot_id.rsplit(":", 1)[1]) == 64
    assert first.snapshot_id == same.snapshot_id
    assert first.snapshot_id != changed.snapshot_id


def test_snapshot_identity_rejects_noncanonical_candle_order_and_duplicates() -> None:
    with pytest.raises(ValueError, match="strictly ordered and unique"):
        MarketDataSnapshot(
            "BTCUSDT", "1m", 120_000, [make(60_000), make(0)], "websocket",
            False, False, "OK", True,
        )
    with pytest.raises(ValueError, match="strictly ordered and unique"):
        MarketDataSnapshot(
            "BTCUSDT", "1m", 120_000, [make(0), make(0)], "websocket",
            False, False, "OK", True,
        )
from dataclasses import replace
from decimal import Decimal

import pytest
