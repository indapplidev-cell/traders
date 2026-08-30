"""Closed-only read model for a future online analysis runner."""

from dataclasses import dataclass, field
from hashlib import sha256
import re

from app.engine_market_data.candle import Candle
from app.engine_market_data.candle_store import CandleStore
from app.engine_market_data.gap_detector import find_missing_open_times
from app.engine_market_data.market_data_health import MarketDataHealth, MarketDataHealthStatus
from app.engine_market_data.market_symbol import normalize_market_symbol
from app.engine_execution.serialization import canonical_json


MARKET_DATA_SNAPSHOT_IDENTITY_VERSION = "market-data-snapshot-v1"
MARKET_DATA_SNAPSHOT_ID_NAMESPACE = "market-data-snapshot:v1"
_SNAPSHOT_ID_RE = re.compile(r"market-data-snapshot:v1:[0-9a-f]{64}\Z")


def is_market_data_snapshot_id(value: object) -> bool:
    return isinstance(value, str) and _SNAPSHOT_ID_RE.fullmatch(value) is not None


def _candle_identity(candle: Candle) -> dict[str, object]:
    return {
        "symbol": candle.symbol,
        "timeframe": candle.timeframe,
        "open_time_ms": candle.open_time_ms,
        "close_time_ms": candle.close_time_ms,
        "open": candle.open,
        "high": candle.high,
        "low": candle.low,
        "close": candle.close,
        "volume": candle.volume,
        "quote_volume": candle.quote_volume,
        "trades_count": candle.trades_count,
        "is_closed": candle.is_closed,
        "source": candle.source,
    }


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
    snapshot_id: str = field(init=False)

    def __post_init__(self) -> None:
        symbol = normalize_market_symbol(self.symbol)
        object.__setattr__(self, "symbol", symbol)
        if self.future_bars_used:
            raise ValueError("Market-data snapshots can never use future bars")
        if any(not candle.is_closed for candle in self.candles):
            raise ValueError("Market-data snapshots accept closed candles only")
        identities = [candle.identity for candle in self.candles]
        if identities != sorted(identities) or len(identities) != len(set(identities)):
            raise ValueError("Market-data snapshot candles must be strictly ordered and unique")
        if any(
            candle.symbol != symbol or candle.timeframe != self.timeframe
            for candle in self.candles
        ):
            raise ValueError("Market-data snapshot candle scope mismatch")
        canonical_identity = canonical_json({
            "identity_version": MARKET_DATA_SNAPSHOT_IDENTITY_VERSION,
            "symbol": symbol,
            "timeframe": self.timeframe,
            "closed_until_ms": int(self.closed_until_ms),
            "source": self.source,
            "candles": [_candle_identity(candle) for candle in self.candles],
        })
        snapshot_id = (
            f"{MARKET_DATA_SNAPSHOT_ID_NAMESPACE}:"
            f"{sha256(canonical_identity.encode('utf-8')).hexdigest()}"
        )
        if not is_market_data_snapshot_id(snapshot_id):
            raise ValueError("Market-data snapshot identity contract failure")
        object.__setattr__(self, "snapshot_id", snapshot_id)

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
