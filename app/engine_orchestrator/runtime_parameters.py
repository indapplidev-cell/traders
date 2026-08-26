"""Immutable, public runtime parameter sets for trade-profile evaluation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from types import MappingProxyType
from typing import Final, Mapping

from app.engine_orchestrator.trade_profile import (
    TradeProfileId,
    TradeSearchProfile,
    resolve_trade_profile,
)


@dataclass(frozen=True, slots=True)
class RuntimeProfileParameters:
    """One authoritative, reconstructible parameter object for a full run.

    Values are deliberately public configuration.  The identifier therefore
    never incorporates a credential, protected binding, or runtime secret.
    """

    contract_version: str
    profile_id: str
    trigger_timeframe: str
    mode: str
    market_data_required_timeframes: tuple[str, ...]
    market_data_context_windows: tuple[tuple[str, int], ...]
    bounded_book_depth_limit: int
    microstructure_max_age_ms: int
    vwap_reference_notional: float
    analysis_compression_ratio: float
    analysis_expansion_ratio: float
    analysis_history_candles: int
    atr_lookback_candles: int
    impulse_lookback_candles: int
    structure_lookback_candles: int
    analysis_decision_candles: int
    confirmation_window_candles: int
    volume_baseline_candles: int
    breakout_volume_baseline_candles: int
    regime_lookback_candles: int
    setup_policy_id: str
    strategy_policy_id: str
    strategy_minimum_allowed_quality: str
    risk_shadow_policy_id: str
    risk_minimum_strategy_quality: str
    risk_minimum_strategy_score: float
    validity_boundaries: int
    minimum_planned_rr: float
    cost_safety_margin_bps: float
    stop_policy_id: str
    target_policy_id: str
    paper_command_creation_enabled: bool
    position_opening_enabled: bool

    def __post_init__(self) -> None:
        profile = resolve_trade_profile(self.profile_id)
        if self.trigger_timeframe != profile.trigger_timeframe or self.mode != profile.mode:
            raise ValueError("runtime parameter identity/profile mismatch")
        if self.market_data_required_timeframes != tuple(
            timeframe for timeframe, _ in profile.market_data_windows
        ) or self.market_data_context_windows != profile.market_data_windows:
            raise ValueError("runtime market-data/profile identity mismatch")
        if (
            self.bounded_book_depth_limit != profile.book_depth_limit
            or self.microstructure_max_age_ms != profile.microstructure_max_age_ms
            or self.vwap_reference_notional != profile.vwap_reference_notional
        ):
            raise ValueError("runtime microstructure/profile identity mismatch")
        if not 0 < self.analysis_compression_ratio < 1 < self.analysis_expansion_ratio:
            raise ValueError("invalid analysis volatility-regime thresholds")
        positive = (
            self.analysis_history_candles,
            self.atr_lookback_candles,
            self.impulse_lookback_candles,
            self.structure_lookback_candles,
            self.analysis_decision_candles,
            self.confirmation_window_candles,
            self.volume_baseline_candles,
            self.breakout_volume_baseline_candles,
            self.regime_lookback_candles,
            self.validity_boundaries,
        )
        if min(positive) <= 0:
            raise ValueError("runtime profile windows must be positive")
        if self.analysis_history_candles < self.regime_lookback_candles:
            raise ValueError("analysis history must cover the regime window")
        if self.regime_lookback_candles < self.structure_lookback_candles:
            raise ValueError("regime window must cover the structure window")
        if self.minimum_planned_rr < 1.5:
            raise ValueError("runtime planned RR must preserve the 1.5 floor")
        for value in (
            self.contract_version,
            self.setup_policy_id,
            self.strategy_policy_id,
            self.risk_shadow_policy_id,
            self.stop_policy_id,
            self.target_policy_id,
        ):
            if not str(value).strip():
                raise ValueError("runtime parameter policy identifiers must not be empty")
        if (
            self.paper_command_creation_enabled != profile.paper_command_creation_enabled
            or self.position_opening_enabled != profile.position_opening_enabled
        ):
            raise ValueError("runtime execution authority/profile mismatch")

    @property
    def parameter_set_id(self) -> str:
        identity = asdict(self)
        if self.profile_id == TradeProfileId.TRADE_15M_V1.value:
            # Preserve the deployed 15m parameter identity: these new fields
            # only make its already-existing market-data contract explicit.
            for name in (
                "market_data_required_timeframes",
                "market_data_context_windows",
                "bounded_book_depth_limit",
                "microstructure_max_age_ms",
                "vwap_reference_notional",
                "analysis_compression_ratio",
                "analysis_expansion_ratio",
            ):
                identity.pop(name)
        canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
        return f"{self.profile_id}-runtime-v1-{digest}"

    def public_provenance(self) -> dict[str, object]:
        return {
            "runtime_parameter_contract_version": self.contract_version,
            "runtime_parameter_set_id": self.parameter_set_id,
            "runtime_parameter_profile_id": self.profile_id,
        }


def _runtime_parameters(profile: TradeSearchProfile) -> RuntimeProfileParameters:
    if profile.trade_profile_id == TradeProfileId.TRADE_5M_V1.value:
        analysis = {
            "atr_lookback_candles": profile.atr_lookback_candles,
            "impulse_lookback_candles": profile.impulse_lookback_candles,
            "structure_lookback_candles": profile.structure_lookback_candles,
            "analysis_decision_candles": profile.structure_lookback_candles,
            "confirmation_window_candles": profile.confirmation_window_candles,
            "volume_baseline_candles": profile.volume_baseline_candles,
            "breakout_volume_baseline_candles": profile.volume_baseline_candles,
            "regime_lookback_candles": profile.regime_lookback_candles,
        }
    else:
        # These are the pre-remediation engine defaults.  Keeping them explicit
        # makes the 15m parameter identity honest without changing 15m behavior.
        analysis = {
            "atr_lookback_candles": 14,
            "impulse_lookback_candles": 96,
            "structure_lookback_candles": 96,
            "analysis_decision_candles": 24,
            "confirmation_window_candles": 3,
            "volume_baseline_candles": 93,
            "breakout_volume_baseline_candles": 20,
            "regime_lookback_candles": 96,
        }
    return RuntimeProfileParameters(
        contract_version="trade-runtime-parameters-v1",
        profile_id=profile.trade_profile_id,
        trigger_timeframe=profile.trigger_timeframe,
        mode=profile.mode,
        market_data_required_timeframes=tuple(
            timeframe for timeframe, _ in profile.market_data_windows
        ),
        market_data_context_windows=profile.market_data_windows,
        bounded_book_depth_limit=profile.book_depth_limit,
        microstructure_max_age_ms=profile.microstructure_max_age_ms,
        vwap_reference_notional=profile.vwap_reference_notional,
        analysis_compression_ratio=0.75,
        analysis_expansion_ratio=1.35,
        analysis_history_candles=profile.analysis_history_candles,
        **analysis,
        setup_policy_id="engine-setup-01-causal-v1",
        strategy_policy_id="engine-strategy-01-shadow-v1",
        strategy_minimum_allowed_quality="ACCEPTABLE",
        risk_shadow_policy_id="ENGINE_RISK_01_RESEARCH_POLICY_V1",
        risk_minimum_strategy_quality="ACCEPTABLE",
        risk_minimum_strategy_score=65.0,
        validity_boundaries=profile.validity_boundaries,
        minimum_planned_rr=profile.minimum_planned_rr,
        cost_safety_margin_bps=profile.cost_safety_margin_bps,
        stop_policy_id="LOCAL_INVALIDATION_STRUCTURE_WITH_VOLATILITY_BUFFER",
        target_policy_id=(
            "CAUSAL_HIERARCHY_ECONOMIC_ACTIONABILITY_V2"
            if profile.trade_profile_id == TradeProfileId.TRADE_5M_V1.value
            else "OPPOSITE_CAUSAL_LEVEL"
        ),
        paper_command_creation_enabled=profile.paper_command_creation_enabled,
        position_opening_enabled=profile.position_opening_enabled,
    )


RUNTIME_PROFILE_PARAMETERS: Final = MappingProxyType({
    profile_id: _runtime_parameters(resolve_trade_profile(profile_id))
    for profile_id in (
        TradeProfileId.TRADE_15M_V1.value,
        TradeProfileId.TRADE_5M_V1.value,
    )
})


def resolve_runtime_parameters(
    profile_id: str,
    *,
    registry: Mapping[str, RuntimeProfileParameters] = RUNTIME_PROFILE_PARAMETERS,
) -> RuntimeProfileParameters:
    """Resolve explicitly and fail closed; there is no profile/default fallback."""
    try:
        parameters = registry[str(profile_id)]
    except KeyError as exc:
        raise ValueError(f"runtime parameter set missing for profile: {profile_id}") from exc
    if parameters.profile_id != str(profile_id):
        raise ValueError("runtime parameter registry identity mismatch")
    return parameters
