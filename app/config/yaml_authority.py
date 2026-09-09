"""Typed, fail-closed loaders for the non-trading YAML authority domains."""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
import yaml


ROOT = Path(__file__).resolve().parents[2]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RiskValues(StrictModel):
    risk_per_trade_bps: float = Field(gt=0)
    max_open_positions: int = Field(gt=0)
    max_new_commands_per_cycle: int = Field(gt=0)
    total_open_risk_limit_bps: float = Field(gt=0)


class RiskSet(StrictModel):
    inherits: str | None
    overrides: dict[str, float | int]


class RiskPolicy(StrictModel):
    schema_version: Literal[1]
    config_version: str
    profiles: dict[str, RiskValues]
    parameter_sets: dict[str, RiskSet]

    def resolve(self, profile_id: str, parameter_set_id: str) -> RiskValues:
        try:
            values = self.profiles[profile_id].model_dump()
        except KeyError as exc:
            raise RuntimeError(f"missing risk profile: {profile_id}") from exc
        visiting: set[str] = set()

        def apply(set_id: str) -> None:
            if set_id in visiting:
                raise RuntimeError(f"risk policy inheritance cycle: {set_id}")
            try:
                definition = self.parameter_sets[set_id]
            except KeyError as exc:
                raise RuntimeError(f"missing risk parameter set: {set_id}") from exc
            visiting.add(set_id)
            if definition.inherits is not None:
                apply(definition.inherits)
            for key, value in definition.overrides.items():
                if key not in values:
                    raise RuntimeError(f"unknown risk override: {key}")
                values[key] = value
            visiting.remove(set_id)

        apply(parameter_set_id)
        return RiskValues.model_validate(values)


class RuntimeProfile(StrictModel):
    enabled: bool
    trade_mode: Literal["TRADE_15M", "SCALPING"]
    display_i18n_key: str
    trigger_timeframe: Literal["5m", "15m"]
    entry_timeframes: tuple[str, ...]
    context_timeframes: tuple[str, ...]
    market_data_windows: dict[str, int] | None = None
    book_depth_limit: int | None = Field(default=None, gt=0)
    microstructure_max_age_ms: int | None = Field(default=None, gt=0)
    vwap_reference_notional: float | None = Field(default=None, gt=0)
    mode: Literal["PRODUCTION_SEARCH", "SHADOW_SEARCH"]
    analysis_history_candles: int | None = Field(default=None, gt=0)
    atr_lookback_candles: int | None = Field(default=None, gt=0)
    impulse_lookback_candles: int | None = Field(default=None, gt=0)
    structure_lookback_candles: int | None = Field(default=None, gt=0)
    confirmation_window_candles: int | None = Field(default=None, gt=0)
    volume_baseline_candles: int | None = Field(default=None, gt=0)
    regime_lookback_candles: int | None = Field(default=None, gt=0)
    analysis_decision_candles: int | None = Field(default=None, gt=0)
    breakout_volume_baseline_candles: int | None = Field(default=None, gt=0)
    impulse_absolute_threshold_pct: float | None = Field(default=None, gt=0)
    impulse_atr_multiplier: float | None = Field(default=None, gt=0)
    validity_boundaries: int | None = Field(default=None, gt=0)
    minimum_planned_rr: float | None = Field(default=None, gt=0)
    cost_safety_margin_bps: float | None = Field(default=None, ge=0)
    paper_command_creation_enabled: bool
    position_opening_enabled: bool


class RuntimeParameters(StrictModel):
    contract_version: str
    analysis_compression_ratio: float = Field(gt=0, lt=1)
    analysis_expansion_ratio: float = Field(gt=1)
    scalping_setup_families: tuple[str, ...]
    strategy_shadow_thresholds: tuple[float, ...]
    strategy_not_evaluated_handling: str
    geometry_atr_buffer_shadow_cohorts: tuple[float, ...]
    geometry_stop_envelope_shadow_cohorts_bps: tuple[float, ...]
    geometry_minimum_target_shadow_cohorts_bps: tuple[float, ...]
    economics_minimum_net_edge_shadow_cohorts_bps: tuple[float, ...]
    rr_shadow_cohorts: tuple[float, ...]
    risk_per_trade_shadow_cohorts_bps: tuple[float, ...]
    portfolio_max_concurrent_shadow_cohorts: tuple[int, ...]
    portfolio_total_open_risk_shadow_cohorts_bps: tuple[float, ...]
    execution_entry_ttl_shadow_cohorts_seconds: tuple[int, ...]
    exit_time_stop_shadow_cohorts_minutes: tuple[int, ...]
    exit_adaptive_rules_production_enabled: bool
    setup_policy_id: str
    strategy_policy_id: str
    strategy_minimum_allowed_quality: str
    risk_shadow_policy_id: str
    risk_minimum_strategy_quality: str
    stop_policy_id: str


class OrchestratorPolicy(StrictModel):
    symbols: tuple[str, ...]
    poll_interval_seconds: float = Field(gt=0)
    health_report_interval_seconds: float = Field(gt=0)
    health_report_path: str
    max_catchup_windows: int = Field(gt=0)
    process_latest_only: bool
    require_all_timeframes_ok: bool
    allow_stale_higher_timeframes: bool
    trigger_source: str
    initial_backoff_seconds: float = Field(gt=0)
    max_backoff_seconds: float = Field(gt=0)
    freshness_retry_interval_seconds: float = Field(gt=0)
    freshness_grace_seconds: float = Field(gt=0)
    freshness_max_attempts: int = Field(gt=0)
    waiting_batch_size: int = Field(gt=0)


class CollectorPolicy(StrictModel):
    output_directory: str
    parameter_set_id: str
    schema_revision: str
    initial_boundary_ms: int = Field(ge=0)
    outcome_ttl_ms: int = Field(gt=0)
    outcome_time_stop_ms: int = Field(gt=0)
    poll_seconds: float = Field(gt=0)
    boundary_wait_seconds: int = Field(gt=0)
    max_part_bytes: int = Field(gt=0)


class RuntimePolicy(StrictModel):
    schema_version: Literal[1]
    config_version: str
    active_profile: str
    profiles: dict[str, RuntimeProfile]
    runtime_parameters: RuntimeParameters
    orchestrator: OrchestratorPolicy
    collector: CollectorPolicy

    @model_validator(mode="after")
    def active_is_enabled(self):
        if self.active_profile not in self.profiles or not self.profiles[self.active_profile].enabled:
            raise ValueError("active runtime profile must exist and be enabled")
        return self


class ResearchSearchPolicy(StrictModel):
    strategy: Literal["auto", "exhaustive", "bounded"]
    seed: int
    exhaustive_max_configs: int = Field(gt=0)
    max_evaluated_configs: int = Field(gt=0)
    batch_size: int = Field(gt=0)
    stage1_fraction: float = Field(ge=0, le=1)
    stage2_fraction: float = Field(ge=0, le=1)
    stage3_fraction: float = Field(ge=0, le=1)
    max_configs_per_observation: int = Field(gt=0)
    minimum_validation_sample: int = Field(gt=0)
    minimum_holdout_sample: int = Field(gt=0)
    max_active_batch_memory_mb: float = Field(gt=0)
    bytes_per_active_config: int = Field(gt=0)
    starting_balance: float = Field(gt=0)

    @model_validator(mode="after")
    def fractions_sum_to_one(self):
        if abs(self.stage1_fraction + self.stage2_fraction + self.stage3_fraction - 1.0) > 1e-9:
            raise ValueError("research stage fractions must sum to one")
        return self


class ResearchDataset(StrictModel):
    source: str
    profile: Literal["trade-5m-v2"]
    closed_only: Literal[False]
    max_rows: int = Field(gt=0)


class ArtifactWriterPolicy(StrictModel):
    retry_delays_seconds: tuple[float, ...]


class ResearchParameters(StrictModel):
    schema_version: Literal[2]
    seed: int
    search: ResearchSearchPolicy
    dataset: ResearchDataset
    output_root: str
    minimum_samples: dict[str, int]
    artifact_writer: ArtifactWriterPolicy
    search_space: dict[str, list[float | int | bool | None]]


class UnitConstants(StrictModel):
    schema_version: Literal[1]
    config_version: str
    milliseconds_per_second: int = Field(gt=0)
    seconds_per_minute: int = Field(gt=0)
    basis_points_per_percent: float = Field(gt=0)
    percent_fraction_scale: float = Field(gt=0)


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f"duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def _load(path: Path, model: type[StrictModel]) -> Any:
    try:
        raw = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
        return model.model_validate(raw)
    except Exception as exc:
        raise RuntimeError(f"invalid authoritative YAML: {path}") from exc


RISK_PATH = Path(os.environ.get("TRADERS_RISK_POLICY_PATH", ROOT / "config/trading/risk_policy.yaml"))
RUNTIME_PATH = Path(os.environ.get("TRADERS_RUNTIME_POLICY_PATH", ROOT / "config/runtime/runtime_policy.yaml"))
RESEARCH_PATH = Path(os.environ.get("TRADERS_RESEARCH_PARAMETERS_PATH", ROOT / "config/research/research_parameters.yaml"))
UNIT_PATH = Path(os.environ.get("TRADERS_UNIT_CONSTANTS_PATH", ROOT / "config/system/unit_constants.yaml"))

RISK_POLICY = _load(RISK_PATH, RiskPolicy)
RUNTIME_POLICY = _load(RUNTIME_PATH, RuntimePolicy)
RESEARCH_PARAMETERS = _load(RESEARCH_PATH, ResearchParameters)
UNIT_CONSTANTS = _load(UNIT_PATH, UnitConstants)


def authority_hash(extra: dict[str, Any] | None = None) -> str:
    payload = {
        "risk": RISK_POLICY.model_dump(mode="json"),
        "runtime": RUNTIME_POLICY.model_dump(mode="json"),
        "research": RESEARCH_PARAMETERS.model_dump(mode="json"),
        "units": UNIT_CONSTANTS.model_dump(mode="json"),
        "extra": extra or {},
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


__all__ = (
    "RESEARCH_PARAMETERS", "RESEARCH_PATH", "RISK_PATH", "RISK_POLICY",
    "RUNTIME_PATH", "RUNTIME_POLICY", "UNIT_CONSTANTS", "UNIT_PATH", "authority_hash",
)
