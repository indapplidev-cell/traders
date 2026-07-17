"""Offline causal-confirmation candidate research for ENGINE-ANALYSIS-31.

This module only groups finalized ENGINE-ANALYSIS-30 blocker rows.  Candidate
families are research labels, not executable rules: they cannot select or
change a regime, create a setup, or create a trade signal.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


STAGE = "ENGINE-ANALYSIS-31"
SOURCE_STAGE = "ENGINE-ANALYSIS-30"
SCHEMA_VERSION = "1.0.0"
RESEARCH_ONLY = True
MISSING_DATA_POLICY = "NOT_OBSERVABLE_SEPARATE_FROM_FALSE"

FORBIDDEN_RUNTIME_IMPACT = (
    "MUST_NOT_CHANGE_RUNTIME",
    "MUST_NOT_CHANGE_TRADING_RUNTIME",
    "MUST_NOT_CHANGE_COMPOSER",
    "MUST_NOT_CHANGE_THRESHOLDS",
    "MUST_NOT_CHANGE_SETUP_CONTRACTS",
    "MUST_NOT_CHANGE_SETUP_ELIGIBILITY",
    "MUST_NOT_CHANGE_SOURCE_REGIME_LOGIC",
    "MUST_NOT_CHANGE_FINAL_REGIME_LOGIC",
    "MUST_NOT_CREATE_SETUP_SIGNALS",
    "MUST_NOT_CREATE_TRADE_SIGNALS",
    "MUST_NOT_CONVERT_UNKNOWN_REGIME",
    "MUST_NOT_CONVERT_NO_ACTION",
    "MUST_NOT_ENTER_PAPER_OR_LIVE_TRADING",
)

_FAMILY_SPECS: tuple[dict[str, Any], ...] = (
    {
        "candidate_id": "ET31-CCR-001",
        "candidate_family": "CAUSAL_BREAKOUT_CONFIRMATION",
        "blocker_codes": ("BREAKOUT_NOT_CONFIRMED", "NEAR_RESISTANCE_WITHOUT_BREAKOUT"),
        "required": ("price_context", "zone_proximity", "breakout_close", "breakout_follow_through"),
        "why": "A breakout observation is absent or unconfirmed; proximity or indicator pressure alone is not causal confirmation.",
        "validation": ("forward-only breakout labeling", "out-of-sample false-breakout rate", "symbol and regime stratification"),
        "fixtures": ("confirmed close and follow-through", "wick-only false breakout", "near resistance without breakout"),
    },
    {
        "candidate_id": "ET31-CDC-002",
        "candidate_family": "CAUSAL_BREAKDOWN_CONFIRMATION",
        "blocker_codes": ("BREAKDOWN_NOT_CONFIRMED", "NEAR_SUPPORT_WITHOUT_BREAKDOWN"),
        "required": ("price_context", "zone_proximity", "breakdown_close", "breakdown_follow_through"),
        "why": "A breakdown observation is absent or unconfirmed; support proximity does not establish a causal downside trigger.",
        "validation": ("forward-only breakdown labeling", "out-of-sample false-breakdown rate", "symbol and regime stratification"),
        "fixtures": ("confirmed close and follow-through", "wick-only false breakdown", "near support without breakdown"),
    },
    {
        "candidate_id": "ET31-RRC-003",
        "candidate_family": "RANGE_REJECTION_CONFIRMATION",
        "blocker_codes": ("CONFIRMED_RANGE_CONTEXT", "NEAR_RESISTANCE_WITHOUT_BREAKOUT", "NEAR_SUPPORT_WITHOUT_BREAKDOWN"),
        "required": ("price_context", "zone_proximity", "range_boundary_rejection", "rejection_follow_through"),
        "why": "A confirmed range describes context but does not prove a tradable rejection at either boundary.",
        "validation": ("causal rejection definition", "out-of-sample continuation versus reversal labels", "range-boundary leakage audit"),
        "fixtures": ("support rejection", "resistance rejection", "range midpoint no trigger"),
    },
    {
        "candidate_id": "ET31-RTR-004",
        "candidate_family": "RANGE_TREND_RESOLUTION_CONFIRMATION",
        "blocker_codes": ("RANGE_TREND_CONFLICT", "LOCAL_RANGE_UNCONFIRMED", "CONFIRMED_RANGE_CONTEXT"),
        "required": ("price_context", "range_state", "trend_structure", "resolution_follow_through"),
        "why": "Range and trend observations remain contextual or conflicted and have no validated causal resolution event.",
        "validation": ("mutually exclusive resolution labels", "walk-forward regime transition study", "conflict abstention benchmark"),
        "fixtures": ("range resolves upward", "range resolves downward", "unresolved range-trend conflict"),
    },
    {
        "candidate_id": "ET31-PCH-005",
        "candidate_family": "PENDING_TO_CONFIRMED_HYPOTHESIS_PROMOTION_RESEARCH",
        "blocker_codes": ("NO_CONFIRMED_CAUSAL_HYPOTHESIS", "ONLY_PENDING_HYPOTHESES", "PENDING_AND_CONFLICTED_ONLY"),
        "required": ("hypothesis_evidence_timeline", "causal_trigger", "invalidation_event", "confirmation_event"),
        "why": "Pending and conflicted hypotheses lack a validated, time-causal promotion contract.",
        "validation": ("promotion label protocol", "temporal leakage audit", "out-of-sample precision and abstention comparison"),
        "fixtures": ("pending becomes confirmed", "pending becomes invalidated", "pending remains conflicted"),
    },
    {
        "candidate_id": "ET31-ICT-006",
        "candidate_family": "INDICATOR_PRESSURE_TO_CAUSAL_TRIGGER_RESEARCH",
        "blocker_codes": ("INDICATOR_PRESSURE_WITHOUT_CAUSAL_TRIGGER",),
        "required": ("indicator_pressure", "price_context", "causal_trigger", "trigger_follow_through"),
        "why": "Indicator pressure is associative evidence and cannot substitute for a price-causal trigger.",
        "validation": ("indicator-only baseline", "incremental causal-trigger study", "out-of-sample calibration"),
        "fixtures": ("pressure plus trigger", "pressure without trigger", "trigger without pressure"),
    },
    {
        "candidate_id": "ET31-MTF-007",
        "candidate_family": "MTF_RISK_RESOLUTION_RESEARCH",
        "blocker_codes": ("MTF_CONFLICT", "HIGHER_TF_BEARISH_RISK", "HIGHER_TF_BULLISH_RISK"),
        "required": ("multi_timeframe", "higher_timeframe_structure", "lower_timeframe_trigger", "mtf_resolution_event"),
        "why": "Higher-timeframe risk or conflict has no validated causal resolution contract at the decision timestamp.",
        "validation": ("as-of timeframe alignment", "conflict-resolution outcome study", "no-lookahead audit"),
        "fixtures": ("bearish higher-TF risk resolves", "bullish higher-TF risk resolves", "MTF conflict persists"),
    },
    {
        "candidate_id": "ET31-LTS-008",
        "candidate_family": "LOW_TREND_STRENGTH_CONFIRMATION_RESEARCH",
        "blocker_codes": ("LOW_TREND_STRENGTH",),
        "required": ("trend_strength", "trend_structure", "causal_trigger", "trend_persistence"),
        "why": "Low strength is an abstention context, not evidence that a future directional move is confirmed.",
        "validation": ("strength calibration by symbol", "walk-forward persistence labels", "threshold-free exploratory analysis"),
        "fixtures": ("low strength then persistence", "low strength remains flat", "low strength reverses"),
    },
    {
        "candidate_id": "ET31-ZPC-009",
        "candidate_family": "ZONE_PROXIMITY_CONFIRMATION_RESEARCH",
        "blocker_codes": ("NEAR_RESISTANCE_WITHOUT_BREAKOUT", "NEAR_SUPPORT_WITHOUT_BREAKDOWN", "ZONE_PROXIMITY_NOT_OBSERVABLE"),
        "required": ("zone_proximity", "zone_role", "price_context", "zone_interaction_event"),
        "why": "Zone proximity is either unavailable or merely contextual; interaction and confirmation are not established.",
        "validation": ("zone-distance observability study", "zone-role transition labels", "out-of-sample interaction outcomes"),
        "fixtures": ("near support interaction", "near resistance interaction", "zone proximity unavailable"),
    },
    {
        "candidate_id": "ET31-NOD-010",
        "candidate_family": "NOT_OBSERVABLE_DATA_REQUIREMENT_RESEARCH",
        "blocker_codes": ("PRICE_CONTEXT_NOT_OBSERVABLE", "ZONE_PROXIMITY_NOT_OBSERVABLE", "INDICATOR_CONTEXT_NOT_OBSERVABLE", "MTF_CONTEXT_NOT_OBSERVABLE"),
        "required": ("price_context", "zone_proximity", "indicator_pressure", "multi_timeframe"),
        "why": "Required inputs are explicitly not observable and must remain distinct from observed false conditions.",
        "validation": ("data lineage and availability audit", "as-of completeness measurement", "missingness bias study"),
        "fixtures": ("all fields observable false", "all fields not observable", "partially observable context"),
    },
)

CANDIDATE_FAMILIES = tuple(spec["candidate_family"] for spec in _FAMILY_SPECS)


def _validate_source_row(row: Mapping[str, Any]) -> None:
    if row.get("source_regime") != row.get("final_regime"):
        raise ValueError("source row changed its finalized regime")
    if row.get("decision_changed_by_diagnostics") is not False:
        raise ValueError("source row changed a decision")
    if row.get("setup_created") is not False or row.get("trade_signal_created") is not False:
        raise ValueError("source row contains a setup or trade signal")
    if row.get("missing_data_policy") != MISSING_DATA_POLICY:
        raise ValueError("not_observable must remain separate from false")


def build_candidate_research(source_dataset: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Group a stage-30 dataset into research-only families without mutation."""

    before = deepcopy(source_dataset)
    if source_dataset.get("stage") != SOURCE_STAGE:
        raise ValueError(f"expected {SOURCE_STAGE} blocker dataset")
    rows = source_dataset.get("rows")
    if not isinstance(rows, list):
        raise ValueError("source dataset rows must be a list")
    total_cases = len(rows)
    case_map: list[dict[str, Any]] = []
    families: list[dict[str, Any]] = []

    for spec in _FAMILY_SPECS:
        matching: list[tuple[Mapping[str, Any], list[str]]] = []
        for row in rows:
            _validate_source_row(row)
            matched = [code for code in spec["blocker_codes"] if code in set(row.get("blocker_codes", []))]
            if matched:
                matching.append((row, matched))
        matched_codes = [code for code in spec["blocker_codes"] if any(code in found for _, found in matching)]
        missing = sorted({field for row, _ in matching for field in row.get("not_observable_fields", [])})
        symbols = sorted({str(row.get("symbol")) for row, _ in matching})
        regimes = sorted({str(row.get("final_regime")) for row, _ in matching})
        affected = len(matching)
        coverage = affected / total_cases if total_cases else 0.0
        priority = round(coverage * 100, 2)
        families.append({
            "candidate_id": spec["candidate_id"],
            "candidate_family": spec["candidate_family"],
            "research_only": True,
            "blocker_codes_matched": matched_codes,
            "configured_blocker_codes": list(spec["blocker_codes"]),
            "affected_case_count": affected,
            "symbols_affected": symbols,
            "regimes_affected": regimes,
            "required_observable_fields": list(spec["required"]),
            "currently_not_observable_fields": missing,
            "why_this_is_not_yet_tradable": spec["why"],
            "required_future_validation": list(spec["validation"]),
            "forbidden_runtime_impact": list(FORBIDDEN_RUNTIME_IMPACT),
            "suggested_future_test_fixtures": list(spec["fixtures"]),
            "priority_score_research_only": priority,
        })
        for row, matched in matching:
            not_observable = list(row.get("not_observable_fields", []))
            case_map.append({
                "candidate_id": spec["candidate_id"],
                "candidate_family": spec["candidate_family"],
                "case_id": row["case_id"],
                "symbol": row["symbol"],
                "timestamp": row["timestamp"],
                "source_regime": row["source_regime"],
                "final_regime": row["final_regime"],
                "no_action": row["no_action"],
                "blocker_codes_matched": matched,
                "observable_fields": list(row.get("observable_fields", [])),
                "not_observable_fields": not_observable,
                "not_observable_is_false": False,
                "missing_data_policy": MISSING_DATA_POLICY,
                "research_only": True,
                "setup_created": False,
                "trade_signal_created": False,
                "decision_changed": False,
            })

    case_map.sort(key=lambda item: (item["candidate_id"], item["timestamp"], item["symbol"], item["case_id"]))
    ranking_rows = sorted(
        ({
            "rank": 0,
            "candidate_id": family["candidate_id"],
            "candidate_family": family["candidate_family"],
            "affected_case_count": family["affected_case_count"],
            "priority_score_research_only": family["priority_score_research_only"],
        } for family in families),
        key=lambda item: (-item["affected_case_count"], item["candidate_id"]),
    )
    for rank, item in enumerate(ranking_rows, 1):
        item["rank"] = rank

    covered = {entry["case_id"] for entry in case_map}
    not_observable_counts = Counter(field for row in rows for field in row.get("not_observable_fields", []))
    common = {
        "stage": STAGE,
        "schema_version": SCHEMA_VERSION,
        "source_stage": SOURCE_STAGE,
        "source_dataset": "ENGINE_ANALYSIS_30_BLOCKER_DATASET.json",
    }
    family_artifact = {**common, "research_only": True, "candidate_family_count": len(families), "candidate_families": families}
    map_artifact = {
        **common,
        "research_only": True,
        "source_case_count": total_cases,
        "covered_case_count": len(covered),
        "uncovered_case_ids": sorted(str(row["case_id"]) for row in rows if row["case_id"] not in covered),
        "candidate_case_mapping_count": len(case_map),
        "case_map": case_map,
    }
    ranking = {
        **common,
        "research_only": True,
        "priority_method": "affected_case_percentage; ties ordered by stable candidate_id; not a trading score",
        "source_case_count": total_cases,
        "known_cases_coverage": {"covered": len(covered), "total": total_cases},
        "not_observable_data_requirements": dict(sorted(not_observable_counts.items())),
        "ranking": ranking_rows,
    }
    if source_dataset != before:
        raise AssertionError("candidate generation mutated source dataset")
    return family_artifact, map_artifact, ranking


_CSV_FIELDS = (
    "candidate_id", "candidate_family", "case_id", "symbol", "timestamp",
    "source_regime", "final_regime", "no_action", "blocker_codes_matched",
    "observable_fields", "not_observable_fields", "not_observable_is_false",
    "missing_data_policy", "research_only", "setup_created",
    "trade_signal_created", "decision_changed",
)


def write_case_map_csv(path: Path, case_map: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_CSV_FIELDS)
        writer.writeheader()
        for row in case_map:
            writer.writerow({key: json.dumps(row[key], sort_keys=True) if isinstance(row[key], list) else row[key] for key in _CSV_FIELDS})


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_manifest(report_dir: Path, artifact_names: Sequence[str], *, source_case_count: int, covered_case_count: int) -> dict[str, Any]:
    generated = []
    for name in artifact_names:
        data = (report_dir / name).read_bytes()
        generated.append({"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    return {
        "stage": STAGE,
        "artifact_count": len(artifact_names) + 1,
        "generated_artifacts": generated,
        "self": {"path": "ENGINE_ANALYSIS_31_ARTIFACT_MANIFEST.json", "hash_omitted": "self-referential"},
        "source_case_count": source_case_count,
        "covered_case_count": covered_case_count,
        "acceptance_status": "ACCEPTED",
        "commit_created": False,
    }
