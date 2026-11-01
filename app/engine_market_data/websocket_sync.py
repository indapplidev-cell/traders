"""Low-latency closed-kline persistence; REST remains recovery authority."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Callable, Iterable
from uuid import uuid4

from app.engine_market_data.binance_kline_ws import BinanceKlineWebSocketClient
from app.engine_market_data.continuous_sync_state import (
    ContinuousSyncStatus,
    SyncStateUpdate,
)


LOGGER = logging.getLogger(__name__)


class WebSocketClosedCandleSync:
    """Persist only Binance-final candles and advance the shared freshness state."""

    def __init__(
        self,
        client: BinanceKlineWebSocketClient,
        candle_repository: object,
        state_repository: object,
        *,
        notifier: Callable[[dict[str, object]], None] | None = None,
        daemon_instance_id: str | None = None,
    ) -> None:
        self.client = client
        self.candles = candle_repository
        self.states = state_repository
        self.notifier = notifier
        self.daemon_instance_id = daemon_instance_id or f"market-data-ws-{uuid4().hex[:12]}"

    def _persist(self, candle: object) -> None:
        if not bool(getattr(candle, "is_closed", False)):
            return
        received_at_ms = int(getattr(candle, "received_at_ms"))
        close_boundary_ms = int(getattr(candle, "close_time_ms")) + 1
        if received_at_ms < close_boundary_ms:
            raise ValueError("closed candle arrived before its exchange boundary")
        self.candles.upsert_candle(candle)
        observed_at = datetime.fromtimestamp(received_at_ms / 1000, tz=timezone.utc)
        self.states.upsert(SyncStateUpdate(
            symbol=str(getattr(candle, "symbol")),
            timeframe=str(getattr(candle, "timeframe")),
            daemon_instance_id=self.daemon_instance_id,
            status=ContinuousSyncStatus.OK,
            last_expected_open_time_ms=int(getattr(candle, "open_time_ms")),
            last_expected_close_boundary_ms=close_boundary_ms,
            last_stored_open_time_ms=int(getattr(candle, "open_time_ms")),
            last_stored_close_boundary_ms=close_boundary_ms,
            last_attempt_at=observed_at,
            last_success_at=observed_at,
            last_inserted_count=1,
            source="binance_public_websocket",
        ))
        event = {
            "event": "CLOSED_CANDLE_COMMITTED",
            "symbol": str(getattr(candle, "symbol")),
            "timeframe": str(getattr(candle, "timeframe")),
            "closed_until_ms": close_boundary_ms,
            "received_at_ms": received_at_ms,
            "exchange_to_receive_ms": received_at_ms - close_boundary_ms,
            "source": "binance_public_websocket",
        }
        if self.notifier is not None:
            self.notifier(event)
        LOGGER.info(json.dumps(event, sort_keys=True))

    async def run(self, symbols: Iterable[str], timeframes: Iterable[str]) -> None:
        async for candle in self.client.listen_klines(symbols, timeframes):
            if candle.is_closed:
                await asyncio.to_thread(self._persist, candle)


__all__ = ["WebSocketClosedCandleSync"]
