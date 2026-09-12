"""Single-symbol, persisted-only PAPER winner/loser separability.

This module is deliberately independent from parameter search.  It reads one
closed PAPER position once, joins it to its exact persisted pre-entry pipeline
snapshot, and emits descriptive evidence only.  It never opens holdout data,
creates ranges, mutates production state, or treats reconstructed observations
as samples.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
from statistics import median
from typing import Any, Callable, Iterable, Mapping, Sequence

from sqlalchemy import text

from app.config.yaml_authority import RESEARCH_PARAMETERS
from .artifact_writer import DEFAULT_ARTIFACT_WRITER
from .engine import ReadOnlyResearchDatabase, resolve_database_binding


SOURCE_TYPE = "PERSISTED_CAUSAL_OBSERVATION"
PROFILE = "trade-5m-v2"
SCHEMA_VERSION = 1


def _path(source: str, *parts: str) -> Callable[[Mapping[str, Any]], object]:
    def get(row: Mapping[str, Any]) -> object:
        value: object = row.get(source) or {}
        for part in parts:
            if not isinstance(value, Mapping):
                return None
            value = value.get(part)
        return value
    return get


def _derived(name: str) -> Callable[[Mapping[str, Any]], object]:
    def get(row: Mapping[str, Any]) -> object:
        entry = _number(_path("paper", "hypothetical_entry_reference")(row))
        stop = _number(_path("paper", "hypothetical_stop_level")(row))
        target = _number(_path("paper", "hypothetical_target_level")(row))
        atr = _number(_path("paper", "paper_context", "causal_primitives", "atr_value")(row))
        if name == "stop_distance_bps" and entry and stop is not None:
            return abs(entry - stop) / entry * 10_000
        if name == "target_distance_bps" and entry and target is not None:
            return abs(target - entry) / entry * 10_000
        if name == "atr_normalized_stop" and atr and entry and stop is not None:
            return abs(entry - stop) / atr
        if name == "utc_hour":
            return datetime.fromtimestamp(int(row["entry_boundary_ms"]) / 1000, timezone.utc).hour
        if name == "utc_day_of_week":
            return datetime.fromtimestamp(int(row["entry_boundary_ms"]) / 1000, timezone.utc).strftime("%A").upper()
        return None
    return get


@dataclass(frozen=True, slots=True)
class FeatureSpec:
    name: str
    family: str
    data_type: str
    source: str
    source_field: str
    getter: Callable[[Mapping[str, Any]], object]
    missing_policy: str = "EXCLUDE_VALUE_NO_IMPUTATION"


FEATURE_SPECS: tuple[FeatureSpec, ...] = (
    FeatureSpec("setup_quality_score", "SETUP", "NUMERIC", "setup_payload_json", "quality_score", _path("setup", "quality_score")),
    FeatureSpec("setup_structural_score", "STRUCTURE", "NUMERIC", "setup_payload_json", "quality_diagnostics.structural_score", _path("setup", "quality_diagnostics", "structural_score")),
    FeatureSpec("setup_confirmation_score", "CONFIRMATION_COUNTS", "NUMERIC", "setup_payload_json", "quality_diagnostics.confirmation_score", _path("setup", "quality_diagnostics", "confirmation_score")),
    FeatureSpec("setup_context_score", "REGIME", "NUMERIC", "setup_payload_json", "quality_diagnostics.context_score", _path("setup", "quality_diagnostics", "context_score")),
    FeatureSpec("source_confidence", "SETUP", "NUMERIC", "setup_payload_json", "source_confidence", _path("setup", "source_confidence")),
    FeatureSpec("strategy_score", "STRATEGY_SCORE", "NUMERIC", "strategy_payload_json", "strategy_score", _path("strategy", "strategy_score")),
    FeatureSpec("strategy_raw_score", "STRATEGY_SCORE", "NUMERIC", "strategy_payload_json", "strategy_raw_score", _path("strategy", "strategy_raw_score")),
    FeatureSpec("strategy_margin_to_threshold", "STRATEGY_SCORE", "NUMERIC", "strategy_payload_json", "strategy_margin_to_threshold", _path("strategy", "strategy_margin_to_threshold")),
    FeatureSpec("risk_score", "STRATEGY_SCORE", "NUMERIC", "risk_payload_json", "risk_score", _path("risk", "risk_score")),
    FeatureSpec("plan_score", "STRATEGY_SCORE", "NUMERIC", "paper_payload_json", "plan_score", _path("paper", "plan_score")),
    FeatureSpec("planned_rr", "GROSS_RR", "NUMERIC", "paper_payload_json", "planned_rr", _path("paper", "planned_rr")),
    FeatureSpec("entry_reference", "ENTRY", "NUMERIC", "paper_payload_json", "hypothetical_entry_reference", _path("paper", "hypothetical_entry_reference")),
    FeatureSpec("stop_distance_bps", "STOP_DISTANCE", "NUMERIC", "derived_causal_geometry", "entry,stop", _derived("stop_distance_bps")),
    FeatureSpec("target_distance_bps", "TARGET_DISTANCE", "NUMERIC", "derived_causal_geometry", "entry,target", _derived("target_distance_bps")),
    FeatureSpec("atr_value", "ATR", "NUMERIC", "paper_payload_json", "paper_context.causal_primitives.atr_value", _path("paper", "paper_context", "causal_primitives", "atr_value")),
    FeatureSpec("atr_normalized_stop", "ATR", "NUMERIC", "derived_causal_geometry", "stop_distance/atr", _derived("atr_normalized_stop")),
    FeatureSpec("volatility_buffer", "VOLATILITY", "NUMERIC", "paper_payload_json", "paper_context.causal_primitives.volatility_buffer", _path("paper", "paper_context", "causal_primitives", "volatility_buffer")),
    FeatureSpec("effective_total_cost_bps", "COST", "NUMERIC", "paper_payload_json", "paper_context.scalping_geometry_diagnostics.effective_total_cost_bps", _path("paper", "paper_context", "scalping_geometry_diagnostics", "effective_total_cost_bps")),
    FeatureSpec("commission_bps", "COMMISSION", "NUMERIC", "paper_payload_json", "paper_context.scalping_geometry_diagnostics.commission_bps", _path("paper", "paper_context", "scalping_geometry_diagnostics", "commission_bps")),
    FeatureSpec("spread_bps", "SPREAD", "NUMERIC", "paper_payload_json", "paper_context.scalping_geometry_diagnostics.spread_bps", _path("paper", "paper_context", "scalping_geometry_diagnostics", "spread_bps")),
    FeatureSpec("slippage_bps", "SLIPPAGE", "NUMERIC", "paper_payload_json", "paper_context.scalping_geometry_diagnostics.entry_slippage_bps", _path("paper", "paper_context", "scalping_geometry_diagnostics", "entry_slippage_bps")),
    FeatureSpec("probability_sample_size", "PROBABILITY", "NUMERIC", "paper_payload_json", "paper_context.scalping_geometry_diagnostics.probability_sample_size", _path("paper", "paper_context", "scalping_geometry_diagnostics", "probability_sample_size")),
    FeatureSpec("estimated_p_win", "PROBABILITY", "NUMERIC", "paper_payload_json", "paper_context.scalping_geometry_diagnostics.p_win_raw", _path("paper", "paper_context", "scalping_geometry_diagnostics", "p_win_raw")),
    FeatureSpec("expected_ev_r", "EV", "NUMERIC", "paper_payload_json", "paper_context.scalping_geometry_diagnostics.expected_ev_r", _path("paper", "paper_context", "scalping_geometry_diagnostics", "expected_ev_r")),
    FeatureSpec("net_edge_bps", "NET_RR", "NUMERIC", "paper_payload_json", "paper_context.scalping_geometry_diagnostics.expected_net_edge_bps", _path("paper", "paper_context", "scalping_geometry_diagnostics", "expected_net_edge_bps")),
    FeatureSpec("utc_hour", "TIME_OF_DAY", "ORDINAL", "entry_boundary_ms", "UTC hour", _derived("utc_hour")),
    FeatureSpec("direction", "DIRECTION", "CATEGORICAL", "paper_positions", "side", lambda row: row.get("side")),
    FeatureSpec("utc_day_of_week", "DAY_OF_WEEK", "CATEGORICAL", "entry_boundary_ms", "UTC weekday", _derived("utc_day_of_week")),
    FeatureSpec("setup_type", "SETUP", "CATEGORICAL", "setup_payload_json", "setup_type", _path("setup", "setup_type")),
    FeatureSpec("regime", "REGIME", "CATEGORICAL", "setup_payload_json", "source_regime", _path("setup", "source_regime")),
    FeatureSpec("impulse_phase", "IMPULSE", "CATEGORICAL", "setup_payload_json", "source_impulse_phase", _path("setup", "source_impulse_phase")),
    FeatureSpec("setup_quality", "SETUP", "ORDINAL", "setup_payload_json", "setup_quality", _path("setup", "setup_quality")),
    FeatureSpec("strategy_quality", "STRATEGY_SCORE", "ORDINAL", "strategy_payload_json", "strategy_quality", _path("strategy", "strategy_quality")),
    FeatureSpec("risk_level", "STRATEGY_SCORE", "ORDINAL", "risk_payload_json", "risk_level", _path("risk", "risk_level")),
    FeatureSpec("confirmation_state", "CONFIRMATION_COUNTS", "CATEGORICAL", "setup_payload_json", "confirmation_state", _path("setup", "confirmation_state")),
    FeatureSpec("entry_reference_source", "ENTRY_REFINEMENT", "CATEGORICAL", "paper_payload_json", "entry_reference_source", _path("paper", "entry_reference_source")),
    FeatureSpec("stop_source", "GEOMETRY", "CATEGORICAL", "paper_payload_json", "stop_source", _path("paper", "stop_source")),
    FeatureSpec("target_source", "GEOMETRY", "CATEGORICAL", "paper_payload_json", "target_source", _path("paper", "target_source")),
    FeatureSpec("has_conflict", "STRUCTURE", "BOOLEAN", "setup_payload_json", "quality_diagnostics.has_conflict", _path("setup", "quality_diagnostics", "has_conflict")),
    FeatureSpec("liquidity_presence", "VOLUME", "BOOLEAN", "setup_payload_json", "diagnostics.liquidity_presence", _path("setup", "diagnostics", "liquidity_presence")),
    FeatureSpec("strategy_cap_applied", "STRATEGY_SCORE", "BOOLEAN", "strategy_payload_json", "strategy_cap_applied", _path("strategy", "strategy_cap_applied")),
    FeatureSpec("risk_pre_approved", "STRATEGY_SCORE", "BOOLEAN", "risk_payload_json", "risk_pre_approved", _path("risk", "risk_pre_approved")),
    FeatureSpec("causal_reset_state", "CAUSAL_RESET_STATE", "CATEGORICAL", "paper_payload_json", "paper_context.causal_reset_state", _path("paper", "paper_context", "causal_reset_state")),
    FeatureSpec("momentum_score", "MOMENTUM", "NUMERIC", "setup_payload_json", "context.momentum_score", _path("setup", "context", "momentum_score")),
    FeatureSpec("volume_ratio", "VOLUME", "NUMERIC", "setup_payload_json", "context.volume_ratio", _path("setup", "context", "volume_ratio")),
    FeatureSpec("dynamic_required_rr", "DYNAMIC_REQUIRED_RR", "NUMERIC", "paper_payload_json", "paper_context.dynamic_required_rr", _path("paper", "paper_context", "dynamic_required_rr")),
)


def _number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _timestamp_ms(value: datetime) -> int:
    return int(value.astimezone(timezone.utc).timestamp() * 1000)


def load_persisted_closed_trades(
    database: ReadOnlyResearchDatabase, *, symbol: str, profile: str = PROFILE,
) -> list[dict[str, Any]]:
    """Read the exact persisted causal snapshot linked to each closed trade."""
    sql = text("""
        SELECT p.position_id,p.symbol,p.side,p.opened_at,p.closed_at,p.realized_pnl,
               c.command_id,c.pipeline_run_id,c.strategy_decision_id,
               c.risk_decision_id,c.setup_id,c.created_at AS command_created_at,
               c.closed_until_ms AS command_boundary_ms,c.future_bars_used,
               r.closed_until_ms,r.setup_payload_json,r.strategy_payload_json,
               r.risk_payload_json,r.paper_payload_json,r.trade_profile_id
        FROM paper_positions p
        JOIN paper_orders o ON o.order_id=p.entry_order_id
        JOIN paper_execution_commands c ON c.command_id=o.command_id
        JOIN online_pipeline_results r
          ON r.run_id=c.pipeline_run_id AND r.symbol=p.symbol
        JOIN online_pipeline_runs u ON u.run_id=r.run_id
        WHERE p.symbol=:symbol AND p.state='CLOSED'
          AND p.mode='PAPER' AND c.mode='PAPER'
          AND u.trade_profile_id=:profile AND r.trade_profile_id=:profile
        ORDER BY p.opened_at,p.position_id
    """)
    with database.connection() as connection:
        return [dict(row) for row in database.execute_select(
            connection, sql.bindparams(symbol=symbol, profile=profile),
        ).mappings()]


def label_net_pnl(value: object) -> str:
    number = _number(value)
    if number is None:
        raise ValueError("authoritative net PAPER PnL is missing")
    return "WIN" if number > 0 else "LOSS" if number < 0 else "NEUTRAL"


def construct_dataset(
    source_rows: Iterable[Mapping[str, Any]], *, symbol: str,
    feature_specs: Sequence[FeatureSpec] = FEATURE_SPECS,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    dataset: list[dict[str, Any]] = []
    seen: set[str] = set()
    diagnostics = {
        "source_rows": 0, "duplicate_trade_rows": 0,
        "cross_symbol_rows": 0, "future_leakage_violations": 0,
        "reconstructed_rows_rejected": 0,
    }
    for source in source_rows:
        diagnostics["source_rows"] += 1
        if source.get("source_type", SOURCE_TYPE) != SOURCE_TYPE:
            diagnostics["reconstructed_rows_rejected"] += 1
            continue
        if str(source.get("symbol")) != symbol:
            diagnostics["cross_symbol_rows"] += 1
            continue
        trade_id = str(source.get("position_id") or "")
        if not trade_id:
            continue
        if trade_id in seen:
            diagnostics["duplicate_trade_rows"] += 1
            continue
        opened_at = source.get("opened_at")
        closed_at = source.get("closed_at")
        if not isinstance(opened_at, datetime) or not isinstance(closed_at, datetime):
            continue
        entry_boundary = _timestamp_ms(opened_at)
        layer_payloads = {
            "setup": source.get("setup_payload_json") or {},
            "strategy": source.get("strategy_payload_json") or {},
            "risk": source.get("risk_payload_json") or {},
            "paper": source.get("paper_payload_json") or {},
        }
        timestamps = [
            int(payload[key]) for payload in layer_payloads.values()
            if isinstance(payload, Mapping) for key in ("created_at_ms", "closed_until_ms")
            if payload.get(key) is not None
        ]
        command_created = source.get("command_created_at")
        if isinstance(command_created, datetime):
            timestamps.append(_timestamp_ms(command_created))
        if bool(source.get("future_bars_used")) or any(
            bool(payload.get("future_bars_used"))
            for payload in layer_payloads.values() if isinstance(payload, Mapping)
        ) or any(stamp > entry_boundary for stamp in timestamps):
            diagnostics["future_leakage_violations"] += 1
            continue
        context = {
            **layer_payloads, "side": source.get("side"),
            "entry_boundary_ms": entry_boundary,
        }
        features: dict[str, object] = {}
        for spec in feature_specs:
            value = spec.getter(context)
            if spec.data_type in {"NUMERIC", "ORDINAL"} and spec.name not in {
                "setup_quality", "strategy_quality", "risk_level",
            }:
                value = _number(value)
            features[spec.name] = value
        paper = layer_payloads["paper"]
        final_generation = paper.get("final_approval_generation") or {}
        runtime_version = (
            paper.get("runtime_parameter_set_id")
            or layer_payloads["setup"].get("runtime_parameter_set_id")
            or source.get("trade_profile_id") or PROFILE
        )
        dataset.append({
            "symbol": symbol,
            "trade_id": trade_id,
            "position_id": trade_id,
            "candidate_id": str(source.get("setup_id") or layer_payloads["setup"].get("setup_id") or "") or None,
            "approval_id": str(
                final_generation.get("final_approval_id")
                or source.get("risk_decision_id") or ""
            ) or None,
            "plan_id": str(paper.get("paper_plan_id") or "") or None,
            "command_id": str(source.get("command_id") or "") or None,
            "pipeline_run_id": str(source.get("pipeline_run_id") or "") or None,
            "entry_boundary_ms": entry_boundary,
            "entry_timestamp": opened_at.astimezone(timezone.utc).isoformat(),
            "close_timestamp": closed_at.astimezone(timezone.utc).isoformat(),
            "profile_id": str(source.get("trade_profile_id") or PROFILE),
            "profile_version": str(runtime_version),
            "source_type": SOURCE_TYPE,
            "causal_feature_timestamp_max_ms": max(timestamps, default=int(source.get("closed_until_ms") or entry_boundary)),
            "net_paper_pnl": _number(source.get("realized_pnl")),
            "label": label_net_pnl(source.get("realized_pnl")),
            "features": features,
        })
        seen.add(trade_id)
    dataset.sort(key=lambda row: (row["entry_boundary_ms"], row["trade_id"]))
    return dataset, diagnostics


def _quantile(values: Sequence[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lo, hi = math.floor(index), math.ceil(index)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] * (hi - index) + ordered[hi] * (index - lo)


def _auc(winners: Sequence[float], losers: Sequence[float]) -> float | None:
    if not winners or not losers:
        return None
    score = sum(1.0 if w > l else 0.5 if w == l else 0.0 for w in winners for l in losers)
    return score / (len(winners) * len(losers))


def _adequacy(winners: int, losers: int) -> str:
    if not winners or not losers:
        return "LOW_SAMPLE"
    if min(winners, losers) < 5 or winners + losers < 20:
        return "DESCRIPTIVE_ONLY"
    return "USABLE"


def _direction(auc: float | None, *, epsilon: float = 0.05) -> str:
    if auc is None or abs(auc - 0.5) <= epsilon:
        return "NO_CLEAR_DIRECTION"
    return "WINNERS_HIGHER" if auc > 0.5 else "WINNERS_LOWER"


def build_registry(
    dataset: Sequence[Mapping[str, Any]], feature_specs: Sequence[FeatureSpec] = FEATURE_SPECS,
) -> list[dict[str, Any]]:
    result = []
    for spec in feature_specs:
        values = [row["features"].get(spec.name) for row in dataset]
        present = [value for value in values if value is not None]
        result.append({
            "feature_name": spec.name, "semantic_family": spec.family,
            "data_type": spec.data_type, "source": spec.source,
            "source_field": spec.source_field,
            "causal_timestamp_basis": "MAX_PERSISTED_LAYER_TIMESTAMP_LE_ENTRY_BOUNDARY",
            "missing_policy": spec.missing_policy,
            "analysis_method": "ROBUST_NUMERIC_RANK_AUC" if spec.data_type == "NUMERIC" else "CATEGORY_WIN_LOSS_LIFT",
            "availability_count": len(present), "missing_count": len(values) - len(present),
            "distinct_count": len({_stable_value(value) for value in present}),
        })
    return result


def _stable_value(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def build_activity(registry: Sequence[Mapping[str, Any]], total: int) -> list[dict[str, Any]]:
    result = []
    for row in registry:
        present, distinct = int(row["availability_count"]), int(row["distinct_count"])
        if present == 0:
            status, reason = "ALL_MISSING", "UNAVAILABLE_HISTORICALLY_NO_IMPUTATION"
        elif present <= max(1, math.floor(total * 0.1)):
            status, reason = "NEARLY_ALL_MISSING", "INSUFFICIENT_COVERAGE"
        elif distinct == 1:
            status, reason = "CONSTANT", "ONE_DISTINCT_OBSERVED_VALUE"
        elif distinct <= 2 and row["data_type"] == "NUMERIC" and total >= 10:
            status, reason = "EFFECTIVELY_CONSTANT", "TWO_DISTINCT_NUMERIC_VALUES"
        else:
            status, reason = "ACTIVE", "OBSERVED_VARIATION"
        result.append({
            "feature": row["feature_name"], "distinct_count": distinct,
            "non_null_count": present, "activity_status": status, "reason": reason,
        })
    return result


def _numeric_distribution(values: Sequence[float]) -> dict[str, float | None]:
    return {
        "mean": sum(values) / len(values) if values else None,
        "median": median(values) if values else None,
        **{f"p{int(q*100):02d}": _quantile(values, q) for q in (.1, .25, .5, .75, .9)},
    }


def numeric_analysis(
    dataset: Sequence[Mapping[str, Any]], registry: Sequence[Mapping[str, Any]],
    activity: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    active = {row["feature"]: row["activity_status"] for row in activity}
    result = []
    for meta in registry:
        name = str(meta["feature_name"])
        if meta["data_type"] != "NUMERIC":
            continue
        winners = [_number(row["features"].get(name)) for row in dataset if row["label"] == "WIN"]
        losers = [_number(row["features"].get(name)) for row in dataset if row["label"] == "LOSS"]
        wins = [value for value in winners if value is not None]
        losses = [value for value in losers if value is not None]
        auc = _auc(wins, losses)
        all_values = wins + losses
        iqr = (_quantile(all_values, .75) or 0) - (_quantile(all_values, .25) or 0)
        win_dist, loss_dist = _numeric_distribution(wins), _numeric_distribution(losses)
        median_delta = (
            abs(float(win_dist["median"]) - float(loss_dist["median"]))
            if win_dist["median"] is not None and loss_dist["median"] is not None else None
        )
        effect = median_delta / iqr if median_delta is not None and iqr > 0 else (0.0 if median_delta == 0 else None)
        separation = None if auc is None else abs(2 * auc - 1)
        result.append({
            "feature": name, "winner_count": len(wins), "loser_count": len(losses),
            "winner_mean": win_dist["mean"], "loser_mean": loss_dist["mean"],
            "winner_median": win_dist["median"], "loser_median": loss_dist["median"],
            **{f"winner_{key}": value for key, value in win_dist.items() if key.startswith("p")},
            **{f"loser_{key}": value for key, value in loss_dist.items() if key.startswith("p")},
            "absolute_median_delta": median_delta,
            "normalized_effect_size": effect,
            "distribution_overlap": None if separation is None else 1 - separation,
            "rank_auc": auc, "separation_score": separation,
            "direction": _direction(auc),
            "sample_adequacy_status": _adequacy(len(wins), len(losses)),
            "usable": active.get(name) == "ACTIVE" and bool(wins) and bool(losses),
            "activity_status": active.get(name),
        })
    return result


def categorical_analysis(
    dataset: Sequence[Mapping[str, Any]], registry: Sequence[Mapping[str, Any]],
    activity: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    active = {row["feature"]: row["activity_status"] for row in activity}
    binary = [row for row in dataset if row["label"] in {"WIN", "LOSS"}]
    global_win_rate = sum(row["label"] == "WIN" for row in binary) / len(binary) if binary else 0
    result = []
    for meta in registry:
        if meta["data_type"] not in {"BOOLEAN", "CATEGORICAL", "ORDINAL"}:
            continue
        name = str(meta["feature_name"])
        buckets: dict[str, dict[str, int]] = {}
        missing = 0
        for row in binary:
            value = row["features"].get(name)
            if value is None:
                missing += 1
                continue
            key = str(value)
            bucket = buckets.setdefault(key, {"count": 0, "wins": 0, "losses": 0})
            bucket["count"] += 1
            bucket["wins"] += int(row["label"] == "WIN")
            bucket["losses"] += int(row["label"] == "LOSS")
        winner_total = sum(bucket["wins"] for bucket in buckets.values())
        loser_total = sum(bucket["losses"] for bucket in buckets.values())
        categories = []
        for key in sorted(buckets):
            bucket = buckets[key]
            rate = bucket["wins"] / bucket["count"]
            categories.append({
                "category": key, **bucket, "win_rate": rate,
                "loss_rate": bucket["losses"] / bucket["count"],
                "share_of_winners": bucket["wins"] / winner_total if winner_total else 0,
                "share_of_losers": bucket["losses"] / loser_total if loser_total else 0,
                "lift_vs_global_win_rate": rate / global_win_rate if global_win_rate else None,
            })
        separation = .5 * sum(abs(c["share_of_winners"] - c["share_of_losers"]) for c in categories)
        result.append({
            "feature": name, "categories": categories,
            "distinct_categories": len(categories),
            "rare_category_count": sum(c["count"] < 2 for c in categories),
            "missing_category_count": missing,
            "separation_score": separation if winner_total and loser_total else None,
            "direction": "CATEGORY_DEPENDENT" if separation > 0 else "NO_CLEAR_DIRECTION",
            "sample_adequacy_status": _adequacy(winner_total, loser_total),
            "usable": active.get(name) == "ACTIVE" and bool(winner_total) and bool(loser_total),
            "activity_status": active.get(name),
        })
    return result


def stability_analysis(
    dataset: Sequence[Mapping[str, Any]], analyses: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    slice_getters = {
        "UTC_DAY": lambda row: str(row["entry_timestamp"])[:10],
        "DIRECTION": lambda row: str(row["features"].get("direction")),
        "SETUP": lambda row: str(row["features"].get("setup_type")),
        "REGIME": lambda row: str(row["features"].get("regime")),
    }
    for analysis in analyses:
        name = str(analysis["feature"])
        global_direction = str(analysis["direction"])
        agreements = disagreements = available = 0
        details = []
        for family, getter in slice_getters.items():
            keys = sorted({getter(row) for row in dataset})
            for key in keys:
                rows = [row for row in dataset if getter(row) == key and row["label"] in {"WIN", "LOSS"}]
                wins = [row for row in rows if row["label"] == "WIN"]
                losses = [row for row in rows if row["label"] == "LOSS"]
                if not wins or not losses:
                    continue
                if "rank_auc" in analysis:
                    w = [_number(row["features"].get(name)) for row in wins]
                    l = [_number(row["features"].get(name)) for row in losses]
                    direction = _direction(_auc([v for v in w if v is not None], [v for v in l if v is not None]))
                else:
                    direction = "CATEGORY_DEPENDENT"
                available += 1
                agree = direction == global_direction and direction != "NO_CLEAR_DIRECTION"
                agreements += int(agree)
                disagreements += int(not agree and direction != "NO_CLEAR_DIRECTION")
                details.append({"slice_family": family, "slice": key, "direction": direction, "rows": len(rows)})
        denominator = agreements + disagreements
        result[name] = {
            "global_direction": global_direction, "direction_agreement_count": agreements,
            "direction_disagreement_count": disagreements, "available_slice_count": available,
            "stability_score": agreements / denominator if denominator else 0.0,
            "slices": details,
        }
    return result


def rank_features(
    registry: Sequence[Mapping[str, Any]], numeric: Sequence[Mapping[str, Any]],
    categorical: Sequence[Mapping[str, Any]], stability: Mapping[str, Mapping[str, Any]],
    total_rows: int,
) -> list[dict[str, Any]]:
    meta = {str(row["feature_name"]): row for row in registry}
    result = []
    for analysis in [*numeric, *categorical]:
        name = str(analysis["feature"])
        coverage = int(meta[name]["availability_count"]) / total_rows if total_rows else 0
        separation = float(analysis.get("separation_score") or 0)
        stable = float(stability[name]["stability_score"])
        sample_count = int(analysis.get("winner_count", 0)) + int(analysis.get("loser_count", 0))
        if not sample_count:
            sample_count = sum(int(c["count"]) for c in analysis.get("categories", []))
        sample_weight = min(1.0, sample_count / 10)
        score = separation * coverage * sample_weight * (0.5 + 0.5 * stable)
        usable = bool(analysis["usable"])
        if not usable:
            evidence_class = "UNUSABLE"
        elif analysis["sample_adequacy_status"] != "USABLE":
            evidence_class = "DESCRIPTIVE_ONLY"
        elif score >= .6:
            evidence_class = "STRONG_EVIDENCE"
        elif score >= .35:
            evidence_class = "MODERATE_EVIDENCE"
        elif score >= .1:
            evidence_class = "WEAK_EVIDENCE"
        else:
            evidence_class = "NO_SEPARATION"
        result.append({
            "feature": name, "data_type": meta[name]["data_type"],
            "separation_score": separation, "coverage": coverage,
            "missingness": 1 - coverage, "stability_score": stable,
            "direction": analysis["direction"], "ranking_score": score,
            "ranking_class": evidence_class,
            "sample_adequacy_status": analysis["sample_adequacy_status"],
            "usable": usable,
        })
    return sorted(result, key=lambda row: (-row["ranking_score"], row["feature"]))


def interaction_screen(
    dataset: Sequence[Mapping[str, Any]], ranking: Sequence[Mapping[str, Any]],
    *, top_n: int,
) -> list[dict[str, Any]]:
    # Restrict to numeric/ordinal features so pair geometry stays meaningful.
    chosen = [row for row in ranking if row["usable"] and row["data_type"] in {"NUMERIC", "ORDINAL"}][:top_n]
    result = []
    for left_index, left in enumerate(chosen):
        for right in chosen[left_index + 1:]:
            usable_rows = []
            for row in dataset:
                if row["label"] not in {"WIN", "LOSS"}:
                    continue
                a, b = _number(row["features"].get(left["feature"])), _number(row["features"].get(right["feature"]))
                if a is not None and b is not None:
                    usable_rows.append((row["label"], a, b))
            if not usable_rows:
                continue
            mins = (min(r[1] for r in usable_rows), min(r[2] for r in usable_rows))
            spans = (max(r[1] for r in usable_rows) - mins[0], max(r[2] for r in usable_rows) - mins[1])
            oriented = []
            for label, a, b in usable_rows:
                av = (a - mins[0]) / spans[0] if spans[0] else .5
                bv = (b - mins[1]) / spans[1] if spans[1] else .5
                if left["direction"] == "WINNERS_LOWER": av = 1 - av
                if right["direction"] == "WINNERS_LOWER": bv = 1 - bv
                oriented.append((label, (av + bv) / 2))
            wins = [score for label, score in oriented if label == "WIN"]
            losses = [score for label, score in oriented if label == "LOSS"]
            auc = _auc(wins, losses)
            combined = None if auc is None else abs(2 * auc - 1)
            best_single = max(float(left["separation_score"]), float(right["separation_score"]))
            result.append({
                "feature_a": left["feature"], "feature_b": right["feature"],
                "sample_count": len(oriented), "interaction_score": combined,
                "univariate_score_a": left["separation_score"],
                "univariate_score_b": right["separation_score"],
                "incremental_separation": None if combined is None else combined - best_single,
                "direction_category_pattern": f"{left['direction']} + {right['direction']}",
                "stability_notes": "DESCRIPTIVE_ONLY_BOUNDED_PAIRWISE_SCREEN",
            })
    return sorted(result, key=lambda row: (-(row["interaction_score"] or -1), row["feature_a"], row["feature_b"]))


def handoff_artifact(
    ranking: Sequence[Mapping[str, Any]], numeric: Sequence[Mapping[str, Any]],
    categorical: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    numeric_by_name = {str(row["feature"]): row for row in numeric}
    categorical_by_name = {str(row["feature"]): row for row in categorical}
    features = []
    for ranked in ranking:
        name = str(ranked["feature"])
        common = {
            "feature": name, "usable": ranked["usable"], "direction": ranked["direction"],
            "separation_score": ranked["separation_score"], "stability_score": ranked["stability_score"],
            "coverage": ranked["coverage"], "missingness": ranked["missingness"],
            "sample_adequacy_status": ranked["sample_adequacy_status"],
        }
        if name in numeric_by_name:
            row = numeric_by_name[name]
            common.update({
                "data_type": "NUMERIC",
                "winner_distribution": {key.removeprefix("winner_"): value for key, value in row.items() if key.startswith("winner_") and key not in {"winner_count"}},
                "loser_distribution": {key.removeprefix("loser_"): value for key, value in row.items() if key.startswith("loser_") and key not in {"loser_count"}},
            })
        else:
            common.update({"data_type": ranked["data_type"], "categories": categorical_by_name[name]["categories"]})
        features.append(common)
    return {
        "artifact": "SEPARABILITY_HANDOFF", "schema_version": SCHEMA_VERSION,
        "purpose": "EMPIRICAL_INPUT_FOR_FUTURE_DATA_DRIVEN_RANGE_GENERATION",
        "descriptive_evidence_only": True,
        "features": features,
    }


def _manifest(
    dataset: Sequence[Mapping[str, Any]], registry: Sequence[Mapping[str, Any]],
    activity: Sequence[Mapping[str, Any]], diagnostics: Mapping[str, int], *, symbol: str,
) -> dict[str, Any]:
    labels = {name: sum(row["label"] == name for row in dataset) for name in ("WIN", "LOSS", "NEUTRAL")}
    start = dataset[0]["entry_timestamp"] if dataset else None
    end = dataset[-1]["close_timestamp"] if dataset else None
    actual_days = None
    if dataset:
        actual_days = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds() / 86400
    active = {row["feature"]: row["activity_status"] for row in activity}
    excluded = sum(status != "ACTIVE" for status in active.values())
    return {
        "artifact": "SEPARABILITY_DATASET_MANIFEST", "schema_version": SCHEMA_VERSION,
        "symbol": symbol, "profile": PROFILE, "history_start": start, "history_end": end,
        "history_actual_days": actual_days, "source_type": SOURCE_TYPE,
        "source_rows": diagnostics["source_rows"], "closed_trades": len(dataset),
        "wins": labels["WIN"], "losses": labels["LOSS"], "neutrals": labels["NEUTRAL"],
        "binary_analysis_rows": labels["WIN"] + labels["LOSS"],
        "feature_count_total": len(registry),
        "numeric_feature_count": sum(row["data_type"] == "NUMERIC" for row in registry),
        "categorical_feature_count": sum(row["data_type"] in {"CATEGORICAL", "BOOLEAN", "ORDINAL"} for row in registry),
        "excluded_feature_count": excluded,
        "usable_feature_count": len(registry) - excluded,
        "constant_feature_count": sum(status in {"CONSTANT", "EFFECTIVELY_CONSTANT"} for status in active.values()),
        "missing_feature_count": sum(status in {"ALL_MISSING", "NEARLY_ALL_MISSING"} for status in active.values()),
        "cross_symbol_rows": diagnostics["cross_symbol_rows"],
        "duplicate_trade_rows": diagnostics["duplicate_trade_rows"],
        "future_leakage_violations": diagnostics["future_leakage_violations"],
        "reconstructed_rows_rejected": diagnostics["reconstructed_rows_rejected"],
        "reconstructed_rows_used": 0, "holdout_opened": False,
        "ranges_generated": False, "search_executed": False,
    }


def _report(manifest: Mapping[str, Any], ranking: Sequence[Mapping[str, Any]], activity: Sequence[Mapping[str, Any]], interactions: Sequence[Mapping[str, Any]]) -> str:
    winners = [row for row in ranking if row["usable"] and row["direction"] == "WINNERS_HIGHER"][:5]
    losers = [row for row in ranking if row["usable"] and row["direction"] == "WINNERS_LOWER"][:5]
    categories = [row for row in ranking if row["usable"] and row["direction"] == "CATEGORY_DEPENDENT"][:5]
    names = lambda rows: ", ".join(str(row["feature"]) for row in rows) or "NONE"
    no_ops = [row["feature"] for row in activity if row["activity_status"] in {"CONSTANT", "EFFECTIVELY_CONSTANT"}]
    missing = [row["feature"] for row in activity if row["activity_status"] in {"ALL_MISSING", "NEARLY_ALL_MISSING"}]
    return f"""# Single-symbol Winner / Loser Separability

- Selected symbol: `{manifest['symbol']}`
- Profile/source: `{manifest['profile']}` / `{manifest['source_type']}`
- History actually used: `{manifest['history_start']}` through `{manifest['history_end']}` ({manifest['history_actual_days']:.6f} days)
- Closed PAPER trades: {manifest['closed_trades']} (WIN {manifest['wins']}, LOSS {manifest['losses']}, NEUTRAL {manifest['neutrals']})
- Binary analysis rows: {manifest['binary_analysis_rows']}
- Causality: persisted exact pre-entry snapshots; future leakage violations {manifest['future_leakage_violations']}
- Single-symbol integrity: cross-symbol rows {manifest['cross_symbol_rows']}; duplicate trade rows {manifest['duplicate_trade_rows']}

## Descriptive evidence

- Top winner-associated numeric features: {names(winners)}
- Top loser-associated numeric features: {names(losers)}
- Top categorical distinctions: {names(categories)}
- Constant/no-op features: {', '.join(no_ops) or 'NONE'}
- Missing/unavailable features: {', '.join(missing) or 'NONE'}
- Top bounded interactions: {', '.join(f"{r['feature_a']} + {r['feature_b']}" for r in interactions[:5]) or 'NONE'}

## Adequacy and scope

This is descriptive evidence only when either class has fewer than five trades or the binary sample has fewer than 20 rows.  The canonical validation policy (20 trades / 3 UTC days) is recorded elsewhere and is not used to suppress separability output.  No production decision, cutoff, threshold, search range, search run, or holdout access is produced here.
"""


def run_separability(
    *, database: ReadOnlyResearchDatabase, symbol: str, output: Path,
    source_rows: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    raw = list(source_rows) if source_rows is not None else load_persisted_closed_trades(database, symbol=symbol)
    dataset, diagnostics = construct_dataset(raw, symbol=symbol)
    registry = build_registry(dataset)
    activity = build_activity(registry, len(dataset))
    numeric = numeric_analysis(dataset, registry, activity)
    categorical = categorical_analysis(dataset, registry, activity)
    analyses = [*numeric, *categorical]
    stability = stability_analysis(dataset, analyses)
    ranking = rank_features(registry, numeric, categorical, stability, len(dataset))
    top_n = int(RESEARCH_PARAMETERS.artifact.top_config_count)
    interactions = interaction_screen(dataset, ranking, top_n=top_n)
    handoff = handoff_artifact(ranking, numeric, categorical)
    manifest = _manifest(dataset, registry, activity, diagnostics, symbol=symbol)
    manifest["dataset_sha256"] = sha256("".join(
        json.dumps(row, sort_keys=True, separators=(",", ":"), default=str) + "\n" for row in dataset
    ).encode()).hexdigest()
    output.mkdir(parents=True, exist_ok=True)
    writer = DEFAULT_ARTIFACT_WRITER
    writer.atomic_text(output / "SEPARABILITY_DATASET.jsonl", "".join(
        json.dumps(row, sort_keys=True, default=str) + "\n" for row in dataset
    ), operation="separability_dataset")
    for filename, artifact in (
        ("SEPARABILITY_DATASET_MANIFEST.json", manifest),
        ("FEATURE_REGISTRY.json", registry),
        ("NUMERIC_SEPARABILITY.json", numeric),
        ("CATEGORICAL_SEPARABILITY.json", categorical),
        ("FEATURE_ACTIVITY.json", activity),
        ("INTERACTION_SCREEN.json", interactions),
        ("FEATURE_RANKING.json", ranking),
        ("SEPARABILITY_HANDOFF.json", handoff),
    ):
        writer.atomic_json(output / filename, artifact, operation=filename.lower())
    writer.atomic_text(output / "REPORT.md", _report(manifest, ranking, activity, interactions), operation="separability_report")
    return {"manifest": manifest, "ranking": ranking, "interactions": interactions, "output": str(output)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="DOGEUSDT")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--database-url")
    args = parser.parse_args(argv)
    output = args.output or Path("artifacts/scalping_v2_parameter_sweep") / f"separability_{args.symbol.lower()}"
    database = ReadOnlyResearchDatabase(resolve_database_binding(explicit_url=args.database_url))
    try:
        result = run_separability(database=database, symbol=args.symbol, output=output)
    finally:
        database.dispose()
    print(json.dumps(result["manifest"], sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
