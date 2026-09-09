"""Immutable probability-authority forensic over a frozen RR cohort.

Production access is SELECT-only.  The report distinguishes current eligible
evidence from deliberately non-authoritative compatibility diagnostics.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config.trade_parameters import SCALPING_V2
from app.engine_paper.scalping_statistics import (
    PaperOutcome, hierarchy_from_outcomes, load_prospective_outcomes,
)
from scripts.forensic_scalping_rr_dynamic_anchor import _psql


PROFILE = "trade-5m-v2"
SET_ID = "scalping-v2-set-2"


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _nested(value: object, *path: str) -> object | None:
    current = value
    for key in path:
        current = _mapping(current).get(key)
    return current


def _text(value: object, default: str = "UNKNOWN") -> str:
    return str(value or default).strip().upper() or default


def _utc_ms(value: object) -> int:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return 0
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp() * 1000)


def _cost_bucket(value: object) -> str:
    try:
        cost = float(value)
    except (TypeError, ValueError):
        return "UNKNOWN"
    return "LOW" if cost <= 20 else "MEDIUM" if cost <= 40 else "HIGH"


def load_rows(start: int, end: int) -> dict[str, dict[str, Any]]:
    sql = f"""SET default_transaction_read_only=on; SELECT row_to_json(x) FROM (
      SELECT r.run_id,r.symbol,r.closed_until_ms,r.setup_payload_json setup,
             r.analysis_payload_json analysis,r.strategy_payload_json strategy,
             r.paper_payload_json paper
      FROM online_pipeline_results r
      WHERE r.trade_profile_id='{PROFILE}' AND r.closed_until_ms BETWEEN {start} AND {end}
      ORDER BY r.closed_until_ms,r.symbol,r.run_id) x;"""
    return {
        item["run_id"]: item
        for line in _psql(sql) if line.startswith("{")
        for item in (json.loads(line),)
    }


def load_closed_paper_outcomes() -> tuple[PaperOutcome, ...]:
    sql = f"""SET default_transaction_read_only=on; SELECT row_to_json(x) FROM (
      SELECT p.symbol,p.side,p.realized_pnl,p.closed_at,
             r.setup_payload_json setup,r.analysis_payload_json analysis,r.paper_payload_json paper
      FROM paper_positions p
      JOIN paper_orders o ON o.order_id=p.entry_order_id
      JOIN paper_execution_commands c ON c.command_id=o.command_id
      JOIN online_pipeline_runs u ON u.run_id=c.pipeline_run_id
      JOIN online_pipeline_results r ON r.run_id=u.run_id
      WHERE p.state='CLOSED' AND u.trade_profile_id='{PROFILE}' ORDER BY p.closed_at) x;"""
    values = []
    for line in _psql(sql):
        if not line.startswith("{"):
            continue
        row = json.loads(line)
        paper = _mapping(row.get("paper"))
        cost = _nested(paper, "paper_context", "scalping_geometry_diagnostics", "effective_total_cost_bps")
        values.append(PaperOutcome(
            symbol=_text(row.get("symbol")),
            setup_type=_text(_nested(row.get("setup"), "setup_type")),
            direction="BULLISH" if _text(row.get("side")) == "LONG" else "BEARISH",
            regime=_text(_nested(row.get("analysis"), "regime")),
            cost_bucket=_cost_bucket(cost),
            won=float(row.get("realized_pnl") or 0) > 0,
            parameter_set_id=str(
                paper.get("parameter_set_id") or paper.get("runtime_parameter_set_id")
                or "legacy-unattributed"
            ).lower(),
            observed_at_ms=_utc_ms(row.get("closed_at")),
        ))
    return tuple(values)


def candidate_identity(proof: Mapping[str, Any], row: Mapping[str, Any]) -> dict[str, Any]:
    diagnostic = _mapping(_nested(row.get("paper"), "paper_context", "scalping_geometry_diagnostics"))
    setup_type = _text(_nested(row.get("setup"), "setup_type"))
    direction = _text(_nested(row.get("paper"), "paper_direction"))
    regime = _text(_nested(row.get("analysis"), "regime"))
    cost_bucket = _cost_bucket(diagnostic.get("effective_total_cost_bps"))
    symbol = _text(row.get("symbol"))
    key = f"exact|{symbol}|{setup_type}|{direction}|{regime}|{cost_bucket}"
    return {
        **dict(proof),
        "bucket_id": key,
        "bucket_key": key,
        "bucket_dimensions": {
            "symbol": symbol, "setup_type": setup_type, "direction": direction,
            "market_regime": regime, "cost_bucket": cost_bucket,
        },
        "strategy": _nested(row.get("strategy"), "strategy_type"),
        "side": "LONG" if direction == "BULLISH" else "SHORT",
        "market_regime": regime,
        "volatility_bucket": None,
        "session_bucket": None,
        "parameter_set_in_bucket_key": False,
        "config_hash_in_bucket_key": False,
    }


def classify_eta(current: int, required: int, rate_per_hour: float) -> tuple[str, float | None]:
    if current >= required:
        return "READY", 0.0
    if rate_per_hour <= 0:
        return "NO_OBSERVED_ACCUMULATION", None
    eta = (required - current) / rate_per_hour
    label = "LT_6H" if eta < 6 else "6_24H" if eta <= 24 else "1_3D" if eta <= 72 else "3_7D" if eta <= 168 else "GT_7D"
    return label, eta


def analyze(
    cohort: list[dict[str, Any]], rows: Mapping[str, Mapping[str, Any]],
    outcomes: tuple[PaperOutcome, ...], anchor: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    candidates = [candidate_identity(item, rows[item["run_id"]]) for item in cohort]
    eligible = tuple(item for item in outcomes if item.parameter_set_id == SET_ID)
    legacy = tuple(item for item in outcomes if item.parameter_set_id != SET_ID)
    required = SCALPING_V2.economics.bucket_min_sample
    bucket_candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in candidates:
        bucket_candidates[item["bucket_key"]].append(item)
    bucket_reports: dict[str, dict[str, Any]] = {}
    for key, grouped in bucket_candidates.items():
        dimensions = grouped[0]["bucket_dimensions"]
        hierarchy = hierarchy_from_outcomes(
            eligible, symbol=dimensions["symbol"], setup_type=dimensions["setup_type"],
            direction=dimensions["direction"], regime=dimensions["market_regime"],
            cost_bucket=dimensions["cost_bucket"], parameter_set_id=SET_ID,
        )
        exact = hierarchy.exact
        timestamps = [item.observed_at_ms for item in eligible if item.observed_at_ms and (
            item.symbol, item.setup_type, item.direction, item.regime, item.cost_bucket
        ) == (
            dimensions["symbol"], dimensions["setup_type"], dimensions["direction"],
            dimensions["market_regime"], dimensions["cost_bucket"],
        )]
        counts = {
            name: sum(value <= item.observed_at_ms <= anchor for item in eligible)
            for name, value in {
                "last_1h": anchor - 3_600_000, "last_4h": anchor - 14_400_000,
                "last_12h": anchor - 43_200_000, "last_24h": anchor - 86_400_000,
            }.items()
        }
        # Rates are leaf-specific, not global; recompute using exact timestamps.
        counts = {name: sum(value <= stamp <= anchor for stamp in timestamps) for name, value in {
            "last_1h": anchor - 3_600_000, "last_4h": anchor - 14_400_000,
            "last_12h": anchor - 43_200_000, "last_24h": anchor - 86_400_000,
        }.items()}
        rate = counts["last_24h"] / 24
        eta_class, eta_hours = classify_eta(exact.samples, required, rate)
        levels = [exact, *hierarchy.parents]
        bucket_reports[key] = {
            "bucket_key": key, "dimensions": dimensions,
            "candidate_count": len(grouped), "sample_count": exact.samples,
            "required_sample_count": required,
            "authority_ratio": exact.samples / required,
            "wins": exact.wins, "losses": exact.samples - exact.wins,
            "effective_sample_count": exact.samples,
            "oldest_observation_ms": min(timestamps) if timestamps else None,
            "newest_observation_ms": max(timestamps) if timestamps else None,
            "accumulation": counts,
            "observed_samples_per_hour_24h": rate,
            "observed_samples_per_day_24h": counts["last_24h"],
            "eta_class": eta_class, "eta_hours": eta_hours,
            "hierarchy": [{
                "level": level.level, "bucket_key": level.bucket_key,
                "sample_count": level.samples, "wins": level.wins,
                "authority": level.samples >= required,
                "conservative_p_win": None,
                "decision": "ACCEPT_AUTHORITY" if level.samples >= required else "INSUFFICIENT",
            } for level in levels],
        }
        for item in grouped:
            item.update({key2: bucket_reports[key][key2] for key2 in (
                "sample_count", "required_sample_count", "authority_ratio", "wins", "losses",
                "oldest_observation_ms", "newest_observation_ms", "accumulation", "eta_class", "eta_hours",
            )})
            item["parent_hierarchy"] = bucket_reports[key]["hierarchy"][1:]

    sample_counts = [item["sample_count"] for item in bucket_reports.values()]
    def sample_range(value: int) -> str:
        if value == 0: return "0"
        if value <= 5: return "1_5"
        if value <= 10: return "6_10"
        if value < required: return f"11_{required - 1}"
        return "GTE_REQUIRED"
    dimensions = ("symbol", "setup_type", "direction", "market_regime", "cost_bucket")
    fragmentation = sorted(({
        "dimension": name,
        "unique_values": len({item["bucket_dimensions"][name] for item in candidates}),
        "split_factor": len({item["bucket_dimensions"][name] for item in candidates}),
        "candidate_coverage": len(candidates),
    } for name in dimensions), key=lambda item: (-item["split_factor"], item["dimension"]))
    legacy_global_authority = len(legacy) >= required
    eta_distribution = Counter(item["eta_class"] for item in bucket_reports.values())
    report = {
        "bucket_key_definition": "level|symbol|setup_type|direction|regime|cost_bucket",
        "bucket_dimensions": list(dimensions),
        "parameter_set_in_bucket_key": False,
        "parameter_set_in_authority_partition": True,
        "config_hash_in_bucket_key": False,
        "bucket_min_sample": required,
        "bucket_min_sample_source": "config/trading/trade_parameters.yaml profiles.trade-5m-v2.economics.bucket_min_sample inherited by Set #2",
        "cohort_count": len(candidates), "unique_leaf_buckets": len(bucket_reports),
        "ready_buckets": sum(value >= required for value in sample_counts),
        "insufficient_buckets": sum(value < required for value in sample_counts),
        "no_accumulation_buckets": sum(value == 0 for value in sample_counts),
        "sample_count_distribution": dict(Counter(sample_range(value) for value in sample_counts)),
        "median_samples_per_bucket": statistics.median(sample_counts) if sample_counts else 0,
        "max_samples_per_bucket": max(sample_counts, default=0),
        "fragmentation_by_dimension": fragmentation,
        "accumulation_rate": {
            "last_1h": sum(item.observed_at_ms >= anchor - 3_600_000 and item.observed_at_ms <= anchor for item in eligible),
            "last_4h": sum(item.observed_at_ms >= anchor - 14_400_000 and item.observed_at_ms <= anchor for item in eligible),
            "last_24h": sum(item.observed_at_ms >= anchor - 86_400_000 and item.observed_at_ms <= anchor for item in eligible),
        },
        "eta_distribution": dict(eta_distribution),
        "set1_set2_evidence_compatibility": "PARTIALLY_COMPATIBLE_NOT_AUTHORITY_ELIGIBLE",
        "compatibility_reason": "setup/regime model is shared, but Set #2 changes target minimum, admission RR and time-stop semantics; legacy collector used TTL60s/time-stop30m versus Set #2 TTL30s/time-stop15m",
        "authority_before_set2": len(legacy), "authority_after_set2": len(eligible),
        "authority_reset_on_set2": True,
        "authority_reset_cause": "parameter_set_id authority prefilter plus zero Set #2 executed outcomes",
        "parent_hierarchy_exists": True,
        "parent_hierarchy_used": any(any(level["authority"] for level in item["hierarchy"][1:]) for item in bucket_reports.values()),
        "parent_hierarchy_defect_found": False,
        "evidence_ingestion_defect_found": True,
        "executed_only_selection_bias": True,
        "root_fragmentation_cause": "SET_PARTITION_PLUS_EXECUTED_ONLY_BOOTSTRAP_DEADLOCK; leaf fragmentation secondary",
        "historical_causal_evidence_available": len(legacy),
        "offline_parent_hierarchy_diagnostic": "LEGACY_GLOBAL_PARENT_ONLY_NOT_PROMOTABLE",
        "candidates_with_authority_current": sum(any(level["authority"] for level in item["hierarchy"]) for item in bucket_reports.values() for _ in range(item["candidate_count"])),
        "candidates_with_authority_diagnostic_alternative": len(candidates) if legacy_global_authority else 0,
        "permanently_sparse_buckets": [key for key, value in bucket_reports.items() if value["eta_class"] == "NO_OBSERVED_ACCUMULATION"],
        "buckets": list(bucket_reports.values()),
    }
    return candidates, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rr-cohort", type=Path, required=True)
    parser.add_argument("--anchor-report", type=Path, required=True)
    parser.add_argument("--prospective-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    cohort = [json.loads(line) for line in args.rr_cohort.read_text(encoding="utf-8").splitlines() if line]
    anchor_report = json.loads(args.anchor_report.read_text(encoding="utf-8"))
    anchor = int(anchor_report["anchor"]["cycle_boundary"])
    rows = load_rows(min(item["cycle_boundary"] for item in cohort), anchor)
    outcomes = load_closed_paper_outcomes()
    outcomes += load_prospective_outcomes(args.prospective_dir, parameter_set_id=SET_ID)
    candidates, report = analyze(cohort, rows, outcomes, anchor)
    report["anchor"] = anchor_report["anchor"]
    report["frozen_cohort"] = anchor_report["frozen_cohort"]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "PROBABILITY_AUTHORITY_FORENSIC_COHORT.jsonl").write_text(
        "".join(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n" for item in candidates),
        encoding="utf-8",
    )
    (args.output_dir / "PROBABILITY_AUTHORITY_REPORT.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    print(json.dumps({key: report[key] for key in (
        "cohort_count", "unique_leaf_buckets", "ready_buckets", "insufficient_buckets",
        "no_accumulation_buckets", "accumulation_rate", "eta_distribution",
        "candidates_with_authority_current", "candidates_with_authority_diagnostic_alternative",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
