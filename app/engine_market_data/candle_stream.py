"""Orchestration of raw websocket updates into closed-candle events."""

from dataclasses import dataclass
from typing import AsyncIterator, Iterable

from app.engine_market_data.candle import Candle
from app.engine_market_data.candle_store import CandleStore
from app.engine_market_data.gap_detector import detect_gap
from app.engine_market_data.gap_recovery import GapRecovery
from app.engine_market_data.market_data_health import MarketDataHealth


@dataclass(frozen=True, slots=True)
class ClosedCandleEvent:
    symbol: str
    timeframe: str
    candle: Candle
    gap_detected: bool
    recovered_count: int
    store_count: int


class CandleStream:
    def __init__(
        self,
        websocket_client: object,
        store: CandleStore,
        gap_recovery: GapRecovery | None = None,
        health: MarketDataHealth | None = None,
    ) -> None:
        self.websocket_client = websocket_client
        self.store = store
        self.gap_recovery = gap_recovery
        self.health = health or store.health

    def process_candle(self, candle: Candle) -> ClosedCandleEvent | None:
        if not candle.is_closed:
            self.store.upsert_candle(candle)
            return None
        previous = self.store.get_latest_closed_candle(candle.symbol, candle.timeframe)
        gap = detect_gap(previous, candle) if previous is not None else None
        recovered_count = 0
        if gap is not None:
            self.health.degraded("missing candles")
            if self.gap_recovery is not None:
                report = self.gap_recovery.recover(candle.symbol, candle.timeframe, gap.missing_open_times)
                recovered_count = report.recovered_count
        self.store.upsert_candle(candle)
        return ClosedCandleEvent(
            symbol=candle.symbol,
            timeframe=candle.timeframe,
            candle=candle,
            gap_detected=gap is not None,
            recovered_count=recovered_count,
            store_count=self.store.count(candle.symbol, candle.timeframe),
        )

    async def listen(self, symbols: Iterable[str], timeframes: Iterable[str]) -> AsyncIterator[ClosedCandleEvent]:
        try:
            async for candle in self.websocket_client.listen_klines(symbols, timeframes):
                event = self.process_candle(candle)
                if event is not None:
                    yield event
        except Exception:
            self.health.disconnected()
            raise

    stream_closed_candles = listen
