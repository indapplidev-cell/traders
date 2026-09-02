"""First-class immutable search-profile contracts for parallel trade research."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final


class TradeProfileId(StrEnum):
    TRADE_15M_V1 = "trade-15m-v1"
    TRADE_5M_V1 = "trade-5m-v1"
    TRADE_5M_V2 = "trade-5m-v2"


class TradeProfileMode(StrEnum):
    PRODUCTION_SEARCH = "PRODUCTION_SEARCH"
    SHADOW_SEARCH = "SHADOW_SEARCH"


class TradeMode(StrEnum):
    TRADE_15M = "TRADE_15M"
    SCALPING = "SCALPING"


DEFAULT_TRADE_PROFILE_ID: Final = TradeProfileId.TRADE_15M_V1.value
ACTIVE_SCALPING_PROFILE_ID: Final = TradeProfileId.TRADE_5M_V2.value


@dataclass(frozen=True, slots=True)
class TradeSearchProfile:
    trade_profile_id: str
    trade_mode: str
    display_i18n_key: str
    trigger_timeframe: str
    primary_timeframe: str
    entry_timeframes: tuple[str, ...]
    context_timeframes: tuple[str, ...]
    market_data_windows: tuple[tuple[str, int], ...]
    book_depth_limit: int
    microstructure_max_age_ms: int
    vwap_reference_notional: float
    mode: str
    analysis_history_candles: int
    atr_lookback_candles: int
    impulse_lookback_candles: int
    structure_lookback_candles: int
    confirmation_window_candles: int
    volume_baseline_candles: int
    regime_lookback_candles: int
    validity_boundaries: int
    minimum_planned_rr: float
    cost_safety_margin_bps: float
    paper_command_creation_enabled: bool
    position_opening_enabled: bool

    def __post_init__(self) -> None:
        TradeProfileId(self.trade_profile_id)
        TradeMode(self.trade_mode)
        TradeProfileMode(self.mode)
        if not self.display_i18n_key.startswith("trading.profile."):
            raise ValueError("trade-profile display i18n key is invalid")
        if self.primary_timeframe != self.trigger_timeframe:
            raise ValueError("primary timeframe must match the trigger timeframe")
        if self.primary_timeframe not in self.entry_timeframes:
            raise ValueError("entry timeframes must include the primary timeframe")
        if set(self.entry_timeframes).intersection(self.context_timeframes):
            raise ValueError("entry and context timeframe roles must be distinct")
        window_map = dict(self.market_data_windows)
        if len(window_map) != len(self.market_data_windows):
            raise ValueError("market-data timeframes must be unique")
        if not set(self.entry_timeframes + self.context_timeframes).issubset(window_map):
            raise ValueError("every semantic timeframe role requires a market-data window")
        if min(window_map.values()) <= 0:
            raise ValueError("market-data windows must be positive")
        if self.book_depth_limit not in {5, 10, 20, 50, 100, 500, 1000, 5000}:
            raise ValueError("unsupported bounded book depth limit")
        if self.microstructure_max_age_ms <= 0 or self.vwap_reference_notional <= 0:
            raise ValueError("microstructure bounds must be positive")
        if self.trigger_timeframe not in {"15m", "5m"}:
            raise ValueError("unsupported trade-profile trigger timeframe")
        if min(
            self.analysis_history_candles,
            self.atr_lookback_candles,
            self.impulse_lookback_candles,
            self.structure_lookback_candles,
            self.confirmation_window_candles,
            self.volume_baseline_candles,
            self.regime_lookback_candles,
            self.validity_boundaries,
        ) <= 0:
            raise ValueError("trade-profile windows must be positive")
        minimum_rr = 1.5 if self.trade_mode == TradeMode.TRADE_15M.value else 0.2
        if self.minimum_planned_rr < minimum_rr:
            raise ValueError(f"trade-profile planned RR must preserve the {minimum_rr:g} profile floor")
        if self.mode == TradeProfileMode.SHADOW_SEARCH.value and (
            self.paper_command_creation_enabled or self.position_opening_enabled
        ):
            raise ValueError("shadow search cannot create PAPER commands or positions")


TRADE_15M_PROFILE: Final = TradeSearchProfile(
    trade_profile_id=TradeProfileId.TRADE_15M_V1.value,
    trade_mode=TradeMode.TRADE_15M.value,
    display_i18n_key="trading.profile.trade_15m.title",
    trigger_timeframe="15m",
    primary_timeframe="15m",
    entry_timeframes=("15m",),
    context_timeframes=("1h", "4h"),
    market_data_windows=(("1m", 240), ("5m", 288), ("15m", 480),
                         ("1h", 240), ("4h", 180), ("1d", 240)),
    book_depth_limit=100,
    microstructure_max_age_ms=5_000,
    vwap_reference_notional=100.0,
    mode=TradeProfileMode.PRODUCTION_SEARCH.value,
    analysis_history_candles=480,
    atr_lookback_candles=14,
    impulse_lookback_candles=8,
    structure_lookback_candles=32,
    confirmation_window_candles=2,
    volume_baseline_candles=20,
    regime_lookback_candles=48,
    validity_boundaries=1,
    minimum_planned_rr=1.5,
    cost_safety_margin_bps=2.0,
    paper_command_creation_enabled=True,
    position_opening_enabled=True,
)

TRADE_5M_PROFILE: Final = TradeSearchProfile(
    trade_profile_id=TradeProfileId.TRADE_5M_V1.value,
    trade_mode=TradeMode.SCALPING.value,
    display_i18n_key="trading.profile.trade_5m.title",
    trigger_timeframe="5m",
    primary_timeframe="5m",
    entry_timeframes=("1m", "5m"),
    context_timeframes=("15m", "1h"),
    market_data_windows=(("1m", 60), ("5m", 120), ("15m", 64), ("1h", 50)),
    book_depth_limit=100,
    microstructure_max_age_ms=5_000,
    vwap_reference_notional=100.0,
    mode=TradeProfileMode.PRODUCTION_SEARCH.value,
    analysis_history_candles=120,
    atr_lookback_candles=24,
    impulse_lookback_candles=12,
    structure_lookback_candles=48,
    confirmation_window_candles=3,
    volume_baseline_candles=36,
    regime_lookback_candles=72,
    validity_boundaries=1,
    minimum_planned_rr=1.5,
    cost_safety_margin_bps=3.0,
    paper_command_creation_enabled=True,
    position_opening_enabled=True,
)

# V2 is the sole active Scalping runtime identity.  V1 remains registered only
# so immutable historical rows can still be reconstructed by readonly tools.
TRADE_5M_V2_PROFILE: Final = TradeSearchProfile(
    trade_profile_id=TradeProfileId.TRADE_5M_V2.value,
    trade_mode=TradeMode.SCALPING.value,
    display_i18n_key="trading.profile.trade_5m.title",
    trigger_timeframe="5m",
    primary_timeframe="5m",
    entry_timeframes=("1m", "5m"),
    context_timeframes=("15m", "1h"),
    market_data_windows=(("1m", 60), ("5m", 120), ("15m", 64), ("1h", 50)),
    book_depth_limit=100,
    microstructure_max_age_ms=5_000,
    vwap_reference_notional=100.0,
    mode=TradeProfileMode.PRODUCTION_SEARCH.value,
    analysis_history_candles=120,
    atr_lookback_candles=12,
    impulse_lookback_candles=8,
    structure_lookback_candles=12,
    confirmation_window_candles=1,
    volume_baseline_candles=12,
    regime_lookback_candles=24,
    validity_boundaries=1,
    minimum_planned_rr=0.4,
    cost_safety_margin_bps=3.0,
    paper_command_creation_enabled=True,
    position_opening_enabled=True,
)

TRADE_PROFILES: Final = MappingProxyType({
    TRADE_15M_PROFILE.trade_profile_id: TRADE_15M_PROFILE,
    TRADE_5M_PROFILE.trade_profile_id: TRADE_5M_PROFILE,
    TRADE_5M_V2_PROFILE.trade_profile_id: TRADE_5M_V2_PROFILE,
})
SCALPING_PROFILE_IDS: Final = frozenset({
    TradeProfileId.TRADE_5M_V1.value,
    TradeProfileId.TRADE_5M_V2.value,
})
ACTIVE_RUNTIME_PROFILE_IDS: Final = frozenset({
    TradeProfileId.TRADE_15M_V1.value,
    ACTIVE_SCALPING_PROFILE_ID,
})

# Identical values are deliberate safety invariants, not copied timeframe tuning.
IDENTICAL_VALUE_JUSTIFICATIONS: Final = MappingProxyType({
    "minimum_planned_rr": "The 15m floor remains 1.5; Scalping policy owns its independent floor.",
    "validity_boundaries": "Each profile expires at its own next trigger boundary.",
})

TRADE_5M_CONTEXT_MINIMUM_WINDOWS: Final = MappingProxyType(
    dict(TRADE_5M_PROFILE.market_data_windows)
)


def resolve_trade_profile(value: str | TradeProfileId | None = None) -> TradeSearchProfile:
    profile_id = DEFAULT_TRADE_PROFILE_ID if value is None else str(value)
    try:
        return TRADE_PROFILES[profile_id]
    except KeyError as exc:
        raise ValueError(f"unsupported trade profile: {profile_id}") from exc
