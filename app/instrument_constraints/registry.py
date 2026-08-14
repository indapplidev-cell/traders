"""Immutable Binance Spot quantity constraints for trading-universe-v2.

The committed v1 values are an offline projection of one bounded public
``GET /api/v3/exchangeInfo`` observation.  Runtime code never performs a
metadata request.  Refreshes must introduce a new registry version rather
than changing the meaning of this one.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Final, Mapping

from app.trading_universe.domain import PREPARED_NEXT_TRADING_UNIVERSE


REGISTRY_VERSION: Final = "trading-universe-v2-binance-spot-quantity-constraints-v1"
UNIVERSE_ID: Final = "trading-universe-v2"
MARKET_TYPE: Final = "BINANCE_SPOT"
SOURCE_ENDPOINT_KIND: Final = "GET /api/v3/exchangeInfo?symbols=<exact-universe>"
SOURCE_OBSERVED_AT_UTC: Final = "2026-08-14T21:32:26.053Z"
SOURCE_SNAPSHOT_SHA256: Final = "9137b071376d8376970aea0e233eea06c3239644f5412bcc05cbfd6eab3207b4"


class InstrumentConstraintRegistryError(ValueError):
    """Raised when registry/source data cannot be proven safe."""


def _decimal(value: object, field: str, *, positive: bool = False) -> Decimal:
    if not isinstance(value, str):
        raise InstrumentConstraintRegistryError(f"{field} must be an exact decimal string")
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise InstrumentConstraintRegistryError(f"{field} is not a Decimal") from exc
    if not parsed.is_finite() or (positive and parsed <= 0) or (not positive and parsed < 0):
        raise InstrumentConstraintRegistryError(f"{field} has an invalid value")
    return parsed


@dataclass(frozen=True, slots=True)
class SourceQuantityFilters:
    lot_min_qty: Decimal
    lot_max_qty: Decimal
    lot_step_size: Decimal
    market_min_qty: Decimal
    market_max_qty: Decimal
    market_step_size: Decimal
    notional_filter_name: str
    min_notional: Decimal
    max_notional: Decimal | None
    min_notional_applies_to_market: bool
    max_notional_applies_to_market: bool


@dataclass(frozen=True, slots=True)
class InstrumentQuantityConstraint:
    symbol: str
    market_type: str
    trading_status: str
    base_asset: str
    quote_asset: str
    quantity_step: Decimal
    min_quantity: Decimal
    max_quantity: Decimal
    market_quantity_step: Decimal | None
    market_min_quantity: Decimal | None
    market_max_quantity: Decimal | None
    min_notional: Decimal | None
    max_notional: Decimal | None
    min_notional_applies_to_relevant_order_type: bool
    max_notional_applies_to_relevant_order_type: bool
    source_filter_names: tuple[str, ...]
    source_filters: SourceQuantityFilters
    source_observed_at_utc: str
    registry_version: str
    universe_id: str

    def __post_init__(self) -> None:
        if self.market_type != MARKET_TYPE or self.trading_status != "TRADING":
            raise InstrumentConstraintRegistryError("symbol is not tradable on Binance Spot")
        if self.quantity_step <= 0 or self.min_quantity < 0 or self.max_quantity < self.min_quantity:
            raise InstrumentConstraintRegistryError("invalid effective quantity bounds")
        if self.min_notional is not None and self.min_notional < 0:
            raise InstrumentConstraintRegistryError("invalid minimum notional")
        if self.max_notional is not None and (
            self.max_notional < 0
            or (self.min_notional is not None and self.max_notional < self.min_notional)
        ):
            raise InstrumentConstraintRegistryError("invalid maximum notional")
        if self.registry_version != REGISTRY_VERSION or self.universe_id != UNIVERSE_ID:
            raise InstrumentConstraintRegistryError("registry binding mismatch")
        if self.source_filter_names != ("LOT_SIZE", "MARKET_LOT_SIZE", "NOTIONAL"):
            raise InstrumentConstraintRegistryError("ambiguous filter applicability")


@dataclass(frozen=True, slots=True)
class InstrumentQuantityConstraintRegistry:
    version: str
    universe_id: str
    market_type: str
    source_endpoint_kind: str
    source_observed_at_utc: str
    source_snapshot_sha256: str
    symbols: Mapping[str, InstrumentQuantityConstraint]

    def __post_init__(self) -> None:
        if self.version != REGISTRY_VERSION or self.universe_id != UNIVERSE_ID:
            raise InstrumentConstraintRegistryError("registry version/universe mismatch")
        if self.market_type != MARKET_TYPE or not self.source_observed_at_utc.endswith("Z"):
            raise InstrumentConstraintRegistryError("registry provenance mismatch")
        expected = PREPARED_NEXT_TRADING_UNIVERSE.symbols
        keys = tuple(self.symbols)
        if len(keys) != len(set(keys)):
            raise InstrumentConstraintRegistryError("duplicate registry symbol")
        if set(keys) != set(expected):
            raise InstrumentConstraintRegistryError("registry symbols do not exactly match universe")
        frozen = MappingProxyType(dict(self.symbols))
        object.__setattr__(self, "symbols", frozen)

    def for_symbol(self, symbol: str) -> InstrumentQuantityConstraint:
        try:
            return self.symbols[symbol]
        except KeyError as exc:
            raise InstrumentConstraintRegistryError("symbol is outside registry") from exc


# Source-native decimal strings from the bounded observation.  LOT_SIZE applies
# to symbol quantity generally. MARKET_LOT_SIZE adds MARKET-specific bounds;
# its zero min/step values disable those individual rules. Effective MARKET
# bounds are the intersection of all enabled rules.
_SOURCE_ROWS: Final = (
    ("BTCUSDT", "BTC", "0.00001000", "9000.00000000", "0.00001000", "0.00000000", "143.33152687", "0.00000000", "5.00000000", "9000000.00000000"),
    ("ETHUSDT", "ETH", "0.00010000", "9000.00000000", "0.00010000", "0.00000000", "2896.43121875", "0.00000000", "5.00000000", "9000000.00000000"),
    ("SOLUSDT", "SOL", "0.00100000", "90000.00000000", "0.00100000", "0.00000000", "81255.48757500", "0.00000000", "5.00000000", "9000000.00000000"),
    ("BNBUSDT", "BNB", "0.00100000", "900000.00000000", "0.00100000", "0.00000000", "7589.53160416", "0.00000000", "5.00000000", "9000000.00000000"),
    ("XRPUSDT", "XRP", "0.10000000", "9222449.00000000", "0.10000000", "0.00000000", "2843939.68375000", "0.00000000", "5.00000000", "9000000.00000000"),
    ("LINKUSDT", "LINK", "0.01000000", "90000.00000000", "0.01000000", "0.00000000", "27513.17804166", "0.00000000", "5.00000000", "9000000.00000000"),
    ("DOGEUSDT", "DOGE", "1.00000000", "9000000.00000000", "1.00000000", "0.00000000", "33619716.97083333", "0.00000000", "1.00000000", "9000000.00000000"),
    ("ADAUSDT", "ADA", "0.10000000", "900000.00000000", "0.10000000", "0.00000000", "1642041.96458333", "0.00000000", "5.00000000", "9000000.00000000"),
    ("AVAXUSDT", "AVAX", "0.01000000", "90000.00000000", "0.01000000", "0.00000000", "36525.77879166", "0.00000000", "5.00000000", "9000000.00000000"),
    ("SUIUSDT", "SUI", "0.10000000", "92141578.00000000", "0.10000000", "0.00000000", "276099.68041666", "0.00000000", "5.00000000", "9000000.00000000"),
)


def _from_source_row(row: tuple[str, ...]) -> InstrumentQuantityConstraint:
    symbol, base, lot_min_s, lot_max_s, lot_step_s, market_min_s, market_max_s, market_step_s, min_notional_s, max_notional_s = row
    lot_min = _decimal(lot_min_s, "LOT_SIZE.minQty")
    lot_max = _decimal(lot_max_s, "LOT_SIZE.maxQty", positive=True)
    lot_step = _decimal(lot_step_s, "LOT_SIZE.stepSize", positive=True)
    market_min = _decimal(market_min_s, "MARKET_LOT_SIZE.minQty")
    market_max = _decimal(market_max_s, "MARKET_LOT_SIZE.maxQty")
    market_step = _decimal(market_step_s, "MARKET_LOT_SIZE.stepSize")
    source = SourceQuantityFilters(
        lot_min, lot_max, lot_step, market_min, market_max, market_step,
        "NOTIONAL", _decimal(min_notional_s, "NOTIONAL.minNotional"),
        _decimal(max_notional_s, "NOTIONAL.maxNotional"), True, False,
    )
    effective_min = max(lot_min, market_min) if market_min > 0 else lot_min
    effective_max = min(lot_max, market_max) if market_max > 0 else lot_max
    return InstrumentQuantityConstraint(
        symbol=symbol, market_type=MARKET_TYPE, trading_status="TRADING",
        base_asset=base, quote_asset="USDT", quantity_step=lot_step,
        min_quantity=effective_min, max_quantity=effective_max,
        market_quantity_step=market_step if market_step > 0 else None,
        market_min_quantity=market_min if market_min > 0 else None,
        market_max_quantity=market_max if market_max > 0 else None,
        min_notional=source.min_notional, max_notional=None,
        min_notional_applies_to_relevant_order_type=True,
        max_notional_applies_to_relevant_order_type=False,
        source_filter_names=("LOT_SIZE", "MARKET_LOT_SIZE", "NOTIONAL"),
        source_filters=source, source_observed_at_utc=SOURCE_OBSERVED_AT_UTC,
        registry_version=REGISTRY_VERSION, universe_id=UNIVERSE_ID,
    )


def _build_registry(rows: tuple[tuple[str, ...], ...]) -> InstrumentQuantityConstraintRegistry:
    entries = tuple(_from_source_row(row) for row in rows)
    if len(entries) != len({entry.symbol for entry in entries}):
        raise InstrumentConstraintRegistryError("duplicate registry symbol")
    return InstrumentQuantityConstraintRegistry(
        REGISTRY_VERSION, UNIVERSE_ID, MARKET_TYPE, SOURCE_ENDPOINT_KIND,
        SOURCE_OBSERVED_AT_UTC, SOURCE_SNAPSHOT_SHA256,
        {entry.symbol: entry for entry in entries},
    )


ACTIVE_QUANTITY_CONSTRAINT_REGISTRY: Final = _build_registry(_SOURCE_ROWS)


def normalize_binance_spot_exchange_info(payload: object) -> InstrumentQuantityConstraintRegistry:
    """Deterministically normalize a bounded official exchangeInfo snapshot."""
    if not isinstance(payload, dict) or not isinstance(payload.get("symbols"), list):
        raise InstrumentConstraintRegistryError("invalid exchangeInfo payload")
    rows: list[tuple[str, ...]] = []
    seen: set[str] = set()
    for symbol_data in payload["symbols"]:
        if not isinstance(symbol_data, dict) or not isinstance(symbol_data.get("filters"), list):
            raise InstrumentConstraintRegistryError("invalid symbol payload")
        symbol = symbol_data.get("symbol")
        if not isinstance(symbol, str) or symbol in seen:
            raise InstrumentConstraintRegistryError("duplicate or invalid source symbol")
        seen.add(symbol)
        if symbol_data.get("status") != "TRADING" or symbol_data.get("isSpotTradingAllowed") is not True:
            raise InstrumentConstraintRegistryError(f"{symbol} is not tradable on Spot")
        filters = {item.get("filterType"): item for item in symbol_data["filters"] if isinstance(item, dict)}
        if not {"LOT_SIZE", "MARKET_LOT_SIZE", "NOTIONAL"}.issubset(filters):
            raise InstrumentConstraintRegistryError(f"{symbol} lacks required filters")
        lot, market, notional = filters["LOT_SIZE"], filters["MARKET_LOT_SIZE"], filters["NOTIONAL"]
        if notional.get("applyMinToMarket") is not True:
            raise InstrumentConstraintRegistryError(f"{symbol} has ambiguous market min notional")
        rows.append((
            symbol, str(symbol_data.get("baseAsset")), str(lot.get("minQty")),
            str(lot.get("maxQty")), str(lot.get("stepSize")), str(market.get("minQty")),
            str(market.get("maxQty")), str(market.get("stepSize")),
            str(notional.get("minNotional")), str(notional.get("maxNotional")),
        ))
    order = {symbol: index for index, symbol in enumerate(PREPARED_NEXT_TRADING_UNIVERSE.symbols)}
    if set(seen) != set(order):
        raise InstrumentConstraintRegistryError("source symbols do not exactly match universe")
    return _build_registry(tuple(sorted(rows, key=lambda row: order[row[0]])))
