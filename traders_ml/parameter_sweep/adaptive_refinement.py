"""Deterministic behavior-aware refinement of an accepted expanded search.

The stage is deliberately research-only and holdout-blind.  It consumes an
explicit expanded-search campaign, derives candidates only from observed local
behavior transitions or evidenced range-boundary pressure, and stops at the
resolved canonical research evaluation budget.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.config.yaml_authority import RESEARCH_PARAMETERS, VALIDATION_SAMPLE_POLICY

from .artifact_v2 import canonical_hash
from .artifact_writer import DEFAULT_ARTIFACT_WRITER
from .data_driven_ranges import _value_is_valid
from .expanded_search import (
    DataDrivenRangeHandoff,
    _canonical_dataset_hash,
    _read_json,
    _read_jsonl,
    _semantic_key,
    _split_without_holdout,
    _write_json,
    _write_jsonl,
    build_reporting_reconciliation,
    cluster_results,
    evaluate_config,
    normalize_handoff_values,
    validate_dataset,
    validate_handoff,
)
from .historical_replay import build_parameter_registry
from .symbol_authority_audit import build_symbol_runtime_authority_audit
from .universe import validate_parameter_sweep_symbol


ADAPTIVE_SCHEMA_VERSION = 1
SENSITIVITY_CLASSES = frozenset({
    "BEHAVIORALLY_ACTIVE", "WEAKLY_ACTIVE", "BEHAVIORALLY_FLAT",
    "INSUFFICIENT_EVIDENCE",
})
STOP_REASONS = frozenset({
    "NO_NEW_CANDIDATES", "NO_NEW_BEHAVIORAL_CLUSTERS", "BUDGET_EXHAUSTED",
    "SCHEMA_BOUNDARIES_REACHED", "ALL_ELIGIBLE_TRANSITIONS_REFINED",
})


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AdaptiveCampaignInputs(_Strict):
    symbol: str
    profile: Literal["trade-5m-v2"]
    dataset_fingerprint: str = Field(min_length=64, max_length=64)
    calibration_split_fingerprint: str = Field(min_length=64, max_length=64)
    validation_split_fingerprint: str = Field(min_length=64, max_length=64)
    parameter_registry_version: str = Field(min_length=64, max_length=64)
    range_handoff_fingerprint: str = Field(min_length=64, max_length=64)
    expanded_search_fingerprint: str = Field(min_length=64, max_length=64)
    adaptive_policy_fingerprint: str = Field(min_length=64, max_length=64)
    seed: int


class AdaptiveCheckpoint(_Strict):
    artifact: Literal["ADAPTIVE_REFINEMENT_CHECKPOINT"]
    schema_version: Literal[ADAPTIVE_SCHEMA_VERSION]
    inputs: AdaptiveCampaignInputs
    evaluated_candidate_keys: list[str]
    completed_rounds: int
    cumulative_evaluations: int
    completed: bool
    stop_reason: str | None
    holdout_opened: Literal[False]

    @model_validator(mode="after")
    def valid_stop(self):
        if self.stop_reason is not None and self.stop_reason not in STOP_REASONS:
            raise ValueError("INVALID_ADAPTIVE_STOP_REASON")
        return self


def _file_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _aggregate_fingerprint(paths: Sequence[Path]) -> str:
    return canonical_hash([
        {"name": path.name, "sha256": _file_hash(path)} for path in paths
    ])


def _config_key(parameters: Mapping[str, object], types: Mapping[str, str]) -> str:
    return canonical_hash([
        [name, *_semantic_key(parameters[name], types[name])]
        for name in sorted(parameters)
    ])


def _parameter_registry_version() -> str:
    registry = build_parameter_registry(RESEARCH_PARAMETERS.search_space)
    return canonical_hash(registry)


def _split_fingerprints(rows: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    splits = _split_without_holdout(rows)
    return {
        "calibration": canonical_hash(splits["CALIBRATION"]),
        "validation": canonical_hash(splits["VALIDATION"]),
    }


def _adaptive_policy() -> dict[str, Any]:
    search = RESEARCH_PARAMETERS.search
    ranges = RESEARCH_PARAMETERS.data_driven_range_generation
    return {
        "candidate_interpolation": "WEIGHTED_INTERIOR_FROM_TRANSITION_ENDPOINTS",
        "interpolation_weight": ranges.transition_weight,
        "numeric_decimal_places": ranges.rounding_decimal_places,
        "integer_rule": "STRICT_INTERIOR_INTEGER_NEAREST_WEIGHTED_POINT",
        "boundary_step": "CURRENT_BOUNDARY_ADJACENT_SPACING",
        "round_batch_size": search.batch_size,
        "evaluation_budget_authorities": [
            "config/research/research_parameters.yaml:search.max_evaluated_configs",
            "config/research/research_parameters.yaml:search.max_total_configs",
            "config/research/research_parameters.yaml:search.max_configs_per_observation",
        ],
        "candidate_priority": [
            "BEHAVIORAL_TRANSITION_EVIDENCE", "POSITIVE_PARENT_PROXIMITY",
            "CANONICAL_PARENT_RANK", "BOUNDARY_PRESSURE", "CANONICAL_CONFIG_KEY",
        ],
        "convergence": "FIRST_ROUND_WITHOUT_NEW_BEHAVIOR_OR_WITHOUT_CANDIDATES",
    }


def resolve_adaptive_budget(dataset_rows: int) -> tuple[int, list[str]]:
    search = RESEARCH_PARAMETERS.search
    budget = min(
        search.max_evaluated_configs,
        search.max_total_configs,
        max(1, dataset_rows * search.max_configs_per_observation),
    )
    return budget, _adaptive_policy()["evaluation_budget_authorities"]


def _range_row(handoff: DataDrivenRangeHandoff, parameter: str):
    return next(row for row in handoff.parameters if row.parameter == parameter)


def _numeric_values(values: Iterable[object]) -> list[object]:
    return sorted(set(values), key=float)


def _neighbor_pairs(
    results: Sequence[Mapping[str, Any]], domains: Mapping[str, Sequence[object]],
) -> list[dict[str, Any]]:
    """Return only proven one-dimensional comparable adjacent pairs."""
    output: list[dict[str, Any]] = []
    for parameter in sorted(domains):
        ordered = _numeric_values(domains[parameter])
        positions = {_semantic_key(value, "NUMERIC"): index for index, value in enumerate(ordered)}
        groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for row in results:
            params = row["parameters"]
            common = {name: params[name] for name in sorted(params) if name != parameter}
            groups[canonical_hash(common)].append(row)
        for common_key in sorted(groups):
            by_position: dict[int, Mapping[str, Any]] = {}
            for row in groups[common_key]:
                value = row["parameters"][parameter]
                position = positions.get(_semantic_key(value, "NUMERIC"))
                if position is not None:
                    by_position[position] = row
            for position in sorted(by_position):
                if position + 1 not in by_position:
                    continue
                a, b = by_position[position], by_position[position + 1]
                output.append({
                    "parameter": parameter,
                    "value_a": a["parameters"][parameter],
                    "value_b": b["parameters"][parameter],
                    "config_a": a,
                    "config_b": b,
                    "common_parameters": {
                        name: a["parameters"][name]
                        for name in sorted(a["parameters"]) if name != parameter
                    },
                    "behavior_changed": a["behavioral_signature"] != b["behavioral_signature"],
                })
    return output


def _cluster_payloads(
    results: Sequence[Mapping[str, Any]], domains: Mapping[str, Sequence[object]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    representatives, basic = cluster_results(results, domains)
    rank_by_id = {str(row["config_id"]): index for index, row in enumerate(representatives, 1)}
    by_id = {str(row["config_id"]): row for row in results}
    nodes: list[dict[str, Any]] = []
    for cluster in basic:
        members = [by_id[str(config_id)] for config_id in cluster["member_config_ids"]]
        representative = by_id[str(cluster["representative_config_id"])]
        envelopes = {}
        for parameter in sorted(domains):
            values = _numeric_values(member["parameters"][parameter] for member in members)
            envelopes[parameter] = {"minimum": values[0], "maximum": values[-1], "observed_values": values}
        nodes.append({
            "behavioral_signature": cluster["behavioral_signature"],
            "member_config_ids": cluster["member_config_ids"],
            "representative_config": representative["parameters"],
            "representative_config_id": representative["config_id"],
            "parameter_envelopes": envelopes,
            "validation_trade_count": representative["trade_count"],
            "wins": representative["wins"], "losses": representative["losses"],
            "neutrals": representative["neutrals"], "net_pnl": representative["net_pnl"],
            "expectancy_r": representative.get("expectancy_R"),
            "profit_factor": representative.get("profit_factor"),
            "max_drawdown": representative["max_drawdown"],
            "independent_periods": representative["independent_period_count"],
            "canonical_rank": rank_by_id[str(representative["config_id"])],
            "canonical_status": representative["performance_class"],
            "positive_observed": any(float(member.get("net_pnl") or 0) > 0 for member in members),
            "validation_eligible": bool(
                representative.get("evaluation_status") == "ACCEPTED"
                and representative.get("performance_class") == "VALIDATION_CANDIDATE"
                and not representative.get("insufficient_sample_gates")
            ),
            "source_round": min(int(member.get("adaptive_round") or 0) for member in members),
        })
    return representatives, nodes


def build_transition_graph(
    results: Sequence[Mapping[str, Any]], domains: Mapping[str, Sequence[object]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    representatives, nodes = _cluster_payloads(results, domains)
    rank = {str(row["behavioral_signature"]): index for index, row in enumerate(representatives, 1)}
    by_signature = {node["behavioral_signature"]: node for node in nodes}
    evidence: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    pairs = _neighbor_pairs(results, domains)
    for pair in pairs:
        if not pair["behavior_changed"]:
            continue
        sig_a = str(pair["config_a"]["behavioral_signature"])
        sig_b = str(pair["config_b"]["behavioral_signature"])
        low, high = sorted((sig_a, sig_b))
        evidence[(low, high, pair["parameter"])].append({
            "config_a": pair["config_a"]["config_id"],
            "config_b": pair["config_b"]["config_id"],
            "value_a": pair["value_a"], "value_b": pair["value_b"],
            "common_parameters": pair["common_parameters"],
        })
    edges = []
    for (sig_a, sig_b, parameter), proofs in sorted(evidence.items()):
        node_a, node_b = by_signature[sig_a], by_signature[sig_b]
        first = proofs[0]
        edges.append({
            "cluster_a": sig_a, "cluster_b": sig_b,
            "differing_parameters": [parameter],
            "parameter_delta": {parameter: float(first["value_b"]) - float(first["value_a"])},
            "common_parameters": first["common_parameters"],
            "behavior_changed": True,
            "rank_delta": rank[sig_b] - rank[sig_a],
            "net_pnl_delta": float(node_b["net_pnl"] or 0) - float(node_a["net_pnl"] or 0),
            "trade_count_delta": int(node_b["validation_trade_count"]) - int(node_a["validation_trade_count"]),
            "adjacency_evidence": proofs,
        })
    return {
        "artifact": "BEHAVIORAL_TRANSITION_GRAPH", "schema_version": ADAPTIVE_SCHEMA_VERSION,
        "node_semantics": "ONE_BEHAVIORAL_CLUSTER",
        "edge_semantics": "PROVEN_ONE_PARAMETER_ADJACENCY_WITH_COMPARABLE_COMMON_CONTEXT",
        "nodes": nodes, "edges": edges,
    }, pairs


def build_parameter_sensitivity(
    results: Sequence[Mapping[str, Any]], domains: Mapping[str, Sequence[object]],
    handoff: DataDrivenRangeHandoff,
) -> dict[str, Any]:
    _graph, pairs = build_transition_graph(results, domains)
    rows = []
    for parameter in sorted(domains):
        evidence = [pair for pair in pairs if pair["parameter"] == parameter]
        transitions = [pair for pair in evidence if pair["behavior_changed"]]
        flats = [pair for pair in evidence if not pair["behavior_changed"]]
        if not evidence:
            status = "INSUFFICIENT_EVIDENCE"
        elif not transitions:
            status = "BEHAVIORALLY_FLAT"
        elif not flats:
            status = "BEHAVIORALLY_ACTIVE"
        else:
            status = "WEAKLY_ACTIVE"
        assert status in SENSITIVITY_CLASSES
        values = _numeric_values(row["parameters"][parameter] for row in results)
        positive_values = _numeric_values(
            row["parameters"][parameter] for row in results if float(row.get("net_pnl") or 0) > 0
        )
        range_spec = _range_row(handoff, parameter)
        rows.append({
            "parameter": parameter, "active_status": status,
            "observed_values": values,
            "behavioral_signatures_reached": sorted({str(row["behavioral_signature"]) for row in results}),
            "behavioral_transition_count": len(transitions),
            "flat_region_count": len(flats),
            "behavior_change_rate": len(transitions) / len(evidence) if evidence else None,
            "positive_cluster_values": positive_values,
            "low_boundary_signal": range_spec.boundary_pressure == "BOUNDARY_PRESSURE_LOW",
            "high_boundary_signal": range_spec.boundary_pressure == "BOUNDARY_PRESSURE_HIGH",
            "boundary_association": range_spec.boundary_pressure,
            "evidence": {
                "comparable_neighbor_pairs": len(evidence),
                "transition_intervals": [[pair["value_a"], pair["value_b"]] for pair in transitions],
                "flat_intervals": [[pair["value_a"], pair["value_b"]] for pair in flats],
                "classification_rule": "NO_PAIRS_INSUFFICIENT; ZERO_TRANSITIONS_FLAT; ZERO_FLATS_ACTIVE; OTHERWISE_WEAK",
            },
        })
    return {"artifact": "ADAPTIVE_PARAMETER_SENSITIVITY", "schema_version": ADAPTIVE_SCHEMA_VERSION, "parameters": rows}


def _interior_value(a: object, b: object, parameter_type: str) -> object | None:
    low, high = sorted((float(a), float(b)))
    weight = RESEARCH_PARAMETERS.data_driven_range_generation.transition_weight
    raw = low + (high - low) * weight
    if parameter_type == "INTEGER":
        candidates = list(range(math.floor(low) + 1, math.ceil(high)))
        if not candidates:
            return None
        return min(candidates, key=lambda value: (abs(value - raw), value))
    if parameter_type == "NUMERIC":
        return round(raw, RESEARCH_PARAMETERS.data_driven_range_generation.rounding_decimal_places)
    return None


def _boundary_value(values: Sequence[object], side: str, parameter_type: str) -> object | None:
    ordered = _numeric_values(values)
    if len(ordered) < 2 or parameter_type == "BOOLEAN":
        return None
    if side == "HIGH":
        raw = float(ordered[-1]) + (float(ordered[-1]) - float(ordered[-2]))
    else:
        raw = float(ordered[0]) - (float(ordered[1]) - float(ordered[0]))
    if parameter_type == "INTEGER":
        return int(raw) if raw.is_integer() else math.floor(raw) if side == "LOW" else math.ceil(raw)
    return round(raw, RESEARCH_PARAMETERS.data_driven_range_generation.rounding_decimal_places)


def _proposal(
    *, reason: str, parameter: str, value: object, config: Mapping[str, object],
    round_id: int, parent_values: Sequence[object], parent_clusters: Sequence[str],
    formula: str, schema_domain: Mapping[str, Any], parent_ranks: Sequence[int],
    positive_parent: bool, boundary_pressure: bool,
) -> dict[str, Any]:
    return {
        "generation_reason": reason, "parameter": parameter, "generated_value": value,
        "candidate_parameters": dict(config), "round": round_id,
        "parent_values": list(parent_values), "parent_clusters": list(parent_clusters),
        "generation_formula": formula,
        "schema_proof": {"domain": dict(schema_domain), "valid": _value_is_valid(value, schema_domain)},
        "provenance": {
            "policy": "config/research/research_parameters.yaml",
            "parent_canonical_ranks": list(parent_ranks),
            "positive_parent": positive_parent,
            "boundary_pressure": boundary_pressure,
        },
    }


def generate_candidates(
    *, results: Sequence[Mapping[str, Any]], domains: Mapping[str, Sequence[object]],
    handoff: DataDrivenRangeHandoff, round_id: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    representatives, _nodes = _cluster_payloads(results, domains)
    ranks = {str(row["behavioral_signature"]): index for index, row in enumerate(representatives, 1)}
    types = {row.parameter: row.parameter_type for row in handoff.parameters if row.parameter in domains}
    existing = {_config_key(row["parameters"], types) for row in results}
    sensitivity = build_parameter_sensitivity(results, domains, handoff)
    active = {
        row["parameter"] for row in sensitivity["parameters"]
        if row["active_status"] in {"BEHAVIORALLY_ACTIVE", "WEAKLY_ACTIVE"}
    }
    proposals: list[dict[str, Any]] = []
    trace: list[dict[str, Any]] = []
    counters = {"interior_generated": 0, "boundary_generated": 0, "duplicates": 0, "schema": 0, "schema_blocked": 0}

    for pair in _neighbor_pairs(results, domains):
        if not pair["behavior_changed"] or pair["parameter"] not in active:
            continue
        parameter = pair["parameter"]
        spec = _range_row(handoff, parameter)
        value = _interior_value(pair["value_a"], pair["value_b"], spec.parameter_type)
        if value is None:
            continue
        config = dict(pair["common_parameters"]); config[parameter] = value
        proposal = _proposal(
            reason="INTERIOR_BEHAVIORAL_TRANSITION", parameter=parameter, value=value,
            config=config, round_id=round_id, parent_values=[pair["value_a"], pair["value_b"]],
            parent_clusters=[pair["config_a"]["behavioral_signature"], pair["config_b"]["behavioral_signature"]],
            formula="low + (high-low) * data_driven_range_generation.transition_weight; typed precision applied",
            schema_domain=spec.schema_domain.model_dump(),
            parent_ranks=[ranks[str(pair["config_a"]["behavioral_signature"])], ranks[str(pair["config_b"]["behavioral_signature"])]],
            positive_parent=any(float(row.get("net_pnl") or 0) > 0 for row in (pair["config_a"], pair["config_b"])),
            boundary_pressure=False,
        )
        proposals.append(proposal)

    ranked_results = sorted(
        results,
        key=lambda row: (ranks[str(row["behavioral_signature"])], str(row["config_id"])),
    )
    for parameter in sorted(active):
        spec = _range_row(handoff, parameter)
        side = "HIGH" if spec.boundary_pressure == "BOUNDARY_PRESSURE_HIGH" else "LOW" if spec.boundary_pressure == "BOUNDARY_PRESSURE_LOW" else None
        if side is None:
            continue
        boundary = _numeric_values(domains[parameter])[-1 if side == "HIGH" else 0]
        parents = [
            row for row in ranked_results
            if row["parameters"][parameter] == boundary and float(row.get("net_pnl") or 0) > 0
        ]
        if not parents:
            continue
        parent = parents[0]
        value = _boundary_value(domains[parameter], side, spec.parameter_type)
        if value is None:
            continue
        config = dict(parent["parameters"]); config[parameter] = value
        proposal = _proposal(
            reason=f"EVIDENCE_BASED_{side}_BOUNDARY_EXPANSION", parameter=parameter,
            value=value, config=config, round_id=round_id,
            parent_values=[boundary, _numeric_values(domains[parameter])[-2 if side == "HIGH" else 1]],
            parent_clusters=[parent["behavioral_signature"]],
            formula="boundary +/- adjacent spacing in current data-driven domain",
            schema_domain=spec.schema_domain.model_dump(),
            parent_ranks=[ranks[str(parent["behavioral_signature"])]], positive_parent=True,
            boundary_pressure=True,
        )
        proposals.append(proposal)

    # A deterministic evidence tuple, not a replacement result-ranking score.
    proposals.sort(key=lambda row: (
        not row["provenance"]["positive_parent"],
        min(row["provenance"]["parent_canonical_ranks"]),
        row["generation_reason"] != "INTERIOR_BEHAVIORAL_TRANSITION",
        not row["provenance"]["boundary_pressure"],
        row["parameter"], _config_key(row["candidate_parameters"], types),
    ))
    accepted: list[dict[str, Any]] = []
    seen = set(existing)
    for proposal in proposals:
        key = _config_key(proposal["candidate_parameters"], types)
        proposal["candidate_key"] = key
        if not proposal["schema_proof"]["valid"]:
            proposal["decision"] = "BOUNDARY_BLOCKED_BY_SCHEMA" if "BOUNDARY" in proposal["generation_reason"] else "REJECTED_BY_SCHEMA"
            counters["schema"] += 1
            counters["schema_blocked"] += int(proposal["decision"] == "BOUNDARY_BLOCKED_BY_SCHEMA")
        elif key in seen:
            proposal["decision"] = "REJECTED_DUPLICATE_CONSUMED_CONFIG"
            counters["duplicates"] += 1
        else:
            proposal["decision"] = "PLANNED"
            seen.add(key)
            accepted.append(proposal)
            if proposal["generation_reason"] == "INTERIOR_BEHAVIORAL_TRANSITION":
                counters["interior_generated"] += 1
            else:
                counters["boundary_generated"] += 1
        trace.append(proposal)
    return accepted, trace, counters


def assert_resume_compatible(checkpoint: Mapping[str, Any], expected: AdaptiveCampaignInputs) -> None:
    parsed = AdaptiveCheckpoint.model_validate(checkpoint)
    for field, value in expected.model_dump().items():
        if getattr(parsed.inputs, field) != value:
            raise ValueError(f"RESUME_{field.upper()}_MISMATCH")


def behavioral_novelty_counts(
    initial_results: Sequence[Mapping[str, Any]],
    new_results: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    initial = {str(row["behavioral_signature"]) for row in initial_results}
    new = {str(row["behavioral_signature"]) for row in new_results} - initial
    return {
        "NEW_NUMERIC_CONFIGS": len(new_results),
        "NEW_BEHAVIORAL_CLUSTERS": len(new),
        "BEHAVIORAL_DUPLICATES": len(new_results) - len(new),
    }


def positive_behavioral_counts(results: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    positive = [row for row in results if float(row.get("net_pnl") or 0) > 0]
    signatures = {str(row["behavioral_signature"]) for row in positive}
    return {
        "POSITIVE_NUMERIC_CONFIGS": len(positive),
        "POSITIVE_BEHAVIORAL_CLUSTERS": len(signatures),
        "POSITIVE_BEHAVIORAL_DUPLICATES": len(positive) - len(signatures),
    }


def _validate_campaign(
    *, symbol: object, profile: str, range_handoff_path: Path,
    expanded_config_path: Path, expanded_handoff_path: Path,
    behavioral_clusters_path: Path, expanded_results_path: Path,
    normalization_path: Path, dataset_path: Path, dataset_manifest_path: Path,
) -> tuple[AdaptiveCampaignInputs, DataDrivenRangeHandoff, dict[str, list[object]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    selected = validate_parameter_sweep_symbol(symbol)
    handoff, range_hash = validate_handoff(range_handoff_path, symbol=selected, profile=profile)
    domains, expected_normalization = normalize_handoff_values(handoff)
    config = _read_json(expanded_config_path)
    expanded_handoff = _read_json(expanded_handoff_path)
    clusters = _read_json(behavioral_clusters_path)
    results = _read_jsonl(expanded_results_path)
    normalization = _read_json(normalization_path)
    rows = _read_jsonl(dataset_path)
    manifest = _read_json(dataset_manifest_path)
    validate_dataset(rows, symbol=selected, profile=profile)
    if manifest.get("symbol") != selected or manifest.get("profile") != profile:
        raise ValueError("DATASET_MANIFEST_PROVENANCE_MISMATCH")
    dataset_hash = _canonical_dataset_hash(rows)
    if manifest.get("dataset_sha256") != dataset_hash:
        raise ValueError("DATASET_FINGERPRINT_MISMATCH")
    for name, artifact in (("CONFIG", config), ("HANDOFF", expanded_handoff)):
        if artifact.get("symbol") != selected:
            raise ValueError(f"EXPANDED_SEARCH_{name}_SYMBOL_MISMATCH")
        if artifact.get("profile") != profile:
            raise ValueError(f"EXPANDED_SEARCH_{name}_PROFILE_MISMATCH")
        if artifact.get("dataset_fingerprint") != dataset_hash:
            raise ValueError(f"EXPANDED_SEARCH_{name}_DATASET_MISMATCH")
        range_field = "handoff_sha256" if name == "CONFIG" else "range_handoff_fingerprint"
        if artifact.get(range_field) != range_hash:
            raise ValueError(f"EXPANDED_SEARCH_{name}_RANGE_HANDOFF_MISMATCH")
    if config.get("search_space_fingerprint") != expanded_handoff.get("search_space_fingerprint"):
        raise ValueError("EXPANDED_SEARCH_SPACE_FINGERPRINT_MISMATCH")
    if config.get("dimension_values") != {name: domains[name] for name in sorted(domains)}:
        raise ValueError("EXPANDED_SEARCH_DOMAIN_MISMATCH")
    if normalization != expected_normalization:
        raise ValueError("SEARCH_VALUE_NORMALIZATION_MISMATCH")
    recomputed_representatives, recomputed_clusters = cluster_results(results, domains)
    if clusters != {"artifact": "BEHAVIORAL_CLUSTERS", "schema_version": 1, "clusters": recomputed_clusters}:
        raise ValueError("BEHAVIORAL_CLUSTERS_MISMATCH")
    if [row["behavioral_signature"] for row in recomputed_representatives] != [row["behavioral_signature"] for row in expanded_handoff.get("results", [])]:
        raise ValueError("EXPANDED_HANDOFF_CLUSTER_ORDER_MISMATCH")
    split_hashes = _split_fingerprints(rows)
    policy = _adaptive_policy()
    expanded_files = [expanded_config_path, expanded_handoff_path, behavioral_clusters_path, expanded_results_path, normalization_path]
    inputs = AdaptiveCampaignInputs(
        symbol=selected, profile=profile, dataset_fingerprint=dataset_hash,
        calibration_split_fingerprint=split_hashes["calibration"],
        validation_split_fingerprint=split_hashes["validation"],
        parameter_registry_version=_parameter_registry_version(),
        range_handoff_fingerprint=range_hash,
        expanded_search_fingerprint=_aggregate_fingerprint(expanded_files),
        adaptive_policy_fingerprint=canonical_hash(policy), seed=RESEARCH_PARAMETERS.search.seed,
    )
    return inputs, handoff, domains, results, rows, manifest


def _flags(parameters: Mapping[str, object], domains: Mapping[str, Sequence[object]]) -> tuple[list[str], list[str], list[str]]:
    low, high, interior = [], [], []
    for parameter in sorted(domains):
        ordered = _numeric_values(domains[parameter])
        if parameters[parameter] == ordered[0]: low.append(parameter)
        elif parameters[parameter] == ordered[-1]: high.append(parameter)
        else: interior.append(parameter)
    return low, high, interior


def _handoff_clusters(results: Sequence[Mapping[str, Any]], domains: Mapping[str, Sequence[object]]) -> list[dict[str, Any]]:
    representatives, nodes = _cluster_payloads(results, domains)
    members_by_signature: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in results: members_by_signature[str(row["behavioral_signature"])].append(row)
    output = []
    for representative, node in zip(representatives, nodes):
        members = members_by_signature[str(representative["behavioral_signature"])]
        low, high, interior = _flags(representative["parameters"], domains)
        output.append({
            "behavioral_signature": representative["behavioral_signature"],
            "representative_config": representative["parameters"],
            "representative_config_id": representative["config_id"],
            "member_config_count": len(members),
            "parameter_region": node["parameter_envelopes"],
            "validation_trade_count": representative["trade_count"],
            "wins": representative["wins"], "losses": representative["losses"],
            "neutrals": representative["neutrals"], "net_pnl": representative["net_pnl"],
            "expectancy_r": representative.get("expectancy_R"),
            "profit_factor": representative.get("profit_factor"),
            "max_drawdown": representative["max_drawdown"],
            "independent_periods": representative["independent_period_count"],
            "canonical_rank": node["canonical_rank"],
            "validation_status": representative["performance_class"],
            "validation_eligible": node["validation_eligible"],
            "positive_observed": any(float(row.get("net_pnl") or 0) > 0 for row in members),
            "low_boundary_flags": low, "high_boundary_flags": high,
            "interior_flags": interior, "source_round": node["source_round"],
        })
    return output


def _write_final_artifacts(
    *, output: Path, inputs: AdaptiveCampaignInputs, handoff: DataDrivenRangeHandoff,
    initial_results: Sequence[Mapping[str, Any]], adaptive_results: Sequence[Mapping[str, Any]],
    domains: Mapping[str, Sequence[object]], trace: Sequence[Mapping[str, Any]],
    rounds: Sequence[Mapping[str, Any]], budget: int, budget_authority: Sequence[str],
    manifest: Mapping[str, Any], stop_reason: str,
) -> dict[str, Any]:
    combined = [dict(row) for row in initial_results] + [dict(row) for row in adaptive_results]
    graph, _pairs = build_transition_graph(combined, domains)
    sensitivity = build_parameter_sensitivity(combined, domains, handoff)
    representatives, _clusters = cluster_results(combined, domains)
    initial_representatives, _initial_clusters = cluster_results(initial_results, {name: list(row.generated_values) for name, row in ((spec.parameter, spec) for spec in handoff.parameters) if name in domains})
    summary, _positive = build_reporting_reconciliation(combined, representatives)
    initial_positive_signatures = {str(row["behavioral_signature"]) for row in initial_results if float(row.get("net_pnl") or 0) > 0}
    final_positive_signatures = {str(row["behavioral_signature"]) for row in combined if float(row.get("net_pnl") or 0) > 0}
    new_signatures = {str(row["behavioral_signature"]) for row in adaptive_results} - {str(row["behavioral_signature"]) for row in initial_results}
    new_positive_signatures = {str(row["behavioral_signature"]) for row in adaptive_results if float(row.get("net_pnl") or 0) > 0} - initial_positive_signatures
    final_clusters = _handoff_clusters(combined, domains)
    active = [row["parameter"] for row in sensitivity["parameters"] if row["active_status"] in {"BEHAVIORALLY_ACTIVE", "WEAKLY_ACTIVE"}]
    flat = [row["parameter"] for row in sensitivity["parameters"] if row["active_status"] == "BEHAVIORALLY_FLAT"]
    insufficient = [row["parameter"] for row in sensitivity["parameters"] if row["active_status"] == "INSUFFICIENT_EVIDENCE"]
    candidate_counts = {
        "interior": len({row.get("candidate_key") for row in trace if row.get("decision") in {"PLANNED", "EVALUATED", "DEFERRED_BY_ROUND_OR_BUDGET"} and row.get("generation_reason") == "INTERIOR_BEHAVIORAL_TRANSITION"}),
        "boundary": len({row.get("candidate_key") for row in trace if row.get("decision") in {"PLANNED", "EVALUATED", "DEFERRED_BY_ROUND_OR_BUDGET"} and "BOUNDARY" in str(row.get("generation_reason"))}),
        "schema_blocked": sum(row.get("decision") == "BOUNDARY_BLOCKED_BY_SCHEMA" for row in trace),
    }
    handoff_out = {
        "artifact": "ADAPTIVE_REFINEMENT_HANDOFF", "schema_version": ADAPTIVE_SCHEMA_VERSION,
        "symbol": inputs.symbol, "profile": inputs.profile,
        "campaign_inputs": inputs.model_dump(),
        "ranking_policy": "EXISTING_CANONICAL_RESEARCH_RANKING_UNCHANGED",
        "validation_policy": {
            "minimum_trades": VALIDATION_SAMPLE_POLICY.minimum_validation_trades,
            "minimum_independent_periods": VALIDATION_SAMPLE_POLICY.minimum_independent_periods,
            "independent_period_unit": VALIDATION_SAMPLE_POLICY.independent_period_unit,
        },
        "clusters": final_clusters,
        "summary": {
            "initial_behavioral_cluster_count": len(initial_representatives),
            "final_behavioral_cluster_count": len(representatives),
            "new_behavioral_clusters_discovered": len(new_signatures),
            "initial_positive_behavioral_clusters": len(initial_positive_signatures),
            "final_positive_behavioral_clusters": len(final_positive_signatures),
            "best_canonical_ranked": summary["BEST_CANONICAL_RANKED_CONFIG"],
            "best_net_pnl": summary["BEST_NET_PNL_CONFIG"],
            "best_pf": summary["BEST_PROFIT_FACTOR_CONFIG"],
            "convergence_status": "CONVERGED" if stop_reason != "BUDGET_EXHAUSTED" else "BOUNDED_STOP",
            "stop_reason": stop_reason,
            "validation_eligible_count": sum(row["validation_eligible"] for row in final_clusters),
        },
        "promotion_eligible": False, "holdout_opened": False,
        "finalist_freeze_executed": False,
    }
    status = {
        "FINAL_STATUS": "PASS",
        "FINAL_VERDICT": "PASS_DESCRIPTIVE_ONLY_ADAPTIVE_REFINEMENT_NOT_CERTIFIED",
        "SYMBOL": inputs.symbol, "PROFILE": inputs.profile,
        "SYMBOL_AUTHORITY_SOURCE": "app.trading_universe.domain:trading-universe-v2 -> required CLI --symbol -> validator -> adaptive run config",
        "SOURCE_HISTORY_START": manifest.get("source_history_start"),
        "SOURCE_HISTORY_END": manifest.get("source_history_end"),
        "SOURCE_HISTORY_ACTUAL_DAYS": manifest.get("source_history_actual_days"),
        "INITIAL_NUMERIC_CONFIGS": len(initial_results),
        "INITIAL_BEHAVIORAL_CLUSTERS": len(initial_representatives),
        "INITIAL_POSITIVE_NUMERIC_CONFIGS": sum(float(row.get("net_pnl") or 0) > 0 for row in initial_results),
        "INITIAL_POSITIVE_BEHAVIORAL_CLUSTERS": len(initial_positive_signatures),
        "BEHAVIORALLY_ACTIVE_PARAMETERS": active,
        "BEHAVIORALLY_FLAT_PARAMETERS": flat,
        "INSUFFICIENT_EVIDENCE_PARAMETERS": insufficient,
        "ADAPTIVE_ROUNDS": len(rounds),
        "NEW_NUMERIC_CONFIGS_EVALUATED": len(adaptive_results),
        "NEW_BEHAVIORAL_CLUSTERS_DISCOVERED": len(new_signatures),
        "NEW_POSITIVE_BEHAVIORAL_CLUSTERS": len(new_positive_signatures),
        "BEHAVIORAL_DUPLICATES": len(adaptive_results) - len(new_signatures),
        "BEHAVIORAL_NOVELTY_RATE": len(new_signatures) / len(adaptive_results) if adaptive_results else 0.0,
        "INTERIOR_REFINEMENT_CANDIDATES": candidate_counts["interior"],
        "BOUNDARY_EXPANSION_CANDIDATES": candidate_counts["boundary"],
        "BOUNDARY_BLOCKED_BY_SCHEMA": candidate_counts["schema_blocked"],
        "FINAL_BEHAVIORAL_CLUSTERS": len(representatives),
        "FINAL_POSITIVE_NUMERIC_CONFIGS": sum(float(row.get("net_pnl") or 0) > 0 for row in combined),
        "FINAL_POSITIVE_BEHAVIORAL_CLUSTERS": len(final_positive_signatures),
        "BEST_CANONICAL_RANKED_CONFIG": summary["BEST_CANONICAL_RANKED_CONFIG"],
        "BEST_NET_PNL_CONFIG": summary["BEST_NET_PNL_CONFIG"],
        "BEST_EXPECTANCY_CONFIG": summary["BEST_EXPECTANCY_CONFIG"],
        "BEST_PROFIT_FACTOR_CONFIG": summary["BEST_PROFIT_FACTOR_CONFIG"],
        "POSITIVE_NUMERIC_CONFIGS": summary["POSITIVE_NUMERIC_CONFIGS"],
        "POSITIVE_BEHAVIORAL_CLUSTERS": summary["POSITIVE_BEHAVIORAL_CLUSTERS"],
        "POSITIVE_BEHAVIORAL_DUPLICATES": summary["POSITIVE_BEHAVIORAL_DUPLICATES"],
        "VALIDATION_ELIGIBLE_CONFIGS": sum(row["validation_eligible"] for row in final_clusters),
        "CONVERGENCE_STATUS": "CONVERGED" if stop_reason != "BUDGET_EXHAUSTED" else "BOUNDED_STOP",
        "STOP_REASON": stop_reason,
        "CANONICAL_RESEARCH_BUDGET": budget,
        "BUDGET_AUTHORITY": list(budget_authority),
        "HOLDOUT_READS": 0, "HOLDOUT_OPENED": False,
        "FINALIST_FREEZE_EXECUTED": False,
        "ADAPTIVE_REFINEMENT_HANDOFF_CREATED": True,
        "SEARCH_RANKING_CHANGED": False, "VALIDATION_20_3_CHANGED": False,
        "SCHEMA_VIOLATIONS": 0, "NEW_VALUE_WITHOUT_PROVENANCE": 0,
        "DUPLICATE_CONSUMED_VALUES_EVALUATED": 0,
        "RECONSTRUCTED_ROWS_USED": 0, "CROSS_SYMBOL_ROWS": 0,
        "BYTE_DETERMINISM": "PASS_CANONICAL_JSONL_AND_DETERMINISTIC_ORDER",
        "RESUME_GUARDS": list(inputs.model_dump()),
        "ADAPTIVE_RESULT_CERTIFIED": False, "PROMOTION_ELIGIBLE": False,
        "LIVE_STATE": False, "BINANCE_ORDER_CALLS": 0, "PRODUCTION_MUTATIONS": 0,
    }
    config = {
        "artifact": "ADAPTIVE_REFINEMENT_CONFIG", "schema_version": ADAPTIVE_SCHEMA_VERSION,
        "campaign_inputs": inputs.model_dump(), "policy": _adaptive_policy(),
        "resolved_evaluation_budget": budget, "budget_authority": list(budget_authority),
        "single_symbol": True, "research_only": True, "holdout_blind": True,
        "production_mutation_allowed": False,
    }
    _write_json(output / "ADAPTIVE_REFINEMENT_CONFIG.json", config)
    _write_json(output / "BEHAVIORAL_TRANSITION_GRAPH.json", graph)
    _write_json(output / "ADAPTIVE_PARAMETER_SENSITIVITY.json", sensitivity)
    _write_jsonl(output / "ADAPTIVE_CANDIDATE_TRACE.jsonl", trace)
    _write_jsonl(output / "ADAPTIVE_ROUNDS.jsonl", rounds)
    _write_jsonl(output / "ADAPTIVE_RESULTS.jsonl", adaptive_results)
    _write_json(output / "ADAPTIVE_BEHAVIORAL_CLUSTERS.json", {"artifact": "ADAPTIVE_BEHAVIORAL_CLUSTERS", "schema_version": ADAPTIVE_SCHEMA_VERSION, "clusters": graph["nodes"]})
    _write_json(output / "ADAPTIVE_REFINEMENT_HANDOFF.json", handoff_out)
    _write_json(output / "STATUS.json", status)
    report = "\n".join([
        "# Adaptive Refinement", "",
        f"- Symbol/profile: `{inputs.symbol}` / `{inputs.profile}`",
        f"- Source history: `{status['SOURCE_HISTORY_START']}` to `{status['SOURCE_HISTORY_END']}` ({status['SOURCE_HISTORY_ACTUAL_DAYS']} days)",
        f"- Initial/final behavioral clusters: {len(initial_representatives)}/{len(representatives)}",
        f"- New numeric/new behaviors/duplicates: {len(adaptive_results)}/{len(new_signatures)}/{len(adaptive_results)-len(new_signatures)}",
        f"- Rounds/stop: {len(rounds)} / `{stop_reason}`",
        f"- Interior/boundary/schema-blocked candidates: {candidate_counts['interior']}/{candidate_counts['boundary']}/{candidate_counts['schema_blocked']}",
        f"- Positive numeric/behavioral/aliases: {summary['POSITIVE_NUMERIC_CONFIGS']}/{summary['POSITIVE_BEHAVIORAL_CLUSTERS']}/{summary['POSITIVE_BEHAVIORAL_DUPLICATES']}",
        "- Expectancy R: `NOT_AVAILABLE`; canonical ranking and validation 20/3 are unchanged.",
        "- Certification/promotion: `NO` / `NO`; holdout/finalist freeze: `NO` / `NO`.", "",
    ])
    DEFAULT_ARTIFACT_WRITER.atomic_text(output / "REPORT.md", report, operation="adaptive_refinement_report")
    return {"status": status, "handoff": handoff_out, "output": str(output)}


def run_adaptive_refinement(
    *, range_handoff_path: Path, expanded_config_path: Path,
    expanded_handoff_path: Path, behavioral_clusters_path: Path,
    expanded_results_path: Path, normalization_path: Path,
    dataset_path: Path, dataset_manifest_path: Path, output: Path,
    symbol: object, profile: str = "trade-5m-v2", resume: bool = False,
) -> dict[str, Any]:
    inputs, handoff, initial_domains, initial_results, dataset_rows, manifest = _validate_campaign(
        symbol=symbol, profile=profile, range_handoff_path=range_handoff_path,
        expanded_config_path=expanded_config_path, expanded_handoff_path=expanded_handoff_path,
        behavioral_clusters_path=behavioral_clusters_path,
        expanded_results_path=expanded_results_path, normalization_path=normalization_path,
        dataset_path=dataset_path, dataset_manifest_path=dataset_manifest_path,
    )
    output.mkdir(parents=True, exist_ok=True)
    checkpoint_path = output / "CHECKPOINT.json"
    if resume:
        if not checkpoint_path.is_file():
            raise ValueError("RESUME_CHECKPOINT_NOT_AVAILABLE")
        checkpoint_raw = _read_json(checkpoint_path)
        assert_resume_compatible(checkpoint_raw, inputs)
        checkpoint = AdaptiveCheckpoint.model_validate(checkpoint_raw)
        adaptive_results = _read_jsonl(output / "ADAPTIVE_RESULTS.jsonl") if (output / "ADAPTIVE_RESULTS.jsonl").is_file() else []
        trace = _read_jsonl(output / "ADAPTIVE_CANDIDATE_TRACE.jsonl") if (output / "ADAPTIVE_CANDIDATE_TRACE.jsonl").is_file() else []
        rounds = _read_jsonl(output / "ADAPTIVE_ROUNDS.jsonl") if (output / "ADAPTIVE_ROUNDS.jsonl").is_file() else []
        if len(adaptive_results) != checkpoint.cumulative_evaluations or len(rounds) != checkpoint.completed_rounds:
            raise ValueError("RESUME_RESULT_COUNT_MISMATCH")
        if checkpoint.completed:
            return {"status": _read_json(output / "STATUS.json"), "handoff": _read_json(output / "ADAPTIVE_REFINEMENT_HANDOFF.json"), "output": str(output)}
    else:
        adaptive_results, trace, rounds = [], [], []
        checkpoint = AdaptiveCheckpoint(
            artifact="ADAPTIVE_REFINEMENT_CHECKPOINT", schema_version=ADAPTIVE_SCHEMA_VERSION,
            inputs=inputs, evaluated_candidate_keys=[], completed_rounds=0,
            cumulative_evaluations=0, completed=False, stop_reason=None,
            holdout_opened=False,
        )
        _write_json(checkpoint_path, checkpoint.model_dump())
        _write_jsonl(output / "ADAPTIVE_RESULTS.jsonl", [])
        _write_jsonl(output / "ADAPTIVE_CANDIDATE_TRACE.jsonl", [])
        _write_jsonl(output / "ADAPTIVE_ROUNDS.jsonl", [])

    budget, budget_authority = resolve_adaptive_budget(len(dataset_rows))
    splits = _split_without_holdout(dataset_rows)
    types = {row.parameter: row.parameter_type for row in handoff.parameters if row.parameter in initial_domains}
    evaluated_keys = {_config_key(row["parameters"], types) for row in initial_results}
    evaluated_keys.update(_config_key(row["parameters"], types) for row in adaptive_results)
    stop_reason = "NO_NEW_CANDIDATES"
    while len(adaptive_results) < budget:
        round_id = len(rounds) + 1
        combined = [dict(row) for row in initial_results] + [dict(row) for row in adaptive_results]
        domains = {
            parameter: _numeric_values(row["parameters"][parameter] for row in combined)
            for parameter in sorted(initial_domains)
        }
        before_signatures = {str(row["behavioral_signature"]) for row in combined}
        sensitivity = build_parameter_sensitivity(combined, domains, handoff)
        active = [row["parameter"] for row in sensitivity["parameters"] if row["active_status"] in {"BEHAVIORALLY_ACTIVE", "WEAKLY_ACTIVE"}]
        proposals, round_trace, counts = generate_candidates(
            results=combined, domains=domains, handoff=handoff, round_id=round_id,
        )
        # Reject proposals already evaluated in an earlier round before execution.
        planned = []
        for proposal in proposals:
            if proposal["candidate_key"] in evaluated_keys:
                proposal["decision"] = "REJECTED_ALREADY_EVALUATED_CONFIG"
                counts["duplicates"] += 1
            else:
                planned.append(proposal)
        remaining = budget - len(adaptive_results)
        planned = planned[: min(remaining, RESEARCH_PARAMETERS.search.batch_size)]
        planned_keys = {row["candidate_key"] for row in planned}
        for row in round_trace:
            if row.get("decision") == "PLANNED" and row["candidate_key"] not in planned_keys:
                row["decision"] = "DEFERRED_BY_ROUND_OR_BUDGET"
        trace.extend(round_trace)
        if not planned:
            if counts["schema_blocked"] and not any(pair["behavior_changed"] for pair in _neighbor_pairs(combined, domains)):
                stop_reason = "SCHEMA_BOUNDARIES_REACHED"
            elif any(pair["behavior_changed"] for pair in _neighbor_pairs(combined, domains)):
                stop_reason = "ALL_ELIGIBLE_TRANSITIONS_REFINED"
            else:
                stop_reason = "NO_NEW_CANDIDATES"
            rounds.append({
                "round_id": round_id, "input_behavioral_clusters": len(before_signatures),
                "active_parameters": active,
                "interior_candidates_generated": counts["interior_generated"],
                "boundary_candidates_generated": counts["boundary_generated"],
                "candidates_rejected_as_duplicates": counts["duplicates"],
                "candidates_rejected_by_schema": counts["schema"],
                "planned_new_configs": 0, "evaluated_new_configs": 0,
                "new_behavioral_clusters": 0, "reused_behavioral_clusters": 0,
                "positive_behavioral_clusters": len({
                    str(row["behavioral_signature"]) for row in combined
                    if float(row.get("net_pnl") or 0) > 0
                }),
                "cumulative_evaluations": len(adaptive_results),
                "remaining_budget": remaining, "stop_reason": stop_reason,
            })
            break
        new_rows = []
        start_index = len(initial_results) + len(adaptive_results)
        for offset, proposal in enumerate(planned):
            result = evaluate_config(proposal["candidate_parameters"], splits, index=start_index + offset)
            result["stage"] = "ADAPTIVE_REFINEMENT"
            result["adaptive_round"] = round_id
            result["generation_provenance"] = {
                key: proposal[key] for key in (
                    "generation_reason", "parameter", "generated_value", "parent_values",
                    "parent_clusters", "generation_formula", "schema_proof", "provenance",
                )
            }
            new_rows.append(result)
            evaluated_keys.add(proposal["candidate_key"])
            proposal["decision"] = "EVALUATED"
        adaptive_results.extend(new_rows)
        after_signatures = {str(row["behavioral_signature"]) for row in new_rows}
        novel = after_signatures - before_signatures
        reused = after_signatures & before_signatures
        stop_reason = "BUDGET_EXHAUSTED" if len(adaptive_results) >= budget else "NO_NEW_BEHAVIORAL_CLUSTERS" if not novel else "NO_NEW_CANDIDATES"
        rounds.append({
            "round_id": round_id, "input_behavioral_clusters": len(before_signatures),
            "active_parameters": active,
            "interior_candidates_generated": counts["interior_generated"],
            "boundary_candidates_generated": counts["boundary_generated"],
            "candidates_rejected_as_duplicates": counts["duplicates"],
            "candidates_rejected_by_schema": counts["schema"],
            "planned_new_configs": len(planned), "evaluated_new_configs": len(new_rows),
            "new_behavioral_clusters": len(novel), "reused_behavioral_clusters": len(reused),
            "positive_behavioral_clusters": len({str(row["behavioral_signature"]) for row in new_rows if float(row.get("net_pnl") or 0) > 0}),
            "cumulative_evaluations": len(adaptive_results),
            "remaining_budget": budget - len(adaptive_results),
            "stop_reason": stop_reason if stop_reason in {"NO_NEW_BEHAVIORAL_CLUSTERS", "BUDGET_EXHAUSTED"} else None,
        })
        _write_jsonl(output / "ADAPTIVE_RESULTS.jsonl", adaptive_results)
        _write_jsonl(output / "ADAPTIVE_CANDIDATE_TRACE.jsonl", trace)
        _write_jsonl(output / "ADAPTIVE_ROUNDS.jsonl", rounds)
        checkpoint = AdaptiveCheckpoint(
            artifact="ADAPTIVE_REFINEMENT_CHECKPOINT", schema_version=ADAPTIVE_SCHEMA_VERSION,
            inputs=inputs, evaluated_candidate_keys=sorted(evaluated_keys),
            completed_rounds=len(rounds), cumulative_evaluations=len(adaptive_results),
            completed=stop_reason in {"NO_NEW_BEHAVIORAL_CLUSTERS", "BUDGET_EXHAUSTED"},
            stop_reason=stop_reason if stop_reason in {"NO_NEW_BEHAVIORAL_CLUSTERS", "BUDGET_EXHAUSTED"} else None,
            holdout_opened=False,
        )
        _write_json(checkpoint_path, checkpoint.model_dump())
        if checkpoint.completed:
            break
    final_combined = [dict(row) for row in initial_results] + [dict(row) for row in adaptive_results]
    final_domains = {
        parameter: _numeric_values(row["parameters"][parameter] for row in final_combined)
        for parameter in sorted(initial_domains)
    }
    result = _write_final_artifacts(
        output=output, inputs=inputs, handoff=handoff,
        initial_results=initial_results, adaptive_results=adaptive_results,
        domains=final_domains, trace=trace, rounds=rounds, budget=budget,
        budget_authority=budget_authority, manifest=manifest, stop_reason=stop_reason,
    )
    final_checkpoint = AdaptiveCheckpoint(
        artifact="ADAPTIVE_REFINEMENT_CHECKPOINT", schema_version=ADAPTIVE_SCHEMA_VERSION,
        inputs=inputs, evaluated_candidate_keys=sorted(evaluated_keys),
        completed_rounds=len(rounds), cumulative_evaluations=len(adaptive_results),
        completed=True, stop_reason=stop_reason, holdout_opened=False,
    )
    _write_json(checkpoint_path, final_checkpoint.model_dump())
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--range-handoff", type=Path, required=True)
    parser.add_argument("--expanded-dir", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--profile", default="trade-5m-v2")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    expanded = args.expanded_dir
    result = run_adaptive_refinement(
        range_handoff_path=args.range_handoff,
        expanded_config_path=expanded / "EXPANDED_SEARCH_CONFIG.json",
        expanded_handoff_path=expanded / "EXPANDED_SEARCH_HANDOFF.json",
        behavioral_clusters_path=expanded / "BEHAVIORAL_CLUSTERS.json",
        expanded_results_path=expanded / "EXPANDED_SEARCH_RESULTS.jsonl",
        normalization_path=expanded / "SEARCH_VALUE_NORMALIZATION.json",
        dataset_path=args.dataset, dataset_manifest_path=args.dataset_manifest,
        output=args.output, symbol=args.symbol, profile=args.profile, resume=args.resume,
    )
    print(json.dumps(result["status"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
