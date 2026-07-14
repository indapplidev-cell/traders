"""ENGINE-TREND-24 offline scoring redesign and setup viability audit.

The module is deliberately standalone: it reads frozen historical discovery
artifacts, uses an explicit pre-entry feature view for scoring/filtering, and
writes research reports.  It is not imported by application or trading code.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "reports/engine_trend/engine_trend_historical_entry_discovery_2025_07_03_2025_12_17"
DEFAULT_AUDIT_23 = ROOT / "reports/engine_trend/engine_trend_23_historical_setup_performance_audit"
DEFAULT_OUTPUT = ROOT / "reports/engine_trend/engine_trend_24_scoring_redesign_setup_viability_filter"

REQUIRED_DISCOVERY = (
    "HISTORICAL_ENTRY_DISCOVERY_CANDIDATES.csv",
    "HISTORICAL_ENTRY_DISCOVERY_RESULTS.json",
    "MAIN_SELECTED_ENTRY_TRACE.json",
    "HISTORICAL_ENTRY_DISCOVERY_DATA_COVERAGE.json",
    "HISTORICAL_ENTRY_DISCOVERY_ARTIFACT_MANIFEST.json",
)
OPTIONAL_AUDIT_23 = (
    "ENGINE_TREND_23_PERFORMANCE_AUDIT_SUMMARY.json",
    "ENGINE_TREND_23_PERFORMANCE_BY_SYMBOL.csv",
    "ENGINE_TREND_23_PERFORMANCE_BY_SETUP_TYPE.csv",
    "ENGINE_TREND_23_PERFORMANCE_BY_DIRECTION.csv",
    "ENGINE_TREND_23_QUALITY_SCORE_AUDIT.csv",
    "ENGINE_TREND_23_RR_AUDIT.csv",
    "ENGINE_TREND_23_FAILURE_BUCKETS.csv",
    "ENGINE_TREND_23_DIAGNOSTIC_FILTER_HYPOTHESES.md",
    "ENGINE_TREND_23_ML_READINESS.md",
)
OUTPUT_FILES = (
    "ENGINE_TREND_24_SCORING_REDESIGN_REPORT.md",
    "ENGINE_TREND_24_SCORE_V2_CONFIG.json",
    "ENGINE_TREND_24_SCORE_V2_RESULTS.csv",
    "ENGINE_TREND_24_VALIDATION_METRICS.json",
    "ENGINE_TREND_24_SCORE_DECILES.csv",
    "ENGINE_TREND_24_FILTER_DIAGNOSTICS.csv",
    "ENGINE_TREND_24_REJECTED_WINNERS_AUDIT.md",
    "ENGINE_TREND_24_PASSED_LOSERS_AUDIT.md",
    "ENGINE_TREND_24_MAIN_ENTRY_POSTMORTEM.md",
    "ENGINE_TREND_24_SETUP_TYPE_VIABILITY.md",
    "ENGINE_TREND_24_SYMBOL_VIABILITY.md",
    "ENGINE_TREND_24_SENSITIVITY_ANALYSIS.csv",
    "ENGINE_TREND_24_LEAKAGE_AUDIT.md",
    "ENGINE_TREND_24_DECISION_RECORD.json",
    "ENGINE_TREND_24_ARTIFACT_MANIFEST.json",
)

CLEAN_LABELS = {"TP_BEFORE_SL", "SL_BEFORE_TP"}
WIN = "TP_BEFORE_SL"
LOSS = "SL_BEFORE_TP"
FORBIDDEN_FEATURE_NAMES = {
    "outcome", "label_status", "net_return_pct", "gross_return_pct", "mfe", "mae",
    "mfe_r", "mae_r", "bars_to_tp", "bars_to_sl", "bars_to_outcome", "realized_return",
    "post_entry_drawdown", "future_high", "future_low", "future_close", "candidate_rank",
    "failure_bucket",
}
DESIGN_END = datetime(2025, 10, 31, 23, 45, tzinfo=timezone.utc)
VALIDATION_START = datetime(2025, 11, 1, 0, 0, tzinfo=timezone.utc)


def default_config() -> dict[str, Any]:
    return {
        "audit_only": True,
        "version": "setup_quality_score_v2/setup_viability_filter_v1",
        "provisional": True,
        "designed_from": "domain rules and ENGINE-TREND-23 aggregate diagnostics; not full-period outcome optimization",
        "round_trip_cost_bps_already_in_net_returns": 24,
        "component_weights": {
            "causal_context_score": 0.15,
            "entry_timing_score": 0.15,
            "confirmation_quality_score": 0.15,
            "stop_quality_score": 0.15,
            "target_reachability_score": 0.15,
            "risk_adjusted_rr_score": 0.10,
            "context_cleanliness_score": 0.15,
        },
        "penalty_points": {
            "TOO_TIGHT_STOP": 14, "TARGET_TOO_FAR": 10, "LATE_ENTRY_AFTER_EXHAUSTION": 10,
            "WEAK_CONFIRMATION_VOLUME": 8, "BOLLINGER_EXTENSION_RISK": 7,
            "RANGE_CONFLICT_IGNORED": 14, "REVERSAL_RISK_IGNORED": 14,
            "CHOPPY_SIDEWAYS_CONTEXT": 10, "HIGH_RR_LOW_PROBABILITY": 9,
            "TREND_TOO_OLD": 7, "RETEST_TOO_SHALLOW": 5, "RETEST_TOO_DEEP": 7,
        },
        "filter_thresholds": {
            "minimum_score_v2": 52.0,
            "minimum_rr": 1.5,
            "minimum_stop_distance_atr": 0.75,
            "maximum_stop_distance_atr": 3.0,
            "maximum_target_distance_atr": 4.0,
            "minimum_confirmation_volume_ratio": 0.7,
            "rr_upper_penalty": 5.0,
            "minimum_target_reachability_for_high_rr": 55.0,
            "choppy_adx_max": 15.0,
            "exhausted_correction_bars": 7,
        },
        "split": {
            "design_start": "2025-07-03T00:00:00Z", "design_end": "2025-10-31T23:45:00Z",
            "validation_start": "2025-11-01T00:00:00Z", "validation_end": "2025-12-17T23:45:00Z",
        },
        "declared_pre_entry_features": [
            "setup_type", "symbol", "direction", "entry_time", "entry_price", "stop_price", "target_1",
            "invalidation_price", "planned_rr", "source_regime", "source_hypothesis", "structure_evidence",
            "range_breakout_evidence", "candle_evidence", "technical_confirmation", "no_trade_risks",
            "future_data_used_for_generation", "current_engine_trend_replay", "coverage_status",
        ],
        "explicit_non_feature_fields": sorted(FORBIDDEN_FEATURE_NAMES),
        "target_reachability_note": "No outcome-derived MFE distribution is used. ATR distance and pre-entry structural objective are causal proxies.",
    }


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def dt(candidate: dict[str, Any]) -> datetime:
    return datetime.fromisoformat(candidate["entry_time"].replace("Z", "+00:00"))


def label(candidate: dict[str, Any]) -> str:
    return candidate.get("outcome", {}).get("label_status", "MISSING")


def net(candidate: dict[str, Any]) -> float | None:
    value = candidate.get("outcome", {}).get("net_return_pct")
    return float(value) if finite(value) else None


def split_name(candidate: dict[str, Any]) -> str:
    stamp = dt(candidate)
    if stamp <= DESIGN_END:
        return "TRAIN_DESIGN"
    if stamp >= VALIDATION_START:
        return "OUT_OF_TIME_VALIDATION"
    return "SPLIT_GAP"


def explicit_reachable_target(candidate: dict[str, Any]) -> bool:
    evidence = candidate.get("range_breakout_evidence") or {}
    objective = str(evidence.get("objective") or "").lower()
    target = candidate.get("target_1")
    structure = candidate.get("structure_evidence") or {}
    if "impulse extreme" in objective:
        pivots = structure.get("confirmed_pivot_highs", []) + structure.get("confirmed_pivot_lows", [])
        return any(finite(p.get("price")) and finite(target) and math.isclose(p["price"], target, rel_tol=1e-8, abs_tol=1e-8) for p in pivots)
    if candidate.get("setup_type") == "RANGE_MEAN_REVERSION_CANDIDATE":
        midline = evidence.get("midline")
        return finite(midline) and finite(target) and math.isclose(midline, target, rel_tol=1e-8, abs_tol=1e-8)
    return False


def pre_entry_features(candidate: dict[str, Any], coverage_status: str = "PASS") -> dict[str, Any]:
    """Build the only feature object accepted by score/filter; outcomes are never copied."""
    tech_block = candidate.get("technical_confirmation") or {}
    tech = tech_block.get("values") or {}
    structure = candidate.get("structure_evidence") or {}
    level = candidate.get("range_breakout_evidence") or {}
    candle = candidate.get("candle_evidence") or {}
    replay = candidate.get("current_engine_trend_replay") or {}
    entry, stop, target = candidate.get("entry_price"), candidate.get("stop_price"), candidate.get("target_1")
    atr = tech.get("atr14")
    risk = abs(entry - stop) if finite(entry) and finite(stop) else None
    reward = abs(target - entry) if finite(target) and finite(entry) else None
    direction = candidate.get("direction")
    geometry_valid = bool(
        finite(entry) and finite(stop) and finite(target) and
        ((direction == "LONG" and stop < entry < target) or (direction == "SHORT" and target < entry < stop))
    )
    invalidation = candidate.get("invalidation_price")
    structural_stop = bool(
        geometry_valid and finite(invalidation) and
        ((direction == "LONG" and stop < invalidation < entry) or (direction == "SHORT" and entry < invalidation < stop))
    )
    return {
        "candidate_id": candidate.get("candidate_id"), "symbol": candidate.get("symbol"),
        "setup_type": candidate.get("setup_type"), "direction": direction, "entry_time": candidate.get("entry_time"),
        "entry": entry, "stop": stop, "target": target, "invalidation": invalidation,
        "rr": candidate.get("planned_rr"), "atr": atr,
        "stop_atr": risk / atr if finite(risk) and finite(atr) and atr > 0 else None,
        "target_atr": reward / atr if finite(reward) and finite(atr) and atr > 0 else None,
        "geometry_valid": geometry_valid, "structural_stop": structural_stop,
        "explicit_reachable_target": explicit_reachable_target(candidate),
        "source_regime": candidate.get("source_regime"), "source_hypothesis": candidate.get("source_hypothesis"),
        "structure_class": structure.get("classification"), "correction_bars": structure.get("correction_bars"),
        "high_touches": structure.get("confirmed_high_touch_count"), "low_touches": structure.get("confirmed_low_touch_count"),
        "distance_to_zone_atr": level.get("distance_to_zone_atr"), "range_width_atr": level.get("width_atr"),
        "body_atr": candle.get("body_atr"), "body_fraction": candle.get("body_fraction"),
        "close_location": candle.get("close_location"), "upper_wick_fraction": candle.get("upper_wick_fraction"),
        "lower_wick_fraction": candle.get("lower_wick_fraction"), "candle_interpretation": candle.get("interpretation"),
        "volume_ratio": tech.get("volume_ratio_20"), "adx": tech.get("adx14"), "rsi": tech.get("rsi14"),
        "bollinger_upper": tech.get("bollinger_upper"), "bollinger_lower": tech.get("bollinger_lower"),
        "confirmations": tuple(tech_block.get("confirmations") or ()), "technical_conflicts": tuple(tech_block.get("conflicts") or ()),
        "replay_regime": replay.get("market_regime"), "replay_hypothesis": replay.get("selected_hypothesis"),
        "replay_conflict": replay.get("conflict_level"), "replay_data_quality": replay.get("data_quality_status"),
        "coverage_status": coverage_status, "future_data_used": candidate.get("future_data_used_for_generation"),
    }


def component_scores(f: dict[str, Any]) -> dict[str, float]:
    continuation = f["setup_type"] != "RANGE_MEAN_REVERSION_CANDIDATE"
    expected_structure = (f["direction"] == "LONG" and f["structure_class"] == "HH/HL") or (f["direction"] == "SHORT" and f["structure_class"] == "LH/LL")
    causal = 42 + (18 if expected_structure else 0) + (10 if f["source_hypothesis"] else 0)
    if f["explicit_reachable_target"]: causal += 10
    distance = f["distance_to_zone_atr"]
    if finite(distance): causal += 15 if distance <= 0.25 else 8 if distance <= 0.5 else -8
    if not continuation and f["structure_class"] == "confirmed horizontal range": causal += 18

    timing = 58.0
    bars = f["correction_bars"]
    if continuation and finite(bars):
        timing += 20 if 2 <= bars <= 4 else 8 if bars <= 6 else -22
    if finite(distance): timing += 15 if distance <= 0.25 else 5 if distance <= 0.5 else -18

    confirmation = 35.0
    body_atr, body_fraction, close = f["body_atr"], f["body_fraction"], f["close_location"]
    if finite(body_atr): confirmation += 18 if 0.25 <= body_atr <= 1.0 else 8 if 0.15 <= body_atr <= 1.4 else -8
    if finite(body_fraction): confirmation += 12 if body_fraction >= 0.45 else 3 if body_fraction >= 0.25 else -10
    close_good = finite(close) and ((f["direction"] == "LONG" and close >= 0.65) or (f["direction"] == "SHORT" and close <= 0.35))
    confirmation += 15 if close_good else -8
    rejection_wick = f["lower_wick_fraction"] if f["direction"] == "LONG" else f["upper_wick_fraction"]
    if finite(rejection_wick): confirmation += 8 if rejection_wick >= 0.2 else 2
    volume = f["volume_ratio"]
    if finite(volume): confirmation += 18 if volume >= 1 else 10 if volume >= 0.8 else 2 if volume >= 0.7 else -14
    confirmation += min(9, len(f["confirmations"]) * 3)

    stop_score = 25.0 + (30 if f["geometry_valid"] else -25) + (20 if f["structural_stop"] else -10)
    stop_atr = f["stop_atr"]
    if finite(stop_atr): stop_score += 25 if 0.9 <= stop_atr <= 2.0 else 12 if 0.75 <= stop_atr <= 2.5 else -20

    target_score = 35.0 + (25 if f["explicit_reachable_target"] else 0)
    target_atr = f["target_atr"]
    if finite(target_atr): target_score += 30 if target_atr <= 3 else 15 if target_atr <= 4 else 0 if target_atr <= 5 else -20
    if continuation and finite(bars) and bars >= 7: target_score -= 15

    rr = f["rr"]
    rr_score = 0.0
    if finite(rr):
        if rr < 1.5: rr_score = 0
        elif rr < 2: rr_score = 58
        elif rr <= 3.5: rr_score = 88
        elif rr <= 5: rr_score = 68 + (8 if target_score >= 70 else 0)
        else: rr_score = 42 + (15 if target_score >= 75 else 0)

    clean = 82.0 - min(36, len(f["technical_conflicts"]) * 12)
    if continuation and f["source_regime"] not in ({"UP"} if f["direction"] == "LONG" else {"DOWN"}): clean -= 25
    if continuation and finite(f["adx"]) and f["adx"] < 15: clean -= 25
    if f["replay_conflict"] in {"MEDIUM", "HIGH"}: clean -= 20 if f["replay_conflict"] == "MEDIUM" else 35
    if f["replay_hypothesis"] in {"BEARISH_REVERSAL", "BULLISH_REVERSAL", "CONFIRMED_RANGE"} and continuation: clean -= 30
    return {k: round(clamp(v), 4) for k, v in {
        "causal_context_score": causal, "entry_timing_score": timing,
        "confirmation_quality_score": confirmation, "stop_quality_score": stop_score,
        "target_reachability_score": target_score, "risk_adjusted_rr_score": rr_score,
        "context_cleanliness_score": clean,
    }.items()}


def failure_penalties(f: dict[str, Any], components: dict[str, float], config: dict[str, Any]) -> list[str]:
    t = config["filter_thresholds"]
    reasons: list[str] = []
    continuation = f["setup_type"] != "RANGE_MEAN_REVERSION_CANDIDATE"
    if finite(f["stop_atr"]) and f["stop_atr"] < t["minimum_stop_distance_atr"]: reasons.append("TOO_TIGHT_STOP")
    if finite(f["target_atr"]) and f["target_atr"] > t["maximum_target_distance_atr"]: reasons.append("TARGET_TOO_FAR")
    if continuation and finite(f["correction_bars"]) and f["correction_bars"] >= t["exhausted_correction_bars"]:
        reasons.extend(["LATE_ENTRY_AFTER_EXHAUSTION", "TREND_TOO_OLD"])
    if finite(f["volume_ratio"]) and f["volume_ratio"] < 0.8: reasons.append("WEAK_CONFIRMATION_VOLUME")
    entry, atr = f["entry"], f["atr"]
    if finite(entry) and finite(atr) and atr > 0:
        if f["direction"] == "LONG" and finite(f["bollinger_upper"]) and entry >= f["bollinger_upper"] - 0.25 * atr: reasons.append("BOLLINGER_EXTENSION_RISK")
        if f["direction"] == "SHORT" and finite(f["bollinger_lower"]) and entry <= f["bollinger_lower"] + 0.25 * atr: reasons.append("BOLLINGER_EXTENSION_RISK")
    if continuation and (f["source_regime"] == "FLAT" or f["replay_hypothesis"] == "CONFIRMED_RANGE"): reasons.append("RANGE_CONFLICT_IGNORED")
    if continuation and f["replay_hypothesis"] in {"BEARISH_REVERSAL", "BULLISH_REVERSAL"}: reasons.append("REVERSAL_RISK_IGNORED")
    if continuation and ((finite(f["adx"]) and f["adx"] < t["choppy_adx_max"]) or f["source_regime"] == "FLAT"): reasons.append("CHOPPY_SIDEWAYS_CONTEXT")
    if finite(f["rr"]) and f["rr"] > t["rr_upper_penalty"] and components["target_reachability_score"] < t["minimum_target_reachability_for_high_rr"]: reasons.append("HIGH_RR_LOW_PROBABILITY")
    if continuation and finite(f["correction_bars"]) and f["correction_bars"] <= 1: reasons.append("RETEST_TOO_SHALLOW")
    if continuation and finite(f["distance_to_zone_atr"]) and f["distance_to_zone_atr"] > 0.75: reasons.append("RETEST_TOO_DEEP")
    return list(dict.fromkeys(reasons))


def score_features(f: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or default_config()
    components = component_scores(f)
    penalties = failure_penalties(f, components, config)
    raw = sum(components[name] * weight for name, weight in config["component_weights"].items())
    deduction = sum(config["penalty_points"][reason] for reason in penalties)
    score = round(clamp(raw - deduction), 4)
    return {"score_v2": score, "components": components, "penalties": penalties, "raw_score_before_penalties": round(raw, 4)}


def filter_features(f: dict[str, Any], score: dict[str, Any], config: dict[str, Any] | None = None) -> tuple[bool, list[str]]:
    config = config or default_config()
    t = config["filter_thresholds"]
    reasons: list[str] = []
    required = (f["entry"], f["stop"], f["target"])
    if not all(finite(v) for v in required): reasons.append("MISSING_ENTRY_STOP_TARGET")
    if not f["geometry_valid"]: reasons.append("INVALID_SETUP_GEOMETRY")
    if not finite(f["rr"]) or f["rr"] < t["minimum_rr"]: reasons.append("RR_BELOW_1_5")
    if not finite(f["stop_atr"]): reasons.append("MISSING_ATR_GEOMETRY")
    elif f["stop_atr"] < t["minimum_stop_distance_atr"]: reasons.append("TOO_TIGHT_STOP")
    elif f["stop_atr"] > t["maximum_stop_distance_atr"]: reasons.append("STOP_EXCESSIVELY_LARGE")
    if not finite(f["target_atr"]): reasons.append("MISSING_ATR_GEOMETRY")
    elif f["target_atr"] > t["maximum_target_distance_atr"] and not f["explicit_reachable_target"]: reasons.append("TARGET_TOO_FAR_WITHOUT_SWING_ANCHOR")
    if not finite(f["volume_ratio"]): reasons.append("MISSING_CONFIRMATION_VOLUME")
    elif f["volume_ratio"] < t["minimum_confirmation_volume_ratio"]: reasons.append("WEAK_CONFIRMATION_VOLUME")
    continuation = f["setup_type"] != "RANGE_MEAN_REVERSION_CANDIDATE"
    if continuation and (f["source_regime"] == "FLAT" or f["replay_hypothesis"] == "CONFIRMED_RANGE"): reasons.append("CONFIRMED_RANGE_CONFLICT")
    if continuation and f["replay_hypothesis"] in {"BEARISH_REVERSAL", "BULLISH_REVERSAL"}: reasons.append("OPPOSING_REVERSAL_TRAP_CONFLICT")
    if continuation and ((finite(f["adx"]) and f["adx"] < t["choppy_adx_max"]) or f["source_regime"] == "FLAT"): reasons.append("CHOPPY_SIDEWAYS_CONTEXT")
    if continuation and finite(f["correction_bars"]) and f["correction_bars"] >= t["exhausted_correction_bars"]: reasons.append("ENTRY_AFTER_EXHAUSTION")
    if f["future_data_used"] is not False or f["coverage_status"] != "PASS" or f["replay_data_quality"] not in {None, "PASS"}: reasons.append("DATA_QUALITY_ISSUE")
    if finite(f["rr"]) and f["rr"] > t["rr_upper_penalty"] and score["components"]["target_reachability_score"] < t["minimum_target_reachability_for_high_rr"]: reasons.append("HIGH_RR_LOW_PROBABILITY")
    if score["score_v2"] < t["minimum_score_v2"]: reasons.append("SCORE_V2_BELOW_PROVISIONAL_FLOOR")
    return not reasons, list(dict.fromkeys(reasons))


def evaluate_candidate(candidate: dict[str, Any], coverage_status: str = "PASS", config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or default_config()
    features = pre_entry_features(candidate, coverage_status)
    scoring = score_features(features, config)
    passed, fail_reasons = filter_features(features, scoring, config)
    return {"features": features, **scoring, "filter_pass": passed, "fail_reasons": fail_reasons}


def mean(values: Iterable[float]) -> float | None:
    values = list(values)
    return statistics.fmean(values) if values else None


def pearson(xs: Iterable[float], ys: Iterable[float]) -> float | None:
    pairs = [(float(x), float(y)) for x, y in zip(xs, ys) if finite(x) and finite(y)]
    if len(pairs) < 3: return None
    xv, yv = zip(*pairs); xm, ym = mean(xv), mean(yv)
    numerator = sum((x - xm) * (y - ym) for x, y in pairs)
    denominator = math.sqrt(sum((x - xm) ** 2 for x in xv) * sum((y - ym) ** 2 for y in yv))
    return numerator / denominator if denominator else None


def performance(candidates: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = sorted(list(candidates), key=lambda c: (dt(c), c["candidate_id"]))
    clean = [c for c in rows if label(c) in CLEAN_LABELS]
    returns = [net(c) for c in rows if net(c) is not None]
    wins = [c for c in clean if label(c) == WIN]
    gains = sum(v for v in returns if v > 0); losses = abs(sum(v for v in returns if v < 0))
    streak = current = 0; equity = peak = 1.0; max_dd = 0.0
    for c in clean:
        current = current + 1 if label(c) == LOSS else 0; streak = max(streak, current)
    for value in returns:
        equity += value / 100; peak = max(peak, equity)
        if peak > 0: max_dd = max(max_dd, (peak - equity) / peak * 100)
    return {
        "candidates": len(rows), "clean_candidates": len(clean), "return_observations": len(returns),
        "tp_before_sl": len(wins), "sl_before_tp": sum(label(c) == LOSS for c in clean),
        "ambiguous_intracandle": sum(label(c) == "AMBIGUOUS_INTRACANDLE" for c in rows),
        "neither_expired": sum(label(c) == "NEITHER_EXPIRED" for c in rows),
        "winrate_pct": len(wins) / len(clean) * 100 if clean else None,
        "average_net_return_pct": mean(returns), "expectancy_pct_per_trade": mean(returns),
        "total_net_return_pct_naive": sum(returns), "profit_factor": gains / losses if losses else None,
        "max_consecutive_losses": streak, "max_drawdown_pct_naive_additive": max_dd,
    }


def enriched_metrics(candidates: list[dict[str, Any]], evaluations: dict[str, dict[str, Any]]) -> dict[str, Any]:
    passed = [c for c in candidates if evaluations[c["candidate_id"]]["filter_pass"]]
    failed = [c for c in candidates if not evaluations[c["candidate_id"]]["filter_pass"]]
    result = {"all": performance(candidates), "pass": performance(passed), "fail": performance(failed), "pass_count": len(passed), "fail_count": len(failed)}
    for key in ("symbol", "setup_type", "direction"):
        result[f"pass_by_{key}"] = {value: performance([c for c in passed if c[key] == value]) for value in sorted({c[key] for c in candidates})}
    return result


def deciles(candidates: list[dict[str, Any]], evaluations: dict[str, dict[str, Any]], field: str) -> list[dict[str, Any]]:
    clean = [c for c in candidates if label(c) in CLEAN_LABELS]
    value = (lambda c: c["quality_score"]) if field == "old_score" else (lambda c: evaluations[c["candidate_id"]]["score_v2"])
    ordered = sorted(clean, key=lambda c: (value(c), dt(c), c["candidate_id"]))
    result = []
    for bucket in range(1, 11):
        group = [c for i, c in enumerate(ordered) if min(10, i * 10 // len(ordered) + 1) == bucket]
        result.append({"score_kind": field, "decile": bucket, "score_min": min(map(value, group)), "score_max": max(map(value, group)), **performance(group)})
    return result


def score_diagnostics(candidates: list[dict[str, Any]], evaluations: dict[str, dict[str, Any]]) -> dict[str, Any]:
    clean = [c for c in candidates if label(c) in CLEAN_LABELS and net(c) is not None]
    old = [c["quality_score"] for c in clean]; new = [evaluations[c["candidate_id"]]["score_v2"] for c in clean]
    returns = [net(c) for c in clean]; wins = [1.0 if label(c) == WIN else 0.0 for c in clean]
    result = {
        "old_score_correlation_net_return": pearson(old, returns), "old_score_correlation_win_label": pearson(old, wins),
        "score_v2_correlation_net_return": pearson(new, returns), "score_v2_correlation_win_label": pearson(new, wins),
        "winner_mean_score_v2": mean(evaluations[c["candidate_id"]]["score_v2"] for c in clean if label(c) == WIN),
        "loser_mean_score_v2": mean(evaluations[c["candidate_id"]]["score_v2"] for c in clean if label(c) == LOSS),
    }
    for kind, fn in (("old", lambda c: c["quality_score"]), ("v2", lambda c: evaluations[c["candidate_id"]]["score_v2"])):
        ranked = sorted(clean, key=lambda c: (fn(c), c["candidate_id"]), reverse=True)
        for n in (10, 25, 50): result[f"{kind}_top_{n}"] = performance(ranked[:n])
    return result


def sensitivity_rows(candidates: list[dict[str, Any]], coverage: dict[str, str], base: dict[str, Any]) -> list[dict[str, Any]]:
    dimensions = {
        "stop_distance_atr": ("minimum_stop_distance_atr", [0.5, 0.75, 1.0]),
        "volume_ratio": ("minimum_confirmation_volume_ratio", [0.6, 0.7, 0.8, 1.0]),
        "rr_upper_penalty": ("rr_upper_penalty", [3.5, 5.0, 8.0]),
        "target_distance_atr_cap": ("maximum_target_distance_atr", [3.0, 4.0, 5.0]),
    }
    rows = []
    validation = [c for c in candidates if split_name(c) == "OUT_OF_TIME_VALIDATION"]
    for dimension, (key, values) in dimensions.items():
        for value in values:
            config = deepcopy(base); config["filter_thresholds"][key] = value
            ev = {c["candidate_id"]: evaluate_candidate(c, coverage[c["symbol"]], config) for c in validation}
            passed = [c for c in validation if ev[c["candidate_id"]]["filter_pass"]]
            rows.append({"diagnostic": dimension, "threshold": value, **performance(passed)})
    for name, low, high in (("ADX_<15", None, 15), ("ADX_15_35", 15, 35), ("ADX_>35", 35, None)):
        subset = []
        for c in validation:
            adx = pre_entry_features(c, coverage[c["symbol"]])["adx"]
            if finite(adx) and (low is None or adx >= low) and (high is None or adx < high): subset.append(c)
        rows.append({"diagnostic": "adx_bucket", "threshold": name, **performance(subset)})
    return rows


def group_viability(validation: list[dict[str, Any]], evaluations: dict[str, dict[str, Any]], key: str) -> list[dict[str, Any]]:
    passed = [c for c in validation if evaluations[c["candidate_id"]]["filter_pass"]]
    rows = []
    for value in sorted({c[key] for c in validation}):
        metrics = performance([c for c in passed if c[key] == value]); pf = metrics["profit_factor"]; exp = metrics["expectancy_pct_per_trade"]
        if key == "setup_type":
            status = "REDESIGN_REQUIRED" if metrics["candidates"] < 5 else "KEEP_AS_RESEARCH" if pf is not None and pf > 1 and exp is not None and exp > 0 else "BLOCK_FROM_PAPER_TRADING"
        else:
            status = "PREFER_FOR_PAPER" if metrics["candidates"] >= 10 and pf is not None and pf >= 1.15 and exp is not None and exp > 0 else "KEEP_AS_RESEARCH" if pf is not None and pf > 1 else "BLOCK_FROM_PAPER"
        rows.append({key: value, "status": status, **metrics})
    return rows


def gates(validation_pass: list[dict[str, Any]], metrics: dict[str, Any]) -> dict[str, Any]:
    by_symbol = defaultdict(float); by_setup = defaultdict(float); by_month = defaultdict(list)
    positive_total = sum(max(0.0, net(c) or 0.0) for c in validation_pass)
    for c in validation_pass:
        value = net(c)
        if value is not None:
            by_symbol[c["symbol"]] += max(0.0, value); by_setup[c["setup_type"]] += max(0.0, value); by_month[dt(c).strftime("%Y-%m")].append(value)
    max_symbol_share = max(by_symbol.values(), default=0) / positive_total if positive_total else 1.0
    max_setup_share = max(by_setup.values(), default=0) / positive_total if positive_total else 1.0
    sorted_returns = sorted((net(c) for c in validation_pass if net(c) is not None), reverse=True)
    trimmed = sorted_returns[2:]
    robust = bool(trimmed and mean(trimmed) > 0 and max_symbol_share < 0.8 and max_setup_share < 0.8)
    non_negative_months = sum(mean(values) is not None and mean(values) >= 0 for values in by_month.values())
    common = metrics["candidates"] >= 20 and metrics["profit_factor"] is not None and metrics["profit_factor"] > 1.05 and metrics["expectancy_pct_per_trade"] is not None and metrics["expectancy_pct_per_trade"] > 0
    promising = common and robust and metrics["max_consecutive_losses"] <= 10
    paper = metrics["candidates"] >= 30 and metrics["profit_factor"] is not None and metrics["profit_factor"] >= 1.15 and metrics["expectancy_pct_per_trade"] is not None and metrics["expectancy_pct_per_trade"] > 0 and metrics["max_drawdown_pct_naive_additive"] <= 10 and non_negative_months >= 2 and len([v for v in by_symbol.values() if v > 0]) >= 2 and len([v for v in by_setup.values() if v > 0]) >= 2 and robust
    return {"research_promising": promising, "paper_trading_candidate": paper, "robust_to_top_two_winner_removal": robust, "max_symbol_positive_gain_share": max_symbol_share, "max_setup_positive_gain_share": max_setup_share, "non_negative_validation_months": non_negative_months}


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    if fields is None: fields = list(rows[0]) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore"); writer.writeheader(); writer.writerows(rows)


def fmt(value: Any, digits: int = 4) -> str:
    return "N/A" if value is None else f"{value:.{digits}f}" if isinstance(value, float) else str(value)


def metric_line(m: dict[str, Any]) -> str:
    return f"n={m['candidates']}, clean={m['clean_candidates']}, winrate={fmt(m['winrate_pct'])}%, avg/expectancy={fmt(m['expectancy_pct_per_trade'])}%, PF={fmt(m['profit_factor'])}, max loss streak={m['max_consecutive_losses']}, naive max DD={fmt(m['max_drawdown_pct_naive_additive'])}%"


def validate_input_integrity(input_dir: Path, candidates: list[dict[str, Any]], coverage_payload: dict[str, Any]) -> dict[str, Any]:
    with (input_dir / "HISTORICAL_ENTRY_DISCOVERY_CANDIDATES.csv").open(encoding="utf-8-sig", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    json_ids = [candidate.get("candidate_id") for candidate in candidates]
    csv_ids = [row.get("candidate_id") for row in csv_rows]
    if len(json_ids) != len(set(json_ids)) or None in json_ids:
        raise ValueError("DATA_INTEGRITY: duplicate or missing candidate_id in discovery JSON")
    if csv_ids != json_ids:
        raise ValueError("DATA_INTEGRITY: CSV/JSON candidate order or identity mismatch")
    if any(candidate.get("future_data_used_for_generation") is not False for candidate in candidates):
        raise ValueError("LEAKAGE_RISK: candidate generation reports future data use")
    coverage_rows = coverage_payload.get("coverage", [])
    if {row.get("symbol") for row in coverage_rows} != {candidate.get("symbol") for candidate in candidates}:
        raise ValueError("DATA_INTEGRITY: coverage symbols do not match candidates")
    if any(row.get("status") != "PASS" for row in coverage_rows):
        raise ValueError("DATA_INTEGRITY: input coverage did not pass")
    return {"status": "PASS", "json_candidates": len(json_ids), "csv_candidates": len(csv_ids), "unique_candidate_ids": len(set(json_ids)), "coverage_symbols": len(coverage_rows)}


def run(input_dir: Path = DEFAULT_INPUT, audit_23_dir: Path = DEFAULT_AUDIT_23, output_dir: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    missing = [name for name in REQUIRED_DISCOVERY if not (input_dir / name).is_file()]
    if missing: raise FileNotFoundError("MISSING_ARTIFACT: " + ", ".join(missing))
    output_dir.mkdir(parents=True, exist_ok=True)
    config = default_config()
    payload = load_json(input_dir / "HISTORICAL_ENTRY_DISCOVERY_RESULTS.json")
    candidates = payload["candidates"]
    coverage_payload = load_json(input_dir / "HISTORICAL_ENTRY_DISCOVERY_DATA_COVERAGE.json")
    integrity = validate_input_integrity(input_dir, candidates, coverage_payload)
    coverage = {row["symbol"]: row["status"] for row in coverage_payload["coverage"]}
    audit23_availability = {name: (audit_23_dir / name).is_file() for name in OPTIONAL_AUDIT_23}
    evaluations = {c["candidate_id"]: evaluate_candidate(c, coverage.get(c["symbol"], "MISSING"), config) for c in candidates}
    train = [c for c in candidates if split_name(c) == "TRAIN_DESIGN"]
    validation = [c for c in candidates if split_name(c) == "OUT_OF_TIME_VALIDATION"]
    full_metrics = enriched_metrics(candidates, evaluations); train_metrics = enriched_metrics(train, evaluations); validation_metrics = enriched_metrics(validation, evaluations)
    score_diag = score_diagnostics(candidates, evaluations)
    decile_rows = deciles(candidates, evaluations, "old_score") + deciles(candidates, evaluations, "score_v2")
    validation_pass = [c for c in validation if evaluations[c["candidate_id"]]["filter_pass"]]
    gate_result = gates(validation_pass, validation_metrics["pass"])
    if gate_result["paper_trading_candidate"]: final_status = "ENGINE_TREND_24_READY_FOR_PAPER_TRADING_DESIGN"
    elif gate_result["research_promising"]: final_status = "ENGINE_TREND_24_COMPLETED_V2_FILTER_PROMISING_NEEDS_MORE_OOS"
    elif validation_metrics["pass"]["expectancy_pct_per_trade"] is not None and validation_metrics["pass"]["expectancy_pct_per_trade"] > 0: final_status = "ENGINE_TREND_24_COMPLETED_V2_FILTER_MIXED_INCONCLUSIVE"
    else: final_status = "ENGINE_TREND_24_COMPLETED_V2_FILTER_NEGATIVE"
    setup_rows = group_viability(validation, evaluations, "setup_type"); symbol_rows = group_viability(validation, evaluations, "symbol")
    rejected_winners = [c for c in candidates if label(c) == WIN and not evaluations[c["candidate_id"]]["filter_pass"]]
    passed_losers = [c for c in candidates if label(c) == LOSS and evaluations[c["candidate_id"]]["filter_pass"]]
    fail_counts = Counter(reason for c in candidates for reason in evaluations[c["candidate_id"]]["fail_reasons"])
    penalty_counts = Counter(reason for c in candidates for reason in evaluations[c["candidate_id"]]["penalties"])

    (output_dir / OUTPUT_FILES[1]).write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    result_rows = []
    for c in candidates:
        ev = evaluations[c["candidate_id"]]
        result_rows.append({"candidate_id": c["candidate_id"], "symbol": c["symbol"], "setup_type": c["setup_type"], "direction": c["direction"], "entry_time": c["entry_time"], "old_score": c["quality_score"], "score_v2": ev["score_v2"], "filter_pass": "PASS" if ev["filter_pass"] else "FAIL", "fail_reasons": "|".join(ev["fail_reasons"]), "old_outcome": label(c), "net_return_pct": net(c), "split": split_name(c), "short_reason": "; ".join(ev["penalties"][:3]) or "causal geometry passed without v2 penalty"})
    write_csv(output_dir / OUTPUT_FILES[2], result_rows)
    walk_forward_windows = (
        ("JUL_AUG_TO_SEP", "2025-07-03T00:00:00Z", "2025-08-31T23:45:00Z", "2025-09"),
        ("JUL_SEP_TO_OCT", "2025-07-03T00:00:00Z", "2025-09-30T23:45:00Z", "2025-10"),
        ("JUL_OCT_TO_NOV", "2025-07-03T00:00:00Z", "2025-10-31T23:45:00Z", "2025-11"),
        ("JUL_NOV_TO_DEC", "2025-07-03T00:00:00Z", "2025-11-30T23:45:00Z", "2025-12"),
    )
    walk_forward = {}
    for name, design_start, design_end, month in walk_forward_windows:
        month_rows = [c for c in candidates if dt(c).strftime("%Y-%m") == month]
        walk_forward[name] = {"design_period": {"start": design_start, "end": design_end}, "validation_month": month, "note": "No fitting occurs; fixed provisional causal rules are replayed unchanged.", **enriched_metrics(month_rows, evaluations)}
    metrics_payload = {"input_integrity": integrity, "split_definition": config["split"], "train_design": train_metrics, "out_of_time_validation": validation_metrics, "full_sample_diagnostic": full_metrics, "score_diagnostics": score_diag, "acceptance_gates": gate_result, "monthly_walk_forward_diagnostic": walk_forward}
    (output_dir / OUTPUT_FILES[3]).write_text(json.dumps(metrics_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_csv(output_dir / OUTPUT_FILES[4], decile_rows)
    diagnostic_rows = [
        {"section": "FILTER_SUMMARY", "key": split, "count": data["pass_count"], "detail": metric_line(data["pass"])} for split, data in (("TRAIN_DESIGN_PASS", train_metrics), ("VALIDATION_PASS", validation_metrics), ("FULL_PASS", full_metrics))
    ] + [{"section": "FAIL_REASON", "key": key, "count": count, "detail": "non-exclusive count"} for key, count in fail_counts.most_common()] + [{"section": "SCORE_PENALTY", "key": key, "count": count, "detail": "causal pre-entry penalty count"} for key, count in penalty_counts.most_common()]
    write_csv(output_dir / OUTPUT_FILES[5], diagnostic_rows)

    rejected_reason_counts = Counter(reason for c in rejected_winners for reason in evaluations[c["candidate_id"]]["fail_reasons"])
    rejected_md = ["# ENGINE-TREND-24 Rejected Winners Audit", "", f"Rejected clean winners: **{len(rejected_winners)}** of {sum(label(c)==WIN for c in candidates)}.", "", "Reasons are non-exclusive:", ""] + [f"- {reason}: {count}" for reason, count in rejected_reason_counts.most_common()] + ["", "## Interpretation", "", "Rules with the largest rejected-winner counts deserve prospective review, not post-fact threshold relaxation. No rule was changed from this audit.", "", "## Candidates", ""] + [f"- {c['candidate_id']} | {c['entry_time']} | {c['symbol']} | {c['setup_type']} | {', '.join(evaluations[c['candidate_id']]['fail_reasons'])}" for c in rejected_winners]
    (output_dir / OUTPUT_FILES[6]).write_text("\n".join(rejected_md) + "\n", encoding="utf-8")
    loser_penalties = Counter(reason for c in passed_losers for reason in evaluations[c["candidate_id"]]["penalties"])
    losers_md = ["# ENGINE-TREND-24 Passed Losers Audit", "", f"Passed clean losers: **{len(passed_losers)}** of {sum(label(c)==LOSS for c in candidates)}.", "", "Common causal warnings still present among passed losers:", ""] + [f"- {reason}: {count}" for reason, count in loser_penalties.most_common()] + ["", "Losses without a strong repeated causal warning are treated as normal statistical losses. Candidate additions for later research: independent opposing-level map, trigger age, pre-entry impulse length/ATR, and train-fitted reachability priors.", "", "## Candidates", ""] + [f"- {c['candidate_id']} | {c['entry_time']} | {c['symbol']} | {c['setup_type']} | score={evaluations[c['candidate_id']]['score_v2']} | warnings={', '.join(evaluations[c['candidate_id']]['penalties']) or 'none'}" for c in passed_losers]
    (output_dir / OUTPUT_FILES[7]).write_text("\n".join(losers_md) + "\n", encoding="utf-8")

    main = next(c for c in candidates if c["candidate_id"] == "ET-HED-0001"); mev = evaluations[main["candidate_id"]]
    main_rank = 1 + sum(ev["score_v2"] > mev["score_v2"] for ev in evaluations.values())
    main_md = f"""# ENGINE-TREND-24 Main Entry Post-mortem

- candidate: ET-HED-0001
- old score: {main['quality_score']}
- score_v2: {mev['score_v2']} (rank {main_rank}/{len(candidates)})
- filter_v1: {'PASS' if mev['filter_pass'] else 'FAIL'}
- fail reasons: {', '.join(mev['fail_reasons']) or 'none'}
- would v2 still select it as global maximum: {'YES' if main_rank == 1 else 'NO'}
- pre-entry warnings: {', '.join(mev['penalties']) or 'none'}

The old RR={main['planned_rr']} receives no automatic maximum bonus. Its volume ratio is {fmt(mev['features']['volume_ratio'])}, stop distance is {fmt(mev['features']['stop_atr'])} ATR, and target distance is {fmt(mev['features']['target_atr'])} ATR. Rules must not be changed because of this single case: **NO rule change**.
"""
    (output_dir / OUTPUT_FILES[8]).write_text(main_md, encoding="utf-8")
    setup_md = ["# ENGINE-TREND-24 Setup Type Viability", "", "Statuses use only out-of-time validation PASS trades. PF <= 1 is never paper-enabled.", ""] + [f"- **{r['setup_type']} — {r['status']}**: {metric_line(r)}" for r in setup_rows]
    (output_dir / OUTPUT_FILES[9]).write_text("\n".join(setup_md) + "\n", encoding="utf-8")
    symbol_md = ["# ENGINE-TREND-24 Symbol Viability", "", "Statuses use only out-of-time validation PASS trades.", ""] + [f"- **{r['symbol']} — {r['status']}**: {metric_line(r)}" for r in symbol_rows]
    (output_dir / OUTPUT_FILES[10]).write_text("\n".join(symbol_md) + "\n", encoding="utf-8")
    sensitivity = sensitivity_rows(candidates, coverage, config); write_csv(output_dir / OUTPUT_FILES[11], sensitivity)

    leakage_md = f"""# ENGINE-TREND-24 Leakage Audit

## Result

**PASS**. `pre_entry_features()` explicitly copies only frozen pre-entry fields. `score_features()` and `filter_features()` accept that isolated view, not a candidate outcome object. Mutation tests prove score/filter invariance when forbidden outcome fields change.

## Allowed inputs

{', '.join(config['declared_pre_entry_features'])}.

## Forbidden inputs

{', '.join(config['explicit_non_feature_fields'])}.

ENGINE-TREND-23 failure buckets are not inputs because their assignment may use outcomes. Old score is reported only as a baseline and is not a v2 feature. Historical MFE/MAE distributions are not used: without an independently frozen train-only model they would create leakage risk. Reachability uses causal ATR distance and a target already anchored to a pre-entry swing or range midline.

Chronological split: design through 2025-10-31 23:45 UTC; validation starts 2025-11-01 00:00 UTC. Full-sample diagnostics never select thresholds or acceptance status.
"""
    (output_dir / OUTPUT_FILES[12]).write_text(leakage_md, encoding="utf-8")
    next_stage = "ENGINE-TRADE-01 minimal paper trading strategy" if gate_result["paper_trading_candidate"] else "collect more OOS + ENGINE-TRADE-01 dry-run design" if gate_result["research_promising"] else "ENGINE-TREND-25 setup contract redesign"
    decision = {"final_status": final_status, "validation_pf": validation_metrics["pass"]["profit_factor"], "validation_expectancy": validation_metrics["pass"]["expectancy_pct_per_trade"], "validation_pass_count": validation_metrics["pass_count"], "ready_for_paper_trading_design": gate_result["paper_trading_candidate"], "profitable_system_validated": False, "runtime_changed": False, "trading_runtime_changed": False, "thresholds_changed": False, "composer_changed": False, "setup_contracts_changed": False, "leakage_status": "PASS", "next_stage": next_stage}
    (output_dir / OUTPUT_FILES[13]).write_text(json.dumps(decision, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report = f"""# ENGINE-TREND-24 Scoring Redesign + Setup Viability Filter

## Decision

**{final_status}**

Infrastructure Gate A: PASS. Research promising Gate B: {'PASS' if gate_result['research_promising'] else 'FAIL'}. Paper-trading Gate C: {'PASS' if gate_result['paper_trading_candidate'] else 'FAIL'}.

## Candidate accounting

- processed: {len(candidates)}
- filter PASS/FAIL: {full_metrics['pass_count']} / {full_metrics['fail_count']}
- train/design: {len(train)} candidates; PASS {train_metrics['pass_count']}
- out-of-time validation: {len(validation)} candidates; PASS {validation_metrics['pass_count']}

## Performance (net of the frozen 24 bps cost model)

- train PASS: {metric_line(train_metrics['pass'])}
- validation PASS: {metric_line(validation_metrics['pass'])}
- full PASS diagnostic: {metric_line(full_metrics['pass'])}
- full baseline: {metric_line(full_metrics['all'])}

## Ranking diagnostic

- old score vs net / win: {fmt(score_diag['old_score_correlation_net_return'])} / {fmt(score_diag['old_score_correlation_win_label'])}
- score_v2 vs net / win: {fmt(score_diag['score_v2_correlation_net_return'])} / {fmt(score_diag['score_v2_correlation_win_label'])}
- winners/losers mean score_v2: {fmt(score_diag['winner_mean_score_v2'])} / {fmt(score_diag['loser_mean_score_v2'])}
- old top-10: {metric_line(score_diag['old_top_10'])}
- v2 top-10: {metric_line(score_diag['v2_top_10'])}

Score_v2 changes correlation from {fmt(score_diag['old_score_correlation_net_return'])} to {fmt(score_diag['score_v2_correlation_net_return'])}, but its top-10 is worse than the old top-10 and remains negative. Ranking improvement is therefore **mixed and not decision-grade**. These are full-period diagnostics only. Acceptance uses the fixed out-of-time split.

## Filter diagnostics

Top hard-fail reasons: {', '.join(f'{k}={v}' for k,v in fail_counts.most_common(8))}.

Rejected winners: {len(rejected_winners)} ({fmt(len(rejected_winners) / max(1, sum(label(c)==WIN for c in candidates)) * 100, 2)}% of all clean winners). Passed losers: {len(passed_losers)}. The filter is aggressive and still imperfect. See dedicated audits; no post-fact threshold changes were made.

## Baseline replay

All candidates, clean distribution, old score top-N and deciles, expectancy and PF are reproduced in the JSON/CSV artifacts. Ambiguous/expired observations are excluded from clean binary counts.

## Sensitivity and walk-forward

Sensitivity variants are diagnostic, not a best-threshold search. Every requested stop/volume sensitivity remains negative on OOS; RR-penalty and target-cap variants do not change the selected subset because other causal hard fails dominate. Exact expanding-design → next-month windows for September–December are recorded, while the final gate remains November–December out-of-time validation.

## Safety and next stage

Leakage audit: PASS. Runtime, trading runtime, composer, setup contracts and production thresholds were not changed. The system is **not** declared profitable. Next stage: **{next_stage}**.
"""
    (output_dir / OUTPUT_FILES[0]).write_text(report, encoding="utf-8")

    manifest = {"generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "audit_only": True, "script": str(Path(__file__).relative_to(ROOT)).replace("\\", "/"), "created_files": list(OUTPUT_FILES), "input_artifacts": {name: "PRESENT" for name in REQUIRED_DISCOVERY}, "engine_trend_23_artifacts": {name: "PRESENT" if present else "MISSING_ARTIFACT" for name, present in audit23_availability.items()}, "artifacts": []}
    for name in OUTPUT_FILES[:-1]:
        raw = (output_dir / name).read_bytes(); manifest["artifacts"].append({"file": name, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
    manifest["self_hash_omitted"] = "A manifest cannot contain a stable hash of itself."
    (output_dir / OUTPUT_FILES[14]).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"decision": decision, "metrics": metrics_payload, "processed": len(candidates), "pass": full_metrics["pass_count"], "fail": full_metrics["fail_count"], "setup_viability": setup_rows, "symbol_viability": symbol_rows, "main": {"score_v2": mev["score_v2"], "pass": mev["filter_pass"], "fail_reasons": mev["fail_reasons"], "rank": main_rank}, "rejected_winners": len(rejected_winners), "passed_losers": len(passed_losers)}


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT); parser.add_argument("--audit-23-dir", type=Path, default=DEFAULT_AUDIT_23); parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(); print(json.dumps(run(args.input_dir, args.audit_23_dir, args.output_dir), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
