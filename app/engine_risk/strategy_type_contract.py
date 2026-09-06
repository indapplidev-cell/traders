"""Bounded profile-aware strategy type compatibility for research Risk."""

from __future__ import annotations

from types import MappingProxyType
from typing import Final

from app.engine_orchestrator.trade_profile import (
    TradeMode,
    TradeProfileId,
    resolve_trade_profile,
)
from app.engine_strategy.strategy_type import StrategyType


SCALPING_RISK_STRATEGY_TYPES: Final = frozenset({
    StrategyType.SCALP_TREND_PULLBACK_RESEARCH.value,
    StrategyType.SCALP_BREAKOUT_RESEARCH.value,
    StrategyType.SCALP_BREAKOUT_RETEST_RESEARCH.value,
    StrategyType.SCALP_RANGE_BOUNCE_RESEARCH.value,
    StrategyType.SCALP_LIQUIDITY_SWEEP_RESEARCH.value,
    StrategyType.SCALP_MOMENTUM_CONTINUATION_RESEARCH.value,
    StrategyType.SCALP_COMPRESSION_BREAK_RESEARCH.value,
})

TRADE_15M_RISK_STRATEGY_TYPES: Final = frozenset({
    StrategyType.BREAKOUT_CONTINUATION_RESEARCH.value,
    StrategyType.TREND_CONTINUATION_RESEARCH.value,
})

RISK_STRATEGY_TYPE_REGISTRY: Final = MappingProxyType({
    (TradeProfileId.TRADE_15M_V1.value, TradeMode.TRADE_15M.value):
        TRADE_15M_RISK_STRATEGY_TYPES,
    (TradeProfileId.TRADE_5M_V2.value, TradeMode.SCALPING.value):
        SCALPING_RISK_STRATEGY_TYPES,
})


def supported_risk_strategy_types(profile_id: str, trade_mode: str) -> frozenset[str]:
    """Return the explicit contract set; invalid profile/mode pairs fail closed."""

    normalized_profile = str(profile_id)
    normalized_mode = str(trade_mode).upper()
    profile = resolve_trade_profile(normalized_profile)
    if profile.trade_mode != normalized_mode:
        return frozenset()
    return RISK_STRATEGY_TYPE_REGISTRY.get(
        (normalized_profile, normalized_mode), frozenset()
    )


def risk_supports_strategy_type(
    profile_id: str, trade_mode: str, strategy_type: object
) -> bool:
    """Accept only a normalized, registered machine code for the exact profile."""

    if not isinstance(strategy_type, str) or not strategy_type:
        return False
    return strategy_type in supported_risk_strategy_types(profile_id, trade_mode)
