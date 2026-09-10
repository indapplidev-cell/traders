"""Typed, fail-closed loaders for the non-trading YAML authority domains."""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
import yaml


def _project_root() -> Path:
    explicit = os.environ.get("TRADERS_CONFIG_ROOT")
    if explicit:
        return Path(explicit)
    candidates = (Path.cwd(), Path(__file__).resolve().parents[2])
    return next((path for path in candidates if (path / "config").is_dir()), candidates[-1])


ROOT = _project_root()


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


class AnalysisAlgorithmPolicy(StrictModel):
    morphology_doji_body_to_range_max: float = Field(ge=0, le=1)
    morphology_spinning_top_body_to_range_max: float = Field(ge=0, le=1)
    morphology_small_body_to_range_max: float = Field(ge=0, le=1)
    morphology_large_body_to_range_min: float = Field(ge=0, le=1)
    morphology_strong_body_to_range_min: float = Field(ge=0, le=1)
    morphology_extended_shadow_to_range_min: float = Field(ge=0, le=1)
    morphology_near_high_threshold: float = Field(ge=0, le=1)
    morphology_near_low_threshold: float = Field(ge=0, le=1)
    nison_shadow_to_body_shape_min: float = Field(gt=0)
    nison_opposite_shadow_to_range_max: float = Field(ge=0, le=1)
    nison_hammer_body_position_min: float = Field(ge=0, le=1)
    nison_star_body_position_max: float = Field(ge=0, le=1)
    altunina_structure_tolerance_ratio: float = Field(gt=0, lt=1)
    altunina_fibonacci_pullback_levels: tuple[float, ...]
    altunina_correction_limit: float = Field(gt=0, lt=1)
    regime_min_score: float = Field(ge=0, le=1)
    regime_min_score_margin: float = Field(ge=0, le=1)
    schwager_zone_cluster_tolerance_ratio: float = Field(gt=0, lt=1)
    schwager_min_zone_touches: int = Field(gt=0)
    schwager_min_range_touches: int = Field(gt=0)
    schwager_min_inside_close_ratio: float = Field(ge=0, le=1)
    schwager_min_range_width_ratio: float = Field(gt=0, lt=1)
    schwager_max_range_width_ratio: float = Field(gt=0, lt=1)
    schwager_breakout_buffer_ratio: float = Field(gt=0, lt=1)
    schwager_follow_through_lookahead: int = Field(gt=0)
    schwager_false_breakout_lookahead: int = Field(gt=0)
    schwager_retest_lookahead: int = Field(gt=0)
    schwager_min_range_duration: int = Field(gt=0)
    schwager_min_boundary_alternations: int = Field(gt=0)
    schwager_min_confirmation_closes: int = Field(gt=0)
    schwager_breakout_confirmation_distance_ratio: float = Field(gt=0, lt=1)
    schwager_false_breakout_time_lookahead: int = Field(gt=0)
    schwager_retest_departure_ratio: float = Field(gt=0, lt=1)


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


class WalAckDaemonPolicy(StrictModel):
    interval_seconds: int = Field(gt=0)
    minimum_interval_seconds: int = Field(gt=0)
    maximum_interval_seconds: int = Field(gt=0)
    cycle_work_seconds: float = Field(gt=0)
    settle_poll_seconds: float = Field(gt=0)
    state_write_attempts: int = Field(gt=0)
    state_write_retry_seconds: float = Field(ge=0)


class PaperReadinessPolicy(StrictModel):
    minimum_pitr_window_seconds: int = Field(gt=0)
    wal_daemon_max_age_seconds: float = Field(gt=0)
    artifact_future_skew_tolerance_seconds: float = Field(ge=0)
    market_health_max_age_seconds: int = Field(gt=0)


class RuntimePolicy(StrictModel):
    schema_version: Literal[1]
    config_version: str
    active_profile: str
    profiles: dict[str, RuntimeProfile]
    runtime_parameters: RuntimeParameters
    analysis_algorithms: AnalysisAlgorithmPolicy
    orchestrator: OrchestratorPolicy
    collector: CollectorPolicy
    wal_ack_daemon: WalAckDaemonPolicy
    paper_readiness: PaperReadinessPolicy

    @model_validator(mode="after")
    def active_is_enabled(self):
        if self.active_profile not in self.profiles or not self.profiles[self.active_profile].enabled:
            raise ValueError("active runtime profile must exist and be enabled")
        for profile_id, profile in self.profiles.items():
            if profile.trade_mode == "SCALPING" and profile.trigger_timeframe != "5m":
                raise ValueError(f"scalping profile cannot fall back to 15m: {profile_id}")
        return self


class ResearchSearchPolicy(StrictModel):
    strategy: Literal["auto", "exhaustive", "bounded", "targeted"]
    seed: int
    exhaustive_max_configs: int = Field(gt=0)
    max_evaluated_configs: int = Field(gt=0)
    max_total_configs: int = Field(gt=0)
    max_concurrent_evaluations: int = Field(gt=0)
    batch_size: int = Field(gt=0)
    checkpoint_cadence: int = Field(gt=0)
    stage_budgets: dict[str, int]
    max_configs_per_observation: int = Field(gt=0)
    minimum_validation_sample: int = Field(gt=0)
    minimum_holdout_sample: int = Field(gt=0)
    max_active_batch_memory_mb: float = Field(gt=0)
    bytes_per_active_config: int = Field(gt=0)
    starting_balance: float = Field(gt=0)

    @model_validator(mode="after")
    def stage_budget_is_bounded(self):
        if any(value < 0 for value in self.stage_budgets.values()):
            raise ValueError("research stage budgets must be non-negative")
        if sum(self.stage_budgets.values()) > self.max_total_configs:
            raise ValueError("research stage budgets exceed max_total_configs")
        return self


class ResearchDataset(StrictModel):
    source: str
    profile: Literal["trade-5m-v2"]
    closed_only: Literal[False]
    max_rows: int = Field(gt=0)


class ArtifactWriterPolicy(StrictModel):
    retry_delays_seconds: tuple[float, ...]


class ResearchArtifactPolicy(StrictModel):
    schema_version: Literal[2]
    top_config_count: int = Field(gt=0)
    finalist_config_count: int = Field(gt=0)
    max_detailed_trades_per_config: int = Field(gt=0)
    soft_total_bytes: int = Field(gt=0)
    hard_total_bytes: int = Field(gt=0)
    soft_results_bytes: int = Field(gt=0)
    hard_results_bytes: int = Field(gt=0)


class ResearchRankingPolicy(StrictModel):
    minimum_trades: int = Field(gt=0)
    minimum_symbol_coverage: int = Field(gt=0)
    minimum_independent_periods: int = Field(gt=0)
    validation_minimum_trades: int = Field(gt=0)
    selection_bias_hypotheses_per_observation: float = Field(gt=0)
    promising_min_expectancy_r: float
    promising_min_profit_factor: float = Field(gt=0)
    validation_candidate_min_stability: float = Field(ge=0, le=1)


class ResearchCalibrationPolicy(StrictModel):
    baseline_set_id: Literal["scalping-v2-set-2"]
    targeted_families: tuple[str, ...]
    frozen_families: tuple[str, ...]
    parameter_families: dict[str, tuple[str, ...]]


class ResearchParameters(StrictModel):
    schema_version: Literal[2]
    seed: int
    search: ResearchSearchPolicy
    dataset: ResearchDataset
    output_root: str
    minimum_samples: dict[str, int]
    artifact: ResearchArtifactPolicy
    ranking: ResearchRankingPolicy
    calibration: ResearchCalibrationPolicy
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
