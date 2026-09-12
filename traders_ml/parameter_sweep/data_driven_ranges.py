"""Research-only, deterministic ranges derived from separability artifacts.

The module deliberately stops at a run-local handoff.  It neither mutates the
research search grid nor invokes search, adaptive refinement, or holdout code.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from app.config.trade_parameters import SCALPING_V2
from app.config.yaml_authority import (
    DataDrivenRangeGenerationPolicy,
    RESEARCH_PARAMETERS,
    RESEARCH_PATH,
    load_data_driven_range_policy,
)

from .artifact_writer import DEFAULT_ARTIFACT_WRITER
from .historical_replay import build_parameter_registry


GENERATOR_ARTIFACT_VERSION = 1


@dataclass(frozen=True, slots=True)
class EvidenceMapping:
    feature: str
    evidence_class: str
    mapping_path: str
    eligible: bool = False
    reason: str = ""


# This is semantic wiring, not candidate-value policy.  Each path mirrors an
# existing engine consumer and is intentionally explicit/auditable.
EVIDENCE_MAPPINGS: dict[str, EvidenceMapping] = {
    "strategy_minimum_score": EvidenceMapping("strategy_score", "DIRECT_EVIDENCE", "strategy_minimum_score -> engine._gate_result >= strategy_score", True),
    "regime_lookback_candles": EvidenceMapping("regime", "INDIRECT_EVIDENCE", "regime_lookback_candles -> regime-history gate -> observed regime"),
    "minimum_planned_rr": EvidenceMapping("planned_rr", "DIRECT_EVIDENCE", "minimum_planned_rr -> engine._gate_result <= planned_rr", True),
    "min_net_edge_bps": EvidenceMapping("net_edge_bps", "DIRECT_EVIDENCE", "min_net_edge_bps -> economics gate <= expected_net_edge_bps", True),
    "min_positive_ev_r": EvidenceMapping("expected_ev_r", "DIRECT_EVIDENCE", "min_positive_ev_r -> economics gate <= expected_ev_r", True),
    "min_ev_reserve_r": EvidenceMapping("expected_ev_r", "DERIVED_EVIDENCE", "min_ev_reserve_r -> EV reserve formula -> expected_ev_r"),
    "bucket_min_sample": EvidenceMapping("probability_sample_size", "DIRECT_EVIDENCE", "bucket_min_sample -> probability sample gate <= probability_sample_size", True),
    "probability_confidence_level": EvidenceMapping("estimated_p_win", "DERIVED_EVIDENCE", "probability_confidence_level -> conservative probability formula -> estimated_p_win"),
    "prior_alpha": EvidenceMapping("estimated_p_win", "DERIVED_EVIDENCE", "prior_alpha -> beta posterior -> estimated_p_win"),
    "prior_beta": EvidenceMapping("estimated_p_win", "DERIVED_EVIDENCE", "prior_beta -> beta posterior -> estimated_p_win"),
    "adverse_fill_reserve_bps": EvidenceMapping("effective_total_cost_bps", "DERIVED_EVIDENCE", "adverse_fill_reserve_bps -> total-cost formula -> effective_total_cost_bps"),
    "entry_slippage_bps": EvidenceMapping("slippage_bps", "DIRECT_EVIDENCE", "entry_slippage_bps -> paper causal primitives -> slippage_bps", True),
    "stop_max_bps": EvidenceMapping("stop_distance_bps", "DIRECT_EVIDENCE", "stop_max_bps -> engine._gate_result >= stop_distance_bps", True),
    "target_min_bps": EvidenceMapping("target_distance_bps", "DIRECT_EVIDENCE", "target_min_bps -> engine._gate_result <= target_distance_bps", True),
    "causal_reset_min_conditions": EvidenceMapping("causal_reset_state", "DERIVED_EVIDENCE", "causal_reset_min_conditions -> reset state machine -> causal_reset_state"),
    "entry_refinement_1m_confirmation_count": EvidenceMapping("confirmation_state", "DERIVED_EVIDENCE", "confirmation count -> 1m refinement state -> confirmation_state"),
    "risk_per_trade_bps": EvidenceMapping("risk_score", "INDIRECT_EVIDENCE", "risk_per_trade_bps -> sizing/risk stages -> risk_score"),
    "max_open_positions": EvidenceMapping("risk_pre_approved", "INDIRECT_EVIDENCE", "max_open_positions -> portfolio gate -> risk_pre_approved"),
    "total_open_risk_limit_bps": EvidenceMapping("risk_pre_approved", "INDIRECT_EVIDENCE", "total_open_risk_limit_bps -> portfolio risk gate -> risk_pre_approved"),
    "max_new_commands_per_cycle": EvidenceMapping("risk_pre_approved", "INDIRECT_EVIDENCE", "max_new_commands_per_cycle -> selector -> downstream approval state"),
}


def _parameter_type(current: object, legacy: Sequence[object]) -> str:
    values = [current, *legacy]
    if any(isinstance(value, bool) for value in values if value is not None):
        return "BOOLEAN"
    if all(isinstance(value, int) and not isinstance(value, bool) for value in values if value is not None):
        return "INTEGER"
    return "NUMERIC"


def _owner_field(owner: str) -> tuple[object, Any]:
    value: object = SCALPING_V2
    parts = owner.split(".")
    for part in parts[:-1]:
        value = getattr(value, part)
    return value, value.__class__.model_fields[parts[-1]]


def _schema_domain(owner: str, current: object, legacy: Sequence[object]) -> dict[str, Any]:
    parameter_type = _parameter_type(current, legacy)
    if parameter_type == "BOOLEAN":
        return {"type": parameter_type, "minimum": None, "maximum": None, "minimum_inclusive": None, "maximum_inclusive": None, "values": [False, True], "allows_null": False}
    _, field = _owner_field(owner)
    lower = upper = None
    lower_inclusive = upper_inclusive = None
    for constraint in field.metadata:
        if getattr(constraint, "ge", None) is not None:
            lower, lower_inclusive = constraint.ge, True
        if getattr(constraint, "gt", None) is not None:
            lower, lower_inclusive = constraint.gt, False
        if getattr(constraint, "le", None) is not None:
            upper, upper_inclusive = constraint.le, True
        if getattr(constraint, "lt", None) is not None:
            upper, upper_inclusive = constraint.lt, False
    return {
        "type": parameter_type, "minimum": lower, "maximum": upper,
        "minimum_inclusive": lower_inclusive, "maximum_inclusive": upper_inclusive,
        "values": None, "allows_null": any(value is None for value in [current, *legacy]),
    }


def _value_is_valid(value: object, domain: Mapping[str, Any]) -> bool:
    if value is None:
        return bool(domain["allows_null"])
    if domain["type"] == "BOOLEAN":
        return isinstance(value, bool)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        return False
    if domain["type"] == "INTEGER" and not float(value).is_integer():
        return False
    number = float(value)
    lower, upper = domain["minimum"], domain["maximum"]
    if lower is not None and (number < lower or (number == lower and domain["minimum_inclusive"] is False)):
        return False
    if upper is not None and (number > upper or (number == upper and domain["maximum_inclusive"] is False)):
        return False
    return True


def build_parameter_evidence_map(
    *, search_space: Mapping[str, Sequence[object]], feature_registry: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    registry = build_parameter_registry({key: list(values) for key, values in search_space.items()})
    features = {str(row["feature_name"]): dict(row) for row in feature_registry}
    rows = []
    mapped_features: set[str] = set()
    for descriptor in registry:
        parameter = str(descriptor["canonical_key"])
        mapping = EVIDENCE_MAPPINGS.get(parameter)
        legacy = list(descriptor["candidate_values"])
        current = descriptor["baseline"]
        runtime_owner = str(descriptor["RUNTIME_OWNER"])
        domain = _schema_domain(runtime_owner, current, legacy)
        authoritative_source = (
            f"config/trading/risk_policy.yaml:profiles.trade-5m-v2.{runtime_owner.removeprefix('risk.')}"
            if runtime_owner.startswith("risk.")
            else f"{descriptor['source_yaml']}:{descriptor['source_path']}"
        )
        feature = features.get(mapping.feature) if mapping else None
        if mapping:
            mapped_features.add(mapping.feature)
        eligible = bool(
            mapping and mapping.eligible and feature
            and feature.get("data_type") in {"NUMERIC", "CYCLIC"}
        )
        evidence_class = mapping.evidence_class if mapping else "NO_AUTHORIZED_EVIDENCE_MAPPING"
        reason = (
            mapping.reason or "EXACT_CONSUMER_PATH_TO_CAUSAL_FEATURE"
            if mapping else "NO_AUDITABLE_PARAMETER_TO_CAUSAL_FEATURE_CONSUMER_PATH"
        )
        rows.append({
            "parameter": parameter, "parameter_name": parameter,
            "parameter_type": domain["type"], "semantic_family": descriptor["family"],
            "current_authoritative_value": current,
            "current_search_values": legacy,
            "authoritative_source": authoritative_source,
            "schema_domain": domain, "consumer": descriptor["consumer"],
            "effect_on_pipeline": list(descriptor["REPLAY_REQUIREMENTS"]),
            "directly_observable_derived_fields": [mapping.feature] if mapping else [],
            "evidence_class": evidence_class,
            "evidence_features": [mapping.feature] if mapping else [],
            "mapping_path": mapping.mapping_path if mapping else None,
            "mapping_confidence": "HIGH" if evidence_class == "DIRECT_EVIDENCE" else "MEDIUM" if evidence_class == "DERIVED_EVIDENCE" else "LOW" if evidence_class == "INDIRECT_EVIDENCE" else "UNAVAILABLE",
            "eligible_for_range_generation": eligible,
            "reason": reason,
        })
    evidence_only = [
        {"feature": name, "status": "EVIDENCE_ONLY_NOT_TUNABLE", "reason": "NO_CURRENT_RESEARCH_TUNABLE_PARAMETER"}
        for name in sorted(set(features) - mapped_features)
    ]
    return {"artifact": "PARAMETER_EVIDENCE_MAP", "schema_version": GENERATOR_ARTIFACT_VERSION, "parameters": rows, "evidence_only_not_tunable": evidence_only}


def _percentile_key(value: float) -> str:
    return f"p{round(value * 100)}"


def _confidence(feature: Mapping[str, Any], adequacy: str, policy: DataDrivenRangeGenerationPolicy) -> str:
    if adequacy != "USABLE":
        return "DESCRIPTIVE_ONLY"
    separation = float(feature.get("separation_score") or 0)
    stability = float(feature.get("stability_score") or 0)
    if separation >= policy.high_confidence_min_separation and stability >= policy.high_confidence_min_stability:
        return "HIGH"
    if separation >= policy.medium_confidence_min_separation and stability >= policy.medium_confidence_min_stability:
        return "MEDIUM"
    return "LOW"


def _clip_and_cast(value: float, domain: Mapping[str, Any], policy: DataDrivenRangeGenerationPolicy) -> int | float:
    lower, upper = domain["minimum"], domain["maximum"]
    if lower is not None:
        value = max(value, float(lower))
    if upper is not None:
        value = min(value, float(upper))
    if domain["type"] == "INTEGER":
        value = float(round(value))
        if lower is not None and domain["minimum_inclusive"] is False and value <= lower:
            value = float(math.floor(lower) + 1)
        if upper is not None and domain["maximum_inclusive"] is False and value >= upper:
            value = float(math.ceil(upper) - 1)
        return int(value)
    return round(value, policy.rounding_decimal_places)


def _candidate_values(
    feature: Mapping[str, Any], current: object, domain: Mapping[str, Any],
    policy: DataDrivenRangeGenerationPolicy,
) -> tuple[list[int | float], dict[str, Any]]:
    winners = feature.get("winner_distribution") or {}
    losers = feature.get("loser_distribution") or {}
    raw: list[tuple[str, float]] = []
    for quantile in policy.winner_dense_quantiles:
        value = winners.get(_percentile_key(quantile))
        if isinstance(value, (int, float)):
            raw.append((f"winner_dense_q{quantile}", float(value)))
    for quantile in policy.observed_support_quantiles:
        key = _percentile_key(quantile)
        observed = [distribution.get(key) for distribution in (winners, losers)]
        observed = [float(value) for value in observed if isinstance(value, (int, float))]
        if observed:
            raw.append((
                f"observed_support_q{quantile}",
                min(observed) if quantile == min(policy.observed_support_quantiles) else max(observed),
            ))
    winner_median, loser_median = winners.get("p50"), losers.get("p50")
    if isinstance(winner_median, (int, float)) and isinstance(loser_median, (int, float)):
        raw.append(("winner_loser_transition", float(loser_median) * policy.transition_weight + float(winner_median) * (1 - policy.transition_weight)))
    if isinstance(current, (int, float)) and not isinstance(current, bool):
        raw.append(("current_authoritative_value", float(current)))
    cast = [(source, _clip_and_cast(value, domain, policy)) for source, value in raw]
    numeric = [float(value) for _, value in cast]
    span = max(numeric) - min(numeric) if numeric else 0
    spacing = span * policy.minimum_spacing_fraction
    selected: list[tuple[str, int | float]] = []
    for source, value in cast:
        if source == "current_authoritative_value" or all(abs(float(value) - float(existing)) >= spacing for _, existing in selected):
            if value not in [existing for _, existing in selected]:
                selected.append((source, value))
    if len(selected) > policy.max_generated_points:
        current_rows = [row for row in selected if row[0] == "current_authoritative_value"]
        selected = [row for row in selected if row[0] != "current_authoritative_value"][: policy.max_generated_points - len(current_rows)] + current_rows
    values = sorted({value for _, value in selected})
    return values, {"raw_candidates": [{"source": source, "value": value} for source, value in raw], "schema_clipped_candidates": [{"source": source, "value": value} for source, value in cast], "minimum_spacing": spacing}


def _boundary_pressure(feature: Mapping[str, Any], legacy: Sequence[object], policy: DataDrivenRangeGenerationPolicy) -> str:
    numeric = sorted(float(value) for value in legacy if isinstance(value, (int, float)) and not isinstance(value, bool))
    winners = feature.get("winner_distribution") or {}
    if len(numeric) < 2 or not winners:
        return "NO_BOUNDARY_PRESSURE"
    tolerance = (numeric[-1] - numeric[0]) * policy.boundary_pressure_tolerance_fraction
    high_key = _percentile_key(policy.boundary_pressure_quantile)
    low_key = _percentile_key(1 - policy.boundary_pressure_quantile)
    if feature.get("direction") == "WINNERS_HIGHER" and float(winners.get(high_key, -math.inf)) >= numeric[-1] - tolerance:
        return "BOUNDARY_PRESSURE_HIGH"
    if feature.get("direction") == "WINNERS_LOWER" and float(winners.get(low_key, math.inf)) <= numeric[0] + tolerance:
        return "BOUNDARY_PRESSURE_LOW"
    return "NO_BOUNDARY_PRESSURE"


def _cyclic_candidate_values(
    feature: Mapping[str, Any], current: object, domain: Mapping[str, Any],
    policy: DataDrivenRangeGenerationPolicy,
) -> list[int | float]:
    period = feature.get("period")
    if not isinstance(period, (int, float)) or period <= 0 or not isinstance(current, (int, float)):
        return []
    values: list[int | float] = []
    for category in feature.get("categories") or []:
        try:
            numeric = float(category["category"]) % float(period)
        except (KeyError, TypeError, ValueError):
            continue
        candidate: int | float = int(numeric) if float(numeric).is_integer() else round(numeric, policy.rounding_decimal_places)
        if _value_is_valid(candidate, domain) and candidate not in values:
            values.append(candidate)
    if current not in values and _value_is_valid(current, domain):
        values.append(current)  # type: ignore[arg-type]
    values.sort(key=lambda value: (float(value) - float(current)) % float(period))
    return values[: policy.max_generated_points]


def generate_range_artifacts(
    *, parameter_map: Mapping[str, Any], handoff: Mapping[str, Any],
    activity: Sequence[Mapping[str, Any]], interactions: Sequence[Mapping[str, Any]],
    manifest: Mapping[str, Any], policy: DataDrivenRangeGenerationPolicy,
    policy_provenance: Mapping[str, str],
    input_provenance: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    feature_by_name = {str(row["feature"]): dict(row) for row in handoff["features"]}
    activity_by_name = {str(row["feature"]): str(row["activity_status"]) for row in activity}
    range_rows, trace_rows, comparison_rows, handoff_rows = [], [], [], []
    adequacy = str(manifest["sample_adequacy"])
    for mapping in parameter_map["parameters"]:
        feature_name = mapping["evidence_features"][0] if mapping["evidence_features"] else None
        feature = feature_by_name.get(feature_name) if feature_name else None
        activity_status = activity_by_name.get(feature_name) if feature_name else None
        current, domain = mapping["current_authoritative_value"], mapping["schema_domain"]
        generated: list[int | float] = []
        calculation: dict[str, Any] = {}
        if not mapping["eligible_for_range_generation"]:
            status, reason = "NOT_GENERATED_NO_MAPPING", "NO_AUTHORIZED_NUMERIC_DIRECT_RANGE_MAPPING"
        elif not feature or not feature.get("usable") or activity_status != "ACTIVE" or float(feature.get("coverage") or 0) < policy.minimum_observed_coverage:
            status, reason = "NOT_GENERATED_UNUSABLE_EVIDENCE", f"EVIDENCE_ACTIVITY_{activity_status or 'MISSING'}"
        elif not _value_is_valid(current, domain):
            status, reason = "NOT_GENERATED_SCHEMA_CONFLICT", "CURRENT_AUTHORITATIVE_VALUE_SCHEMA_INVALID"
        elif feature.get("semantic_type") == "CYCLIC" or feature.get("do_not_generate_linear_min_max_range"):
            generated = _cyclic_candidate_values(feature, current, domain, policy)
            if len(generated) < policy.low_sample_minimum_points:
                status, reason, generated = "NOT_GENERATED_UNUSABLE_EVIDENCE", "INSUFFICIENT_CYCLIC_EMPIRICAL_CATEGORIES", []
            else:
                status = "PROVISIONAL_LOW_SAMPLE" if adequacy != "USABLE" else "GENERATED"
                reason = "CYCLIC_EMPIRICAL_DOMAIN_WITH_WRAP_AROUND_NO_LINEAR_MIN_MAX"
        else:
            generated, calculation = _candidate_values(feature, current, domain, policy)
            if any(not _value_is_valid(value, domain) for value in generated):
                status, reason, generated = "NOT_GENERATED_SCHEMA_CONFLICT", "GENERATED_CANDIDATE_SCHEMA_INVALID", []
            elif len(generated) < policy.low_sample_minimum_points:
                status, reason, generated = "NOT_GENERATED_UNUSABLE_EVIDENCE", "INSUFFICIENT_DISTINCT_EMPIRICAL_CANDIDATES", []
            else:
                status = "PROVISIONAL_LOW_SAMPLE" if adequacy != "USABLE" else "GENERATED"
                reason = "EMPIRICAL_WINNER_DENSE_TRANSITION_SUPPORT_PLUS_CURRENT"
        confidence = _confidence(feature or {}, adequacy, policy) if generated else "UNAVAILABLE"
        pressure = _boundary_pressure(feature or {}, mapping["current_search_values"], policy) if generated else "NO_BOUNDARY_PRESSURE"
        current_included = current in generated if generated else False
        range_row = {
            "parameter": mapping["parameter"], "parameter_type": mapping["parameter_type"],
            "current_value": current, "schema_min": domain["minimum"], "schema_max": domain["maximum"], "schema_domain": domain,
            "evidence_class": mapping["evidence_class"], "evidence_features": mapping["evidence_features"],
            "evidence_direction": feature.get("direction") if feature else None,
            "separation_score": feature.get("separation_score") if feature else None,
            "stability_score": feature.get("stability_score") if feature else None,
            "sample_adequacy": adequacy, "range_status": status, "range_confidence": confidence,
            "generated_min": min(generated) if generated and feature and feature.get("semantic_type") != "CYCLIC" else None,
            "generated_max": max(generated) if generated and feature and feature.get("semantic_type") != "CYCLIC" else None,
            "generated_values": generated, "current_value_included": current_included,
            "boundary_pressure": pressure, "boundary_expansion_candidate": pressure != "NO_BOUNDARY_PRESSURE",
            "promotion_eligible": False,
            "provenance": {"separability_artifact": "SEPARABILITY_HANDOFF.json", "mapping_artifact": "PARAMETER_EVIDENCE_MAP.json", "input_sha256": dict(input_provenance or {}), "policy": dict(policy_provenance)},
            "generator_version": policy.generator_version, "reason": reason,
        }
        range_rows.append(range_row)
        related_interactions = [dict(row) for row in interactions if feature_name in {row.get("feature_a"), row.get("feature_b")}]
        trace_rows.append({
            "parameter": mapping["parameter"], "input_evidence": feature,
            "mapping_path": mapping["mapping_path"],
            "winner_distribution_summary": feature.get("winner_distribution") if feature else None,
            "loser_distribution_summary": feature.get("loser_distribution") if feature else None,
            "policy_values_used": policy.model_dump(mode="json"), "policy_provenance": dict(policy_provenance),
            "schema_clipping": calculation.get("schema_clipped_candidates"),
            "candidate_calculation": calculation or None, "final_generated_range": generated,
            "interaction_annotations": related_interactions, "reason": reason,
        })
        legacy_set, generated_set = set(mapping["current_search_values"]), set(generated)
        comparison_rows.append({
            "parameter": mapping["parameter"], "legacy_values": mapping["current_search_values"], "generated_values": generated,
            "overlap": sorted(legacy_set & generated_set, key=lambda value: (str(type(value)), str(value))),
            "newly_suggested_values": sorted(generated_set - legacy_set),
            "legacy_values_not_supported_by_current_evidence": sorted(legacy_set - generated_set, key=lambda value: (str(type(value)), str(value))),
            "diagnostic_only_no_removal_authorized": True,
        })
        if generated:
            handoff_rows.append({
                "parameter": mapping["parameter"], "generated_values": generated,
                "confidence": confidence, "provisional": status == "PROVISIONAL_LOW_SAMPLE",
                "boundary_pressure": pressure,
                "joint_search_priority_annotations": [
                    {"feature_a": row["feature_a"], "feature_b": row["feature_b"], "interaction_score": row.get("interaction_score")}
                    for row in related_interactions
                ],
            })
    ranges = {"artifact": "DATA_DRIVEN_SEARCH_RANGES", "schema_version": GENERATOR_ARTIFACT_VERSION, "symbol": manifest["symbol"], "profile": manifest["profile"], "separability_status": manifest["final_status"], "sample_adequacy": adequacy, "input_sha256": dict(input_provenance or {}), "promotion_eligible": False, "search_executed": False, "parameters": range_rows}
    trace = {"artifact": "RANGE_GENERATION_TRACE", "schema_version": GENERATOR_ARTIFACT_VERSION, "parameters": trace_rows}
    comparison = {"artifact": "LEGACY_RANGE_COMPARISON", "schema_version": GENERATOR_ARTIFACT_VERSION, "diagnostic_only": True, "parameters": comparison_rows}
    range_handoff = {"artifact": "DATA_DRIVEN_RANGE_HANDOFF", "schema_version": GENERATOR_ARTIFACT_VERSION, "research_approved_only": True, "promotion_eligible": False, "search_executed": False, "adaptive_refinement_executed": False, "holdout_opened": False, "parameters": handoff_rows}
    return {"ranges": ranges, "trace": trace, "comparison": comparison, "handoff": range_handoff}


def _report(parameter_map: Mapping[str, Any], artifacts: Mapping[str, Any]) -> str:
    ranges = artifacts["ranges"]
    lines = [
        "# Single-symbol Data-driven Range Generation", "",
        f"- Symbol/profile: `{ranges['symbol']}` / `{ranges['profile']}`",
        f"- Separability/sample adequacy: `{ranges['separability_status']}` / `{ranges['sample_adequacy']}`", "",
        "These ranges are provisional research ranges.",
        "They are not statistically certified.",
        "They must not be promoted automatically.", "", "## Parameter results", "",
    ]
    mapping_by_name = {row["parameter"]: row for row in parameter_map["parameters"]}
    for row in ranges["parameters"]:
        mapping = mapping_by_name[row["parameter"]]
        lines.append(
            f"- `{row['parameter']}` — {mapping['evidence_class']} via {', '.join(mapping['evidence_features']) or 'NONE'}; "
            f"{row['range_status']}; domain `{row['generated_values']}`; confidence {row['range_confidence']}; "
            f"current included {row['current_value_included']}; {row['boundary_pressure']}; {row['reason']}"
        )
    lines.extend(["", "## Legacy comparison", "", "Legacy values are comparison-only. Unsupported values are not removed from research or production configuration.", "", "Promotion eligible: **NO**. Search executed: **NO**. Adaptive refinement: **NO**. Holdout opened: **NO**.", ""])
    return "\n".join(lines)


def run_range_generation(*, input_dir: Path, output: Path, policy_path: Path = RESEARCH_PATH) -> dict[str, Any]:
    def read(name: str) -> Any:
        return json.loads((input_dir / name).read_text(encoding="utf-8"))
    policy, provenance = load_data_driven_range_policy(policy_path)
    input_names = (
        "FEATURE_REGISTRY.json", "SEPARABILITY_HANDOFF.json", "FEATURE_ACTIVITY.json",
        "INTERACTION_SCREEN.json", "SEPARABILITY_DATASET_MANIFEST.json",
    )
    input_provenance = {
        name: sha256((input_dir / name).read_bytes()).hexdigest() for name in input_names
    }
    input_provenance[str(policy_path)] = sha256(policy_path.read_bytes()).hexdigest()
    feature_registry = read("FEATURE_REGISTRY.json")
    parameter_map = build_parameter_evidence_map(search_space=RESEARCH_PARAMETERS.search_space, feature_registry=feature_registry)
    artifacts = generate_range_artifacts(
        parameter_map=parameter_map, handoff=read("SEPARABILITY_HANDOFF.json"),
        activity=read("FEATURE_ACTIVITY.json"), interactions=read("INTERACTION_SCREEN.json"),
        manifest=read("SEPARABILITY_DATASET_MANIFEST.json"), policy=policy,
        policy_provenance=provenance, input_provenance=input_provenance,
    )
    output.mkdir(parents=True, exist_ok=True)
    writer = DEFAULT_ARTIFACT_WRITER
    for name, value in (
        ("PARAMETER_EVIDENCE_MAP.json", parameter_map),
        ("DATA_DRIVEN_SEARCH_RANGES.json", artifacts["ranges"]),
        ("RANGE_GENERATION_TRACE.json", artifacts["trace"]),
        ("DATA_DRIVEN_RANGE_HANDOFF.json", artifacts["handoff"]),
        ("LEGACY_RANGE_COMPARISON.json", artifacts["comparison"]),
    ):
        writer.atomic_json(output / name, value, operation=name.lower())
    writer.atomic_text(output / "REPORT.md", _report(parameter_map, artifacts), operation="data_driven_range_report")
    return {"parameter_map": parameter_map, **artifacts, "output": str(output)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--policy", type=Path, default=RESEARCH_PATH)
    args = parser.parse_args(argv)
    result = run_range_generation(input_dir=args.input_dir, output=args.output, policy_path=args.policy)
    summary = result["ranges"]
    print(json.dumps({
        "symbol": summary["symbol"], "profile": summary["profile"],
        "separability_status": summary["separability_status"], "sample_adequacy": summary["sample_adequacy"],
        "ranges_generated": sum(bool(row["generated_values"]) for row in summary["parameters"]),
        "promotion_eligible": False, "search_executed": False,
    }, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
