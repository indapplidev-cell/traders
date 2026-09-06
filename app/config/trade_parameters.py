"""Strict server-owned trading parameter configuration."""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
import yaml


CONFIG_PATH = Path(
    os.environ.get(
        "TRADERS_TRADE_PARAMETERS_PATH",
        Path(__file__).resolve().parents[2] / "config" / "trading" / "trade_parameters.yaml",
    )
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SignalParameters(StrictModel):
    timeframe: Literal["5m"]
    required_timeframes: tuple[str, ...]
    market_data_windows: dict[str, int]
    allowed_setup_types: tuple[str, ...]
    analysis_history_candles: int = Field(gt=0)
    atr_lookback_candles: int = Field(gt=0)
    impulse_lookback_candles: int = Field(gt=0)
    structure_lookback_candles: int = Field(gt=0)
    confirmation_window_candles: int = Field(gt=0)
    volume_baseline_candles: int = Field(gt=0)
    regime_lookback_candles: int = Field(gt=0)
    strategy_minimum_score: float = Field(ge=0, le=100)


class RiskParameters(StrictModel):
    risk_per_trade_bps: float = Field(gt=0)
    max_open_positions: int = Field(gt=0)
    max_new_commands_per_cycle: int = Field(gt=0)
    total_open_risk_limit_bps: float = Field(gt=0)


class GeometryParameters(StrictModel):
    atr_multiplier: float = Field(gt=0)
    stop_min_bps: float = Field(ge=0)
    stop_max_bps: float = Field(gt=0)
    target_policy: str = Field(min_length=1)
    target_min_bps: float = Field(gt=0)
    minimum_planned_rr: float = Field(gt=0)

    @model_validator(mode="after")
    def valid_stop_range(self):
        if self.stop_min_bps >= self.stop_max_bps:
            raise ValueError("stop_min_bps must be less than stop_max_bps")
        return self


class EconomicsParameters(StrictModel):
    min_net_edge_bps: float = Field(ge=0)
    min_positive_ev_r: float = Field(ge=0)
    min_ev_reserve_r: float = Field(ge=0)
    bucket_min_sample: int = Field(gt=0)
    probability_confidence_level: float = Field(gt=0, lt=1)
    prior_alpha: float = Field(gt=0)
    prior_beta: float = Field(gt=0)
    static_rr_fallback_enabled: Literal[False]
    parent_bucket_fallback_order: tuple[str, ...]


class CostParameters(StrictModel):
    commission_source: Literal["binance_dynamic"]
    conservative_fallback_policy: Literal["FAIL_CLOSED"]
    configured_entry_fee_bps: float = Field(ge=0)
    configured_exit_fee_bps: float = Field(ge=0)
    spread_policy: str = Field(min_length=1)
    slippage_policy: str = Field(min_length=1)
    entry_slippage_bps: float = Field(ge=0)
    exit_slippage_bps: float = Field(ge=0)
    adverse_fill_reserve_bps: float = Field(ge=0)
    cost_safety_margin_bps: float = Field(ge=0)
    max_depth_impact_bps: float = Field(ge=0)
    max_cost_snapshot_age_seconds: int = Field(gt=0)
    book_depth_limit: int = Field(gt=0)
    vwap_reference_notional: float = Field(gt=0)
    microstructure_max_age_ms: int = Field(gt=0)


class LifecycleParameters(StrictModel):
    plan_ttl_seconds: int = Field(gt=0)
    entry_fill_window_seconds: int = Field(gt=0)
    validity_boundaries: int = Field(gt=0)
    exit_time_stop_minutes: int = Field(gt=0)
    maximum_price_drift_bps: float = Field(ge=0)


class CausalOpportunityParameters(StrictModel):
    one_execution_per_opportunity: bool
    reset_policy: str = Field(min_length=1)
    reset_min_conditions: int = Field(gt=0)


class EntryRefinementParameters(StrictModel):
    enabled: bool
    mode: Literal["SHADOW"]
    timeout_seconds: int = Field(gt=0)
    authoritative_promotion_allowed: Literal[False]


class ScalpingV2Parameters(StrictModel):
    enabled: Literal[True]
    signal: SignalParameters
    risk: RiskParameters
    geometry: GeometryParameters
    economics: EconomicsParameters
    costs: CostParameters
    lifecycle: LifecycleParameters
    causal_opportunity: CausalOpportunityParameters
    entry_refinement_1m: EntryRefinementParameters


class Disabled15mParameters(StrictModel):
    enabled: Literal[False]


class TradingProfiles(StrictModel):
    trade_5m_v2: ScalpingV2Parameters = Field(alias="trade-5m-v2")
    trade_15m_v1: Disabled15mParameters = Field(alias="trade-15m-v1")


class TradeParameters(StrictModel):
    schema_version: Literal[1]
    config_version: str = Field(min_length=1)
    profiles: TradingProfiles

    @property
    def config_hash(self) -> str:
        canonical = json.dumps(
            self.model_dump(mode="json", by_alias=True), sort_keys=True,
            separators=(",", ":"), ensure_ascii=True,
        )
        return sha256(canonical.encode("utf-8")).hexdigest()


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f"duplicate trade parameter field: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def load_trade_parameters(path: Path = CONFIG_PATH) -> TradeParameters:
    try:
        raw = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
        return TradeParameters.model_validate(raw)
    except Exception as exc:
        raise RuntimeError(f"invalid authoritative trade parameters: {path}") from exc


TRADE_PARAMETERS = load_trade_parameters()
SCALPING_V2 = TRADE_PARAMETERS.profiles.trade_5m_v2


__all__ = (
    "CONFIG_PATH", "SCALPING_V2", "TRADE_PARAMETERS", "TradeParameters",
    "load_trade_parameters",
)
