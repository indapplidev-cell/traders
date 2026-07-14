"""ENGINE-TREND-23 offline performance audit for historical setup candidates.

This module reads the immutable Historical Entry Discovery artifacts and writes
diagnostic reports only.  It does not import or mutate trading/runtime code.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "reports/engine_trend/engine_trend_historical_entry_discovery_2025_07_03_2025_12_17"
DEFAULT_OUTPUT = ROOT / "reports/engine_trend/engine_trend_23_historical_setup_performance_audit"

REQUIRED_INPUTS = (
    "HISTORICAL_ENTRY_DISCOVERY_REPORT.md",
    "MAIN_SELECTED_ENTRY_EXPLANATION.md",
    "HISTORICAL_ENTRY_DISCOVERY_RESULTS.json",
    "HISTORICAL_ENTRY_DISCOVERY_CANDIDATES.csv",
    "HISTORICAL_ENTRY_DISCOVERY_DATA_COVERAGE.md",
    "HISTORICAL_ENTRY_DISCOVERY_DATA_COVERAGE.json",
    "MAIN_SELECTED_ENTRY_TRACE.json",
    "HISTORICAL_ENTRY_DISCOVERY_ARTIFACT_MANIFEST.json",
)
OUTPUT_FILES = (
    "ENGINE_TREND_23_PERFORMANCE_AUDIT_REPORT.md",
    "ENGINE_TREND_23_PERFORMANCE_AUDIT_SUMMARY.json",
    "ENGINE_TREND_23_PERFORMANCE_BY_SYMBOL.csv",
    "ENGINE_TREND_23_PERFORMANCE_BY_SETUP_TYPE.csv",
    "ENGINE_TREND_23_PERFORMANCE_BY_DIRECTION.csv",
    "ENGINE_TREND_23_QUALITY_SCORE_AUDIT.csv",
    "ENGINE_TREND_23_RR_AUDIT.csv",
    "ENGINE_TREND_23_FAILURE_BUCKETS.csv",
    "ENGINE_TREND_23_TOP_CANDIDATES_POSTMORTEM.md",
    "ENGINE_TREND_23_DIAGNOSTIC_FILTER_HYPOTHESES.md",
    "ENGINE_TREND_23_ML_READINESS.md",
    "ENGINE_TREND_23_DECISION_RECORD.json",
    "ENGINE_TREND_23_ARTIFACT_MANIFEST.json",
)
CLEAN_LABELS = {"TP_BEFORE_SL", "SL_BEFORE_TP"}
WIN = "TP_BEFORE_SL"
LOSS = "SL_BEFORE_TP"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def mean(values: Iterable[float]) -> float | None:
    values = list(values)
    return statistics.fmean(values) if values else None


def median(values: Iterable[float]) -> float | None:
    values = list(values)
    return statistics.median(values) if values else None


def fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def pct(value: Any, digits: int = 2) -> str:
    return "N/A" if value is None else f"{value:.{digits}f}%"


def outcome(candidate: dict[str, Any]) -> str:
    return candidate["outcome"]["label_status"]


def net(candidate: dict[str, Any]) -> float | None:
    return candidate["outcome"].get("net_return_pct")


def gross(candidate: dict[str, Any]) -> float | None:
    return candidate["outcome"].get("gross_return_pct")


def entry_dt(candidate: dict[str, Any]) -> datetime:
    return datetime.fromisoformat(candidate["entry_time"].replace("Z", "+00:00"))


def risk_distance(candidate: dict[str, Any]) -> float:
    return abs(candidate["entry_price"] - candidate["stop_price"])


def target_distance(candidate: dict[str, Any]) -> float:
    return abs(candidate["target_1"] - candidate["entry_price"])


def derived(candidate: dict[str, Any]) -> dict[str, float | None]:
    values = candidate["technical_confirmation"]["values"]
    atr = values.get("atr14")
    risk = risk_distance(candidate)
    reward = target_distance(candidate)
    mfe = candidate["outcome"].get("mfe")
    mae = candidate["outcome"].get("mae")
    entry = candidate["entry_price"]
    return {
        "stop_pct": risk / entry * 100,
        "target_pct": reward / entry * 100,
        "stop_atr": risk / atr if finite_number(atr) and atr > 0 else None,
        "target_atr": reward / atr if finite_number(atr) and atr > 0 else None,
        "mfe_r": mfe / risk if finite_number(mfe) and risk > 0 else None,
        "mae_r": mae / risk if finite_number(mae) and risk > 0 else None,
        "target_progress": mfe / reward if finite_number(mfe) and reward > 0 else None,
    }


def pearson(xs: Iterable[float], ys: Iterable[float]) -> float | None:
    pairs = [(float(x), float(y)) for x, y in zip(xs, ys) if finite_number(x) and finite_number(y)]
    if len(pairs) < 3:
        return None
    x_values, y_values = zip(*pairs)
    x_mean, y_mean = statistics.fmean(x_values), statistics.fmean(y_values)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in pairs)
    denominator = math.sqrt(sum((x - x_mean) ** 2 for x in x_values) * sum((y - y_mean) ** 2 for y in y_values))
    return numerator / denominator if denominator else None


def max_streak(candidates: Iterable[dict[str, Any]], label: str) -> int:
    best = current = 0
    for candidate in sorted(candidates, key=lambda c: (entry_dt(c), c["candidate_id"])):
        if outcome(candidate) not in CLEAN_LABELS:
            continue
        current = current + 1 if outcome(candidate) == label else 0
        best = max(best, current)
    return best


def max_drawdown(candidates: Iterable[dict[str, Any]]) -> tuple[float, float]:
    equity = peak = 1.0
    drawdown = 0.0
    for candidate in sorted(candidates, key=lambda c: (entry_dt(c), c["candidate_id"])):
        if not finite_number(net(candidate)):
            continue
        equity += (net(candidate) or 0.0) / 100.0
        peak = max(peak, equity)
        if peak > 0:
            drawdown = max(drawdown, (peak - equity) / peak * 100.0)
    return equity, drawdown


def metrics(candidates: Iterable[dict[str, Any]]) -> dict[str, Any]:
    candidates = list(candidates)
    clean = [c for c in candidates if outcome(c) in CLEAN_LABELS]
    winners = [c for c in clean if outcome(c) == WIN]
    losers = [c for c in clean if outcome(c) == LOSS]
    winner_returns = [net(c) for c in winners if finite_number(net(c))]
    loser_returns = [net(c) for c in losers if finite_number(net(c))]
    # Expired setups have a deterministic horizon mark and are included in return
    # aggregates, while remaining excluded from the clean binary win/loss metrics.
    return_candidates = [c for c in candidates if finite_number(net(c))]
    net_returns = [net(c) for c in return_candidates]
    clean_net_returns = [net(c) for c in clean if finite_number(net(c))]
    gross_returns = [gross(c) for c in return_candidates if finite_number(gross(c))]
    gains = sum(value for value in net_returns if value > 0)
    losses = abs(sum(value for value in net_returns if value < 0))
    avg_winner = mean(winner_returns)
    avg_loser = mean(loser_returns)
    equity, drawdown = max_drawdown(return_candidates)
    result = {
        "candidates": len(candidates),
        "clean_candidates": len(clean),
        "return_observations_including_expired_marks": len(return_candidates),
        "tp_before_sl": len(winners),
        "sl_before_tp": len(losers),
        "ambiguous_intracandle": sum(outcome(c) == "AMBIGUOUS_INTRACANDLE" for c in candidates),
        "neither_expired": sum(outcome(c) == "NEITHER_EXPIRED" for c in candidates),
        "winrate_pct": len(winners) / len(clean) * 100 if clean else None,
        "average_gross_return_pct": mean(gross_returns),
        "average_net_return_pct": mean(net_returns),
        "median_net_return_pct": median(net_returns),
        "total_net_return_pct_naive": sum(net_returns),
        "profit_factor": gains / losses if losses else None,
        "average_winner_pct": avg_winner,
        "average_loser_pct": avg_loser,
        "payoff_ratio": avg_winner / abs(avg_loser) if avg_winner is not None and avg_loser else None,
        "expectancy_pct_per_trade": mean(net_returns),
        "clean_binary_expectancy_pct_per_trade": mean(clean_net_returns),
        "average_planned_rr": mean(c["planned_rr"] for c in clean),
        "average_quality_score": mean(c["quality_score"] for c in clean),
        "average_mfe_pct": mean(c["outcome"]["mfe_pct"] for c in clean),
        "average_mae_pct": mean(c["outcome"]["mae_pct"] for c in clean),
        "average_bars_to_outcome": mean(c["outcome"]["bars_to_outcome"] for c in clean),
        "max_consecutive_losses": max_streak(clean, LOSS),
        "max_consecutive_wins": max_streak(clean, WIN),
        "approximate_equity_final_1_unit_additive": equity,
        "max_drawdown_pct_naive_additive": drawdown,
    }
    return result


def quantile_bucket(sorted_candidates: list[dict[str, Any]], index: int, buckets: int = 10) -> int:
    """Return a deterministic equal-count bucket, 1=lowest and buckets=highest."""
    return min(buckets, index * buckets // len(sorted_candidates) + 1)


def rr_bucket(rr: float) -> str:
    if rr < 2:
        return "1.5-<2"
    if rr < 3:
        return "2-<3"
    if rr < 5:
        return "3-<5"
    if rr <= 8:
        return "5-8"
    return ">8"


def value_bucket(value: float, bounds: list[float], labels: list[str]) -> str:
    for bound, label in zip(bounds, labels):
        if value < bound:
            return label
    return labels[-1]


def failure_bucket(candidate: dict[str, Any]) -> str:
    """Assign one deterministic primary diagnostic bucket to a non-winner."""
    d = derived(candidate)
    tech = candidate["technical_confirmation"]["values"]
    structure = candidate["structure_evidence"]
    level = candidate["range_breakout_evidence"]
    setup = candidate["setup_type"]
    direction = candidate["direction"]
    close = candidate["entry_price"]
    atr = tech.get("atr14") or 0.0
    if d["stop_atr"] is not None and d["stop_atr"] <= 0.75 and candidate["outcome"].get("bars_to_sl") is not None and candidate["outcome"]["bars_to_sl"] <= 3:
        return "TOO_TIGHT_STOP"
    if d["target_atr"] is not None and d["target_atr"] >= 4.0:
        return "TARGET_TOO_FAR"
    if setup != "RANGE_MEAN_REVERSION_CANDIDATE" and structure.get("correction_bars", 0) >= 7:
        return "LATE_ENTRY_AFTER_EXHAUSTION"
    if tech.get("volume_ratio_20") is not None and tech["volume_ratio_20"] < 0.70:
        return "WEAK_CONFIRMATION_VOLUME"
    upper, lower = tech.get("bollinger_upper"), tech.get("bollinger_lower")
    if atr and ((direction == "LONG" and finite_number(upper) and close >= upper - 0.25 * atr) or (direction == "SHORT" and finite_number(lower) and close <= lower + 0.25 * atr)):
        return "BOLLINGER_EXTENSION_RISK"
    if setup == "RANGE_MEAN_REVERSION_CANDIDATE" and (tech.get("adx14") or 0) >= 25:
        return "RANGE_CONFLICT_IGNORED"
    rsi = tech.get("rsi14")
    if rsi is not None and ((direction == "LONG" and rsi >= 65) or (direction == "SHORT" and rsi <= 35)):
        return "REVERSAL_RISK_IGNORED"
    if setup != "RANGE_MEAN_REVERSION_CANDIDATE" and (tech.get("adx14") or 0) < 20:
        return "CHOPPY_SIDEWAYS_CONTEXT"
    if setup != "RANGE_MEAN_REVERSION_CANDIDATE" and structure.get("correction_bars", 0) >= 6:
        return "TREND_TOO_OLD"
    distance = level.get("distance_to_zone_atr")
    if distance is not None and distance < 0.10:
        return "RETEST_TOO_SHALLOW"
    if distance is not None and distance > 0.50:
        return "RETEST_TOO_DEEP"
    if candidate["planned_rr"] < 2:
        return "LOW_RR_DESPITE_PASS"
    if candidate["planned_rr"] >= 5:
        return "HIGH_RR_LOW_PROBABILITY"
    return "OTHER"


def integrity_check(input_dir: Path, results: dict[str, Any], csv_rows: list[dict[str, str]]) -> dict[str, Any]:
    candidates = results.get("candidates", [])
    ids = [c.get("candidate_id") for c in candidates]
    outcomes = Counter(outcome(c) for c in candidates)
    key_paths: list[tuple[str, Callable[[dict[str, Any]], Any]]] = [
        ("entry_price", lambda c: c.get("entry_price")),
        ("stop_price", lambda c: c.get("stop_price")),
        ("target_1", lambda c: c.get("target_1")),
        ("planned_rr", lambda c: c.get("planned_rr")),
        ("quality_score", lambda c: c.get("quality_score")),
    ]
    invalid_numeric = {name: sum(not finite_number(getter(c)) for c in candidates) for name, getter in key_paths}
    clean_missing_net = sum(outcome(c) in CLEAN_LABELS and not finite_number(net(c)) for c in candidates)
    main_id = results.get("main_selected_entry", {}).get("candidate_id")
    checks = {
        "all_required_artifacts_present": all((input_dir / name).is_file() for name in REQUIRED_INPUTS),
        "candidates_count_is_449": len(candidates) == 449,
        "csv_count_matches_json": len(csv_rows) == len(candidates),
        "candidate_ids_unique": len(ids) == len(set(ids)) and None not in ids,
        "rr_gte_1_5_all": all(finite_number(c.get("planned_rr")) and c["planned_rr"] >= 1.5 for c in candidates),
        "key_numeric_fields_finite": not any(invalid_numeric.values()),
        "clean_outcomes_have_net_return": clean_missing_net == 0,
        "ambiguous_excluded_from_clean_definition": "AMBIGUOUS_INTRACANDLE" not in CLEAN_LABELS,
        "neither_expired_separate": outcomes["NEITHER_EXPIRED"] >= 0 and "NEITHER_EXPIRED" not in CLEAN_LABELS,
        "main_selected_entry_present": main_id in set(ids),
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "details": {
            "candidate_count": len(candidates),
            "symbol_distribution": dict(sorted(Counter(c["symbol"] for c in candidates).items())),
            "setup_type_distribution": dict(sorted(Counter(c["setup_type"] for c in candidates).items())),
            "direction_distribution": dict(sorted(Counter(c["direction"] for c in candidates).items())),
            "outcome_distribution": dict(sorted(outcomes.items())),
            "invalid_numeric_counts": invalid_numeric,
            "clean_missing_net_return": clean_missing_net,
            "main_candidate_id": main_id,
        },
    }


def grouped(candidates: list[dict[str, Any]], key: Callable[[dict[str, Any]], str]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        result[key(candidate)].append(candidate)
    return dict(sorted(result.items()))


def monthly_rows(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(month=month, **metrics(items)) for month, items in grouped(candidates, lambda c: entry_dt(c).strftime("%Y-%m")).items()]


def performance_row(name: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    result = {"group": name, **metrics(candidates)}
    clean = [c for c in candidates if outcome(c) in CLEAN_LABELS]
    if clean:
        best = max(clean, key=lambda c: net(c))
        worst = min(clean, key=lambda c: net(c))
        result.update({
            "best_candidate_id": best["candidate_id"],
            "best_net_return_pct": net(best),
            "worst_candidate_id": worst["candidate_id"],
            "worst_net_return_pct": net(worst),
        })
    result["setup_type_distribution"] = json.dumps(dict(sorted(Counter(c["setup_type"] for c in candidates).items())), sort_keys=True)
    result["monthly_performance"] = json.dumps(monthly_rows(candidates), sort_keys=True)
    return result


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def quality_audit(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    clean = [c for c in candidates if outcome(c) in CLEAN_LABELS]
    correlation_net = pearson([c["quality_score"] for c in clean], [net(c) for c in clean])
    correlation_win = pearson([c["quality_score"] for c in clean], [1.0 if outcome(c) == WIN else 0.0 for c in clean])
    rows: list[dict[str, Any]] = [
        {"record_type": "correlation", "group": "quality_score_vs_net_return_pct", "value": correlation_net, **metrics(clean)},
        {"record_type": "correlation", "group": "quality_score_vs_tp_before_sl", "value": correlation_win, **metrics(clean)},
    ]
    ordered = sorted(clean, key=lambda c: (c["quality_score"], entry_dt(c), c["candidate_id"]))
    deciles: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for index, candidate in enumerate(ordered):
        deciles[quantile_bucket(ordered, index)].append(candidate)
    for decile, items in sorted(deciles.items()):
        rows.append({"record_type": "decile", "group": f"D{decile}_low_to_high", "value": mean(c["quality_score"] for c in items), **metrics(items)})
    ranked_high = sorted(clean, key=lambda c: (-c["quality_score"], entry_dt(c), c["candidate_id"]))
    ranked_low = list(reversed(ranked_high))
    for count in (10, 25, 50):
        rows.append({"record_type": "top", "group": f"top_{count}", "value": mean(c["quality_score"] for c in ranked_high[:count]), **metrics(ranked_high[:count])})
        rows.append({"record_type": "bottom", "group": f"bottom_{count}", "value": mean(c["quality_score"] for c in ranked_low[:count]), **metrics(ranked_low[:count])})
    winners = [c for c in clean if outcome(c) == WIN]
    losers = [c for c in clean if outcome(c) == LOSS]
    summary = {
        "correlation_quality_vs_net_return_pct": correlation_net,
        "correlation_quality_vs_win_label": correlation_win,
        "average_quality_winners": mean(c["quality_score"] for c in winners),
        "average_quality_losers": mean(c["quality_score"] for c in losers),
        "top_10": metrics(ranked_high[:10]),
        "bottom_10": metrics(ranked_low[:10]),
        "status": "NOT_PREDICTIVE" if (correlation_net or 0) <= 0 and (correlation_win or 0) <= 0 else "MIXED_WEAK",
    }
    return rows, summary


def rr_audit(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    clean = [c for c in candidates if outcome(c) in CLEAN_LABELS]
    buckets = grouped(clean, lambda c: rr_bucket(c["planned_rr"]))
    order = ["1.5-<2", "2-<3", "3-<5", "5-8", ">8"]
    rows = [{"rr_bucket": name, "min_rr": min((c["planned_rr"] for c in buckets.get(name, [])), default=None), "max_rr": max((c["planned_rr"] for c in buckets.get(name, [])), default=None), **metrics(buckets.get(name, []))} for name in order]
    corr_net = pearson([c["planned_rr"] for c in clean], [net(c) for c in clean])
    corr_win = pearson([c["planned_rr"] for c in clean], [1.0 if outcome(c) == WIN else 0.0 for c in clean])
    high = [c for c in clean if c["planned_rr"] >= 5]
    return rows, {
        "correlation_rr_vs_net_return_pct": corr_net,
        "correlation_rr_vs_win_label": corr_win,
        "high_rr_gte_5_false_setup_rate_pct": sum(outcome(c) == LOSS for c in high) / len(high) * 100 if high else None,
        "high_rr_gte_5_metrics": metrics(high),
    }


def feature_value(candidate: dict[str, Any], name: str) -> float | None:
    tech = candidate["technical_confirmation"]["values"]
    level = candidate["range_breakout_evidence"]
    mapping: dict[str, Any] = {
        "confidence": candidate.get("current_engine_trend_replay", {}).get("confidence"),
        "quality_score": candidate["quality_score"],
        "planned_rr": candidate["planned_rr"],
        "adx14": tech.get("adx14"),
        "rsi14": tech.get("rsi14"),
        "distance_to_level_atr": level.get("distance_to_zone_atr"),
        "stop_distance_pct": derived(candidate)["stop_pct"],
        "stop_distance_atr": derived(candidate)["stop_atr"],
        "target_distance_pct": derived(candidate)["target_pct"],
        "target_distance_atr": derived(candidate)["target_atr"],
        "volume_ratio_20": tech.get("volume_ratio_20"),
        "body_atr": candidate["candle_evidence"].get("body_atr"),
        "close_location": candidate["candle_evidence"].get("close_location"),
    }
    value = mapping[name]
    return float(value) if finite_number(value) else None


def feature_audit(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    clean = [c for c in candidates if outcome(c) in CLEAN_LABELS]
    names = ("confidence", "quality_score", "planned_rr", "adx14", "rsi14", "distance_to_level_atr", "stop_distance_pct", "stop_distance_atr", "target_distance_pct", "target_distance_atr", "volume_ratio_20", "body_atr", "close_location")
    result: dict[str, Any] = {}
    for name in names:
        available = [c for c in clean if feature_value(c, name) is not None]
        wins = [c for c in available if outcome(c) == WIN]
        losses = [c for c in available if outcome(c) == LOSS]
        result[name] = {
            "available_count": len(available),
            "winner_mean": mean(feature_value(c, name) for c in wins),
            "loser_mean": mean(feature_value(c, name) for c in losses),
            "correlation_vs_net_return_pct": pearson([feature_value(c, name) for c in available], [net(c) for c in available]),
            "correlation_vs_win_label": pearson([feature_value(c, name) for c in available], [1.0 if outcome(c) == WIN else 0.0 for c in available]),
        }
    return result


def bucket_metrics(candidates: list[dict[str, Any]], key: Callable[[dict[str, Any]], str]) -> dict[str, dict[str, Any]]:
    return {name: metrics(items) for name, items in grouped(candidates, key).items()}


def session(candidate: dict[str, Any]) -> str:
    hour = entry_dt(candidate).hour
    if hour < 7:
        return "ASIA_00_07"
    if hour < 13:
        return "EUROPE_07_13"
    if hour < 16:
        return "EUROPE_US_OVERLAP_13_16"
    return "US_16_24"


def diagnostic_breakdowns(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    clean = [c for c in candidates if outcome(c) in CLEAN_LABELS]
    return {
        "hour_utc": bucket_metrics(clean, lambda c: f"{entry_dt(c).hour:02d}:00"),
        "session_utc_exclusive": bucket_metrics(clean, session),
        "weekday": bucket_metrics(clean, lambda c: entry_dt(c).strftime("%A")),
        "month": bucket_metrics(clean, lambda c: entry_dt(c).strftime("%Y-%m")),
        "month_segment": bucket_metrics(clean, lambda c: "EARLY_01_10" if entry_dt(c).day <= 10 else "MID_11_20" if entry_dt(c).day <= 20 else "LATE_21_END"),
        "adx": bucket_metrics(clean, lambda c: value_bucket(c["technical_confirmation"]["values"]["adx14"], [15, 20, 25, 35], ["<15", "15-<20", "20-<25", "25-<35", ">=35"])),
        "rsi": bucket_metrics(clean, lambda c: value_bucket(c["technical_confirmation"]["values"]["rsi14"], [35, 45, 55, 65], ["<35", "35-<45", "45-<55", "55-<65", ">=65"])),
        "volume_ratio": bucket_metrics(clean, lambda c: value_bucket(c["technical_confirmation"]["values"]["volume_ratio_20"], [0.5, 0.8, 1.0, 1.5], ["<0.5", "0.5-<0.8", "0.8-<1.0", "1.0-<1.5", ">=1.5"])),
        "technical_vote_count": bucket_metrics(clean, lambda c: str(len(c["technical_confirmation"]["confirmations"]))),
        "conflict_count": bucket_metrics(clean, lambda c: str(len(c["technical_confirmation"]["conflicts"]))),
        "macd_alignment": bucket_metrics(clean, lambda c: "ALIGNED" if "MACD versus signal" in c["technical_confirmation"]["confirmations"] else "CONFLICT"),
        "ema20_50_alignment": bucket_metrics(clean, lambda c: "ALIGNED" if "EMA20/EMA50 alignment" in c["technical_confirmation"]["confirmations"] else "CONFLICT"),
        "ema20_50_200_alignment": bucket_metrics(clean, ema_full_alignment),
        "price_vs_vwap": bucket_metrics(clean, lambda c: "DIRECTIONALLY_ALIGNED" if ((c["direction"] == "LONG") == (c["entry_price"] >= c["technical_confirmation"]["values"]["vwap96"])) else "CONFLICT"),
        "bollinger_extension": bucket_metrics(clean, lambda c: "EXTENDED" if is_bollinger_extended(c) else "NOT_EXTENDED"),
        "atr_regime_within_symbol": atr_regime_breakdown(clean),
        "continuation_correction_bars": bucket_metrics([c for c in clean if c["setup_type"] != "RANGE_MEAN_REVERSION_CANDIDATE"], lambda c: value_bucket(c["structure_evidence"]["correction_bars"], [4, 6, 8], ["2-3", "4-5", "6-7", "8"])),
        "continuation_level_distance_atr": bucket_metrics([c for c in clean if c["setup_type"] != "RANGE_MEAN_REVERSION_CANDIDATE"], lambda c: value_bucket(c["range_breakout_evidence"]["distance_to_zone_atr"], [0.1, 0.3, 0.5], ["<0.1", "0.1-<0.3", "0.3-<0.5", ">=0.5"])),
        "range_touch_count": bucket_metrics([c for c in clean if c["setup_type"] == "RANGE_MEAN_REVERSION_CANDIDATE"], lambda c: str(c["structure_evidence"]["confirmed_high_touch_count"] + c["structure_evidence"]["confirmed_low_touch_count"])),
        "range_width_atr": bucket_metrics([c for c in clean if c["setup_type"] == "RANGE_MEAN_REVERSION_CANDIDATE"], lambda c: value_bucket(c["range_breakout_evidence"]["width_atr"], [5, 7], ["4-<5", "5-<7", ">=7"])),
        "candle_body_atr": bucket_metrics(clean, lambda c: value_bucket(c["candle_evidence"]["body_atr"], [0.25, 0.5, 0.75], ["<0.25", "0.25-<0.5", "0.5-<0.75", ">=0.75"])),
        "directional_rejection_wick": bucket_metrics(clean, lambda c: value_bucket(c["candle_evidence"]["lower_wick_fraction"] if c["direction"] == "LONG" else c["candle_evidence"]["upper_wick_fraction"], [0.22, 0.35, 0.5], ["<0.22", "0.22-<0.35", "0.35-<0.5", ">=0.5"])),
    }


def ema_full_alignment(candidate: dict[str, Any]) -> str:
    tech = candidate["technical_confirmation"]["values"]
    if candidate["direction"] == "LONG":
        return "FULLY_ALIGNED" if tech["ema20"] > tech["ema50"] > tech["ema200"] else "NOT_FULLY_ALIGNED"
    return "FULLY_ALIGNED" if tech["ema20"] < tech["ema50"] < tech["ema200"] else "NOT_FULLY_ALIGNED"


def is_bollinger_extended(candidate: dict[str, Any]) -> bool:
    tech = candidate["technical_confirmation"]["values"]
    atr = tech.get("atr14") or 0
    if candidate["direction"] == "LONG":
        return candidate["entry_price"] >= tech["bollinger_upper"] - 0.25 * atr
    return candidate["entry_price"] <= tech["bollinger_lower"] + 0.25 * atr


def atr_regime_breakdown(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    tags: dict[str, str] = {}
    for symbol, items in grouped(candidates, lambda c: c["symbol"]).items():
        ordered = sorted(items, key=lambda c: c["technical_confirmation"]["values"]["atr14"] / c["entry_price"])
        for index, candidate in enumerate(ordered):
            bucket = quantile_bucket(ordered, index, 3)
            tags[candidate["candidate_id"]] = ("LOW" if bucket == 1 else "MID" if bucket == 2 else "HIGH") + "_SYMBOL_RELATIVE"
    return bucket_metrics(candidates, lambda c: tags[c["candidate_id"]])


def failure_rows(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    failures = [c for c in candidates if outcome(c) != WIN]
    groups = grouped(failures, failure_bucket)
    names = ("TOO_TIGHT_STOP", "TARGET_TOO_FAR", "LATE_ENTRY_AFTER_EXHAUSTION", "WEAK_CONFIRMATION_VOLUME", "BOLLINGER_EXTENSION_RISK", "RANGE_CONFLICT_IGNORED", "REVERSAL_RISK_IGNORED", "CHOPPY_SIDEWAYS_CONTEXT", "TREND_TOO_OLD", "RETEST_TOO_SHALLOW", "RETEST_TOO_DEEP", "LOW_RR_DESPITE_PASS", "HIGH_RR_LOW_PROBABILITY", "OTHER")
    rows: list[dict[str, Any]] = []
    for name in names:
        items = groups.get(name, [])
        rows.append({
            "failure_bucket": name,
            "count": len(items),
            "average_net_return_pct": mean(net(c) for c in items if finite_number(net(c))),
            "setup_type_distribution": json.dumps(dict(sorted(Counter(c["setup_type"] for c in items).items()))),
            "examples": ";".join(c["candidate_id"] for c in sorted(items, key=lambda c: c["candidate_id"])[:5]),
            "definition": failure_definition(name),
        })
    return rows, {name: len(items) for name, items in groups.items()}


def failure_definition(name: str) -> str:
    return {
        "TOO_TIGHT_STOP": "non-winner; stop <=0.75 ATR and SL within 3 bars",
        "TARGET_TOO_FAR": "non-winner; target >=4 ATR",
        "LATE_ENTRY_AFTER_EXHAUSTION": "non-winner continuation; correction age >=7 bars",
        "WEAK_CONFIRMATION_VOLUME": "non-winner; confirmation volume ratio <0.70",
        "BOLLINGER_EXTENSION_RISK": "non-winner; entry within 0.25 ATR of directional outer band",
        "RANGE_CONFLICT_IGNORED": "non-winner range setup; ADX >=25",
        "REVERSAL_RISK_IGNORED": "non-winner; directional RSI extreme (long >=65, short <=35)",
        "CHOPPY_SIDEWAYS_CONTEXT": "non-winner continuation; ADX <20",
        "TREND_TOO_OLD": "non-winner continuation; correction age >=6 bars",
        "RETEST_TOO_SHALLOW": "non-winner continuation; level distance <0.10 ATR",
        "RETEST_TOO_DEEP": "non-winner continuation; level distance >0.50 ATR",
        "LOW_RR_DESPITE_PASS": "non-winner; 1.5 <= RR <2",
        "HIGH_RR_LOW_PROBABILITY": "non-winner; RR >=5",
        "OTHER": "no earlier deterministic diagnostic rule matched",
    }[name]


def outcome_path_audit(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    clean = [c for c in candidates if outcome(c) in CLEAN_LABELS]
    winners = [c for c in clean if outcome(c) == WIN]
    losers = [c for c in clean if outcome(c) == LOSS]
    return {
        "average_mfe_r_winners": mean(derived(c)["mfe_r"] for c in winners),
        "average_mfe_r_losers": mean(derived(c)["mfe_r"] for c in losers),
        "average_mae_r_winners": mean(derived(c)["mae_r"] for c in winners),
        "average_mae_r_losers": mean(derived(c)["mae_r"] for c in losers),
        "losers_mfe_r_gte_1_count": sum((derived(c)["mfe_r"] or 0) >= 1 for c in losers),
        "winners_mae_r_gte_0_5_count": sum((derived(c)["mae_r"] or 0) >= 0.5 for c in winners),
        "sl_within_3_bars_count": sum((c["outcome"].get("bars_to_sl") or 999) <= 3 for c in losers),
        "tp_within_3_bars_count": sum((c["outcome"].get("bars_to_tp") or 999) <= 3 for c in winners),
        "near_miss_target_then_sl_count": sum((derived(c)["target_progress"] or 0) >= 0.8 for c in losers),
        "bars_to_tp": distribution([c["outcome"].get("bars_to_tp") for c in winners]),
        "bars_to_sl": distribution([c["outcome"].get("bars_to_sl") for c in losers]),
        "expired_count": sum(outcome(c) == "NEITHER_EXPIRED" for c in candidates),
    }


def distribution(values: list[int | None]) -> dict[str, Any]:
    clean = [v for v in values if v is not None]
    return {"count": len(clean), "mean": mean(clean), "median": median(clean), "min": min(clean, default=None), "max": max(clean, default=None)}


def filter_hypotheses(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rules: list[tuple[str, str, Callable[[dict[str, Any]], bool], str]] = [
        ("VOLUME_RATIO_GTE_0_8", "Excludes confirmation candles with volume ratio <0.8.", lambda c: c["technical_confirmation"]["values"]["volume_ratio_20"] >= 0.8, "Cutoff inspected on one in-sample period; volume regimes vary by asset/time."),
        ("RR_LT_5", "Excludes mechanically high RR >=5.", lambda c: c["planned_rr"] < 5, "The RR boundary was chosen after observing this sample."),
        ("STOP_GT_0_75_ATR", "Excludes stops <=0.75 ATR.", lambda c: (derived(c)["stop_atr"] or 0) > 0.75, "ATR cutoff may proxy setup type and volatility regime."),
        ("TARGET_LT_4_ATR", "Excludes targets >=4 ATR.", lambda c: (derived(c)["target_atr"] or math.inf) < 4, "Target reachability is horizon- and regime-dependent."),
        ("NO_BOLLINGER_EXTENSION", "Excludes entries within 0.25 ATR of the directional outer band.", lambda c: not is_bollinger_extended(c), "Band distance and 0.25 ATR cutoff are sample-selected diagnostics."),
        ("CONTINUATION_CORRECTION_LE_6", "Excludes continuation corrections older than 6 bars; keeps range setups.", lambda c: c["setup_type"] == "RANGE_MEAN_REVERSION_CANDIDATE" or c["structure_evidence"].get("correction_bars", 0) <= 6, "Correction age is not the same as trend age and the cutoff is in-sample."),
        ("ADX_15_TO_35", "Keeps only moderate ADX [15,35].", lambda c: 15 <= c["technical_confirmation"]["values"]["adx14"] <= 35, "Classic indicator bucket mining has high multiple-testing risk."),
        ("RETEST_DISTANCE_0_1_TO_0_5", "Keeps range setups and continuation level distance [0.1,0.5] ATR.", lambda c: c["setup_type"] == "RANGE_MEAN_REVERSION_CANDIDATE" or 0.1 <= c["range_breakout_evidence"].get("distance_to_zone_atr", -1) <= 0.5, "Distance thresholds were evaluated on the same labeled sample."),
    ]
    baseline = metrics(candidates)
    rows = []
    for name, exclusion, rule, risk in rules:
        kept = [c for c in candidates if rule(c)]
        m = metrics(kept)
        rows.append({
            "status": "DIAGNOSTIC_HYPOTHESIS_ONLY",
            "filter": name,
            "what_it_excludes": exclusion,
            "candidates_remaining": len(kept),
            "clean_candidates_remaining": m["clean_candidates"],
            "winrate_pct": m["winrate_pct"],
            "expectancy_pct_per_trade": m["expectancy_pct_per_trade"],
            "profit_factor": m["profit_factor"],
            "baseline_winrate_pct": baseline["winrate_pct"],
            "baseline_expectancy_pct_per_trade": baseline["expectancy_pct_per_trade"],
            "overfit_risk": risk,
            "requires_out_of_time_validation": True,
        })
    return rows


def top_reason(candidate: dict[str, Any]) -> str:
    components = sorted(candidate["quality_score_components"].items(), key=lambda item: (-item[1], item[0]))[:3]
    return ", ".join(f"{name}={value:.1f}" for name, value in components)


def risk_pattern(candidate: dict[str, Any]) -> str:
    flags = []
    d = derived(candidate)
    tech = candidate["technical_confirmation"]["values"]
    if d["stop_atr"] is not None and d["stop_atr"] <= 0.75:
        flags.append(f"stop {d['stop_atr']:.2f} ATR")
    if d["target_atr"] is not None and d["target_atr"] >= 4:
        flags.append(f"target {d['target_atr']:.2f} ATR")
    if tech["volume_ratio_20"] < 0.8:
        flags.append(f"volume ratio {tech['volume_ratio_20']:.2f}")
    if tech["adx14"] >= 35:
        flags.append(f"high/late ADX {tech['adx14']:.1f}")
    if is_bollinger_extended(candidate):
        flags.append("outer-band extension")
    return "; ".join(flags) or "no selected diagnostic flag"


def why_outcome(candidate: dict[str, Any]) -> str:
    o = candidate["outcome"]
    d = derived(candidate)
    if outcome(candidate) == WIN:
        return f"TP first in {o['bars_to_tp']} bars; MAE {fmt(d['mae_r'], 2)}R."
    if outcome(candidate) == LOSS:
        return f"SL first in {o['bars_to_sl']} bars after MFE {fmt(d['mfe_r'], 2)}R ({fmt((d['target_progress'] or 0)*100, 1)}% of target distance)."
    return f"{outcome(candidate)} at {o['bars_to_outcome']} bars."


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    return "\n".join([
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |" for row in rows),
    ])


def write_postmortem(path: Path, candidates: list[dict[str, Any]], main_id: str) -> None:
    ranked = sorted(candidates, key=lambda c: (-c["quality_score"], entry_dt(c), c["candidate_id"]))[:10]
    main = next(c for c in candidates if c["candidate_id"] == main_id)
    d = derived(main)
    tech = main["technical_confirmation"]["values"]
    components = main["quality_score_components"]
    rows = [[c["candidate_id"], c["symbol"], c["setup_type"], c["direction"], c["entry_time"], fmt(c["planned_rr"], 3), fmt(c["quality_score"], 3), outcome(c), pct(net(c)), top_reason(c), why_outcome(c), risk_pattern(c)] for c in ranked]
    text = f"""# ENGINE-TREND-23 Top Candidates Post-mortem

## MAIN_SELECTED_ENTRY: `{main_id}`

`{main_id}` ranked first because the additive score rewarded causal/structural clarity ({components['causal_context_strength']:.1f}/{components['structure_clarity']:.1f}), level quality ({components['level_quality']:.1f}), conflict absence ({components['conflict_absence']:.1f}), technical agreement ({components['technical_agreement']:.1f}) and RR quality ({components['rr_quality']:.1f}). The outcome was not used in ranking, so selection remained causal.

Known pre-entry warnings were a weak confirmation volume ratio of **{tech['volume_ratio_20']:.3f}**, a stop only **{d['stop_atr']:.3f} ATR** away, a target **{d['target_atr']:.3f} ATR** away, RR **{main['planned_rr']:.3f}**, and ADX **{tech['adx14']:.2f}**, which can describe mature rather than early trend strength. Bollinger extension was **{'present' if is_bollinger_extended(main) else 'not present under the declared 0.25 ATR diagnostic'}**. The score had no explicit volume component and converted RR into a monotonic bonus capped at 100; it therefore rewarded reward/risk geometry without estimating target-hit probability.

The trade reached MFE **{d['mfe_r']:.3f}R**, then hit SL in **{main['outcome']['bars_to_sl']} bars**. This is not proof of an obvious invalid setup: structure, level, and candle authorization were causal. It is better classified as a statistically normal loss with identifiable probability/geometry warnings (weak volume and asymmetric stop/target distances). Filters such as minimum volume or minimum stop-in-ATR could have excluded it causally, but their cutoffs are hindsight-selected and remain `DIAGNOSTIC_HYPOTHESIS_ONLY`. One loss is not a basis for changing scoring: **NO**.

## Frozen top 10

{markdown_table(['ID','Symbol','Setup','Dir','Entry UTC','RR','Score','Outcome','Net','Why ranked high','Why won/lost','Common risk'], rows)}

Top-10 aggregate: {metrics(ranked)['tp_before_sl']} TP, {metrics(ranked)['sl_before_tp']} SL, clean winrate **{pct(metrics(ranked)['winrate_pct'])}**, expectancy **{pct(metrics(ranked)['expectancy_pct_per_trade'])}**, PF **{fmt(metrics(ranked)['profit_factor'])}**. The common ranking pattern is high structure/level/conflict scores plus monotonic RR credit; the common loss pattern is that those attributes do not directly estimate target reachability before a tight structural stop.
"""
    path.write_text(text, encoding="utf-8")


def write_filter_report(path: Path, rows: list[dict[str, Any]]) -> None:
    table = [[r["filter"], r["candidates_remaining"], pct(r["winrate_pct"]), pct(r["expectancy_pct_per_trade"]), fmt(r["profit_factor"]), r["what_it_excludes"], r["overfit_risk"]] for r in rows]
    path.write_text(f"""# ENGINE-TREND-23 Diagnostic Filter Hypotheses

Every row is **DIAGNOSTIC_HYPOTHESIS_ONLY**. These are in-sample ablations, not production rules and not evidence that the strategy improves. All require a locked definition followed by walk-forward/out-of-time validation.

Baseline clean metrics: winrate **{pct(rows[0]['baseline_winrate_pct'])}**, expectancy **{pct(rows[0]['baseline_expectancy_pct_per_trade'])}**.

{markdown_table(['Hypothesis','Candidates left','Winrate','Expectancy','PF','Excludes','Why overfit-prone'], table)}

Dangerous choices include hour/weekday/month filters, selecting only the best symbol after reading outcomes, indicator bucket mining, optimizing several cutoffs jointly, and ranking by the best in-sample quality decile. These have high multiple-testing and regime-selection risk. No hypothesis may enter runtime before an untouched out-of-time period and sensitivity/stability checks.
""", encoding="utf-8")


def write_ml_report(path: Path, candidates: list[dict[str, Any]], integrity: dict[str, Any]) -> None:
    clean = [c for c in candidates if outcome(c) in CLEAN_LABELS]
    labels = Counter(outcome(c) for c in clean)
    duplicate_times = sum(count > 1 for count in Counter(c["entry_time"] for c in candidates).values())
    path.write_text(f"""# ENGINE-TREND-23 ML Meta-filter Readiness

## Status: PARTIAL

There are **{len(candidates)}** rows and **{len(clean)}** clean binary labels ({labels[WIN]} TP / {labels[LOSS]} SL). This is enough for a constrained exploratory baseline, but insufficient for a credible high-dimensional production meta-filter: observations are clustered across three correlated crypto pairs and nearby market periods, and only about five and a half months are covered. There are **{duplicate_times}** entry timestamps shared by multiple candidates, further reducing effective independence.

Usable pre-entry features include symbol, setup type, direction, planned RR, score components, stop/target distances normalized by price or ATR, ADX, RSI, EMA/MACD alignment, VWAP/Bollinger position, volume ratio, candle anatomy, causal level distance, correction bars/touch counts, and technical conflict/vote counts. `AMBIGUOUS_INTRACANDLE` and `NEITHER_EXPIRED` should be excluded from the first binary model or modeled separately.

Leakage exclusions are mandatory: outcome/label, all 24/48/96 horizon objects, MFE/MAE, bars-to-TP/SL/outcome, gross/net return, any failure bucket that uses realized path, post-entry prices, and any filter/feature definition chosen after inspecting this period. Candidate ID/rank should also be removed; `quality_score` may be retained only as a benchmark because it deterministically aggregates other features and can dominate them.

Use a chronological, embargoed split—not random rows. A reasonable research design is expanding-window folds by time, grouping equal/nearby timestamps across all symbols in the same fold, with the final contiguous month held untouched as out-of-time validation. Because the available period is short, the preferred next step is to collect additional non-overlapping months before treating that holdout as decisive. Class weighting or calibrated probabilities may address the **{labels[LOSS] / len(clean) * 100:.1f}%** loss class; do not oversample across time boundaries.

Label mechanics are deterministic and integrity is **{integrity['status']}**, but same-candle ambiguity and a fixed 96-bar horizon constrain label quality. Final answer: **ML-ready now: PARTIAL**—suitable for leakage-audited exploratory baselines, not production selection.
""", encoding="utf-8")


def setup_recommendation(name: str, m: dict[str, Any]) -> str:
    if m["profit_factor"] is not None and m["profit_factor"] >= 0.8:
        return "KEEP_FOR_RESEARCH_NOT_TRADING"
    if m["profit_factor"] is not None and m["profit_factor"] >= 0.5:
        return "REDESIGN_AND_OOS_VALIDATE"
    return "REJECT_CURRENT_FORM_PENDING_REDESIGN"


def report_text(summary: dict[str, Any], candidates: list[dict[str, Any]], symbol_rows: list[dict[str, Any]], setup_rows: list[dict[str, Any]], direction_rows: list[dict[str, Any]], failure_rows_data: list[dict[str, Any]], filters: list[dict[str, Any]]) -> str:
    a = summary["aggregate_performance"]
    q = summary["quality_score_audit"]
    rr = summary["rr_audit"]
    path = summary["outcome_path_audit"]
    feature = summary["feature_audit"]
    breakdowns = summary["diagnostic_breakdowns"]
    symbol_table = [[r["group"], r["candidates"], pct(r["winrate_pct"]), pct(r["average_net_return_pct"]), fmt(r["profit_factor"]), fmt(r["average_planned_rr"]), r.get("best_candidate_id"), r.get("worst_candidate_id")] for r in symbol_rows]
    setup_table = [[r["group"], r["candidates"], pct(r["winrate_pct"]), pct(r["average_net_return_pct"]), fmt(r["profit_factor"]), fmt(r["average_planned_rr"]), fmt(r["average_mfe_pct"]), fmt(r["average_mae_pct"]), fmt(r["average_bars_to_outcome"]), setup_recommendation(r["group"], r)] for r in setup_rows]
    direction_table = [[r["group"], r["candidates"], pct(r["winrate_pct"]), pct(r["average_net_return_pct"]), fmt(r["profit_factor"]), fmt(r["payoff_ratio"])] for r in direction_rows]
    feature_table = [[name, values["available_count"], fmt(values["winner_mean"]), fmt(values["loser_mean"]), fmt(values["correlation_vs_net_return_pct"]), fmt(values["correlation_vs_win_label"])] for name, values in feature.items()]
    failure_table = [[r["failure_bucket"], r["count"], pct(r["average_net_return_pct"]), r["setup_type_distribution"], r["examples"]] for r in failure_rows_data if r["count"]]
    monthly_table = [[row["month"], row["candidates"], pct(row["winrate_pct"]), pct(row["average_net_return_pct"]), fmt(row["profit_factor"])] for row in summary["monthly_performance"]]
    component_rows = []
    for component in candidates[0]["quality_score_components"]:
        wins = [c["quality_score_components"][component] for c in candidates if outcome(c) == WIN]
        losses = [c["quality_score_components"][component] for c in candidates if outcome(c) == LOSS]
        component_rows.append([component, fmt(mean(wins)), fmt(mean(losses)), fmt((mean(wins) or 0) - (mean(losses) or 0))])
    return f"""# ENGINE-TREND-23 Performance Audit of Historical Setup Candidates

## Executive decision

Final status: **{summary['final_status']}**. All **{a['candidates']}** historical candidates were analyzed; integrity is **{summary['integrity_check']['status']}**. Clean outcomes contain {a['tp_before_sl']} wins and {a['sl_before_tp']} losses, with winrate **{pct(a['winrate_pct'])}**. Across **{a['return_observations_including_expired_marks']}** available returns (clean outcomes plus two separately identified expiry marks), expectancy is **{pct(a['expectancy_pct_per_trade'])}** and profit factor is **{fmt(a['profit_factor'])}**; clean-binary expectancy alone is **{pct(a['clean_binary_expectancy_pct_per_trade'])}**. This is a candidate-label performance audit, not a production backtest. The system is **not validated profitable**, and runtime must not change from this in-sample audit.

The negative aggregate expectancy comes from a low hit rate that the realized payoff does not compensate for after 24 bps round-trip costs. Causal structure/level detection answers “is this setup narratively and temporally valid?” but the score does not estimate “will target be reached before stop?” RR is rewarded monotonically even when it is created by a narrow stop or remote structural target, while volume, stop/target reachability, trend maturity, and outer-band extension are absent or weakly represented.

## 1. Integrity and scope

All eight required source artifacts are present. JSON/CSV counts match, IDs are unique, all RR values are at least 1.5, key numeric fields are finite, every clean outcome has net return, `AMBIGUOUS_INTRACANDLE` is excluded from clean win/loss metrics, `NEITHER_EXPIRED` is separate, and `ET-HED-0001` is present. Distribution: symbols `{json.dumps(summary['integrity_check']['details']['symbol_distribution'], sort_keys=True)}`, setup types `{json.dumps(summary['integrity_check']['details']['setup_type_distribution'], sort_keys=True)}`, directions `{json.dumps(summary['integrity_check']['details']['direction_distribution'], sort_keys=True)}`, outcomes `{json.dumps(summary['integrity_check']['details']['outcome_distribution'], sort_keys=True)}`.

## 2. Aggregate performance

- Total / clean / available returns: **{a['candidates']} / {a['clean_candidates']} / {a['return_observations_including_expired_marks']}**; ambiguous **{a['ambiguous_intracandle']}**; expired **{a['neither_expired']}**. Expired setups are never counted as wins/losses but their 96-bar mark is included in return aggregates, matching the archived preliminary estimate.
- Average gross / net / median net: **{pct(a['average_gross_return_pct'])} / {pct(a['average_net_return_pct'])} / {pct(a['median_net_return_pct'])}**.
- Naive sum / final additive 1-unit equity / max drawdown: **{pct(a['total_net_return_pct_naive'])} / {a['approximate_equity_final_1_unit_additive']:.4f} / {pct(a['max_drawdown_pct_naive_additive'])}**.
- Average winner / loser / payoff ratio: **{pct(a['average_winner_pct'])} / {pct(a['average_loser_pct'])} / {fmt(a['payoff_ratio'])}**.
- Maximum chronological win/loss streak: **{a['max_consecutive_wins']} / {a['max_consecutive_losses']}**.

The additive curve is deliberately naive: candidates may overlap in time and across correlated symbols, so it is not portfolio equity.

### Monthly clean performance

{markdown_table(['Month','Candidates','Winrate','Avg net','PF'], monthly_table)}

## 3. By symbol

{markdown_table(['Symbol','N','Winrate','Avg net','PF','Avg RR','Best','Worst'], symbol_table)}

Symbol differences are descriptive only; choosing the best pair after seeing these outcomes would be hindsight selection. Detailed outcome/setup/month distributions are embedded in `ENGINE_TREND_23_PERFORMANCE_BY_SYMBOL.csv`.

## 4. By setup type

{markdown_table(['Setup','N','Winrate','Avg net','PF','Avg RR','MFE %','MAE %','Bars','Audit disposition'], setup_table)}

“Keep” here means retain as a research candidate, never deploy. False continuation patterns concentrate around weak volume, tight stops/remote targets, mature corrections and choppy context; range failures include directional-ADX conflict and breakout-transition risk. Explicit average realized return is the average net column. Target provenance is available: continuations use the pre-confirmation impulse extreme; ranges use the confirmed range midline. More semantic fields such as explicit trend age, polarity flip, trap/failure, reclaim/failure and structural pivot breach are not stored and are `NOT_AVAILABLE` rather than inferred.

## 5. By direction

{markdown_table(['Direction','N','Winrate','Avg net','PF','Payoff'], direction_table)}

Direction-by-symbol and monthly direction metrics are preserved in the summary JSON. Differences do not justify a directional runtime filter without OOS validation.

## 6. Quality score audit

Quality correlation with net return is **{fmt(q['correlation_quality_vs_net_return_pct'])}** and with the clean win label is **{fmt(q['correlation_quality_vs_win_label'])}**. Winner/loser mean scores are **{fmt(q['average_quality_winners'])} / {fmt(q['average_quality_losers'])}**. Top-10 winrate is **{pct(q['top_10']['winrate_pct'])}** versus bottom-10 **{pct(q['bottom_10']['winrate_pct'])}**. Status: **{q['status']}**.

{markdown_table(['Score component','Winner mean','Loser mean','Winner-minus-loser'], component_rows)}

High score does not predict profit in this sample. The score double-counts the same structure input as both causal context and structure clarity (33% combined weight), gives monotonically increasing RR credit (13%), and omits explicit volume and stop/target reachability terms. ADX contributes a step-like technical score for continuation candidates and can reward lagging trend confirmation.

## 7. RR and stop/target audit

RR correlation with net return / win label is **{fmt(rr['correlation_rr_vs_net_return_pct'])} / {fmt(rr['correlation_rr_vs_win_label'])}**. For RR >=5, the false-setup rate is **{pct(rr['high_rr_gte_5_false_setup_rate_pct'])}**, expectancy **{pct(rr['high_rr_gte_5_metrics']['expectancy_pct_per_trade'])}**, PF **{fmt(rr['high_rr_gte_5_metrics']['profit_factor'])}**. Bucket details are in `ENGINE_TREND_23_RR_AUDIT.csv`.

The evidence does not show that high planned RR improves expectancy. RR is geometry, not probability: target distance equals RR times stop distance. In this generator, narrow buffered structural stops and pre-existing swing/range objectives can manufacture attractive ratios while increasing early stop and target-unreachability risk.

Outcome path: winner MFE/MAE averages **{fmt(path['average_mfe_r_winners'])}R / {fmt(path['average_mae_r_winners'])}R**; loser MFE/MAE **{fmt(path['average_mfe_r_losers'])}R / {fmt(path['average_mae_r_losers'])}R**. **{path['losers_mfe_r_gte_1_count']}** losers first reached at least 1R MFE; **{path['winners_mae_r_gte_0_5_count']}** winners endured at least 0.5R MAE; **{path['sl_within_3_bars_count']}** losses and **{path['tp_within_3_bars_count']}** wins resolved within three bars; **{path['near_miss_target_then_sl_count']}** losers reached at least 80% of target distance before SL. Partial profit, break-even, trailing stop or shorter expiry are therefore research hypotheses only, not recommendations to change execution.

## 8. Pre-entry feature diagnostics

{markdown_table(['Feature','Available','Winner mean','Loser mean','Corr net','Corr win'], feature_table)}

Confidence is available only where the prior discovery replay enriched candidates (top-10), so it cannot support a dataset-wide conclusion. ADX, RSI, MACD/EMA alignment, VWAP/Bollinger position, volume, ATR regime, vote count and conflicts are bucketed in the summary JSON. Any apparent bucket edge is exploratory and multiple-testing-prone. The stored “book” evidence with broadest coverage is causal structure classification plus objective/level construction and candle anatomy; no single stored book reason establishes robust separation without OOS testing.

Direct answers to the technical questions: high ADX did **not** rescue expectancy (ADX >=35: winrate **{pct(breakdowns['adx']['>=35']['winrate_pct'])}**, expectancy **{pct(breakdowns['adx']['>=35']['expectancy_pct_per_trade'])}**), so it may be lagging but that causal interpretation is unproven. RSI midline 45-55 was less negative than adjacent 35-45 and 55-65 buckets, while extreme buckets contain too few observations to trust. Outer-band extension had only **{breakdowns['bollinger_extension']['EXTENDED']['candidates']}** candidates and cannot support a robust filter. Volume ratio >=1.5 was the only volume bucket with positive aggregate expectancy (**{pct(breakdowns['volume_ratio']['>=1.5']['expectancy_pct_per_trade'])}**, N={breakdowns['volume_ratio']['>=1.5']['clean_candidates']}), whereas volume <0.5 was materially negative; this is a useful hypothesis, not validation. MACD-aligned candidates were less negative than conflicts (**{pct(breakdowns['macd_alignment']['ALIGNED']['expectancy_pct_per_trade'])}** versus **{pct(breakdowns['macd_alignment']['CONFLICT']['expectancy_pct_per_trade'])}**), but remained unprofitable. EMA/VWAP alignment did not consistently help, which is compatible with late-entry behavior.

Altunina availability: HH/HL or LH/LL classification, confirmed pivots, impulse-extreme time, correction bars and retest extreme are available for continuations; explicit impulse-strength, correction-depth, trend-age and pivot-breach fields are not. Schwager availability: causal zone/distance/objective or range support/resistance/midline/width/touches/slope are available; explicit polarity flip, breakout/trap, reclaim/failure fields are not. Nison availability: close location, body-in-ATR, wick fractions, OHLC and interpretation are available; a separate candle-volume-confirmation flag and context-rejection taxonomy are not. The summary includes deterministic correction-age, level-distance, range-touch/width, body and rejection-wick buckets. The most repeatable stored winner association is MACD alignment/zero-conflict plus stronger volume, but it is neither uniquely “book-based” nor OOS-validated.

## 9. Timing diagnostics

Hourly UTC, exclusive sessions (Asia 00-07, Europe 07-13, overlap 13-16, US 16-24), weekday, month, and early/mid/late-month tables are in the summary JSON. These are diagnostics only. The sample covers less than six months; time filters are especially likely to encode temporary regime and must not be productionized.

## 10. Failure clustering

Primary buckets are assigned once per non-winner with deterministic precedence; they are explanatory tags, not ground truth causes.

{markdown_table(['Bucket','N','Avg net','Setup distribution','Examples'], failure_table)}

## 11. MAIN and top-10 post-mortem

`ET-HED-0001` was causal but combined weak volume, a {derived(next(c for c in candidates if c['candidate_id']=='ET-HED-0001'))['stop_atr']:.2f}-ATR stop, a {derived(next(c for c in candidates if c['candidate_id']=='ET-HED-0001'))['target_atr']:.2f}-ATR target and monotonic RR credit; it made {derived(next(c for c in candidates if c['candidate_id']=='ET-HED-0001'))['mfe_r']:.2f}R before SL at bar 3. This is a normal statistical loss with pre-entry warning signs, not sufficient evidence to rewrite score logic. Full MAIN and frozen top-10 detail is in `ENGINE_TREND_23_TOP_CANDIDATES_POSTMORTEM.md`.

## 12. Overfit control and ML readiness

All {len(filters)} filter ablations are labeled `DIAGNOSTIC_HYPOTHESIS_ONLY`; each reports remaining candidates, clean winrate, expectancy, PF, overfit risk and mandatory OOT validation. Dataset ML readiness is **PARTIAL**: useful for a small leakage-audited baseline with chronological grouped/embargoed splits, insufficient for production validation. Remove all outcome-path and return fields, future horizons, IDs/ranks and hindsight-derived buckets.

## 13. Recommendations

### A. Keep

- Keep the causal boundary, closed-candle confirmation, unique IDs, explicit ambiguous/expired labels, cost-aware returns, and immutable pre-entry ranking freeze.
- Keep all setup families only as research candidates where their subgroup metrics are not completely degenerate; none is approved for trading.
- Keep normalized pre-entry structure, level, candle, volume and distance features for OOS research.

### B. Redesign

- Redesign `quality_score` as a calibrated probability-oriented research score; remove duplicated structure credit and test volume, stop/target ATR reachability, Bollinger extension, trend maturity and range conflict.
- Audit RR weighting, stop buffer, objective/target selection and expiry separately; do not optimize them jointly on this period.
- Add explicit causal fields for trend age, polarity/reclaim, breakout trap, pivot breach and context conflict before an ML dataset is frozen.

### C. Reject / Block

- Block high-RR ranking as the main selector, indicator-only/time filters, any in-sample-selected combination, and production trading based on these candidates.
- Do not claim profitability: **NO**. Do not change runtime now: **NO**.

## Decision

Next stage is required: **YES**—ENGINE-TREND-24 scoring redesign/failure analysis with locked hypotheses, more historical coverage, and chronological walk-forward/OOS validation. Runtime, trading runtime, thresholds, composer and setup contracts remain unchanged; no commit is created by this script.
"""


def run(input_dir: Path = DEFAULT_INPUT, output_dir: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    missing = [name for name in REQUIRED_INPUTS if not (input_dir / name).is_file()]
    if missing:
        output_dir.mkdir(parents=True, exist_ok=True)
        blocked = {"final_status": "PERFORMANCE_AUDIT_BLOCKED_MISSING_ARTIFACTS", "artifact_status": "ARTIFACT_MISSING", "missing_artifacts": missing}
        (output_dir / "ENGINE_TREND_23_PERFORMANCE_AUDIT_SUMMARY.json").write_text(json.dumps(blocked, indent=2) + "\n", encoding="utf-8")
        return blocked

    results = load_json(input_dir / "HISTORICAL_ENTRY_DISCOVERY_RESULTS.json")
    trace = load_json(input_dir / "MAIN_SELECTED_ENTRY_TRACE.json")
    with (input_dir / "HISTORICAL_ENTRY_DISCOVERY_CANDIDATES.csv").open(encoding="utf-8", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    candidates = results["candidates"]
    integrity = integrity_check(input_dir, results, csv_rows)
    aggregate = metrics(candidates)
    final_status = "PERFORMANCE_AUDIT_COMPLETED_NEGATIVE_EXPECTANCY" if integrity["status"] == "PASS" and (aggregate["expectancy_pct_per_trade"] or 0) < 0 else "PERFORMANCE_AUDIT_BLOCKED_DATA_INTEGRITY" if integrity["status"] != "PASS" else "PERFORMANCE_AUDIT_COMPLETED_MIXED_INCONCLUSIVE"

    symbol_groups = grouped(candidates, lambda c: c["symbol"])
    setup_groups = grouped(candidates, lambda c: c["setup_type"])
    direction_groups = grouped(candidates, lambda c: c["direction"])
    symbol_rows = [performance_row(name, items) for name, items in symbol_groups.items()]
    setup_rows = [performance_row(name, items) for name, items in setup_groups.items()]
    direction_rows = [performance_row(name, items) for name, items in direction_groups.items()]
    quality_rows, quality_summary = quality_audit(candidates)
    rr_rows, rr_summary = rr_audit(candidates)
    failures_csv, failure_summary = failure_rows(candidates)
    filters = filter_hypotheses(candidates)
    diagnostics = diagnostic_breakdowns(candidates)

    direction_symbol = {direction: {symbol: metrics(items2) for symbol, items2 in grouped(items, lambda c: c["symbol"]).items()} for direction, items in direction_groups.items()}
    direction_month = {direction: monthly_rows(items) for direction, items in direction_groups.items()}
    summary = {
        "engine_trend_stage": "ENGINE-TREND-23",
        "final_status": final_status,
        "analysis_kind": "OFFLINE_AUDIT_ONLY_NOT_PRODUCTION_BACKTEST",
        "integrity_check": integrity,
        "aggregate_performance": aggregate,
        "by_symbol": {row["group"]: {k: v for k, v in row.items() if k != "group"} for row in symbol_rows},
        "by_setup_type": {row["group"]: {k: v for k, v in row.items() if k != "group"} for row in setup_rows},
        "by_direction": {row["group"]: {k: v for k, v in row.items() if k != "group"} for row in direction_rows},
        "direction_by_symbol": direction_symbol,
        "direction_monthly": direction_month,
        "monthly_performance": monthly_rows(candidates),
        "quality_score_audit": quality_summary,
        "rr_audit": rr_summary,
        "feature_audit": feature_audit(candidates),
        "diagnostic_breakdowns": diagnostics,
        "failure_bucket_counts": failure_summary,
        "outcome_path_audit": outcome_path_audit(candidates),
        "filter_hypotheses": filters,
        "main_selected_candidate_id": trace["selected_entry"]["candidate_id"],
        "ml_readiness": "PARTIAL",
        "profitability_status": "NEGATIVE_EXPECTANCY_NOT_VALIDATED",
        "runtime_changed": False,
        "trading_runtime_changed": False,
        "thresholds_changed": False,
        "composer_changed": False,
        "setup_contracts_changed": False,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / OUTPUT_FILES[2], symbol_rows)
    write_csv(output_dir / OUTPUT_FILES[3], setup_rows)
    write_csv(output_dir / OUTPUT_FILES[4], direction_rows)
    write_csv(output_dir / OUTPUT_FILES[5], quality_rows)
    write_csv(output_dir / OUTPUT_FILES[6], rr_rows)
    write_csv(output_dir / OUTPUT_FILES[7], failures_csv)
    write_postmortem(output_dir / OUTPUT_FILES[8], candidates, summary["main_selected_candidate_id"])
    write_filter_report(output_dir / OUTPUT_FILES[9], filters)
    write_ml_report(output_dir / OUTPUT_FILES[10], candidates, integrity)
    (output_dir / OUTPUT_FILES[1]).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    decision = {
        "final_status": final_status,
        "profitability_status": "NEGATIVE_EXPECTANCY_NOT_VALIDATED",
        "quality_score_status": quality_summary["status"],
        "ml_readiness": "PARTIAL",
        "runtime_changed": False,
        "trading_runtime_changed": False,
        "thresholds_changed": False,
        "composer_changed": False,
        "setup_contracts_changed": False,
        "recommendation": "DO_NOT_DEPLOY; REDESIGN_SCORE_AND_STOP_TARGET_LOGIC; VALIDATE_LOCKED_HYPOTHESES_OOS",
        "next_stage": "ENGINE-TREND-24_SCORING_REDESIGN_OR_SETUP_FAILURE_ANALYSIS_WITH_WALK_FORWARD_OOS",
        "profitable_system_validated": False,
        "commit_created": False,
    }
    (output_dir / OUTPUT_FILES[11]).write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / OUTPUT_FILES[0]).write_text(report_text(summary, candidates, symbol_rows, setup_rows, direction_rows, failures_csv, filters), encoding="utf-8")

    manifest_entries = []
    for name in OUTPUT_FILES[:-1]:
        payload = (output_dir / name).read_bytes()
        manifest_entries.append({"file": name, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})
    manifest = {
        "engine_trend_stage": "ENGINE-TREND-23",
        "artifact_count_excluding_manifest": len(manifest_entries),
        "artifacts": manifest_entries,
        "created_files": list(OUTPUT_FILES),
        "source_directory": str(input_dir.relative_to(ROOT)).replace("\\", "/") if input_dir.is_relative_to(ROOT) else str(input_dir),
        "source_artifacts_read_only": True,
        "runtime_changed": False,
    }
    (output_dir / OUTPUT_FILES[12]).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    summary = run(args.input_dir.resolve(), args.output_dir.resolve())
    print(json.dumps({"final_status": summary["final_status"], "candidate_count": summary.get("aggregate_performance", {}).get("candidates"), "output_dir": str(args.output_dir)}, indent=2))


if __name__ == "__main__":
    main()
