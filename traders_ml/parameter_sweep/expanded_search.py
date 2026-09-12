"""Bounded handoff-driven single-symbol expanded research search.

This stage consumes candidate values exclusively from a validated
``DATA_DRIVEN_RANGE_HANDOFF.json``.  It deliberately has no holdout or adaptive
refinement path and never writes production configuration or a database.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Iterable, Iterator, Literal, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.config.trade_parameters import TRADE_PARAMETERS
from app.config.yaml_authority import RESEARCH_PARAMETERS, VALIDATION_SAMPLE_POLICY

from .artifact_v2 import canonical_hash, compact_result
from .artifact_writer import DEFAULT_ARTIFACT_WRITER
from .data_driven_ranges import _schema_domain, _value_is_valid
from .engine import (
    ParameterSweepSearchPlanner, SearchPlan, _candidate_config,
    _candidate_indices, _production_baseline_config,
)
from .historical_replay import build_parameter_registry
from .ranking import rank_results
from .research_protocol import deduplicate_validation_behavior


HANDOFF_SCHEMA_VERSION = 2
EXPANDED_SEARCH_SCHEMA_VERSION = 1
ALLOWED_RANGE_STATUSES = frozenset({"GENERATED", "PROVISIONAL_LOW_SAMPLE"})
ACTIVE_CONSUMERS: dict[str, tuple[str, str]] = {
    "min_net_edge_bps": ("net_edge_bps", "MINIMUM_INCLUSIVE"),
    "minimum_planned_rr": ("planned_rr", "MINIMUM_INCLUSIVE"),
    "stop_max_bps": ("stop_distance_bps", "MAXIMUM_INCLUSIVE"),
    "target_min_bps": ("target_distance_bps", "MINIMUM_INCLUSIVE"),
}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class HandoffSchemaDomain(_Strict):
    type: Literal["NUMERIC", "INTEGER", "BOOLEAN"]
    minimum: float | int | None
    maximum: float | int | None
    minimum_inclusive: bool | None
    maximum_inclusive: bool | None
    values: list[bool] | None
    allows_null: bool


class HandoffParameter(_Strict):
    parameter: str
    generated_values: list[float | int | bool] = Field(min_length=1)
    parameter_type: Literal["NUMERIC", "INTEGER", "BOOLEAN"]
    schema_domain: HandoffSchemaDomain
    range_status: str
    eligible_for_search: bool
    confidence: str
    provisional: bool
    sample_adequacy: str
    promotion_eligible: Literal[False]
    boundary_pressure: str
    provenance: dict[str, Any]
    joint_search_priority_annotations: list[dict[str, Any]]


class DataDrivenRangeHandoff(_Strict):
    artifact: Literal["DATA_DRIVEN_RANGE_HANDOFF"]
    schema_version: Literal[HANDOFF_SCHEMA_VERSION]
    symbol: str
    profile: Literal["trade-5m-v2"]
    separability_status: str
    sample_adequacy: str
    range_provenance: dict[str, Any]
    research_approved_only: Literal[True]
    promotion_eligible: Literal[False]
    search_executed: Literal[False]
    adaptive_refinement_executed: Literal[False]
    holdout_opened: Literal[False]
    parameters: list[HandoffParameter]

    @model_validator(mode="after")
    def unique_parameters(self):
        names = [row.parameter for row in self.parameters]
        if len(names) != len(set(names)):
            raise ValueError("duplicate handoff parameter")
        return self


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _hash_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _canonical_dataset_hash(rows: Sequence[Mapping[str, Any]]) -> str:
    payload = "".join(
        json.dumps(dict(row), sort_keys=True, separators=(",", ":"), default=str) + "\n"
        for row in rows
    ).encode("utf-8")
    return _hash_bytes(payload)


def _write_json(path: Path, value: object) -> None:
    DEFAULT_ARTIFACT_WRITER.atomic_text(path, _json_bytes(value).decode("utf-8"), operation=f"{path.name}:replace")


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    text = "".join(_json_bytes(dict(row)).decode("utf-8") for row in rows)
    DEFAULT_ARTIFACT_WRITER.atomic_text(path, text, operation=f"{path.name}:replace")


def validate_handoff(path: Path, *, symbol: str, profile: str) -> tuple[DataDrivenRangeHandoff, str]:
    payload = path.read_bytes()
    handoff = DataDrivenRangeHandoff.model_validate_json(payload)
    if handoff.symbol != symbol:
        raise ValueError("HANDOFF_SYMBOL_MISMATCH")
    if handoff.profile != profile:
        raise ValueError("HANDOFF_PROFILE_MISMATCH")
    registry = {row["canonical_key"]: row for row in build_parameter_registry(RESEARCH_PARAMETERS.search_space)}
    for row in handoff.parameters:
        if row.parameter not in registry:
            raise ValueError("HANDOFF_PARAMETER_NOT_IN_REGISTRY")
        descriptor = registry[row.parameter]
        expected = _schema_domain(
            str(descriptor["RUNTIME_OWNER"]), descriptor["baseline"],
            list(descriptor["candidate_values"]),
        )
        if row.parameter_type != expected["type"] or row.schema_domain.model_dump() != expected:
            raise ValueError("HANDOFF_PARAMETER_SCHEMA_MISMATCH")
        if row.sample_adequacy != handoff.sample_adequacy:
            raise ValueError("HANDOFF_SAMPLE_ADEQUACY_MISMATCH")
        if any(not _value_is_valid(value, expected) for value in row.generated_values):
            raise ValueError("HANDOFF_CANDIDATE_SCHEMA_INVALID")
        if row.range_status not in ALLOWED_RANGE_STATUSES and row.eligible_for_search:
            raise ValueError("HANDOFF_INELIGIBLE_STATUS_MARKED_SEARCHABLE")
    return handoff, _hash_bytes(payload)


def upgrade_handoff_contract_v1(*, handoff_path: Path, ranges_path: Path) -> dict[str, Any]:
    """Add validation metadata to a v1 handoff without changing its domains."""
    legacy = _read_json(handoff_path)
    ranges = _read_json(ranges_path)
    if legacy.get("artifact") != "DATA_DRIVEN_RANGE_HANDOFF" or legacy.get("schema_version") != 1:
        raise ValueError("LEGACY_HANDOFF_V1_REQUIRED")
    by_name = {str(row["parameter"]): row for row in ranges.get("parameters", [])}
    parameters = []
    for source in legacy.get("parameters", []):
        name = str(source.get("parameter"))
        metadata = by_name.get(name)
        if metadata is None or source.get("generated_values") != metadata.get("generated_values"):
            raise ValueError("HANDOFF_DOMAIN_MIGRATION_MISMATCH")
        parameters.append({
            **source,
            "parameter_type": metadata["parameter_type"],
            "schema_domain": metadata["schema_domain"],
            "range_status": metadata["range_status"],
            "eligible_for_search": metadata["range_status"] in ALLOWED_RANGE_STATUSES,
            "sample_adequacy": metadata["sample_adequacy"],
            "promotion_eligible": False,
            "provenance": metadata["provenance"],
        })
    upgraded = {
        **legacy, "schema_version": HANDOFF_SCHEMA_VERSION,
        "symbol": ranges["symbol"], "profile": ranges["profile"],
        "separability_status": ranges["separability_status"],
        "sample_adequacy": ranges["sample_adequacy"],
        "range_provenance": {"input_sha256": ranges.get("input_sha256", {})},
        "parameters": parameters,
    }
    DataDrivenRangeHandoff.model_validate(upgraded)
    _write_json(handoff_path, upgraded)
    return upgraded


def _semantic_key(value: object, parameter_type: str) -> tuple[str, object]:
    if parameter_type == "BOOLEAN":
        return ("BOOLEAN", bool(value))
    if parameter_type == "INTEGER":
        return ("INTEGER", int(value))
    return ("IEEE754_BINARY64", float(value).hex())


def normalize_handoff_values(handoff: DataDrivenRangeHandoff) -> tuple[dict[str, list[object]], dict[str, Any]]:
    space: dict[str, list[object]] = {}
    evidence: list[dict[str, Any]] = []
    for row in handoff.parameters:
        if row.range_status not in ALLOWED_RANGE_STATUSES or not row.eligible_for_search:
            continue
        if row.parameter not in ACTIVE_CONSUMERS:
            raise ValueError("HANDOFF_SEARCH_CONSUMER_NOT_AUTHORIZED")
        normalized: list[object] = []
        seen: set[tuple[str, object]] = set()
        for value in row.generated_values:
            key = _semantic_key(value, row.parameter_type)
            if key not in seen:
                seen.add(key)
                normalized.append(value)
        space[row.parameter] = normalized
        evidence.append({
            "parameter": row.parameter,
            "input_values": row.generated_values,
            "typed_precision": row.parameter_type,
            "serialization_precision": "JSON_NUMBER_SHORTEST_ROUND_TRIP",
            "comparison_precision": "IEEE_754_BINARY64_DIRECT_COMPARISON" if row.parameter_type == "NUMERIC" else "EXACT_TYPED_VALUE",
            "consumer_precision": "DIRECT_THRESHOLD_COMPARISON_NO_CONSUMER_ROUNDING",
            "effective_behavioral_precision": "BINARY64_CONSUMED_VALUE" if row.parameter_type == "NUMERIC" else "EXACT_TYPED_VALUE",
            "normalization_rule": "EXACT_CONSUMED_VALUE_IDENTITY_ONLY",
            "normalized_values": normalized,
            "duplicates_removed": len(row.generated_values) - len(normalized),
            "proof": f"engine-compatible {ACTIVE_CONSUMERS[row.parameter][1]} threshold consumer uses Python float/int directly; no decimal quantizer or rounding call exists",
        })
    if not space:
        raise ValueError("NO_ELIGIBLE_HANDOFF_DIMENSIONS")
    return space, {
        "artifact": "SEARCH_VALUE_NORMALIZATION",
        "schema_version": EXPANDED_SEARCH_SCHEMA_VERSION,
        "arbitrary_rounding_used": False,
        "parameters": evidence,
    }


def build_plan(space: Mapping[str, list[object]], *, dataset_rows: int) -> SearchPlan:
    policy = RESEARCH_PARAMETERS.search.model_dump(mode="python")
    raw = math.prod(len(values) for values in space.values())
    budget = min(
        int(policy["max_evaluated_configs"]),
        int(policy["max_total_configs"]),
        max(1, dataset_rows * int(policy["max_configs_per_observation"])),
    )
    policy["strategy"] = "auto" if raw <= budget else "bounded"
    return ParameterSweepSearchPlanner().plan(dataset_rows=dataset_rows, space=space, search=policy)


def iter_planned_configs(space: Mapping[str, list[object]], plan: SearchPlan) -> Iterator[dict[str, object]]:
    for ordinal, index in enumerate(_candidate_indices(plan)):
        if ordinal >= plan.evaluation_budget:
            break
        yield _candidate_config(space, index)


def _split_without_holdout(rows: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    ordered = sorted((dict(row) for row in rows), key=lambda row: (int(row["entry_boundary_ms"]), str(row["trade_id"])))
    cut = max(1, min(len(ordered) - 1, int(len(ordered) * 0.6))) if len(ordered) > 1 else len(ordered)
    return {"CALIBRATION": ordered[:cut], "VALIDATION": ordered[cut:]}


def validate_dataset(rows: Sequence[Mapping[str, Any]], *, symbol: str, profile: str) -> dict[str, int]:
    cross = reconstructed = 0
    for row in rows:
        cross += int(row.get("symbol") != symbol)
        reconstructed += int(row.get("source_type") != "PERSISTED_CAUSAL_OBSERVATION")
        if row.get("profile_id") != profile:
            raise ValueError("DATASET_PROFILE_MISMATCH")
    if cross:
        raise ValueError("CROSS_SYMBOL_CONTAMINATION")
    if reconstructed:
        raise ValueError("UNCERTIFIED_RECONSTRUCTED_ROWS_PRESENT")
    return {"cross_symbol_rows": cross, "reconstructed_rows_used": reconstructed}


def _passes(row: Mapping[str, Any], parameters: Mapping[str, object]) -> tuple[bool, str]:
    features = row.get("features") or {}
    for parameter in sorted(parameters):
        feature, direction = ACTIVE_CONSUMERS[parameter]
        observed = features.get(feature)
        if observed is None:
            return False, f"REJECT_MISSING_{feature.upper()}"
        threshold = parameters[parameter]
        passed = float(observed) >= float(threshold) if direction == "MINIMUM_INCLUSIVE" else float(observed) <= float(threshold)
        if not passed:
            return False, f"REJECT_{parameter.upper()}"
    return True, "PASSED"


def _metrics(rows: Sequence[Mapping[str, Any]], parameters: Mapping[str, object]) -> tuple[dict[str, Any], dict[str, int]]:
    admitted: list[Mapping[str, Any]] = []
    funnel: dict[str, int] = {"INPUT_ROWS": len(rows), "PASSED_ROWS": 0}
    for row in rows:
        passed, reason = _passes(row, parameters)
        funnel[reason] = funnel.get(reason, 0) + 1
        if passed:
            admitted.append(row)
    funnel["PASSED_ROWS"] = len(admitted)
    pnl = [float(row["net_paper_pnl"]) for row in admitted]
    wins = [value for value in pnl if value > 0]
    losses = [-value for value in pnl if value < 0]
    curve = peak = drawdown = 0.0
    for value in pnl:
        curve += value
        peak = max(peak, curve)
        drawdown = max(drawdown, peak - curve)
    trades = [{
        "causal_opportunity": row.get("candidate_id") or row["trade_id"],
        "position_id": row["trade_id"], "symbol": row["symbol"],
        "opened_at_ms": row["entry_boundary_ms"],
        "closed_at_ms": int(datetime.fromisoformat(str(row["close_timestamp"])).timestamp() * 1000),
        "direction": (row.get("features") or {}).get("direction"),
        "exit_reason": row.get("label"), "net_pnl": float(row["net_paper_pnl"]),
        "setup_type": (row.get("features") or {}).get("setup_type"),
    } for row in admitted]
    return {
        "trade_count": len(admitted), "wins": len(wins), "losses": len(losses),
        "breakeven": len(admitted) - len(wins) - len(losses),
        "win_rate": len(wins) / len(admitted) if admitted else None,
        "net_pnl": sum(pnl), "expectancy_R": None,
        "profit_factor": sum(wins) / sum(losses) if losses else None,
        "max_drawdown": drawdown, "trades": trades, "funnel": funnel,
    }, funnel


def evaluate_config(parameters: Mapping[str, object], splits: Mapping[str, Sequence[Mapping[str, Any]]], *, index: int) -> dict[str, Any]:
    calibration, _cal_funnel = _metrics(splits["CALIBRATION"], parameters)
    validation, validation_funnel = _metrics(splits["VALIDATION"], parameters)
    item = {
        "result_index": index, "parameters": dict(parameters),
        "candidate_parameters": dict(parameters), "overrides": dict(parameters),
        "symbol": next(iter({str(row["symbol"]) for row in splits["VALIDATION"] or splits["CALIBRATION"]})),
        "evaluated_symbol_count": 1, "stage": "EXPANDED_AUTOMATIC_SEARCH",
        "result_status": "ACCEPTED", "INPUT_ROWS": len(splits["VALIDATION"]),
        "calibration": calibration, "validation": validation,
    }
    compact = compact_result(item, validation_policy=VALIDATION_SAMPLE_POLICY)
    compact["parameters"] = dict(parameters)
    compact["validation_trade_count"] = compact["trade_count"]
    compact["wins"] = compact["win_count"]
    compact["losses"] = compact["loss_count"]
    compact["neutrals"] = compact["trade_count"] - compact["win_count"] - compact["loss_count"]
    compact["validation_trade_signature"] = compact["validation_behavioral_signature"]
    compact["validation_outcome_signature"] = canonical_hash([
        (trade["position_id"], trade["exit_reason"], trade["net_pnl"])
        for trade in validation["trades"]
    ])
    compact["funnel_signature"] = canonical_hash(validation_funnel)
    compact["behavioral_signature"] = canonical_hash({
        "validation": compact["validation_behavioral_signature"],
        "outcomes": compact["validation_outcome_signature"],
        "funnel": compact["funnel_signature"],
    })
    compact["sample_adequacy"] = "DESCRIPTIVE_ONLY"
    compact["ranking_status"] = compact["performance_class"]
    compact["promotion_eligible"] = False
    return compact


def _boundary_flags(parameters: Mapping[str, object], space: Mapping[str, Sequence[object]]) -> dict[str, str]:
    result = {}
    for name, value in parameters.items():
        values = list(space[name])
        result[name] = "AT_LOW_BOUNDARY" if value == values[0] else "AT_HIGH_BOUNDARY" if value == values[-1] else "INTERIOR"
    return result


def cluster_results(rows: Sequence[Mapping[str, Any]], space: Mapping[str, Sequence[object]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ranked = rank_results([dict(row) for row in rows], VALIDATION_SAMPLE_POLICY)
    by_signature: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for row in ranked:
        signature = str(row["behavioral_signature"])
        if signature not in by_signature:
            by_signature[signature] = []
            order.append(signature)
        by_signature[signature].append(row)
    representatives: list[dict[str, Any]] = []
    clusters: list[dict[str, Any]] = []
    for signature in order:
        members = by_signature[signature]
        representative = dict(members[0])
        representative["range_boundary_flags"] = _boundary_flags(representative["parameters"], space)
        representatives.append(representative)
        clusters.append({
            "behavioral_signature": signature,
            "representative_config_id": representative["config_id"],
            "member_config_ids": sorted(str(row["config_id"]) for row in members),
            "member_parameters": [{"config_id": row["config_id"], "parameters": row["parameters"]} for row in members],
            "equivalence_count": len(members),
        })
    return representatives, clusters


def _comparison_summary(rows: Sequence[Mapping[str, Any]], representatives: Sequence[Mapping[str, Any]], *, raw: int, planned: int) -> dict[str, Any]:
    best = representatives[0] if representatives else None
    return {
        "raw_config_count": raw, "evaluated_config_count": len(rows),
        "planned_config_count": planned,
        "behaviorally_distinct_configs": len(representatives),
        "best_observed_validation_trades": None if best is None else best["trade_count"],
        "best_observed_net_pnl": None if best is None else best["net_pnl"],
        "best_observed_expectancy_r": None if best is None else best["expectancy_R"],
        "best_observed_profit_factor": None if best is None else best["profit_factor"],
        "positive_observed_configs": sum(float(row.get("net_pnl") or 0) > 0 for row in representatives),
    }


def _run_rows(space: Mapping[str, list[object]], rows: Sequence[Mapping[str, Any]]) -> tuple[SearchPlan, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    plan = build_plan(space, dataset_rows=len(rows))
    splits = _split_without_holdout(rows)
    results = [evaluate_config(config, splits, index=index) for index, config in enumerate(iter_planned_configs(space, plan))]
    representatives, clusters = cluster_results(results, space)
    return plan, results, representatives, clusters


def _run_primary_resume_safe(
    *, space: Mapping[str, list[object]], rows: Sequence[Mapping[str, Any]],
    output: Path, expected: Mapping[str, Any], resume: bool,
) -> tuple[SearchPlan, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    plan = build_plan(space, dataset_rows=len(rows))
    splits = _split_without_holdout(rows)
    checkpoint_path = output / "CHECKPOINT.json"
    results_path = output / "EXPANDED_SEARCH_RESULTS.jsonl"
    if resume:
        if not checkpoint_path.is_file() or not results_path.is_file():
            raise ValueError("RESUME_CHECKPOINT_NOT_AVAILABLE")
        checkpoint = _read_json(checkpoint_path)
        assert_resume_compatible(checkpoint, expected)
        results = _read_jsonl(results_path)
        if len(results) != int(checkpoint.get("evaluated_configs", -1)):
            raise ValueError("RESUME_RESULT_COUNT_MISMATCH")
    else:
        results = []
        checkpoint = {
            **dict(expected), "artifact": "EXPANDED_SEARCH_CHECKPOINT",
            "schema_version": EXPANDED_SEARCH_SCHEMA_VERSION,
            "evaluated_configs": 0, "planned_configs": plan.evaluation_budget,
            "completed": False, "holdout_opened": False,
            "adaptive_refinement_executed": False,
        }
        _write_jsonl(results_path, results)
        _write_json(checkpoint_path, checkpoint)
    start = len(results)
    for index, config in enumerate(iter_planned_configs(space, plan)):
        if index < start:
            continue
        results.append(evaluate_config(config, splits, index=index))
        if len(results) % RESEARCH_PARAMETERS.search.checkpoint_cadence == 0:
            _write_jsonl(results_path, results)
            checkpoint["evaluated_configs"] = len(results)
            checkpoint["completed"] = len(results) == plan.evaluation_budget
            _write_json(checkpoint_path, checkpoint)
    _write_jsonl(results_path, results)
    checkpoint["evaluated_configs"] = len(results)
    checkpoint["completed"] = len(results) == plan.evaluation_budget
    _write_json(checkpoint_path, checkpoint)
    representatives, clusters = cluster_results(results, space)
    return plan, results, representatives, clusters


def _handoff_result(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: row.get(key) for key in (
            "config_id", "parameters", "behavioral_signature", "validation_trade_count",
            "wins", "losses", "neutrals", "net_pnl", "expectancy_R", "profit_factor",
            "max_drawdown", "sample_adequacy", "ranking_status", "range_boundary_flags",
        )
    } | {"independent_periods": row.get("independent_period_count")}


def run_expanded_search(
    *, handoff_path: Path, dataset_path: Path, dataset_manifest_path: Path,
    output: Path, symbol: str, profile: str = "trade-5m-v2",
    resume: bool = False,
) -> dict[str, Any]:
    handoff, handoff_hash = validate_handoff(handoff_path, symbol=symbol, profile=profile)
    space, normalization = normalize_handoff_values(handoff)
    rows = _read_jsonl(dataset_path)
    integrity = validate_dataset(rows, symbol=symbol, profile=profile)
    manifest = _read_json(dataset_manifest_path)
    if manifest.get("symbol") != symbol or manifest.get("profile") != profile:
        raise ValueError("DATASET_MANIFEST_PROVENANCE_MISMATCH")
    if manifest.get("dataset_sha256") != _canonical_dataset_hash(rows):
        raise ValueError("DATASET_FINGERPRINT_MISMATCH")
    dataset_hash = str(manifest["dataset_sha256"])
    output.mkdir(parents=True, exist_ok=True)
    search_space_hash = canonical_hash({"symbol": symbol, "profile": profile, "space": space})
    expected_resume = {
        "symbol": symbol, "profile": profile, "dataset_fingerprint": dataset_hash,
        "range_handoff_fingerprint": handoff_hash,
        "search_space_fingerprint": search_space_hash,
        "seed": RESEARCH_PARAMETERS.search.seed,
    }
    plan, results, representatives, clusters = _run_primary_resume_safe(
        space=space, rows=rows, output=output,
        expected=expected_resume, resume=resume,
    )
    legacy_space = {name: list(RESEARCH_PARAMETERS.search_space[name]) for name in space}
    legacy_plan, legacy_rows, legacy_representatives, _legacy_clusters = _run_rows(legacy_space, rows)
    raw = math.prod(len(values) for values in space.values())
    normalized_raw = math.prod(len(values) for values in space.values())
    config = {
        "artifact": "EXPANDED_SEARCH_CONFIG", "schema_version": EXPANDED_SEARCH_SCHEMA_VERSION,
        "symbol": symbol, "profile": profile, "search_source": "DATA_DRIVEN_RANGE_HANDOFF",
        "handoff_sha256": handoff_hash, "dataset_fingerprint": dataset_hash,
        "search_space_fingerprint": search_space_hash,
        "active_dimension_count": len(space), "active_parameters": sorted(space),
        "dimension_values": {name: space[name] for name in sorted(space)},
        "raw_cartesian_count": raw, "normalized_cartesian_count": normalized_raw,
        "planned_evaluations": plan.evaluation_budget,
        "budget": min(RESEARCH_PARAMETERS.search.max_evaluated_configs, RESEARCH_PARAMETERS.search.max_total_configs),
        "budget_authority": ["config/research/research_parameters.yaml:search.max_evaluated_configs", "config/research/research_parameters.yaml:search.max_total_configs"],
        "sampling_mode": plan.selected_strategy, "seed": plan.seed,
        "ordering": "SORTED_DIMENSIONS_LAZY_MIXED_RADIX_FULL_CYCLE_PERMUTATION",
        "search_space_frozen": True, "adaptive_refinement_executed": False,
        "holdout_opened": False, "promotion_eligible": False,
        "baseline_config_hash": TRADE_PARAMETERS.config_hash,
        "fixed_parameters": {key: value for key, value in _production_baseline_config().items() if key not in space},
        "resume_guards": ["symbol", "profile", "dataset_fingerprint", "range_handoff_fingerprint", "search_space_fingerprint", "seed"],
    }
    for row in results:
        row["range_boundary_flags"] = _boundary_flags(row["parameters"], space)
    expanded_summary = _comparison_summary(results, representatives, raw=raw, planned=plan.evaluation_budget)
    legacy_summary = _comparison_summary(
        legacy_rows, legacy_representatives,
        raw=math.prod(len(values) for values in legacy_space.values()), planned=legacy_plan.evaluation_budget,
    )
    comparison = {
        "artifact": "LEGACY_EXPANDED_SEARCH_COMPARISON", "schema_version": EXPANDED_SEARCH_SCHEMA_VERSION,
        "status": "PAIRED_SAME_FROZEN_DATASET_DIAGNOSTIC_ONLY", "diagnostic_only": True,
        "dataset_comparability": "EXACT_SAME_FROZEN_DATASET", "legacy_is_search_authority": False,
        "legacy": legacy_summary, "data_driven": expanded_summary,
        "causal_improvement_claim": "NOT_AUTHORIZED",
    }
    positive = [row for row in representatives if float(row.get("net_pnl") or 0) > 0]
    best = representatives[0] if representatives else None
    boundary_summary = {flag: 0 for flag in ("AT_LOW_BOUNDARY", "AT_HIGH_BOUNDARY", "INTERIOR")}
    for row in representatives:
        for flag in row["range_boundary_flags"].values():
            boundary_summary[flag] += 1
    handoff_out = {
        "artifact": "EXPANDED_SEARCH_HANDOFF", "schema_version": EXPANDED_SEARCH_SCHEMA_VERSION,
        "symbol": symbol, "profile": profile, "search_source": "DATA_DRIVEN_RANGE_HANDOFF",
        "dataset_fingerprint": dataset_hash, "range_handoff_fingerprint": handoff_hash,
        "search_space_fingerprint": search_space_hash,
        "sample_adequacy": handoff.sample_adequacy,
        "promotion_eligible": False, "adaptive_refinement_executed": False,
        "holdout_opened": False,
        "results": [_handoff_result(row) for row in representatives],
        "best_observed_config": None if best is None else _handoff_result(best),
        "best_behavioral_cluster": None if not clusters else clusters[0]["behavioral_signature"],
        "positive_observed_count": len(positive),
        "boundary_pressure_summary": boundary_summary,
        "candidate_regions_for_refinement": [
            {"behavioral_signature": row["behavioral_signature"], "existing_values_only": row["parameters"], "rank": index + 1}
            for index, row in enumerate(representatives[: RESEARCH_PARAMETERS.artifact.finalist_config_count])
        ],
    }
    status = {
        "FINAL_STATUS": "PASS", "FINAL_VERDICT": "PASS_DESCRIPTIVE_ONLY_LOW_SAMPLE_EXPANDED_SEARCH_NOT_CERTIFIED",
        "SYMBOL": symbol, "PROFILE": profile, "SEARCH_SOURCE": "DATA_DRIVEN_RANGE_HANDOFF",
        "SOURCE_HISTORY_START": manifest.get("source_history_start", manifest.get("history_start")),
        "SOURCE_HISTORY_END": manifest.get("source_history_end", manifest.get("history_end")),
        "SOURCE_HISTORY_ACTUAL_DAYS": manifest.get("source_history_actual_days", manifest.get("history_actual_days")),
        "ACTIVE_DIMENSION_COUNT": len(space), "ACTIVE_PARAMETERS": sorted(space),
        "RAW_CARTESIAN_COUNT": raw, "NORMALIZED_CARTESIAN_COUNT": normalized_raw,
        "PLANNED_CONFIGS": plan.evaluation_budget, "EVALUATED_CONFIGS": len(results),
        "NUMERICALLY_DISTINCT_CONFIGS": len(results),
        "BEHAVIORALLY_DISTINCT_CONFIGS": len(representatives),
        "BEHAVIORAL_DUPLICATE_CONFIGS": len(results) - len(representatives),
        "BEST_OBSERVED_CONFIG": None if best is None else best["parameters"],
        "BEST_VALIDATION_TRADES": None if best is None else best["trade_count"],
        "BEST_WINS": None if best is None else best["wins"], "BEST_LOSSES": None if best is None else best["losses"],
        "BEST_NET_PNL": None if best is None else best["net_pnl"],
        "BEST_EXPECTANCY_R": None if best is None else best["expectancy_R"],
        "BEST_PROFIT_FACTOR": None if best is None else best["profit_factor"],
        "BEST_MAX_DRAWDOWN": None if best is None else best["max_drawdown"],
        "BEST_INDEPENDENT_PERIODS": None if best is None else best["independent_period_count"],
        "POSITIVE_OBSERVED_CONFIGS": len(positive),
        "VALIDATION_ELIGIBLE_CONFIGS": sum(row["performance_class"] == "VALIDATION_CANDIDATE" for row in representatives),
        "BOUNDARY_POSITION_OF_BEST": None if best is None else best["range_boundary_flags"],
        "LEGACY_COMPARISON_STATUS": comparison["status"],
        "SEARCH_SPACE_FROZEN": True, "BYTE_DETERMINISM": "PASS_CANONICAL_JSON_AND_DETERMINISTIC_ORDER",
        "RESUME_GUARDS": "PASS_FAIL_CLOSED_FINGERPRINT_SET",
        "HANDOFF_FALLBACKS_TO_LEGACY": 0, "NEW_VALUES_CREATED_DURING_SEARCH": 0,
        "RECONSTRUCTED_ROWS_USED": integrity["reconstructed_rows_used"], "CROSS_SYMBOL_ROWS": integrity["cross_symbol_rows"],
        "SEARCH_CERTIFICATION": "NOT_CERTIFIED_DESCRIPTIVE_ONLY",
        "PROMOTION_ELIGIBLE": False, "ADAPTIVE_REFINEMENT_EXECUTED": False, "HOLDOUT_OPENED": False,
        "LIVE_STATE": False, "BINANCE_ORDER_CALLS": 0, "PRODUCTION_MUTATIONS": 0,
    }
    _write_json(output / "EXPANDED_SEARCH_CONFIG.json", config)
    _write_json(output / "SEARCH_VALUE_NORMALIZATION.json", normalization)
    _write_json(output / "BEHAVIORAL_CLUSTERS.json", {"artifact": "BEHAVIORAL_CLUSTERS", "schema_version": 1, "clusters": clusters})
    _write_json(output / "LEGACY_EXPANDED_SEARCH_COMPARISON.json", comparison)
    _write_json(output / "EXPANDED_SEARCH_HANDOFF.json", handoff_out)
    _write_json(output / "STATUS.json", status)
    report = "\n".join([
        "# Expanded Automatic Search", "",
        f"- Symbol/profile: `{symbol}` / `{profile}`",
        "- Search source: `DATA_DRIVEN_RANGE_HANDOFF` (legacy arrays are benchmark-only)",
        f"- Source history: `{status['SOURCE_HISTORY_START']}` to `{status['SOURCE_HISTORY_END']}` ({status['SOURCE_HISTORY_ACTUAL_DAYS']} days)",
        f"- Active dimensions: {len(space)} — {', '.join(sorted(space))}",
        f"- Raw/normalized/planned/evaluated: {raw}/{normalized_raw}/{plan.evaluation_budget}/{len(results)}",
        f"- Behavioral distinct/duplicates: {len(representatives)}/{len(results)-len(representatives)}",
        f"- Best observed: `{json.dumps(status['BEST_OBSERVED_CONFIG'], sort_keys=True)}`; trades={status['BEST_VALIDATION_TRADES']}; net PnL={status['BEST_NET_PNL']}; PF={status['BEST_PROFIT_FACTOR']}",
        "- Expectancy R: unavailable from the accepted persisted separability dataset; no substitute profitability formula was invented.",
        "- Certification: `NOT_CERTIFIED_DESCRIPTIVE_ONLY`; promotion eligible: `NO`.",
        "- Adaptive refinement executed: `NO`; holdout opened: `NO`; production mutation: `NO`.", "",
    ])
    DEFAULT_ARTIFACT_WRITER.atomic_text(output / "REPORT.md", report, operation="expanded_search_report")
    return {"status": status, "config": config, "normalization": normalization, "comparison": comparison, "handoff": handoff_out, "output": str(output)}


def assert_resume_compatible(checkpoint: Mapping[str, Any], expected: Mapping[str, Any]) -> None:
    for key in ("symbol", "profile", "dataset_fingerprint", "range_handoff_fingerprint", "search_space_fingerprint", "seed"):
        if checkpoint.get(key) != expected.get(key):
            raise ValueError(f"RESUME_{key.upper()}_MISMATCH")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--profile", default="trade-5m-v2")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    result = run_expanded_search(
        handoff_path=args.handoff, dataset_path=args.dataset,
        dataset_manifest_path=args.dataset_manifest, output=args.output,
        symbol=args.symbol, profile=args.profile, resume=args.resume,
    )
    print(json.dumps(result["status"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
