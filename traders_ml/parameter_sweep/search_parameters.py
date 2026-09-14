"""Canonical supported parameter registry and causal empirical domains."""
from dataclasses import dataclass, asdict
from math import isfinite
from pathlib import Path

from .frozen_funnel import SEARCHABLE_PARAMETERS
from .search_history import HistoryProvider
from .result_search import REGISTRY_VERSION, fingerprint


@dataclass(frozen=True)
class ParameterSpec:
    key: str
    value_type: str
    unit: str
    lower: float
    upper: float
    consumer: str
    family: str
    evidence: str


SPECS = (
    ParameterSpec("signal.strategy_minimum_score","float","score",0,100,"RiskPolicy","signal/setup","observed_strategy_scores"),
    ParameterSpec("signal.impulse_atr_multiplier","float","ratio",0.1,3,"OnlineAnalysisRunner","signal/setup","candle_body_range_ratios"),
    ParameterSpec("signal.impulse_absolute_threshold_pct","float","percent",0.001,10,"OnlineAnalysisRunner","signal/setup","absolute_candle_returns_percent"),
    ParameterSpec("signal.regime_lookback_candles","int","candles",8,64,"OnlineAnalysisRunner","regime","declared_discrete_windows"),
    ParameterSpec("signal.confirmation_window_candles","int","candles",1,8,"SetupDetector","confirmation/entry","declared_discrete_windows"),
    ParameterSpec("geometry.atr_multiplier","float","ratio",0.25,1,"ScalpingPaperRunner","geometry","declared_shadow_geometry_cohorts"),
    ParameterSpec("geometry.stop_max_bps","float","bps",5,200,"ScalpingPaperRunner","geometry","observed_stop_admission_boundaries"),
    ParameterSpec("geometry.minimum_planned_rr","float","ratio",0.2,4,"ScalpingPaperRunner","geometry","observed_risk_reward"),
    ParameterSpec("economics.min_net_edge_bps","float","bps",0,200,"ScalpingPaperRunner","economics admission","observed_market_move_bps"),
)
assert {s.key for s in SPECS} == SEARCHABLE_PARAMETERS


def quantiles(values):
    ordered=sorted(float(v) for v in values if v is not None and isfinite(float(v)))
    if not ordered:
        return []
    return [ordered[round((len(ordered)-1)*q)] for q in (0.1,0.5,0.9)]


def generate_space(directory: Path):
    manifest, _ = HistoryProvider.load(directory)
    rows=HistoryProvider.partition(directory,"search")
    snapshots=[r for r in rows if r["kind"]=="PERSISTED_BOUNDARY"]
    if not snapshots:
        raise ValueError("FROZEN_BASELINE_REQUIRED")
    frozen=snapshots[0]["frozen"]
    if len({r["frozen"]["resolved_config_hash"] for r in snapshots})!=1:
        raise ValueError("EXPLICIT_BASELINE_REQUIRED_FOR_MULTIPLE_EPOCHS")
    baseline=frozen["parameters"]
    candles=[r for r in rows if r["kind"]=="CANDLE" and r["timeframe"]=="5m"]
    returns=[abs(float(c["close"])/float(c["open"])-1)*100 for c in candles]
    ratios=[abs(float(c["close"])-float(c["open"]))/max(float(c["high"])-float(c["low"]),1e-12) for c in candles]
    end=manifest["intervals"]["search_end_ms"]
    snapshots=[r for r in snapshots if ((r.get("geometry") or {}).get("decision_cutoff_timestamp_ms") or r["closed_until_ms"])<end
               and (r.get("risk") or {}).get("created_at_ms",r["closed_until_ms"])<end]
    geometry=[r["geometry"] for r in snapshots if r.get("geometry")]
    observed={"observed_strategy_scores":[r["risk"].get("source_strategy_score") for r in snapshots if r.get("risk")],
        "candle_body_range_ratios":ratios,"absolute_candle_returns_percent":returns,
        "observed_market_move_bps":[r*100 for r in returns],
        "observed_stop_admission_boundaries":[abs(float(g["entry"])-float(g["final_stop"]))/float(g["entry"])*10000
            for g in geometry if g.get("entry") and g.get("final_stop")],
        "observed_risk_reward":[g.get("gross_rr") for g in geometry]}
    domains,registry={},[]
    for spec in SPECS:
        empirical=quantiles(observed.get(spec.evidence,[]))
        if spec.key=="signal.regime_lookback_candles": empirical=[8,16,32,64]
        if spec.key=="signal.confirmation_window_candles": empirical=[1,2,4,8]
        if spec.key=="geometry.atr_multiplier": empirical=[0.25,0.5,0.75,1.0]
        base=baseline[spec.key]
        if not spec.lower<=base<=spec.upper:
            raise ValueError("BASELINE_OUTSIDE_REGISTERED_DOMAIN:"+spec.key)
        cast=int if spec.value_type=="int" else lambda v:round(float(v),8)
        values=sorted(set([base]+[cast(min(spec.upper,max(spec.lower,v))) for v in empirical]))
        if spec.key=="geometry.stop_max_bps":
            values=[v for v in values if v>baseline["geometry.stop_min_bps"]]
        if spec.key=="signal.regime_lookback_candles":
            values=[v for v in values if v>=baseline["signal.structure_lookback_candles"]]
        domains[spec.key]=values
        registry.append(asdict(spec)|{"config_path":"profiles.trade-5m-v2."+spec.key,"searchable":True,
            "baseline":base,"values":values,"source":spec.evidence,"quantiles":[0.1,0.5,0.9],
            "required_data":"CLOSED_SEARCH_CANDLES_AND_CAUSAL_BOUNDARY_SNAPSHOTS",
            "conditional_constraints":["stop_max_bps > frozen stop_min_bps",
                "regime_lookback_candles >= frozen structure_lookback_candles","typed configuration and runtime profile validation"],
            "generation":"BASELINE_PLUS_SEARCH_EMPIRICAL_QUANTILES_OR_DECLARED_DISCRETE"})
    for key,value in baseline.items():
        if key in SEARCHABLE_PARAMETERS: continue
        family=key.split('.')[0]
        reason={"risk":"FROZEN_CAPITAL_AND_RISK_AUTHORITY","costs":"EXTERNAL_COSTS_NOT_OPTIMIZED",
            "lifecycle":"FROZEN_PRODUCTION_LIFECYCLE_CONTRACT","exit_policy":"SHADOW_DIAGNOSTICS_CANNOT_CLOSE",
            "entry_refinement_1m":"SHADOW_ONLY_NO_EXECUTION_PROMOTION"}.get(family,"NO_REGISTERED_SEARCH_CONSUMER")
        registry.append({"key":key,"baseline":value,"searchable":False,"reason":reason})
    result={"registry_version":REGISTRY_VERSION,"dataset_fingerprint":manifest["fingerprint"],
        "baseline_source_hash":frozen["resolved_config_hash"],"domains":domains,"registry":registry,
        "generation_interval":{"start":manifest["intervals"]["search_start_ms"],"end":end},
        "independent_data_used":False,"exit_tail_used":False}
    result["fingerprint"]=fingerprint(result)
    return result
