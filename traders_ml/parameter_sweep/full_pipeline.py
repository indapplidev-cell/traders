"""Full-chain, LONG-only scalping calibration contracts and safety gates.

This module is the control plane for the causal production-component replay.  It
does not contain a second trading strategy and never mutates production state.
The existing historical reconstruction, PipelineRunner and PAPER lifecycle are
the only permitted decision/execution implementations.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Literal, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import text

from .engine import ReadOnlyResearchDatabase, resolve_database_binding


CONTRACT_VERSION = "full-pipeline-calibration/1"
REGISTRY_VERSION = "full-pipeline-stage-parameter-registry/1"
TRACE_VERSION = "full-pipeline-decision-trace/1"
TRADE_VERSION = "full-pipeline-trade-evaluation/1"
CANDIDATE_VERSION = "full-pipeline-candidate/1"
CANARY_VERSION = "full-pipeline-paper-canary/1"
DATASET_VERSION = "full-pipeline-frozen-dataset/1"

STAGES = (
    "ANALYSIS", "STRUCTURAL_SETUP", "STRATEGY_ADMISSION",
    "RISK_COMPATIBILITY", "GEOMETRY", "TARGET", "COSTS", "RR",
    "FINAL_RISK", "PORTFOLIO", "APPROVAL", "PAPER_PLAN", "FILL",
    "POSITION_MANAGEMENT", "EXIT", "ACCOUNTING",
)


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


def fingerprint(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(payload.encode("utf-8")).hexdigest()


class TimeWindow(Contract):
    name: str = Field(min_length=1)
    role: Literal["TRAIN", "VALIDATION", "INTERNAL_HOLDOUT", "EXTERNAL_HOLDOUT"]
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    locked: bool = False

    @model_validator(mode="after")
    def ordered(self) -> "TimeWindow":
        if self.start_ms >= self.end_ms:
            raise ValueError("window start must precede end")
        return self


class SearchBudget(Contract):
    one_factor: int = Field(default=200, gt=0)
    per_block: int = Field(default=1000, gt=0)
    joint: int = Field(default=5000, gt=0)
    local_refinement: int = Field(default=1000, gt=0)
    maximum_rounds: int = Field(default=5, ge=1, le=5)
    worker_count: Literal[1] = 1


class AcceptanceGates(Contract):
    minimum_closed_trades: int = Field(default=300, gt=0)
    minimum_independent_days: int = Field(default=10, gt=0)
    minimum_symbols: int = Field(default=10, gt=0, le=20)
    minimum_net_expectancy_bps: float = Field(default=8.0, gt=0)
    minimum_profit_factor: float = Field(default=1.20, gt=1)
    minimum_win_rate_exclusive: float = Field(default=0.50, ge=0, lt=1)
    maximum_drawdown_fraction: float = Field(default=0.05, gt=0, le=1)
    maximum_symbol_profit_share: float = Field(default=0.20, gt=0, le=1)
    maximum_day_profit_share: float = Field(default=0.25, gt=0, le=1)
    minimum_profitable_walk_forward_folds: int = Field(default=3, ge=1, le=4)
    stress_cost_multiplier: float = Field(default=1.25, ge=1)
    minimum_stress_profit_factor: float = Field(default=1.0, ge=1)


class FullPipelineCalibrationRequestV1(Contract):
    version: Literal["full-pipeline-calibration/1"] = CONTRACT_VERSION
    symbols: tuple[str, ...]
    direction: Literal["LONG"] = "LONG"
    data_start_ms: int = Field(ge=0)
    data_end_ms: int = Field(gt=0)
    windows: tuple[TimeWindow, ...]
    seed: int = Field(default=20261102, ge=0)
    initial_equity: float = Field(default=1000.0, gt=0)
    search: SearchBudget = Field(default_factory=SearchBudget)
    gates: AcceptanceGates = Field(default_factory=AcceptanceGates)
    maximum_regime_sets: int = Field(default=3, ge=1, le=3)
    automatic_paper_canary: Literal[True] = True
    live_allowed: Literal[False] = False

    @model_validator(mode="after")
    def valid_request(self) -> "FullPipelineCalibrationRequestV1":
        normalized = tuple(sorted(str(symbol).upper() for symbol in self.symbols))
        if len(normalized) != 20 or len(set(normalized)) != 20:
            raise ValueError("exactly 20 unique symbols are required")
        if self.data_start_ms >= self.data_end_ms:
            raise ValueError("invalid dataset period")
        if not self.windows:
            raise ValueError("walk-forward windows are required")
        for window in self.windows:
            if window.start_ms < self.data_start_ms or window.end_ms > self.data_end_ms:
                if window.role != "EXTERNAL_HOLDOUT":
                    raise ValueError("window outside dataset period")
        internal = [window for window in self.windows if window.role == "INTERNAL_HOLDOUT"]
        external = [window for window in self.windows if window.role == "EXTERNAL_HOLDOUT"]
        if len(internal) != 1 or not internal[0].locked:
            raise ValueError("one locked internal holdout is required")
        if len(external) != 1 or not external[0].locked:
            raise ValueError("one locked external holdout is required")
        object.__setattr__(self, "symbols", normalized)
        return self

    @property
    def identity(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


class FullPipelineCalibrationRequestV2(Contract):
    """Calibration request for symbols with different causal history depths."""

    version: Literal["full-pipeline-calibration/2"] = "full-pipeline-calibration/2"
    symbols: tuple[str, ...]
    direction: Literal["LONG"] = "LONG"
    data_start_ms: int = Field(ge=0)
    data_end_ms: int = Field(gt=0)
    windows: tuple[TimeWindow, ...]
    warmup_bars: dict[str, int] = Field(
        default_factory=lambda: {"1m": 60, "5m": 120, "15m": 64, "1h": 50}
    )
    minimum_segment_bars_5m: int = Field(default=12, ge=1)
    seed: int = Field(default=20261102, ge=0)
    initial_equity: float = Field(default=1000.0, gt=0)
    search: SearchBudget = Field(default_factory=SearchBudget)
    gates: AcceptanceGates = Field(default_factory=AcceptanceGates)
    maximum_regime_sets: int = Field(default=3, ge=1, le=3)
    maximum_no_improvement_rounds: int = Field(default=3, ge=1, le=10)
    automatic_paper_canary: Literal[True] = True
    live_allowed: Literal[False] = False

    @model_validator(mode="after")
    def valid_request(self) -> "FullPipelineCalibrationRequestV2":
        normalized = tuple(sorted(str(symbol).upper() for symbol in self.symbols))
        if len(normalized) != 20 or len(set(normalized)) != 20:
            raise ValueError("exactly 20 unique symbols are required")
        if self.data_start_ms >= self.data_end_ms:
            raise ValueError("invalid dataset period")
        if set(self.warmup_bars) != {"1m", "5m", "15m", "1h"}:
            raise ValueError("warmup bars required for 1m/5m/15m/1h")
        if any(value <= 0 for value in self.warmup_bars.values()):
            raise ValueError("warmup bars must be positive")
        internal = [window for window in self.windows if window.role == "INTERNAL_HOLDOUT"]
        external = [window for window in self.windows if window.role == "EXTERNAL_HOLDOUT"]
        if len(internal) != 1 or not internal[0].locked:
            raise ValueError("one locked internal holdout is required")
        if len(external) != 1 or not external[0].locked:
            raise ValueError("one locked external holdout is required")
        non_external = sorted(
            (window for window in self.windows if window.role != "EXTERNAL_HOLDOUT"),
            key=lambda item: (item.start_ms, item.end_ms, item.name),
        )
        if any(window.start_ms < self.data_start_ms or window.end_ms > self.data_end_ms
               for window in non_external):
            raise ValueError("non-external window outside dataset period")
        validation = [window for window in self.windows if window.role == "VALIDATION"]
        if not validation:
            raise ValueError("at least one validation window is required")
        object.__setattr__(self, "symbols", normalized)
        return self

    @property
    def identity(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


class CoverageSegmentV2(Contract):
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    rows_5m: int = Field(ge=0)

    @model_validator(mode="after")
    def ordered(self) -> "CoverageSegmentV2":
        if self.end_ms <= self.start_ms:
            raise ValueError("coverage segment end must follow start")
        return self


class SymbolCoverageV2(Contract):
    symbol: str = Field(min_length=3)
    status: Literal["USABLE", "PARTIAL_COVERAGE", "UNUSABLE"]
    available_start_ms: int | None = None
    available_end_ms: int | None = None
    usable_start_ms: int | None = None
    usable_end_ms: int | None = None
    segments: tuple[CoverageSegmentV2, ...] = ()
    timeframe_inventory: dict[str, dict[str, Any]] = Field(default_factory=dict)
    fold_participation: dict[str, bool] = Field(default_factory=dict)
    reasons: tuple[str, ...] = ()


class RaggedDatasetManifestV2(Contract):
    version: Literal["ragged-full-pipeline-dataset/2"] = "ragged-full-pipeline-dataset/2"
    request_hash: str = Field(min_length=64, max_length=64)
    registry_hash: str = Field(min_length=64, max_length=64)
    dataset_hash: str = Field(min_length=64, max_length=64)
    status: Literal["FROZEN", "BLOCKED_DATA"]
    symbols: tuple[SymbolCoverageV2, ...]
    usable_symbol_count: int = Field(ge=0, le=20)
    partial_symbol_count: int = Field(ge=0, le=20)
    historical_cost_evidence: dict[str, Any]
    cost_model_hash: str = Field(min_length=64, max_length=64)
    blocked_reasons: tuple[str, ...] = ()
    closed_only_required: Literal[True] = True
    production_mutations: Literal[0] = 0


class StageParameterDomain(Contract):
    name: str = Field(min_length=1)
    stage: Literal[
        "ANALYSIS", "STRUCTURAL_SETUP", "STRATEGY_ADMISSION",
        "RISK_COMPATIBILITY", "GEOMETRY", "TARGET", "COSTS", "RR",
        "FINAL_RISK", "PORTFOLIO", "APPROVAL", "PAPER_PLAN", "FILL",
        "POSITION_MANAGEMENT", "EXIT", "ACCOUNTING",
    ]
    family: str = Field(min_length=1)
    value_type: Literal["FLOAT", "INTEGER", "BOOLEAN", "WEIGHT_SIMPLEX", "DATA_DRIVEN"]
    values: tuple[Any, ...] = ()
    lower: float | None = None
    upper: float | None = None
    invariant: str = Field(min_length=1)
    source: str = Field(min_length=1)
    safety_critical: bool = False
    immutable: bool = False

    @model_validator(mode="after")
    def valid_domain(self) -> "StageParameterDomain":
        if self.immutable and self.values:
            raise ValueError("immutable parameters cannot declare a search domain")
        if not self.immutable and self.value_type != "DATA_DRIVEN" and not self.values:
            raise ValueError("searchable parameters require values")
        return self


class StageParameterRegistryV1(Contract):
    version: Literal["full-pipeline-stage-parameter-registry/1"] = REGISTRY_VERSION
    parameters: tuple[StageParameterDomain, ...]

    @model_validator(mode="after")
    def unique(self) -> "StageParameterRegistryV1":
        names = [item.name for item in self.parameters]
        if len(names) != len(set(names)):
            raise ValueError("duplicate parameter registry name")
        return self

    @property
    def identity(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


class StageDecision(Contract):
    stage: Literal[
        "ANALYSIS", "STRUCTURAL_SETUP", "STRATEGY_ADMISSION",
        "RISK_COMPATIBILITY", "GEOMETRY", "TARGET", "COSTS", "RR",
        "FINAL_RISK", "PORTFOLIO", "APPROVAL", "PAPER_PLAN", "FILL",
        "POSITION_MANAGEMENT", "EXIT", "ACCOUNTING",
    ]
    passed: bool
    reason: str = Field(min_length=1)
    score: float | None = None
    threshold: float | None = None
    parameter_snapshot: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)


class PipelineDecisionTraceV1(Contract):
    version: Literal["full-pipeline-decision-trace/1"] = TRACE_VERSION
    trace_id: str = Field(min_length=1)
    configuration_hash: str = Field(min_length=64, max_length=64)
    dataset_hash: str = Field(min_length=64, max_length=64)
    symbol: str = Field(min_length=3)
    boundary_ms: int = Field(ge=0)
    direction: Literal["LONG"] = "LONG"
    decisions: tuple[StageDecision, ...]
    terminal_stage: str = Field(min_length=1)
    future_bars_used: Literal[False] = False

    @model_validator(mode="after")
    def chronological_stages(self) -> "PipelineDecisionTraceV1":
        names = tuple(item.stage for item in self.decisions)
        positions = [STAGES.index(name) for name in names]
        if positions != sorted(set(positions)):
            raise ValueError("stage decisions must be unique and chronological")
        if self.terminal_stage not in STAGES:
            raise ValueError("unknown terminal stage")
        first_failure = next((item.stage for item in self.decisions if not item.passed), None)
        if first_failure is not None and self.terminal_stage != first_failure:
            raise ValueError("terminal stage must be the first failed stage")
        return self


class EndToEndTradeEvaluationV1(Contract):
    version: Literal["full-pipeline-trade-evaluation/1"] = TRADE_VERSION
    trade_id: str = Field(min_length=1)
    configuration_hash: str = Field(min_length=64, max_length=64)
    symbol: str = Field(min_length=3)
    setup_family: str = Field(min_length=1)
    regime: str = Field(min_length=1)
    entry_boundary_ms: int = Field(ge=0)
    exit_boundary_ms: int = Field(gt=0)
    entry_price: float = Field(gt=0)
    exit_price: float = Field(gt=0)
    quantity: float = Field(gt=0)
    gross_pnl: float
    fees: float = Field(ge=0)
    spread_cost: float = Field(ge=0)
    slippage_cost: float = Field(ge=0)
    reserve_cost: float = Field(ge=0)
    net_pnl: float
    net_pnl_bps: float
    risk_r: float
    exit_reason: str = Field(min_length=1)
    future_bars_used: Literal[False] = False

    @model_validator(mode="after")
    def accounting(self) -> "EndToEndTradeEvaluationV1":
        expected = self.gross_pnl - self.fees - self.spread_cost - self.slippage_cost - self.reserve_cost
        tolerance = max(1e-9, abs(expected) * 1e-9)
        if abs(expected - self.net_pnl) > tolerance:
            raise ValueError("trade accounting identity failed")
        if self.exit_boundary_ms <= self.entry_boundary_ms:
            raise ValueError("exit must follow entry")
        return self


class CandidateMetrics(Contract):
    closed_trades: int = Field(ge=0)
    independent_days: int = Field(ge=0)
    symbols: int = Field(ge=0)
    net_pnl: float
    expectancy_bps: float
    profit_factor: float
    win_rate: float = Field(ge=0, le=1)
    max_drawdown_fraction: float = Field(ge=0)
    maximum_symbol_profit_share: float = Field(ge=0, le=1)
    maximum_day_profit_share: float = Field(ge=0, le=1)
    profitable_walk_forward_folds: int = Field(ge=0, le=4)
    stress_net_pnl: float
    stress_profit_factor: float
    baseline_max_drawdown_fraction: float = Field(ge=0)
    neighbor_stability_pass: bool


class FullPipelineCandidateV1(Contract):
    version: Literal["full-pipeline-candidate/1"] = CANDIDATE_VERSION
    candidate_id: str = Field(min_length=1)
    request_hash: str = Field(min_length=64, max_length=64)
    dataset_hash: str = Field(min_length=64, max_length=64)
    registry_hash: str = Field(min_length=64, max_length=64)
    configuration_hash: str = Field(min_length=64, max_length=64)
    seed: int = Field(ge=0)
    parameters: dict[str, Any]
    metrics: CandidateMetrics
    gate_results: dict[str, bool]
    status: Literal["ELIGIBLE", "NO_ELIGIBLE_CANDIDATE"]
    paper_active: Literal[False] = False
    live_active: Literal[False] = False

    @model_validator(mode="after")
    def status_matches_gates(self) -> "FullPipelineCandidateV1":
        eligible = bool(self.gate_results) and all(self.gate_results.values())
        if eligible != (self.status == "ELIGIBLE"):
            raise ValueError("candidate status does not match gates")
        return self


class PaperCanaryManifestV1(Contract):
    version: Literal["full-pipeline-paper-canary/1"] = CANARY_VERSION
    candidate_id: str = Field(min_length=1)
    candidate_hash: str = Field(min_length=64, max_length=64)
    rollback_parameter_set: str = Field(min_length=1)
    shadow_hours: Literal[24] = 24
    first_command_limit: Literal[1] = 1
    bounded_command_limit: Literal[20] = 20
    qualification_minimum_closed_trades: Literal[50] = 50
    qualification_minimum_days: Literal[7] = 7
    qualification_maximum_days: Literal[14] = 14
    maximum_canary_drawdown_fraction: Literal[0.01] = 0.01
    minimum_rolling_profit_factor: Literal[0.8] = 0.8
    live_allowed: Literal[False] = False
    activation_status: Literal["BLOCKED_PENDING_ELIGIBILITY", "READY_FOR_PAPER_CANARY"]


def default_registry() -> StageParameterRegistryV1:
    def domain(name: str, stage: str, family: str, values: Sequence[Any], invariant: str,
               source: str, *, value_type: str = "FLOAT", safety: bool = False) -> StageParameterDomain:
        return StageParameterDomain(
            name=name, stage=stage, family=family, value_type=value_type,
            values=tuple(values), invariant=invariant, source=source,
            safety_critical=safety,
        )

    items: list[StageParameterDomain] = [
        domain("analysis.graphical_weights", "ANALYSIS", "ANALYSIS", (5,), "simplex_sum=100,max_component=45", "independent-expert", value_type="WEIGHT_SIMPLEX"),
        domain("analysis.technical_weights", "ANALYSIS", "ANALYSIS", (7,), "simplex_sum=100,max_component=45", "independent-expert", value_type="WEIGHT_SIMPLEX"),
        domain("analysis.lookbacks", "ANALYSIS", "ANALYSIS", (), "baseline+q10/q25/q50/q75/q90,max_points=7", "data-driven-range-generator", value_type="DATA_DRIVEN"),
        domain("analysis.altunina", "ANALYSIS", "ANALYSIS", (), "causal_closed_candles_only,max_points=7", "runtime-policy.analysis_algorithms", value_type="DATA_DRIVEN"),
        domain("analysis.schwager", "ANALYSIS", "ANALYSIS", (), "causal_closed_candles_only,max_points=7", "runtime-policy.analysis_algorithms", value_type="DATA_DRIVEN"),
        domain("analysis.nison", "ANALYSIS", "ANALYSIS", (), "causal_closed_candles_only,max_points=7", "runtime-policy.analysis_algorithms", value_type="DATA_DRIVEN"),
        domain("setup.family_thresholds", "STRUCTURAL_SETUP", "SETUP", (), "per_family_causal_thresholds,max_points=7", "setup-detector", value_type="DATA_DRIVEN"),
        domain("setup.confirmation_count", "STRUCTURAL_SETUP", "SETUP", (1, 2, 3), "closed_boundaries_only", "trade-parameters", value_type="INTEGER"),
        domain("strategy.entry_weights", "STRATEGY_ADMISSION", "STRATEGY", (7,), "simplex_sum=100,max_component=45", "trade-parameters", value_type="WEIGHT_SIMPLEX"),
        domain("strategy.minimum_score", "STRATEGY_ADMISSION", "STRATEGY", (40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90), "0<=score<=100", "trade-parameters"),
        domain("geometry.atr_multiplier", "GEOMETRY", "GEOMETRY", (0.15, 0.25, 0.35, 0.50, 0.75), "positive", "trade-parameters"),
        domain("geometry.stop_max_bps", "GEOMETRY", "GEOMETRY", (18, 24, 30, 36, 45, 55, 65), "stop_min<stop_max", "trade-parameters"),
        domain("geometry.target_min_bps", "TARGET", "GEOMETRY", (20, 30, 40, 50, 60, 80), "causal_target_only", "trade-parameters"),
        domain("economics.minimum_planned_rr", "RR", "ECONOMICS", (0.6, 0.8, 1.0, 1.2, 1.5), "positive", "trade-parameters"),
        domain("economics.min_net_edge_bps", "COSTS", "ECONOMICS", (5, 8, 10, 12, 15, 20), "observed_costs_not_reduced", "trade-parameters"),
        domain("economics.min_positive_ev_r", "COSTS", "ECONOMICS", (0, 0.02, 0.05, 0.10), "non_negative", "trade-parameters"),
        domain("economics.min_ev_reserve_r", "COSTS", "ECONOMICS", (0, 0.02, 0.05, 0.10), "non_negative", "trade-parameters"),
        domain("economics.bucket_min_sample", "COSTS", "ECONOMICS", (20, 30, 50, 100), "positive", "trade-parameters", value_type="INTEGER"),
        domain("economics.probability_confidence", "COSTS", "ECONOMICS", (0.85, 0.90, 0.95), "0<value<1", "trade-parameters"),
        domain("costs.max_depth_impact_bps", "COSTS", "COSTS", (5, 10, 15, 20), "cannot_exceed_current_safety_cap", "trade-parameters", safety=True),
        domain("risk.risk_per_trade_bps", "RISK_COMPATIBILITY", "RISK", (2.5, 5, 7.5, 10), "<=10_equity_bps", "risk-policy", safety=True),
        domain("risk.max_open_positions", "PORTFOLIO", "RISK", (1, 2), "<=2", "risk-policy", value_type="INTEGER", safety=True),
        domain("risk.max_new_commands_per_cycle", "PORTFOLIO", "RISK", (1, 2), "<=2", "risk-policy", value_type="INTEGER", safety=True),
        domain("risk.total_open_risk_limit_bps", "PORTFOLIO", "RISK", (25, 35, 50), "<=50_equity_bps", "risk-policy", safety=True),
        domain("lifecycle.plan_ttl_seconds", "PAPER_PLAN", "LIFECYCLE", (30, 60, 90, 120), "positive", "trade-parameters", value_type="INTEGER"),
        domain("lifecycle.entry_fill_window_seconds", "FILL", "LIFECYCLE", (30, 60, 90, 120), "positive", "trade-parameters", value_type="INTEGER"),
        domain("lifecycle.validity_boundaries", "APPROVAL", "LIFECYCLE", (1, 2), "positive", "trade-parameters", value_type="INTEGER"),
        domain("lifecycle.maximum_price_drift_bps", "FILL", "LIFECYCLE", (3, 5, 8, 10), "<=10", "trade-parameters", safety=True),
        domain("exit.weights", "EXIT", "EXIT", (4,), "simplex_sum=100,max_component=45", "trade-parameters", value_type="WEIGHT_SIMPLEX"),
        domain("exit.at_risk_threshold", "POSITION_MANAGEMENT", "EXIT", (30, 35, 40, 45, 50, 55, 60), "at_risk<exit<=strong_reversal", "trade-parameters"),
        domain("exit.exit_threshold", "EXIT", "EXIT", (55, 60, 65, 70, 75, 80, 85), "at_risk<exit<=strong_reversal", "trade-parameters"),
        domain("exit.strong_reversal_threshold", "EXIT", "EXIT", (70, 75, 80, 85, 90, 95), "at_risk<exit<=strong_reversal", "trade-parameters"),
        domain("exit.confirmation_boundaries", "EXIT", "EXIT", (2, 3, 4, 5), "2<=value<=5", "trade-parameters", value_type="INTEGER"),
        domain("exit.profit_protection_progress", "POSITION_MANAGEMENT", "EXIT", (0.30, 0.40, 0.50, 0.60, 0.70), "0<=value<=1", "trade-parameters"),
        domain("exit.profit_lock_buffer_bps", "EXIT", "EXIT", (8, 10, 12, 15, 20), ">=8", "trade-parameters"),
        domain("exit.time_stop_minutes", "EXIT", "EXIT", (5, 10, 15, 20, 30, 45), "positive", "trade-parameters", value_type="INTEGER"),
    ]
    for name, stage, source in (
        ("costs.actual_commission", "COSTS", "historical-account-commission"),
        ("costs.observed_spread", "COSTS", "historical-book"),
        ("costs.observed_slippage", "COSTS", "historical-fill"),
        ("safety.closed_candles", "ANALYSIS", "market-data"),
        ("safety.idempotency", "APPROVAL", "paper-lifecycle"),
        ("safety.accounting_identity", "ACCOUNTING", "paper-accounting"),
        ("safety.live_allowed", "APPROVAL", "operator-control"),
    ):
        items.append(StageParameterDomain(
            name=name, stage=stage, family="IMMUTABLE", value_type="BOOLEAN",
            invariant="immutable_fail_closed", source=source,
            safety_critical=True, immutable=True,
        ))
    return StageParameterRegistryV1(parameters=tuple(items))


def evaluate_gates(metrics: CandidateMetrics, gates: AcceptanceGates) -> dict[str, bool]:
    return {
        "minimum_closed_trades": metrics.closed_trades >= gates.minimum_closed_trades,
        "minimum_independent_days": metrics.independent_days >= gates.minimum_independent_days,
        "minimum_symbols": metrics.symbols >= gates.minimum_symbols,
        "positive_net_pnl": metrics.net_pnl > 0,
        "minimum_expectancy": metrics.expectancy_bps >= gates.minimum_net_expectancy_bps,
        "minimum_profit_factor": metrics.profit_factor >= gates.minimum_profit_factor,
        "minimum_win_rate": metrics.win_rate > gates.minimum_win_rate_exclusive,
        "maximum_drawdown": metrics.max_drawdown_fraction <= gates.maximum_drawdown_fraction,
        "drawdown_not_worse_than_baseline": metrics.max_drawdown_fraction <= metrics.baseline_max_drawdown_fraction,
        "maximum_symbol_concentration": metrics.maximum_symbol_profit_share <= gates.maximum_symbol_profit_share,
        "maximum_day_concentration": metrics.maximum_day_profit_share <= gates.maximum_day_profit_share,
        "walk_forward_stability": metrics.profitable_walk_forward_folds >= gates.minimum_profitable_walk_forward_folds,
        "stress_net_positive": metrics.stress_net_pnl > 0,
        "stress_profit_factor": metrics.stress_profit_factor >= gates.minimum_stress_profit_factor,
        "neighbor_stability": metrics.neighbor_stability_pass,
    }


def metrics_from_trades(
    trades: Sequence[EndToEndTradeEvaluationV1], *, initial_equity: float,
    baseline_max_drawdown_fraction: float, profitable_walk_forward_folds: int,
    neighbor_stability_pass: bool, stress_multiplier: float,
) -> CandidateMetrics:
    ordered = sorted(trades, key=lambda item: (item.exit_boundary_ms, item.trade_id))
    gross_profit = sum(max(0.0, item.net_pnl) for item in ordered)
    gross_loss = abs(sum(min(0.0, item.net_pnl) for item in ordered))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (1_000_000.0 if gross_profit > 0 else 0.0)
    equity = peak = float(initial_equity)
    maximum_drawdown = 0.0
    by_symbol: dict[str, float] = {}
    by_day: dict[str, float] = {}
    stress_values: list[float] = []
    for item in ordered:
        equity += item.net_pnl
        peak = max(peak, equity)
        maximum_drawdown = max(maximum_drawdown, (peak - equity) / peak if peak > 0 else 1.0)
        by_symbol[item.symbol] = by_symbol.get(item.symbol, 0.0) + item.net_pnl
        day = datetime.fromtimestamp(item.exit_boundary_ms / 1000, timezone.utc).date().isoformat()
        by_day[day] = by_day.get(day, 0.0) + item.net_pnl
        costs = item.fees + item.spread_cost + item.slippage_cost + item.reserve_cost
        stress_values.append(item.gross_pnl - costs * stress_multiplier)
    net = sum(item.net_pnl for item in ordered)
    positive_net = max(net, 0.0)
    maximum_symbol_share = (
        max((max(value, 0.0) for value in by_symbol.values()), default=0.0) / positive_net
        if positive_net > 0 else 1.0
    )
    maximum_day_share = (
        max((max(value, 0.0) for value in by_day.values()), default=0.0) / positive_net
        if positive_net > 0 else 1.0
    )
    stress_profit = sum(max(0.0, value) for value in stress_values)
    stress_loss = abs(sum(min(0.0, value) for value in stress_values))
    stress_pf = stress_profit / stress_loss if stress_loss > 0 else (1_000_000.0 if stress_profit > 0 else 0.0)
    return CandidateMetrics(
        closed_trades=len(ordered), independent_days=len(by_day), symbols=len(by_symbol),
        net_pnl=net,
        expectancy_bps=(sum(item.net_pnl_bps for item in ordered) / len(ordered) if ordered else 0.0),
        profit_factor=profit_factor,
        win_rate=(sum(item.net_pnl > 0 for item in ordered) / len(ordered) if ordered else 0.0),
        max_drawdown_fraction=maximum_drawdown,
        maximum_symbol_profit_share=min(1.0, maximum_symbol_share),
        maximum_day_profit_share=min(1.0, maximum_day_share),
        profitable_walk_forward_folds=profitable_walk_forward_folds,
        stress_net_pnl=sum(stress_values), stress_profit_factor=stress_pf,
        baseline_max_drawdown_fraction=baseline_max_drawdown_fraction,
        neighbor_stability_pass=neighbor_stability_pass,
    )


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _load_request(path: Path) -> FullPipelineCalibrationRequestV1 | FullPipelineCalibrationRequestV2:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("version") == "full-pipeline-calibration/2":
        return FullPipelineCalibrationRequestV2.model_validate(raw)
    return FullPipelineCalibrationRequestV1.model_validate(raw)


def freeze_dataset(request_path: Path, output: Path, database_url: str | None) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(output)
    request = _load_request(request_path)
    registry = default_registry()
    database = ReadOnlyResearchDatabase(resolve_database_binding(explicit_url=database_url))
    inventory: dict[str, Any] = {}
    coverage_failures: list[dict[str, Any]] = []
    interval_ms = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000}
    cost_evidence: dict[str, Any] = {}
    try:
        with database.connection() as connection:
            for timeframe in ("1m", "5m", "15m", "1h"):
                table = f"candles_{timeframe}"
                rows = connection.execute(text(f"""
                    SELECT symbol, count(*) AS rows, min(open_time_ms) AS minimum,
                           max(close_time_ms) AS maximum,
                           count(*) FILTER (WHERE is_closed=false) AS open_rows,
                           count(DISTINCT open_time_ms) AS distinct_boundaries,
                           md5(string_agg(data_checksum, '' ORDER BY symbol,open_time_ms)) AS digest
                    FROM {table}
                    WHERE symbol = ANY(:symbols) AND open_time_ms >= :start_ms
                      AND open_time_ms < :end_ms
                    GROUP BY symbol ORDER BY symbol
                """), {
                    "symbols": list(request.symbols), "start_ms": request.data_start_ms,
                    "end_ms": request.data_end_ms,
                }).mappings().all()
                inventory[timeframe] = [dict(row) for row in rows]
                by_symbol = {str(row["symbol"]): row for row in rows}
                expected = math.ceil((request.data_end_ms - request.data_start_ms) / interval_ms[timeframe])
                for symbol in request.symbols:
                    row = by_symbol.get(symbol)
                    reasons: list[str] = []
                    if row is None:
                        reasons.append("MISSING_SYMBOL")
                    else:
                        if int(row["minimum"]) > request.data_start_ms + interval_ms[timeframe]:
                            reasons.append("LATE_HISTORY_START")
                        if int(row["maximum"]) < request.data_end_ms - 1:
                            reasons.append("EARLY_HISTORY_END")
                        if int(row["open_rows"]) != 0:
                            reasons.append("UNCLOSED_CANDLES")
                        if int(row["rows"]) != int(row["distinct_boundaries"]):
                            reasons.append("DUPLICATE_BOUNDARIES")
                        if int(row["rows"]) < expected:
                            reasons.append("GAPS_OR_PARTIAL_COVERAGE")
                    if reasons:
                        coverage_failures.append({
                            "timeframe": timeframe, "symbol": symbol,
                            "reasons": reasons,
                            "available_rows": 0 if row is None else int(row["rows"]),
                            "expected_rows": expected,
                            "available_start_ms": None if row is None else int(row["minimum"]),
                            "required_start_ms": request.data_start_ms,
                        })
            cost_row = connection.execute(text("""
                SELECT count(*) FILTER (WHERE paper_status='PAPER_PLAN_READY') AS strict_rows,
                       min(closed_until_ms) FILTER (WHERE paper_status='PAPER_PLAN_READY') AS minimum_boundary_ms,
                       max(closed_until_ms) FILTER (WHERE paper_status='PAPER_PLAN_READY') AS maximum_boundary_ms
                FROM online_pipeline_runs
                WHERE trade_profile_id='trade-5m-v2'
                  AND closed_until_ms >= :start_ms AND closed_until_ms < :end_ms
            """), {"start_ms": request.data_start_ms, "end_ms": request.data_end_ms}).mappings().one()
            cost_evidence = dict(cost_row)
    finally:
        database.dispose()
    blocked_reasons = []
    if coverage_failures:
        blocked_reasons.append("INCOMPLETE_20_SYMBOL_WALK_FORWARD_CANDLE_COVERAGE")
    if int(cost_evidence.get("strict_rows") or 0) < request.gates.minimum_closed_trades:
        blocked_reasons.append("INSUFFICIENT_CAUSAL_HISTORICAL_COST_EVIDENCE")
    evidence = {
        "version": DATASET_VERSION,
        "request_hash": request.identity,
        "registry_hash": registry.identity,
        "source": "postgresql-readonly-checksummed-manifest",
        "period": [request.data_start_ms, request.data_end_ms],
        "symbols": list(request.symbols), "timeframes": inventory,
        "coverage_failures": coverage_failures,
        "historical_cost_evidence": cost_evidence,
        "status": "BLOCKED_DATA" if blocked_reasons else "FROZEN",
        "blocked_reasons": blocked_reasons,
        "closed_only_required": True, "production_mutations": 0,
    }
    evidence["dataset_hash"] = fingerprint(evidence)
    output.mkdir(parents=True)
    _write_json(output / "REQUEST.json", request.model_dump(mode="json"))
    _write_json(output / "PARAMETER_REGISTRY.json", registry.model_dump(mode="json"))
    _write_json(output / "DATASET_MANIFEST.json", evidence)
    return evidence


def _read_trades(path: Path) -> list[EndToEndTradeEvaluationV1]:
    if path.suffix.lower() == ".jsonl":
        return [EndToEndTradeEvaluationV1.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [EndToEndTradeEvaluationV1.model_validate(dict(row)) for row in csv.DictReader(handle)]


def verify_candidate(
    request_path: Path, candidate_path: Path, trades_path: Path, output: Path,
) -> FullPipelineCandidateV1:
    request = _load_request(request_path)
    raw = json.loads(candidate_path.read_text(encoding="utf-8"))
    trades = _read_trades(trades_path)
    configuration_hash = fingerprint(raw["parameters"])
    if any(item.configuration_hash != configuration_hash for item in trades):
        raise ValueError("TRADE_CONFIGURATION_HASH_MISMATCH")
    metrics = metrics_from_trades(
        trades, initial_equity=request.initial_equity,
        baseline_max_drawdown_fraction=float(raw["baseline_max_drawdown_fraction"]),
        profitable_walk_forward_folds=int(raw["profitable_walk_forward_folds"]),
        neighbor_stability_pass=bool(raw["neighbor_stability_pass"]),
        stress_multiplier=request.gates.stress_cost_multiplier,
    )
    gates = evaluate_gates(metrics, request.gates)
    candidate = FullPipelineCandidateV1(
        candidate_id=str(raw["candidate_id"]), request_hash=request.identity,
        dataset_hash=str(raw["dataset_hash"]), registry_hash=default_registry().identity,
        configuration_hash=configuration_hash, seed=request.seed,
        parameters=dict(raw["parameters"]), metrics=metrics, gate_results=gates,
        status="ELIGIBLE" if all(gates.values()) else "NO_ELIGIBLE_CANDIDATE",
    )
    output.mkdir(parents=True, exist_ok=True)
    _write_json(output / "VERIFIED_CANDIDATE.json", candidate.model_dump(mode="json"))
    _write_json(output / "VERIFIER_INTEGRITY.json", {
        "candidate_hash": fingerprint(candidate.model_dump(mode="json")),
        "trade_hash": fingerprint([item.model_dump(mode="json") for item in trades]),
        "gate_hash": fingerprint(gates), "eligible": candidate.status == "ELIGIBLE",
    })
    return candidate


def build_canary(candidate_path: Path, output: Path, rollback_parameter_set: str) -> PaperCanaryManifestV1:
    candidate = FullPipelineCandidateV1.model_validate_json(candidate_path.read_text(encoding="utf-8"))
    ready = candidate.status == "ELIGIBLE" and all(candidate.gate_results.values())
    manifest = PaperCanaryManifestV1(
        candidate_id=candidate.candidate_id,
        candidate_hash=fingerprint(candidate.model_dump(mode="json")),
        rollback_parameter_set=rollback_parameter_set,
        activation_status="READY_FOR_PAPER_CANARY" if ready else "BLOCKED_PENDING_ELIGIBILITY",
    )
    output.mkdir(parents=True, exist_ok=True)
    _write_json(output / "PAPER_CANARY_MANIFEST.json", manifest.model_dump(mode="json"))
    if not ready:
        raise ValueError("PAPER_CANARY_BLOCKED_NO_ELIGIBLE_CANDIDATE")
    return manifest


def record_blocked_action(action: str, request_path: Path, dataset: Path, output: Path) -> dict[str, Any]:
    request = _load_request(request_path)
    manifest_path = dataset / "DATASET_MANIFEST.json"
    if not manifest_path.exists():
        raise ValueError("FULL_PIPELINE_FROZEN_DATASET_REQUIRED")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    reasons = list(manifest.get("blocked_reasons") or [])
    if manifest.get("status") == "FROZEN" and not (dataset / "DECISION_TRACES.jsonl").exists():
        reasons.append("FULL_PIPELINE_CAUSAL_TRACE_DATASET_REQUIRED")
    if not reasons:
        reasons.append("FULL_PIPELINE_EXECUTION_ENGINE_NOT_STARTED")
    result = {
        "version": "full-pipeline-action-status/1", "action": action.upper(),
        "status": "BLOCKED_DATA", "request_hash": request.identity,
        "dataset_hash": manifest.get("dataset_hash"), "blocked_reasons": reasons,
        "coverage_failure_count": len(manifest.get("coverage_failures") or []),
        "historical_cost_evidence": manifest.get("historical_cost_evidence") or {},
        "production_mutations": 0, "paper_activated": False, "live_activated": False,
    }
    output.mkdir(parents=True, exist_ok=True)
    _write_json(output / "STATUS.json", result)
    (output / "REPORT.md").write_text(
        "# Full-pipeline calibration status\n\n"
        f"`{action.upper()} = BLOCKED_DATA`\n\n"
        "The action was not allowed to reinterpret incomplete history as a causal "
        "end-to-end dataset.\n\n## Blocking reasons\n\n"
        + "\n".join(f"- `{reason}`" for reason in reasons)
        + "\n\nPAPER and LIVE configuration were not changed.\n",
        encoding="utf-8",
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Full causal scalping pipeline calibration")
    parser.add_argument("action", choices=("freeze", "baseline", "cache-v3", "candidate-signals-v3", "parity-v3", "train", "verify", "paper-canary"))
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--database-url")
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--changes", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--trades", type=Path)
    parser.add_argument("--rollback-parameter-set", default="scalping-v2-set-2")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.action == "freeze":
        request = _load_request(args.request)
        if isinstance(request, FullPipelineCalibrationRequestV2):
            from .full_pipeline_ragged import freeze_ragged_dataset
            manifest_v2 = freeze_ragged_dataset(args.request, args.output, args.database_url)
            status = manifest_v2.status
            dataset_hash = manifest_v2.dataset_hash
        else:
            manifest = freeze_dataset(args.request, args.output, args.database_url)
            status = manifest["status"]
            dataset_hash = manifest["dataset_hash"]
        print(f"FULL_PIPELINE_FREEZE = {status} dataset_hash={dataset_hash}")
        if status != "FROZEN":
            raise SystemExit(2)
        return
    if args.action == "cache-v3":
        if args.dataset is None:
            raise SystemExit("FULL_PIPELINE_FROZEN_DATASET_REQUIRED")
        from .full_pipeline_v3 import build_feature_cache_v3
        result = build_feature_cache_v3(args.request, args.dataset, args.output, args.database_url)
        print(f"FULL_PIPELINE_CACHE_V3 = {result.status} boundaries={result.completed_boundaries}")
        return
    if args.action == "candidate-signals-v3":
        if args.dataset is None or args.cache is None:
            raise SystemExit("CANDIDATE_V3_DATASET_AND_CACHE_REQUIRED")
        from .full_pipeline_candidate_v3 import build_native_candidate_signal_cache_v3
        changes = json.loads(args.changes.read_text(encoding="utf-8")) if args.changes else {}
        if not isinstance(changes, dict):
            raise SystemExit("CANDIDATE_V3_CHANGES_OBJECT_REQUIRED")
        result = build_native_candidate_signal_cache_v3(
            args.request, args.dataset, args.cache, args.output, changes)
        print(f"FULL_PIPELINE_CANDIDATE_SIGNALS_V3 = {result['status']} "
              f"boundaries={result['completed_boundaries']}")
        return
    if args.action == "parity-v3":
        if args.dataset is None or args.cache is None or args.candidate is None:
            raise SystemExit("PARITY_V3_DATASET_CACHE_AND_SIGNALS_REQUIRED")
        from .full_pipeline_parity_v3 import audit_native_stage_parity_v3
        result = audit_native_stage_parity_v3(
            args.request, args.dataset, args.cache, args.candidate, args.output)
        print(f"FULL_PIPELINE_PARITY_V3 = {result['status']} "
              f"boundaries={result['totals']['boundaries']}")
        return
    if args.action in {"baseline", "train"}:
        # Training is intentionally fail-closed until a frozen trace dataset from
        # the production-component reconstructor is supplied.  A candle manifest
        # alone cannot be silently treated as executable trade evidence.
        if args.dataset is None:
            raise SystemExit("FULL_PIPELINE_FROZEN_DATASET_REQUIRED")
        manifest_path = args.dataset / "DATASET_MANIFEST.json"
        if not manifest_path.exists():
            raise SystemExit("FULL_PIPELINE_FROZEN_DATASET_REQUIRED")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("version") == "ragged-full-pipeline-dataset/2":
            if manifest.get("status") != "FROZEN":
                result = record_blocked_action(args.action, args.request, args.dataset, args.output)
                print(f"FULL_PIPELINE_{args.action.upper()} = {result['status']}")
                raise SystemExit(2)
            from .full_pipeline_ragged import reconstruct_baseline, train_ragged
            if args.action == "baseline":
                result = reconstruct_baseline(
                    args.request, args.dataset, args.output, args.database_url,
                )
            else:
                if args.baseline is None:
                    raise SystemExit("FULL_PIPELINE_BASELINE_DIRECTORY_REQUIRED")
                result = train_ragged(args.request, args.dataset, args.baseline, args.output)
            print(f"FULL_PIPELINE_{args.action.upper()} = {result['status']}")
            return
        if manifest.get("status") != "FROZEN" or not (args.dataset / "DECISION_TRACES.jsonl").exists():
            result = record_blocked_action(args.action, args.request, args.dataset, args.output)
            print(f"FULL_PIPELINE_{args.action.upper()} = {result['status']}")
            raise SystemExit(2)
        raise SystemExit("FULL_PIPELINE_EXECUTION_ENGINE_REQUIRED")
    if args.action == "verify":
        if args.candidate is None or args.trades is None:
            raise SystemExit("FULL_PIPELINE_CANDIDATE_AND_TRADES_REQUIRED")
        result = verify_candidate(args.request, args.candidate, args.trades, args.output)
        print(f"FULL_PIPELINE_VERIFY = {result.status}")
        return
    if args.action == "paper-canary":
        if args.candidate is None:
            raise SystemExit("FULL_PIPELINE_VERIFIED_CANDIDATE_REQUIRED")
        manifest = build_canary(args.candidate, args.output, args.rollback_parameter_set)
        print(f"FULL_PIPELINE_PAPER_CANARY = {manifest.activation_status}")


if __name__ == "__main__":
    main()
