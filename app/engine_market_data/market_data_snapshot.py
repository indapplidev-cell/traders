"""Closed-only read model for a future online analysis runner."""

from dataclasses import dataclass

from app.engine_market_data.candle import Candle
from app.engine_market_data.candle_store import CandleStore
from app.engine_market_data.gap_detector import find_missing_open_times
from app.engine_market_data.market_data_health import MarketDataHealth, MarketDataHealthStatus
from app.engine_market_data.market_symbol import normalize_market_symbol


@dataclass(frozen=True, slots=True)
class MarketDataSnapshot:
    symbol: str
    timeframe: str
    closed_until_ms: int
    candles: list[Candle]
    source: str
    has_gaps: bool
    future_bars_used: bool
    health_status: str
    enough_data: bool

    def __post_init__(self) -> None:
        if self.future_bars_used:
            raise ValueError("Market-data snapshots can never use future bars")
        if any(not candle.is_closed for candle in self.candles):
            raise ValueError("Market-data snapshots accept closed candles only")

    @classmethod
    def from_store(
        cls,
        store: CandleStore,
        symbol: str,
        timeframe: str,
        *,
        minimum_candles: int = 1,
        limit: int | None = None,
        health: MarketDataHealth | None = None,
    ) -> "MarketDataSnapshot":
        if minimum_candles < 0:
            raise ValueError("minimum_candles must be non-negative")
        symbol = normalize_market_symbol(symbol)
        candles = store.get_candles(symbol, timeframe, limit=limit)
        has_gaps = bool(find_missing_open_times(candles, timeframe))
        enough_data = len(candles) >= minimum_candles
        active_health = health or store.health
        status = active_health.status
        if (has_gaps or not enough_data) and status == MarketDataHealthStatus.OK:
            status = MarketDataHealthStatus.DEGRADED
        sources = sorted({candle.source for candle in candles})
        source = sources[0] if len(sources) == 1 else ("mixed" if sources else "none")
        return cls(
            symbol=symbol,
            timeframe=timeframe,
            closed_until_ms=candles[-1].close_time_ms if candles else 0,
            candles=candles,
            source=source,
            has_gaps=has_gaps,
            future_bars_used=False,
            health_status=status.value,
            enough_data=enough_data,
        )


def build_market_data_snapshot(
    store: CandleStore, symbol: str, timeframe: str, *, minimum_candles: int = 1,
    limit: int | None = None, health: MarketDataHealth | None = None,
) -> MarketDataSnapshot:
    return MarketDataSnapshot.from_store(
        store, symbol, timeframe, minimum_candles=minimum_candles, limit=limit, health=health
    )


def build_market_data_snapshot_from_db(
    repository: object, symbol: str, timeframe: str, limit: int,
    *, min_required: int | None = None, health: MarketDataHealth | None = None,
) -> MarketDataSnapshot:
    """Build the same causal read model from closed PostgreSQL rows."""
    if limit < 0: raise ValueError("limit must be non-negative")
    minimum = limit if min_required is None else min_required
    candles = repository.get_candles(symbol, timeframe, limit=limit)
    has_gaps = bool(find_missing_open_times(candles, timeframe))
    enough_data = len(candles) >= minimum
    status = (health or MarketDataHealth()).status
    if (has_gaps or not enough_data) and status == MarketDataHealthStatus.OK:
        status = MarketDataHealthStatus.DEGRADED
    sources = sorted({c.source for c in candles})
    return MarketDataSnapshot(symbol=normalize_market_symbol(symbol), timeframe=timeframe,
        closed_until_ms=candles[-1].close_time_ms if candles else 0, candles=candles,
        source=sources[0] if len(sources) == 1 else ("mixed" if sources else "none"),
        has_gaps=has_gaps, future_bars_used=False, health_status=status.value,
        enough_data=enough_data)
