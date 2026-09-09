"""Strict server-owned trading parameter configuration."""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
from copy import deepcopy
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
import yaml

from app.config.yaml_authority import RISK_POLICY, RISK_PATH, authority_hash


CONFIG_PATH = Path(
    os.environ.get(
        "TRADERS_TRADE_PARAMETERS_PATH",
        RISK_PATH.parent / "trade_parameters.yaml",
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
    impulse_absolute_threshold_pct: float = Field(gt=0)
    impulse_atr_multiplier: float = Field(gt=0)
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


class CommissionParameters(StrictModel):
    source: Literal["binance_account_commission"]
    real_account_data: Literal[True]
    refresh_interval_seconds: int = Field(gt=0)
    retry_interval_seconds: int = Field(gt=0)
    max_snapshot_age_seconds: int = Field(gt=0)
    fail_closed: Literal[True]
    allow_stub_fallback: Literal[False]
    entry_liquidity_role: Literal["MAKER", "TAKER"]
    exit_liquidity_role: Literal["MAKER", "TAKER"]

    @model_validator(mode="after")
    def valid_refresh_policy(self):
        if self.refresh_interval_seconds > self.max_snapshot_age_seconds:
            raise ValueError("commission refresh interval cannot exceed max snapshot age")
        if self.retry_interval_seconds > self.refresh_interval_seconds:
            raise ValueError("commission retry interval cannot exceed refresh interval")
        return self


class CostParameters(StrictModel):
    commission_source: Literal["binance_dynamic"]
    commission: CommissionParameters
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


class StalePositionPolicyParameters(StrictModel):
    enabled: Literal[True]
    mode: Literal["SHADOW"]
    soft_timeout_seconds: int = Field(gt=0)
    hard_timeout_seconds: int = Field(gt=0)
    min_target_progress_at_soft_timeout: float = Field(ge=0, le=1)
    min_mfe_bps_at_soft_timeout: float | None = Field(default=None, ge=0)
    min_remaining_ev_r_at_soft_timeout: float = Field(ge=0)
    extension_allowed: bool
    extension_seconds: int = Field(ge=0)
    max_extensions: int = Field(ge=0)
    extension_requires_positive_net_exit_pnl: bool
    extension_requires_setup_valid: bool
    extension_requires_momentum_valid: bool
    net_break_even_protection_enabled: bool
    break_even_activation_target_progress: float = Field(ge=0, le=1)
    use_current_exit_costs: Literal[True]

    @model_validator(mode="after")
    def valid_timeout_policy(self):
        if self.soft_timeout_seconds >= self.hard_timeout_seconds:
            raise ValueError("soft timeout must be below hard timeout")
        if not self.extension_allowed and self.max_extensions != 0:
            raise ValueError("disabled extension policy must have zero extensions")
        if self.extension_allowed and self.max_extensions > 0 and self.extension_seconds == 0:
            raise ValueError("enabled extensions must have a positive duration")
        return self


class ExitPolicyParameters(StrictModel):
    stale_position: StalePositionPolicyParameters


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
    exit_policy: ExitPolicyParameters
    causal_opportunity: CausalOpportunityParameters
    entry_refinement_1m: EntryRefinementParameters


class Disabled15mParameters(StrictModel):
    enabled: Literal[False]


class TradingProfiles(StrictModel):
    trade_5m_v2: ScalpingV2Parameters = Field(alias="trade-5m-v2")
    trade_15m_v1: Disabled15mParameters = Field(alias="trade-15m-v1")


class ParameterSetDefinition(StrictModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    version: str = Field(min_length=1)
    inherits: str | None = None
    overrides: dict[str, Any]


class PaperParameterSetSelector(StrictModel):
    previous_parameter_set: str = Field(min_length=1)
    active_parameter_set: str = Field(min_length=1)
    switched_at_utc: str = Field(min_length=1)
    activation_cycle_boundary_ms: int = Field(ge=0)
    activation_revision: str = Field(min_length=1)
    activation_reason: str = Field(min_length=1)


class ScalpingV2SetArchitecture(StrictModel):
    parameter_sets: dict[str, ParameterSetDefinition]
    paper: PaperParameterSetSelector


@dataclass(frozen=True, slots=True)
class ResolvedParameterSet:
    id: str
    label: str
    version: str
    parameters: ScalpingV2Parameters
    resolved_config_hash: str
    activation_cycle_boundary_ms: int
    activation_revision: str
    previous_parameter_set: str
    switched_at_utc: str
    provenance: dict[str, str]


class ParameterSource(StrEnum):
    SET_2_OVERRIDE = "SET_2_OVERRIDE"
    SET_1_INHERITED = "SET_1_INHERITED"
    SET_1_BASELINE = "SET_1_BASELINE"
    NAMED_SET_OVERRIDE = "NAMED_SET_OVERRIDE"
    DYNAMIC_BINANCE_COMMISSION = "DYNAMIC_BINANCE_COMMISSION"
    RUNTIME_DYNAMIC = "RUNTIME_DYNAMIC"
    SHADOW_POLICY = "SHADOW_POLICY"
    LEGACY_UNAVAILABLE = "LEGACY_UNAVAILABLE"


def parameter_snapshot(resolved: ResolvedParameterSet) -> dict[str, Any]:
    """Serialize values and their resolver-owned origin from one captured set."""
    rows = {}
    def visit(values, prefix=""):
        for key, value in values.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                visit(value, path)
                continue
            owner = resolved.provenance.get(path, "scalping-v2-set-1")
            source = (ParameterSource.SET_2_OVERRIDE if owner == "scalping-v2-set-2"
                      else ParameterSource.SET_1_INHERITED if owner == "scalping-v2-set-1" and resolved.id != owner
                      else ParameterSource.SET_1_BASELINE if owner == "scalping-v2-set-1"
                      else ParameterSource.NAMED_SET_OVERRIDE)
            source_file = "config/trading/risk_policy.yaml" if path.startswith("risk.") else "config/trading/trade_parameters.yaml"
            source_path = path.removeprefix("risk.") if path.startswith("risk.") else path
            rows[path] = {"value": value, "source": source.value, "owner_set_id": owner,
                          "source_file": source_file, "source_path": source_path,
                          "source_kind": "AUTHORITATIVE_YAML", "unit": _unit_for(path),
                          "source_component": f"{source_file}::{source_path}"}
    visit(resolved.parameters.model_dump(mode="json"))
    return {"parameter_set_id": resolved.id, "parameter_set_label": resolved.label,
            "parameter_set_version": resolved.version, "resolved_config_hash": resolved.resolved_config_hash,
            "activation_cycle_boundary_ms": resolved.activation_cycle_boundary_ms,
            "parameters": rows}


def _unit_for(path: str) -> str:
    if path.endswith("_bps"):
        return "bps"
    if path.endswith("_pct"):
        return "percent"
    if path.endswith("_seconds"):
        return "seconds"
    if path.endswith("_ms"):
        return "milliseconds"
    if path.endswith("_minutes"):
        return "minutes"
    if path.endswith("_candles") or path.endswith("_boundaries"):
        return "count"
    return "dimensionless"


class TradeParameters(StrictModel):
    schema_version: Literal[1]
    config_version: str = Field(min_length=1)
    profiles: TradingProfiles
    scalping_v2: ScalpingV2SetArchitecture

    @model_validator(mode="after")
    def valid_parameter_set_registry(self):
        definitions = tuple(self.scalping_v2.parameter_sets.values())
        if len({item.id for item in definitions}) != len(definitions):
            raise ValueError("parameter-set IDs must be unique")
        for definition in definitions:
            self.resolve_scalping_v2_parameter_set(definition.id)
        self.resolve_scalping_v2_parameter_set()
        self.resolve_scalping_v2_parameter_set(
            self.scalping_v2.paper.previous_parameter_set
        )
        return self

    @staticmethod
    def _semantic_hash(parameters: ScalpingV2Parameters) -> str:
        return authority_hash({"trade_parameters": parameters.model_dump(mode="json")})

    def resolve_scalping_v2_parameter_set(
        self, parameter_set_id: str | None = None,
    ) -> ResolvedParameterSet:
        selected = parameter_set_id or self.scalping_v2.paper.active_parameter_set
        definitions = {item.id: item for item in self.scalping_v2.parameter_sets.values()}
        if selected not in definitions:
            raise RuntimeError(f"UNKNOWN_PARAMETER_SET: {selected}")
        baseline = self.profiles.trade_5m_v2.model_dump(mode="python")
        resolving: set[str] = set()

        def resolve_values(current_id: str) -> tuple[dict[str, Any], dict[str, str]]:
            if current_id in resolving:
                raise RuntimeError(f"INVALID_PARAMETER_SET: inheritance cycle at {current_id}")
            definition = definitions.get(current_id)
            if definition is None:
                raise RuntimeError(f"UNKNOWN_PARAMETER_SET: {current_id}")
            resolving.add(current_id)
            if definition.inherits is None:
                values, provenance = deepcopy(baseline), {}
            else:
                values, provenance = resolve_values(definition.inherits)
            for dotted, value in definition.overrides.items():
                parts = dotted.split(".")
                target: dict[str, Any] = values
                for part in parts[:-1]:
                    nested = target.get(part)
                    if not isinstance(nested, dict):
                        raise RuntimeError(f"INVALID_PARAMETER_SET: unknown override {dotted}")
                    target = nested
                if parts[-1] not in target:
                    raise RuntimeError(f"INVALID_PARAMETER_SET: unknown override {dotted}")
                target[parts[-1]] = value
                provenance[dotted] = current_id
            resolving.remove(current_id)
            return values, provenance

        try:
            values, provenance = resolve_values(selected)
            parameters = ScalpingV2Parameters.model_validate(values)
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"INVALID_PARAMETER_SET: {selected}") from exc
        definition = definitions[selected]
        return ResolvedParameterSet(
            id=definition.id, label=definition.label, version=definition.version,
            parameters=parameters,
            resolved_config_hash=self._semantic_hash(parameters),
            activation_cycle_boundary_ms=self.scalping_v2.paper.activation_cycle_boundary_ms,
            activation_revision=self.scalping_v2.paper.activation_revision,
            previous_parameter_set=self.scalping_v2.paper.previous_parameter_set,
            switched_at_utc=self.scalping_v2.paper.switched_at_utc,
            provenance=provenance,
        )

    def resolve_scalping_v2_for_cycle(self, cycle_boundary_ms: int) -> ResolvedParameterSet:
        """Resolve one immutable cycle snapshot at the documented activation cutoff."""
        selector = self.scalping_v2.paper
        selected = (
            selector.previous_parameter_set
            if int(cycle_boundary_ms) < selector.activation_cycle_boundary_ms
            else selector.active_parameter_set
        )
        return self.resolve_scalping_v2_parameter_set(selected)

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
        profile = raw["profiles"]["trade-5m-v2"]
        if "risk" in profile:
            raise RuntimeError("duplicate risk authority in trade_parameters.yaml")
        profile["risk"] = RISK_POLICY.profiles["trade-5m-v2"].model_dump(mode="python")
        for definition in raw["scalping_v2"]["parameter_sets"].values():
            set_id = definition["id"]
            risk = RISK_POLICY.parameter_sets.get(set_id)
            if risk is not None:
                for key, value in risk.overrides.items():
                    dotted = f"risk.{key}"
                    if dotted in definition["overrides"]:
                        raise RuntimeError(f"duplicate authority for {dotted}")
                    definition["overrides"][dotted] = value
        return TradeParameters.model_validate(raw)
    except RuntimeError as exc:
        if str(exc).startswith(("UNKNOWN_PARAMETER_SET", "INVALID_PARAMETER_SET")):
            raise
        raise RuntimeError(f"invalid authoritative trade parameters: {path}") from exc
    except Exception as exc:
        raise RuntimeError(f"invalid authoritative trade parameters: {path}") from exc


TRADE_PARAMETERS = load_trade_parameters()
ACTIVE_SCALPING_V2_PARAMETER_SET = TRADE_PARAMETERS.resolve_scalping_v2_parameter_set()
SCALPING_V2 = ACTIVE_SCALPING_V2_PARAMETER_SET.parameters


__all__ = (
    "ACTIVE_SCALPING_V2_PARAMETER_SET", "CONFIG_PATH", "ResolvedParameterSet",
    "SCALPING_V2", "TRADE_PARAMETERS", "TradeParameters", "load_trade_parameters",
)
