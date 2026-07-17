"""Pure adapter from engine_market_data snapshots to engine_analysis candles."""

from __future__ import annotations

from datetime import datetime, timezone

from app.engine_analysis.online_errors import InvalidMarketDataSnapshotError
from app.engine_analysis.schemas import EngineAnalysisCandle
from app.engine_market_data.candle_stream import ClosedCandleEvent
from app.engine_market_data.market_data_snapshot import MarketDataSnapshot


class MarketDataAdapter:
    """Validate a closed snapshot and convert only the candles it contains."""

    def __init__(self, candle_store: object | None = None) -> None:
        self.candle_store = candle_store

    def adapt(self, snapshot: MarketDataSnapshot) -> tuple[EngineAnalysisCandle, ...]:
        if bool(getattr(snapshot, "future_bars_used", True)):
            raise InvalidMarketDataSnapshotError("snapshot.future_bars_used must be false")
        candles = list(getattr(snapshot, "candles", ()))
        if any(not candle.is_closed for candle in candles):
            raise InvalidMarketDataSnapshotError("snapshot contains an open candle")
        open_times = [candle.open_time_ms for candle in candles]
        if open_times != sorted(open_times):
            raise InvalidMarketDataSnapshotError("candles are not sorted by open_time_ms")
        if len(open_times) != len(set(open_times)):
            raise InvalidMarketDataSnapshotError("candles contain duplicate open_time_ms")
        if candles and candles[-1].close_time_ms > snapshot.closed_until_ms:
            raise InvalidMarketDataSnapshotError("last candle closes after closed_until_ms")
        if any(candle.symbol != snapshot.symbol or candle.timeframe != snapshot.timeframe for candle in candles):
            raise InvalidMarketDataSnapshotError("candle identity differs from snapshot identity")
        return tuple(
            EngineAnalysisCandle(
                timestamp=datetime.fromtimestamp(candle.open_time_ms / 1000, tz=timezone.utc).isoformat(),
                open=float(candle.open),
                high=float(candle.high),
                low=float(candle.low),
                close=float(candle.close),
                volume=float(candle.volume),
            )
            for candle in candles
        )

    convert = adapt

    def snapshot_from_closed_candle_event(
        self, event: ClosedCandleEvent, *, minimum_candles: int
    ) -> MarketDataSnapshot:
        if not event.candle.is_closed:
            raise InvalidMarketDataSnapshotError("event candle is not closed")
        embedded = getattr(event, "snapshot", None)
        if isinstance(embedded, MarketDataSnapshot):
            return embedded
        if self.candle_store is None:
            raise InvalidMarketDataSnapshotError("closed-candle event requires a candle store")
        return MarketDataSnapshot.from_store(
            self.candle_store,
            event.symbol,
            event.timeframe,
            minimum_candles=minimum_candles,
        )
