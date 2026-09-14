"""Offline adapter to the authoritative market-history pipeline.

Only the funnel is implemented here. No fills or profitable results are inferred
from an admission decision. Each instance owns its trial's mutable runner state.
"""
from __future__ import annotations

from dataclasses import replace, asdict
from pathlib import Path
import json

from app.config.trade_parameters import ScalpingV2Parameters, ResolvedParameterSet, frozen_parameter_hash
from app.engine_market_data.candle import Candle
from app.engine_orchestrator.orchestrator_config import OrchestratorConfig
from app.engine_orchestrator.pipeline_runner import PipelineRunner
from app.engine_orchestrator.runtime_parameters import _runtime_parameters
from app.engine_paper.scalping_paper_runner import ScalpingPaperRunner
from .historical_reconstruction import CausalCandleRepository
from .historical_statistics import HistoricalStatistics
from .history_applicability import HistoricalCostSource
from .search_history import HistoryProvider, TIMEFRAMES
from .result_search import fingerprint
from .opportunity_registry import ResearchOpportunityRegistry

SEARCHABLE_PARAMETERS = frozenset({
    "signal.strategy_minimum_score", "signal.impulse_atr_multiplier",
    "signal.impulse_absolute_threshold_pct", "signal.regime_lookback_candles",
    "signal.confirmation_window_candles", "geometry.atr_multiplier",
    "geometry.stop_max_bps", "geometry.minimum_planned_rr", "economics.min_net_edge_bps",
})


def resolve_frozen_configuration(frozen: dict, overrides: dict) -> ResolvedParameterSet:
    flat = dict(frozen["parameters"])
    unknown = set(overrides) - set(flat)
    if unknown:
        raise ValueError("UNKNOWN_PARAMETER:" + ",".join(sorted(unknown)))
    nested = {}
    for dotted, value in flat.items():
        target = nested
        parts = dotted.split(".")
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        target[parts[-1]] = value
    ScalpingV2Parameters.model_validate(nested)
    for dotted, value in overrides.items():
        target = nested
        parts = dotted.split(".")
        for part in parts[:-1]:
            target = target[part]
        target[parts[-1]] = value
    parameters = ScalpingV2Parameters.model_validate(nested)
    runtime = frozen["runtime_parameters"]
    return ResolvedParameterSet(id=runtime["named_parameter_set_id"],
        label=runtime["parameter_set_label"], version=runtime["parameter_set_version"],
        parameters=parameters, resolved_config_hash=frozen_parameter_hash(parameters,frozen["resolved_config_hash"]),
        activation_cycle_boundary_ms=runtime["activation_cycle_boundary_ms"],
        activation_revision=runtime["activation_revision"], previous_parameter_set="FROZEN_RESEARCH",
        switched_at_utc="FROZEN_RESEARCH", provenance={})


class _FrozenOrchestratorConfig(OrchestratorConfig):
    def __init__(self, parameters, **kwargs):
        object.__setattr__(self, "parameters", parameters)
        super().__init__(**kwargs)

    @property
    def trade_profile(self):
        p = self.parameters
        return replace(super().trade_profile,
            market_data_windows=tuple((tf, p.signal.market_data_windows[tf]) for tf, _ in super().trade_profile.market_data_windows),
            **{k: getattr(p.signal, k) for k in ("analysis_history_candles", "atr_lookback_candles",
                "impulse_lookback_candles", "structure_lookback_candles", "confirmation_window_candles",
                "volume_baseline_candles", "regime_lookback_candles")},
            book_depth_limit=p.costs.book_depth_limit, microstructure_max_age_ms=p.costs.microstructure_max_age_ms,
            vwap_reference_notional=p.costs.vwap_reference_notional, validity_boundaries=p.lifecycle.validity_boundaries,
            minimum_planned_rr=p.geometry.minimum_planned_rr, cost_safety_margin_bps=p.costs.cost_safety_margin_bps)


class _OfflineInputs:
    def __init__(self, runtime, parameters, statistics):
        self.runtime, self.parameters, self.statistics = runtime, parameters, statistics
        self.cost = None
        self.cutoff = 0
        self.statistics_missing = False

    def select(self, row):
        self.cost = HistoricalCostSource(row, self.runtime, self.parameters)
        self.cutoff = int((row.get("geometry") or {}).get("decision_cutoff_timestamp_ms") or row["closed_until_ms"])
        self.statistics_missing = False

    def load(self, *args, **kwargs):
        return self.cost.load(*args, **kwargs)

    def resolve(self, **kwargs):
        if self.statistics is None:
            self.statistics_missing = True
            raise ValueError("HISTORICAL_STATISTICS_REQUIRED")
        return self.statistics.at(self.cutoff).resolve(**kwargs)


class _HistoricalPaperRunner(ScalpingPaperRunner):
    def process_risk_decision(self, source):
        # created_at is transport metadata; inject the historical evaluation clock.
        return super().process_risk_decision(replace(source, created_at_ms=self._clock_ms()))


class FrozenFunnel:
    def __init__(self, directory: Path, overrides: dict):
        self.manifest, rows = HistoryProvider.load(directory)
        if set(overrides)-SEARCHABLE_PARAMETERS:
            raise ValueError("UNSUPPORTED_PARAMETER_CONSUMER:"+",".join(sorted(set(overrides)-SEARCHABLE_PARAMETERS)))
        if self.manifest["missing_inputs"]:
            raise ValueError("DATASET_HAS_HARD_GAPS")
        self.boundaries = {(r["symbol"], r["closed_until_ms"]): r for r in rows if r["kind"] == "PERSISTED_BOUNDARY"}
        frozen = next(iter(self.boundaries.values()))["frozen"]
        if any(r["frozen"]["resolved_config_hash"] != frozen["resolved_config_hash"] for r in self.boundaries.values()):
            raise ValueError("EXPLICIT_BASELINE_REQUIRED_FOR_MULTIPLE_EPOCHS")
        self.resolved = resolve_frozen_configuration(frozen, overrides)
        baseline = resolve_frozen_configuration(frozen, {})
        baseline_config = _FrozenOrchestratorConfig(baseline.parameters,
            symbols=tuple(self.manifest["symbols"]), trade_profile_id="trade-5m-v2")
        baseline_runtime = json.loads(json.dumps(asdict(_runtime_parameters(baseline_config.trade_profile, baseline))))
        changed = [k for k,v in frozen["runtime_parameters"].items()
                   if k != "resolved_config_hash" and baseline_runtime.get(k) != v]
        if changed:
            raise ValueError("FROZEN_RUNTIME_CONSUMER_MISMATCH:" + ",".join(changed))
        config = _FrozenOrchestratorConfig(self.resolved.parameters, symbols=tuple(self.manifest["symbols"]), trade_profile_id="trade-5m-v2",
            required_timeframes=tuple(self.resolved.parameters.signal.required_timeframes),
            minimum_windows=dict(self.resolved.parameters.signal.market_data_windows))
        runtime = _runtime_parameters(config.trade_profile, self.resolved)
        statistics = HistoricalStatistics(json.loads((directory / "STATISTICS.json").read_text()), 0) if self.manifest.get("statistics") else None
        self.inputs = _OfflineInputs(runtime, frozen["parameters"] | overrides, statistics)
        self.diagnostic_inputs = _OfflineInputs(runtime, frozen["parameters"] | overrides, statistics)
        self.repositories = {}
        for symbol in self.manifest["symbols"]:
            groups = {tf: [] for tf in TIMEFRAMES}
            for row in rows:
                if row["kind"] == "CANDLE" and row["symbol"] == symbol:
                    groups[row["timeframe"]].append(Candle(**{key: row[key] for key in
                        ("symbol", "timeframe", "open_time_ms", "close_time_ms", "open", "high", "low", "close", "volume")},
                        is_closed=True, source="FROZEN_HISTORY"))
            self.repositories[symbol] = CausalCandleRepository(symbol, groups)
        paper = _HistoricalPaperRunner(runtime_parameters=runtime, scalping_parameters=self.resolved.parameters,
            cost_source=self.inputs, statistics_source=self.inputs, clock_ms=lambda: self.inputs.cutoff,
            opportunity_registry=ResearchOpportunityRegistry())
        self.runner = PipelineRunner(config, self, resolved_parameter_set=self.resolved,
            paper_runner=paper, strategy_cap_cost_source=self.diagnostic_inputs, scalping_statistics_source=self.inputs)
        self.last_boundary = -1

    def get_candles(self, symbol, timeframe, **kwargs):
        return self.repositories[symbol].get_candles(symbol, timeframe, **kwargs)

    def run(self, symbol: str, boundary: int):
        if boundary < self.last_boundary:
            raise ValueError("NONCHRONOLOGICAL_TRIAL")
        interval = self.manifest["intervals"]
        if not interval["search_start_ms"] <= boundary < interval["search_end_ms"]:
            raise ValueError("BOUNDARY_OUTSIDE_SEARCH_INTERVAL")
        self.last_boundary = boundary
        row = self.boundaries.get((symbol, boundary), {"symbol": symbol, "closed_until_ms": boundary})
        self.inputs.select(row)
        self.diagnostic_inputs.select(row)
        result = self.runner.run(symbol, boundary)
        if result.safety_counters.has_violation:
            raise ValueError("FUNNEL_CAUSALITY_OR_SAFETY_VIOLATION")
        return result, self.inputs.cost.blocker, self.inputs.statistics_missing
