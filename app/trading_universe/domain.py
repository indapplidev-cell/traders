"""Immutable, versioned trading-universe definitions.

Market-data preparation and trading activation are deliberately separate.
Canaries persist ``allowed_symbols`` as their lifetime snapshot; this module
binds that snapshot to an immutable version at creation time.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.engine_market_data.market_symbol import normalize_market_symbol


TARGET_TIMEFRAMES = ("1m", "5m", "15m", "1h", "4h", "1d")


class TradingUniverseActivationState(StrEnum):
    ACTIVE = "ACTIVE"
    PREPARED_NOT_ACTIVE = "PREPARED_NOT_ACTIVE"


@dataclass(frozen=True, slots=True)
class TradingUniverseVersion:
    version_id: str
    symbols: tuple[str, ...]
    activation_state: TradingUniverseActivationState

    def __post_init__(self) -> None:
        normalized = tuple(normalize_market_symbol(value) for value in self.symbols)
        if not self.version_id or normalized != self.symbols:
            raise ValueError("trading universe must have a stable id and normalized symbols")
        if not normalized or len(normalized) > 10 or len(set(normalized)) != len(normalized):
            raise ValueError("trading universe must contain 1..10 unique symbols")


ACTIVE_TRADING_UNIVERSE = TradingUniverseVersion(
    version_id="trading-universe-v1",
    symbols=("BTCUSDT", "ETHUSDT", "SOLUSDT"),
    activation_state=TradingUniverseActivationState.ACTIVE,
)

PREPARED_NEXT_TRADING_UNIVERSE = TradingUniverseVersion(
    version_id="trading-universe-v2",
    symbols=(
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
        "LINKUSDT", "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "SUIUSDT",
    ),
    activation_state=TradingUniverseActivationState.PREPARED_NOT_ACTIVE,
)

_VERSIONS = {
    ACTIVE_TRADING_UNIVERSE.version_id: ACTIVE_TRADING_UNIVERSE,
    PREPARED_NEXT_TRADING_UNIVERSE.version_id: PREPARED_NEXT_TRADING_UNIVERSE,
}


def resolve_universe(version_id: str) -> TradingUniverseVersion:
    try:
        return _VERSIONS[version_id]
    except KeyError as exc:
        raise ValueError("unknown trading universe version") from exc


def market_data_streams(
    universe: TradingUniverseVersion = PREPARED_NEXT_TRADING_UNIVERSE,
) -> tuple[tuple[str, str], ...]:
    """Return the deterministic symbol-major collection plan."""

    return tuple((symbol, timeframe) for symbol in universe.symbols for timeframe in TARGET_TIMEFRAMES)


@dataclass(frozen=True, slots=True)
class CanaryUniverseBinding:
    universe_version_id: str
    allowed_symbols: tuple[str, ...]


def bind_new_canary(
    universe_version_id: str,
    allowed_symbols: tuple[str, ...],
    *,
    active_version_id: str = ACTIVE_TRADING_UNIVERSE.version_id,
) -> CanaryUniverseBinding:
    """Freeze a new canary to an explicitly active universe version.

    Prepared versions fail closed until a separate activation change.  The
    returned symbols are persisted in ``paper_first_canary_sessions`` and are
    never looked up dynamically during the canary lifetime.
    """

    universe = resolve_universe(universe_version_id)
    if universe.version_id != active_version_id:
        raise ValueError("trading universe version is not active")
    normalized = tuple(normalize_market_symbol(value) for value in allowed_symbols)
    if not normalized or len(set(normalized)) != len(normalized):
        raise ValueError("canary symbols must be unique and non-empty")
    if any(symbol not in universe.symbols for symbol in normalized):
        raise ValueError("canary symbol is outside the bound universe version")
    return CanaryUniverseBinding(universe.version_id, normalized)


def runtime_universe(version_id: str) -> TradingUniverseVersion:
    """Resolve a persisted active version with runtime ACTIVE semantics."""

    universe = resolve_universe(version_id)
    return TradingUniverseVersion(
        version_id=universe.version_id,
        symbols=universe.symbols,
        activation_state=TradingUniverseActivationState.ACTIVE,
    )
