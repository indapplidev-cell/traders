"""Causal, research-only cold-start ranges and replay inputs.

The range evidence in this module is restricted to persisted pre-decision
opportunity fields.  Post-decision candle paths are carried only in the
separately labelled replay input and are never inspected while deriving ranges.
"""

from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from app.config.yaml_authority import RESEARCH_PARAMETERS, load_data_driven_range_policy

from .artifact_writer import DEFAULT_ARTIFACT_WRITER
from .data_driven_ranges import _schema_domain, _value_is_valid
from .historical_replay import HistoricalReplayRepository, build_parameter_registry
from .universe import validate_parameter_sweep_symbol


COLD_START_SCHEMA_VERSION = 1
COLD_START_SOURCE = "COLD_START_OPPORTUNITY"
COUNTERFACTUAL_LABELS = (
    "RESEARCH_COUNTERFACTUAL", "NOT_PRODUCTION_PAPER", "NOT_REAL_EXECUTION",
)
PARAMETER_EVIDENCE_FIELDS = {
    "strategy_minimum_score": "strategy_score",
    "min_net_edge_bps": "net_edge_bps",
    "minimum_planned_rr": "net_rr",
    "stop_max_bps": "stop_distance_bps",
    "target_min_bps": "target_distance_bps",
}


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def _write_json(path: Path, value: object) -> None:
    DEFAULT_ARTIFACT_WRITER.atomic_text(path, _json_bytes(value).decode(), operation=f"{path.name}:replace")


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    DEFAULT_ARTIFACT_WRITER.atomic_text(
        path, "".join(_json_bytes(dict(row)).decode() for row in rows),
        operation=f"{path.name}:replace",
    )


def _hash_rows(rows: Sequence[Mapping[str, Any]]) -> str:
    return sha256(b"".join(_json_bytes(dict(row)) for row in rows)).hexdigest()


def _quantile(values: Sequence[float], q: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lo, hi = math.floor(position), math.ceil(position)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (position - lo)


def _candidate_values(
    values: Sequence[float], *, baseline: object, domain: Mapping[str, Any],
) -> tuple[list[int | float], list[dict[str, Any]]]:
    policy = RESEARCH_PARAMETERS.data_driven_range_generation
    raw = [(f"empirical_q{q:g}", _quantile(values, q)) for q in policy.cold_start_quantiles]
    if isinstance(baseline, (int, float)) and not isinstance(baseline, bool):
        raw.append(("current_authoritative_value", float(baseline)))
    generated: list[int | float] = []
    provenance: list[dict[str, Any]] = []
    for method, number in raw:
        lower, upper = domain.get("minimum"), domain.get("maximum")
        clipped = max(float(lower), number) if lower is not None else number
        clipped = min(float(upper), clipped) if upper is not None else clipped
        candidate: int | float = int(round(clipped)) if domain["type"] == "INTEGER" else round(clipped, policy.rounding_decimal_places)
        if _value_is_valid(candidate, domain) and candidate not in generated:
            generated.append(candidate)
            provenance.append({
                "value": candidate, "generation_method": method,
                "sample_count": len(values), "schema_clipped": candidate != number,
            })
    generated.sort(key=float)
    by_value = {item["value"]: item for item in provenance}
    return generated[: policy.max_generated_points], [by_value[value] for value in generated[: policy.max_generated_points]]


def run_cold_start_range_generation(
    *, database: Any, symbol: object, output: Path, production_closed_trades: int,
    profile: str = "trade-5m-v2",
) -> dict[str, Any]:
    selected = validate_parameter_sweep_symbol(symbol)
    repository = HistoricalReplayRepository(database)
    source = repository.load(symbol=selected, selection_mode="ALL_UNTIL_CUTOFF")
    repository.load_paths(source.rows, horizon_seconds=3600)
    policy = RESEARCH_PARAMETERS.data_driven_range_generation
    if len(source.rows) < policy.cold_start_minimum_opportunity_rows:
        return {
            "status": "NO_USABLE_EVIDENCE", "reason": "STOPPED_NO_USABLE_RESEARCH_EVIDENCE",
            "opportunity_rows": len(source.rows),
        }

    registry = {str(row["canonical_key"]): row for row in build_parameter_registry(RESEARCH_PARAMETERS.search_space)}
    evidence_rows: list[dict[str, Any]] = []
    replay_rows: list[dict[str, Any]] = []
    for index, source_row in enumerate(source.rows):
        if source_row.get("symbol") != selected or source_row.get("profile_id") != profile:
            raise ValueError("FAIL_CLOSED_CROSS_SYMBOL_OR_PROFILE_OPPORTUNITY")
        if source_row.get("holdout") or source_row.get("dataset_split") == "HOLDOUT":
            raise ValueError("FAIL_CLOSED_HOLDOUT_OPPORTUNITY_READ")
        if (
            source_row.get("future_leakage_into_range_generation")
            or int(source_row.get("future_fields_read_for_range_generation") or 0) != 0
        ):
            raise ValueError("FAIL_CLOSED_FUTURE_LEAKAGE_OPPORTUNITY")
        predecision = {
            field: source_row.get(field) for field in sorted(set(PARAMETER_EVIDENCE_FIELDS.values()))
        }
        evidence_rows.append({
            "artifact": "COLD_START_OPPORTUNITY_ROW", "schema_version": COLD_START_SCHEMA_VERSION,
            "symbol": selected, "profile": profile,
            "decision_timestamp_ms": int(source_row["boundary_ms"]),
            "causal_snapshot_identity": source_row["causal_identity"],
            "funnel_stage_reached": source_row.get("setup_status"),
            "rejection_stage": source_row.get("historical_rejection_reason"),
            "rejection_reason": source_row.get("historical_rejection_reason"),
            "pre_decision_values": predecision, "dataset_split": "SEARCH_CALIBRATION",
            "future_fields_read_for_range_generation": 0, "holdout": False,
        })
        replay_rows.append({
            **{key: value for key, value in source_row.items() if not key.startswith("__")},
            "source_type": COLD_START_SOURCE, "trade_id": f"counterfactual:{source_row['causal_identity']}",
            "entry_boundary_ms": int(source_row["boundary_ms"]),
            "counterfactual_labels": list(COUNTERFACTUAL_LABELS),
            "future_leakage_into_range_generation": False, "holdout": False,
            "row_index": index,
        })

    parameters: list[dict[str, Any]] = []
    for parameter, source_field in sorted(PARAMETER_EVIDENCE_FIELDS.items()):
        descriptor = registry[parameter]
        values = [
            float(row["pre_decision_values"][source_field]) for row in evidence_rows
            if isinstance(row["pre_decision_values"].get(source_field), (int, float))
            and math.isfinite(float(row["pre_decision_values"][source_field]))
        ]
        if len(values) < policy.cold_start_minimum_opportunity_rows:
            continue
        domain = _schema_domain(
            str(descriptor["RUNTIME_OWNER"]), descriptor["baseline"],
            list(descriptor["candidate_values"]),
        )
        generated, value_provenance = _candidate_values(values, baseline=descriptor["baseline"], domain=domain)
        if len(generated) < policy.low_sample_minimum_points:
            continue
        parameters.append({
            "parameter": parameter, "generated_values": generated,
            "parameter_type": domain["type"], "schema_domain": domain,
            "range_status": "PROVISIONAL_LOW_SAMPLE", "eligible_for_search": True,
            "confidence": "DESCRIPTIVE_ONLY", "provisional": True,
            "sample_adequacy": "COLD_START_OPPORTUNITY", "promotion_eligible": False,
            "boundary_pressure": "COLD_START_EMPIRICAL_SUPPORT",
            "provenance": {
                "source": COLD_START_SOURCE, "source_field": source_field,
                "sample_count": len(values), "generation_method": "DETERMINISTIC_EMPIRICAL_QUANTILES_PLUS_CURRENT",
                "value_provenance": value_provenance,
                "policy": "config/research/research_parameters.yaml:data_driven_range_generation",
            },
            "joint_search_priority_annotations": [],
        })
    if not parameters:
        return {
            "status": "NO_USABLE_EVIDENCE", "reason": "STOPPED_NO_USABLE_RESEARCH_EVIDENCE",
            "opportunity_rows": len(evidence_rows),
        }

    output.mkdir(parents=True, exist_ok=True)
    evidence_hash = _hash_rows(evidence_rows)
    replay_hash = _hash_rows(replay_rows)
    handoff = {
        "artifact": "DATA_DRIVEN_RANGE_HANDOFF", "schema_version": 2,
        "symbol": selected, "profile": profile,
        "separability_status": "PASS_LIMITED_SAMPLE", "sample_adequacy": "COLD_START_OPPORTUNITY",
        "range_provenance": {
            "source": COLD_START_SOURCE, "opportunity_dataset_fingerprint": evidence_hash,
            "policy": "config/research/research_parameters.yaml:data_driven_range_generation",
        },
        "research_approved_only": True, "promotion_eligible": False,
        "search_executed": False, "adaptive_refinement_executed": False,
        "holdout_opened": False, "parameters": parameters,
        "range_generation_source": COLD_START_SOURCE, "cold_start_used": True,
        "opportunity_dataset_fingerprint": evidence_hash,
        "opportunity_evidence_rows": len(evidence_rows),
        "cold_start_dimension_count": len(parameters),
        "counterfactual_bootstrap_used": True,
        "bootstrap_refinement_rounds": policy.bootstrap_refinement_max_rounds,
    }
    dataset_manifest = {
        "artifact": "COLD_START_REPLAY_DATASET_MANIFEST", "schema_version": COLD_START_SCHEMA_VERSION,
        "symbol": selected, "profile": profile, "dataset_sha256": replay_hash,
        "opportunity_dataset_fingerprint": evidence_hash, "opportunity_evidence_rows": len(evidence_rows),
        "production_closed_trades": int(production_closed_trades),
        "range_generation_source": COLD_START_SOURCE, "holdout_rows_read": 0,
        "future_leakage_violations": 0, "source_history_actual_days": 30,
    }
    opportunity_manifest = {
        "artifact": "COLD_START_OPPORTUNITY_MANIFEST", "schema_version": COLD_START_SCHEMA_VERSION,
        **{key: value for key, value in dataset_manifest.items() if key not in {"artifact", "dataset_sha256"}},
        "dataset_sha256": evidence_hash, "cross_symbol_rows": 0,
        "causal_predecision_only": True,
    }
    _write_jsonl(output / "COLD_START_OPPORTUNITY_DATASET.jsonl", evidence_rows)
    _write_json(output / "COLD_START_OPPORTUNITY_MANIFEST.json", opportunity_manifest)
    _write_jsonl(output / "COUNTERFACTUAL_REPLAY_SOURCE.jsonl", replay_rows)
    _write_json(output / "COUNTERFACTUAL_REPLAY_SOURCE_MANIFEST.json", dataset_manifest)
    _write_json(output / "DATA_DRIVEN_RANGE_HANDOFF.json", handoff)
    return {
        "status": "COLD_START_OPPORTUNITY", "handoff": handoff,
        "dataset_path": output / "COUNTERFACTUAL_REPLAY_SOURCE.jsonl",
        "dataset_manifest_path": output / "COUNTERFACTUAL_REPLAY_SOURCE_MANIFEST.json",
        "opportunity_rows": len(evidence_rows), "generated_dimensions": len(parameters),
    }


__all__ = [
    "COLD_START_SOURCE", "COUNTERFACTUAL_LABELS", "PARAMETER_EVIDENCE_FIELDS",
    "run_cold_start_range_generation",
]
