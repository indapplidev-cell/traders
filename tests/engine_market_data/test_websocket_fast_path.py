from types import SimpleNamespace

import pytest

from app.engine_market_data.continuous_sync_state import ContinuousSyncStatus
from app.engine_market_data.websocket_sync import WebSocketClosedCandleSync


class Candles:
    def __init__(self):
        self.values = []

    def upsert_candle(self, candle):
        self.values.append(candle)


class States:
    def __init__(self):
        self.values = []

    def upsert(self, state):
        self.values.append(state)


def candle(*, closed=True, received=60_250):
    return SimpleNamespace(
        symbol="BTCUSDT", timeframe="1m", open_time_ms=0,
        close_time_ms=59_999, received_at_ms=received, is_closed=closed,
    )


def test_closed_websocket_candle_commits_state_then_emits_event():
    candles, states, events = Candles(), States(), []
    service = WebSocketClosedCandleSync(
        object(), candles, states, notifier=events.append,
        daemon_instance_id="ws-test",
    )

    service._persist(candle())

    assert len(candles.values) == len(states.values) == len(events) == 1
    assert states.values[0].status is ContinuousSyncStatus.OK
    assert states.values[0].source == "binance_public_websocket"
    assert events[0]["closed_until_ms"] == 60_000
    assert events[0]["exchange_to_receive_ms"] == 250


def test_open_or_pre_boundary_event_cannot_advance_freshness():
    candles, states = Candles(), States()
    service = WebSocketClosedCandleSync(object(), candles, states)

    service._persist(candle(closed=False))
    with pytest.raises(ValueError, match="before its exchange boundary"):
        service._persist(candle(received=59_999))

    assert candles.values == []
    assert states.values == []
