"""First-class immutable search-profile contracts for parallel trade research."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from app.config.trade_parameters import SCALPING_V2
from app.config.yaml_authority import RUNTIME_POLICY


class TradeProfileId(StrEnum):
    TRADE_15M_V1 = "trade-15m-v1"
    TRADE_5M_V2 = "trade-5m-v2"


class TradeProfileMode(StrEnum):
    PRODUCTION_SEARCH = "PRODUCTION_SEARCH"
    SHADOW_SEARCH = "SHADOW_SEARCH"


class TradeMode(StrEnum):
    TRADE_15M = "TRADE_15M"
    SCALPING = "SCALPING"


DEFAULT_TRADE_PROFILE_ID: Final = RUNTIME_POLICY.active_profile
ACTIVE_SCALPING_PROFILE_ID: Final = RUNTIME_POLICY.active_profile


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


def _profile_from_yaml(profile_id: str) -> TradeSearchProfile:
    source = RUNTIME_POLICY.profiles[profile_id]
    is_v2 = profile_id == TradeProfileId.TRADE_5M_V2.value
    signal = SCALPING_V2.signal if is_v2 else None
    costs = SCALPING_V2.costs if is_v2 else None
    lifecycle = SCALPING_V2.lifecycle if is_v2 else None
    geometry = SCALPING_V2.geometry if is_v2 else None
    return TradeSearchProfile(
        trade_profile_id=profile_id,
        trade_mode=source.trade_mode,
        display_i18n_key=source.display_i18n_key,
        trigger_timeframe=source.trigger_timeframe,
        primary_timeframe=source.trigger_timeframe,
        entry_timeframes=source.entry_timeframes,
        context_timeframes=source.context_timeframes,
        market_data_windows=tuple(
            (signal.market_data_windows if signal else source.market_data_windows or {}).items()
        ),
        book_depth_limit=costs.book_depth_limit if costs else int(source.book_depth_limit),
        microstructure_max_age_ms=(
            costs.microstructure_max_age_ms if costs else int(source.microstructure_max_age_ms)
        ),
        vwap_reference_notional=(
            costs.vwap_reference_notional if costs else float(source.vwap_reference_notional)
        ),
        mode=source.mode,
        analysis_history_candles=(
            signal.analysis_history_candles if signal else int(source.analysis_history_candles)
        ),
        atr_lookback_candles=(signal.atr_lookback_candles if signal else int(source.atr_lookback_candles)),
        impulse_lookback_candles=(signal.impulse_lookback_candles if signal else int(source.impulse_lookback_candles)),
        structure_lookback_candles=(signal.structure_lookback_candles if signal else int(source.structure_lookback_candles)),
        confirmation_window_candles=(signal.confirmation_window_candles if signal else int(source.confirmation_window_candles)),
        volume_baseline_candles=(signal.volume_baseline_candles if signal else int(source.volume_baseline_candles)),
        regime_lookback_candles=(signal.regime_lookback_candles if signal else int(source.regime_lookback_candles)),
        validity_boundaries=(lifecycle.validity_boundaries if lifecycle else int(source.validity_boundaries)),
        minimum_planned_rr=(geometry.minimum_planned_rr if geometry else float(source.minimum_planned_rr)),
        cost_safety_margin_bps=(costs.cost_safety_margin_bps if costs else float(source.cost_safety_margin_bps)),
        paper_command_creation_enabled=source.paper_command_creation_enabled,
        position_opening_enabled=source.position_opening_enabled,
    )


TRADE_15M_PROFILE: Final = _profile_from_yaml(TradeProfileId.TRADE_15M_V1.value)

# V2 is the sole supported Scalping runtime identity. Historical v1 values are
# plain persisted strings and remain readable without a runnable profile.
TRADE_5M_V2_PROFILE: Final = _profile_from_yaml(TradeProfileId.TRADE_5M_V2.value)

TRADE_PROFILES: Final = MappingProxyType({
    TRADE_15M_PROFILE.trade_profile_id: TRADE_15M_PROFILE,
    TRADE_5M_V2_PROFILE.trade_profile_id: TRADE_5M_V2_PROFILE,
})
SCALPING_PROFILE_IDS: Final = frozenset({
    TradeProfileId.TRADE_5M_V2.value,
})
ACTIVE_RUNTIME_PROFILE_IDS: Final = frozenset({
    profile_id for profile_id, profile in RUNTIME_POLICY.profiles.items() if profile.enabled
})

# Identical values are deliberate safety invariants, not copied timeframe tuning.
IDENTICAL_VALUE_JUSTIFICATIONS: Final = MappingProxyType({
    "minimum_planned_rr": "The 15m floor remains 1.5; Scalping policy owns its independent floor.",
    "validity_boundaries": "Each profile expires at its own next trigger boundary.",
})

TRADE_5M_CONTEXT_MINIMUM_WINDOWS: Final = MappingProxyType(
    dict(TRADE_5M_V2_PROFILE.market_data_windows)
)


def resolve_trade_profile(value: str | TradeProfileId | None = None) -> TradeSearchProfile:
    profile_id = DEFAULT_TRADE_PROFILE_ID if value is None else str(value)
    try:
        return TRADE_PROFILES[profile_id]
    except KeyError as exc:
        raise ValueError(f"unsupported trade profile: {profile_id}") from exc
