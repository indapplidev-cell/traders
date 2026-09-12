"""Eligibility-first, holdout-blind validation ranking for one symbol."""

from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from app.config.yaml_authority import (
    RESEARCH_PATH,
    ValidationSamplePolicy,
    load_research_parameters,
    load_validation_sample_policy,
)

from .adaptive_refinement import _aggregate_fingerprint
from .artifact_v2 import canonical_hash
from .expanded_search import (
    _canonical_dataset_hash,
    _read_json,
    _read_jsonl,
    _split_without_holdout,
    validate_dataset,
)
from .finalist_freeze import validation_ranking_handoff_fingerprint
from .historical_replay import build_parameter_registry
from .ranking import rank_results
from .symbol_authority_audit import build_symbol_runtime_authority_audit
from .universe import validate_parameter_sweep_symbol
from .artifact_writer import DEFAULT_ARTIFACT_WRITER


SCHEMA_VERSION = 1
CANONICAL_RANKING_COMPARATOR = (
    "expectancy_R DESC; profit_factor ranking value DESC; max_drawdown ASC; "
    "min(trade_count, validation_minimum_trades) DESC; symbol_coverage DESC; "
    "rank_stability DESC; config_id DESC"
)
RANKING_POLICY_ID = "EXISTING_CANONICAL_RESEARCH_RANKING_UNCHANGED"
POSITIVE_INFINITY_MARKER = "+INFINITY"


class ValidationRankingError(RuntimeError):
    """Stable fail-closed validation-ranking failure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _required(row: Mapping[str, Any], key: str) -> Any:
    if key not in row:
        raise ValidationRankingError(f"FAIL_CLOSED_MISSING_CANONICAL_FIELD_{key.upper()}")
    return row[key]


def _file_sha256(path: Path) -> str:
    if not path.is_file():
        raise ValidationRankingError(f"FAIL_CLOSED_MISSING_INPUT_{path.name.upper()}")
    return sha256(path.read_bytes()).hexdigest()


def _safe_json(path: Path) -> dict[str, Any]:
    try:
        value = _read_json(path)
    except (OSError, json.JSONDecodeError, TypeError) as error:
        raise ValidationRankingError(f"FAIL_CLOSED_INVALID_INPUT_{path.name.upper()}") from error
    if not isinstance(value, dict):
        raise ValidationRankingError(f"FAIL_CLOSED_INVALID_INPUT_{path.name.upper()}")
    return value


def _safe_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ValidationRankingError(f"FAIL_CLOSED_MISSING_INPUT_{path.name.upper()}")
    try:
        rows = _read_jsonl(path)
    except (OSError, json.JSONDecodeError, TypeError) as error:
        raise ValidationRankingError(f"FAIL_CLOSED_INVALID_INPUT_{path.name.upper()}") from error
    if any(not isinstance(row, dict) for row in rows):
        raise ValidationRankingError(f"FAIL_CLOSED_INVALID_INPUT_{path.name.upper()}")
    return rows


def validation_policy_payload(policy: ValidationSamplePolicy) -> dict[str, Any]:
    """Fingerprintable policy plus the pre-existing non-numeric readiness gates."""
    return {
        "minimum_validation_trades": policy.minimum_validation_trades,
        "minimum_independent_periods": policy.minimum_independent_periods,
        "independent_period_unit": policy.independent_period_unit,
        "typed_authority": policy.artifact_fields(),
        "existing_artifact_readiness_gates": {
            "evaluation_status": {
                "required": "ACCEPTED",
                "source": "traders_ml/parameter_sweep/ranking.py:rank_results",
            },
            "symbol_coverage": {
                "required": 1,
                "source": "traders_ml/parameter_sweep/artifact_v2.py:compact_result",
            },
            "minimum_slice_count": {
                "required": 2,
                "source": "traders_ml/parameter_sweep/artifact_v2.py:compact_result",
            },
            "setup_coverage": {
                "required": 1,
                "source": "traders_ml/parameter_sweep/artifact_v2.py:_readiness_from_projection",
            },
        },
    }


def ranking_policy_payload() -> dict[str, Any]:
    return {
        "policy_id": RANKING_POLICY_ID,
        "comparator": CANONICAL_RANKING_COMPARATOR,
        "implementation": "traders_ml/parameter_sweep/ranking.py:rank_results",
        "positive_zero_loss_pf_ranking_value": POSITIVE_INFINITY_MARKER,
        "other_missing_pf_ranking_value": 0,
        "stored_profit_factor_mutated": False,
    }


def policy_fingerprints(policy: ValidationSamplePolicy) -> tuple[str, str]:
    return canonical_hash(validation_policy_payload(policy)), canonical_hash(ranking_policy_payload())


def profit_factor_ranking_semantics(row: Mapping[str, Any]) -> tuple[float, float | str, str]:
    stored = _required(row, "profit_factor")
    wins = int(_required(row, "wins"))
    losses = int(_required(row, "losses"))
    net_pnl = float(_required(row, "net_pnl"))
    if stored is not None:
        numeric = float(stored)
        return numeric, numeric, "STORED_PROFIT_FACTOR"
    if wins > 0 and losses == 0 and net_pnl > 0:
        return math.inf, POSITIVE_INFINITY_MARKER, "POSITIVE_ZERO_LOSS_RANKING_ONLY_SURROGATE"
    return 0.0, 0, "OTHER_MISSING_PROFIT_FACTOR_ZERO_SENTINEL"


def validation_eligibility(
    row: Mapping[str, Any], policy: ValidationSamplePolicy,
) -> dict[str, Any]:
    """Resolve all established readiness gates before any ranking selection."""
    required = (
        "config_id", "behavioral_signature", "validation_trade_count", "trade_count",
        "independent_period_count", "independent_period_unit", "symbol_coverage",
        "symbol_coverage_pass", "minimum_slice_count", "setup_coverage",
        "evaluation_status", "wins", "losses", "neutrals", "net_pnl",
        "expectancy_R", "profit_factor", "max_drawdown", "parameters",
    )
    for key in required:
        _required(row, key)
    if int(row["validation_trade_count"]) != int(row["trade_count"]):
        raise ValidationRankingError("FAIL_CLOSED_VALIDATION_TRADE_COUNT_MISMATCH")
    if row["independent_period_unit"] != policy.independent_period_unit:
        raise ValidationRankingError("FAIL_CLOSED_INDEPENDENT_PERIOD_UNIT_MISMATCH")
    gates = {
        "evaluation_status": {
            "current": row["evaluation_status"], "required": "ACCEPTED",
            "pass": row["evaluation_status"] == "ACCEPTED", "classification": "EXISTING_GATE",
        },
        "validation_trade_count": {
            "current": int(row["validation_trade_count"]),
            "required": policy.minimum_validation_trades,
            "pass": int(row["validation_trade_count"]) >= policy.minimum_validation_trades,
            "classification": "EXISTING_GATE",
        },
        "independent_period_count": {
            "current": row["independent_period_count"],
            "required": policy.minimum_independent_periods,
            "pass": row["independent_period_count"] is not None
            and int(row["independent_period_count"]) >= policy.minimum_independent_periods,
            "classification": "EXISTING_GATE",
        },
        "symbol_coverage": {
            "current": int(row["symbol_coverage"]), "required": 1,
            "pass": row["symbol_coverage_pass"] is True and int(row["symbol_coverage"]) == 1,
            "classification": "EXISTING_GATE",
        },
        "minimum_slice_count": {
            "current": int(row["minimum_slice_count"]), "required": 2,
            "pass": int(row["minimum_slice_count"]) >= 2, "classification": "EXISTING_GATE",
        },
        "setup_coverage": {
            "current": int(row["setup_coverage"]), "required": 1,
            "pass": int(row["setup_coverage"]) >= 1, "classification": "EXISTING_GATE",
        },
    }
    failures = [name for name, gate in gates.items() if not gate["pass"]]
    if not failures:
        status = "VALIDATION_ELIGIBLE"
    elif len(failures) > 1:
        status = "MULTIPLE_READINESS_FAILURES"
    elif failures[0] == "validation_trade_count":
        status = "INSUFFICIENT_TRADES"
    elif failures[0] == "independent_period_count":
        status = "INSUFFICIENT_INDEPENDENT_PERIODS"
    else:
        status = "INSUFFICIENT_OTHER_CANONICAL_GATE"
    return {
        "config_id": str(row["config_id"]),
        "behavioral_signature": str(row["behavioral_signature"]),
        "validation_trade_count": int(row["validation_trade_count"]),
        "required_validation_trade_count": policy.minimum_validation_trades,
        "independent_period_count": row["independent_period_count"],
        "required_independent_period_count": policy.minimum_independent_periods,
        "independent_period_unit": policy.independent_period_unit,
        "canonical_gate_results": gates,
        "gate_results": gates,
        "validation_eligible": not failures,
        "validation_status": status,
        "ineligibility_reasons": failures,
    }


def robustness_diagnostics(row: Mapping[str, Any]) -> dict[str, Any]:
    trades = int(row["validation_trade_count"])
    periods = int(row["independent_period_count"] or 0)
    buckets = list(row.get("independent_period_buckets") or [])
    if not trades:
        maximum, share, distribution = 0, None, {}
    elif periods == 1 and len(buckets) == 1:
        maximum, share, distribution = trades, 1.0, {str(buckets[0]): trades}
    elif trades == periods and len(buckets) == periods:
        maximum, share = 1, 1.0 / trades
        distribution = {str(bucket): 1 for bucket in buckets}
    else:
        maximum, share = None, None
        distribution = "NOT_AVAILABLE_FROM_ACCEPTED_COMPACT_ARTIFACT"
    return {
        "independent_period_count": periods,
        "independent_period_buckets": buckets,
        "direction_coverage": row.get("direction_coverage"),
        "setup_coverage": int(row["setup_coverage"]),
        "regime_coverage": int(row.get("regime_coverage") or 0),
        "slice_count": int(row["minimum_slice_count"]),
        "trade_distribution_by_period": distribution,
        "max_trades_in_one_period": maximum,
        "share_of_trades_in_largest_period": share,
        "number_of_non_empty_periods": periods,
        "classification": {
            "independent_period_count": "EXISTING_GATE",
            "setup_coverage": "EXISTING_GATE",
            "slice_count": "EXISTING_GATE",
            "direction_coverage": "DIAGNOSTIC_ONLY",
            "regime_coverage": "DIAGNOSTIC_ONLY",
            "temporal_concentration": "DIAGNOSTIC_ONLY",
        },
    }


def _rank_projection(
    row: Mapping[str, Any], eligibility: Mapping[str, Any], *, rank: int, lane: str,
) -> dict[str, Any]:
    _numeric_pf, serialized_pf, reason = profit_factor_ranking_semantics(row)
    return {
        "canonical_rank": rank,
        "canonical_validation_rank": rank,
        "ranking_lane": lane,
        "config_id": str(row["config_id"]),
        "behavioral_signature": str(row["behavioral_signature"]),
        "parameters": dict(row["parameters"]),
        "validation_trade_count": int(row["validation_trade_count"]),
        "wins": int(row["wins"]), "losses": int(row["losses"]),
        "neutrals": int(row["neutrals"]), "net_pnl": row["net_pnl"],
        "expectancy_r": row["expectancy_R"],
        "stored_profit_factor": row["profit_factor"],
        "profit_factor_available": row["profit_factor"] is not None,
        "profit_factor_ranking_value": serialized_pf,
        "profit_factor_ranking_reason": reason,
        "max_drawdown": row["max_drawdown"],
        "independent_periods": int(row["independent_period_count"] or 0),
        "symbol_coverage": int(row["symbol_coverage"]),
        "rank_stability": float(row.get("rank_stability") or 0),
        "canonical_gate_results": dict(eligibility["canonical_gate_results"]),
        "validation_status": eligibility["validation_status"],
        "validation_eligible": eligibility["validation_eligible"],
        "ineligibility_reasons": list(eligibility["ineligibility_reasons"]),
        "robustness_diagnostics": robustness_diagnostics(row),
    }


def _behavioral_representatives(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    order: list[str] = []
    for row in rows:
        signature = str(row["behavioral_signature"])
        if signature not in groups:
            order.append(signature)
        groups[signature].append(row)
    output: list[dict[str, Any]] = []
    for rank, signature in enumerate(order, 1):
        members = groups[signature]
        representative = dict(members[0])
        representative.update({
            "canonical_rank": rank,
            "canonical_validation_rank": rank,
            "representative_config_id": representative["config_id"],
            "member_config_ids": [str(row["config_id"]) for row in members],
            "numeric_member_count": len(members),
        })
        output.append(representative)
    return output


def build_validation_rankings(
    rows: Sequence[Mapping[str, Any]], policy: ValidationSamplePolicy,
) -> dict[str, Any]:
    records = [validation_eligibility(row, policy) for row in rows]
    by_id = {str(record["config_id"]): record for record in records}
    accepted = [dict(row) for row in rows if row["evaluation_status"] == "ACCEPTED"]
    eligible_source = [row for row in accepted if by_id[str(row["config_id"])]["validation_eligible"]]
    descriptive_source = [row for row in accepted if not by_id[str(row["config_id"])]["validation_eligible"]]
    eligible_ranked = rank_results(eligible_source, policy)
    descriptive_ranked = rank_results(descriptive_source, policy)
    eligible_numeric = [
        _rank_projection(row, by_id[str(row["config_id"])], rank=index, lane="ELIGIBLE_VALIDATION_RANKING")
        for index, row in enumerate(eligible_ranked, 1)
    ]
    descriptive_numeric = [
        _rank_projection(row, by_id[str(row["config_id"])], rank=index, lane="DESCRIPTIVE_NON_ELIGIBLE_RANKING")
        for index, row in enumerate(descriptive_ranked, 1)
    ]
    eligible_behavioral = _behavioral_representatives(eligible_numeric)
    descriptive_behavioral = _behavioral_representatives(descriptive_numeric)
    positive = [row for row in accepted if float(row["net_pnl"] or 0) > 0]
    return {
        "eligibility": records,
        "eligible_numeric": eligible_numeric,
        "descriptive_numeric": descriptive_numeric,
        "eligible_behavioral": eligible_behavioral,
        "descriptive_behavioral": descriptive_behavioral,
        "positive_numeric_count": len(positive),
        "positive_behavioral_count": len({str(row["behavioral_signature"]) for row in positive}),
        "excluded_non_accepted_count": len(rows) - len(accepted),
    }


def _validate_campaign(
    *, symbol: object, profile: str, research_parameters_path: Path,
    range_handoff_path: Path, expanded_config_path: Path,
    expanded_handoff_path: Path, expanded_clusters_path: Path,
    expanded_results_path: Path, normalization_path: Path,
    adaptive_config_path: Path, adaptive_handoff_path: Path,
    adaptive_clusters_path: Path, adaptive_results_path: Path,
    dataset_path: Path, dataset_manifest_path: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], dict[str, Any]]:
    selected = validate_parameter_sweep_symbol(symbol)
    research = load_research_parameters(research_parameters_path)
    policy = load_validation_sample_policy(research_parameters_path)
    range_handoff = _safe_json(range_handoff_path)
    expanded_config = _safe_json(expanded_config_path)
    expanded_handoff = _safe_json(expanded_handoff_path)
    expanded_clusters = _safe_json(expanded_clusters_path)
    normalization = _safe_json(normalization_path)
    adaptive_config = _safe_json(adaptive_config_path)
    adaptive_handoff = _safe_json(adaptive_handoff_path)
    adaptive_clusters = _safe_json(adaptive_clusters_path)
    expanded_results = _safe_jsonl(expanded_results_path)
    adaptive_results = _safe_jsonl(adaptive_results_path)
    dataset_rows = _safe_jsonl(dataset_path)
    manifest = _safe_json(dataset_manifest_path)
    try:
        dataset_counts = validate_dataset(dataset_rows, symbol=selected, profile=profile)
    except ValueError as error:
        raise ValidationRankingError(f"FAIL_CLOSED_{error}") from error
    dataset_fingerprint = _canonical_dataset_hash(dataset_rows)
    if manifest.get("symbol") != selected or manifest.get("profile") != profile:
        raise ValidationRankingError("FAIL_CLOSED_DATASET_MANIFEST_IDENTITY_MISMATCH")
    if manifest.get("dataset_sha256") != dataset_fingerprint:
        raise ValidationRankingError("FAIL_CLOSED_DATASET_FINGERPRINT_MISMATCH")
    for artifact in (range_handoff, expanded_config, expanded_handoff, adaptive_handoff):
        if artifact.get("symbol") != selected or artifact.get("profile") != profile:
            raise ValidationRankingError("FAIL_CLOSED_CAMPAIGN_IDENTITY_MISMATCH")
    if adaptive_config.get("campaign_inputs") != adaptive_handoff.get("campaign_inputs"):
        raise ValidationRankingError("FAIL_CLOSED_ADAPTIVE_CAMPAIGN_INPUT_MISMATCH")
    inputs = adaptive_handoff.get("campaign_inputs")
    if not isinstance(inputs, dict):
        raise ValidationRankingError("FAIL_CLOSED_ADAPTIVE_CAMPAIGN_INPUT_MISSING")
    split = _split_without_holdout(dataset_rows)
    split_fingerprints = {
        "calibration": canonical_hash(split["CALIBRATION"]),
        "validation": canonical_hash(split["VALIDATION"]),
    }
    range_fingerprint = _file_sha256(range_handoff_path)
    expanded_fingerprint = _aggregate_fingerprint([
        expanded_config_path, expanded_handoff_path, expanded_clusters_path,
        expanded_results_path, normalization_path,
    ])
    parameter_registry_fingerprint = canonical_hash(build_parameter_registry(research.search_space))
    expected_inputs = {
        "symbol": selected, "profile": profile,
        "dataset_fingerprint": dataset_fingerprint,
        "calibration_split_fingerprint": split_fingerprints["calibration"],
        "validation_split_fingerprint": split_fingerprints["validation"],
        "parameter_registry_version": parameter_registry_fingerprint,
        "range_handoff_fingerprint": range_fingerprint,
        "expanded_search_fingerprint": expanded_fingerprint,
    }
    for key, expected in expected_inputs.items():
        if inputs.get(key) != expected:
            raise ValidationRankingError(f"FAIL_CLOSED_{key.upper()}_MISMATCH")
    if expanded_config.get("dataset_fingerprint") != dataset_fingerprint or expanded_handoff.get("dataset_fingerprint") != dataset_fingerprint:
        raise ValidationRankingError("FAIL_CLOSED_EXPANDED_DATASET_FINGERPRINT_MISMATCH")
    if expanded_config.get("handoff_sha256") != range_fingerprint or expanded_handoff.get("range_handoff_fingerprint") != range_fingerprint:
        raise ValidationRankingError("FAIL_CLOSED_RANGE_HANDOFF_FINGERPRINT_MISMATCH")
    declared_policy = adaptive_handoff.get("validation_policy")
    expected_policy = {
        "minimum_trades": policy.minimum_validation_trades,
        "minimum_independent_periods": policy.minimum_independent_periods,
        "independent_period_unit": policy.independent_period_unit,
    }
    if declared_policy != expected_policy:
        raise ValidationRankingError("FAIL_CLOSED_VALIDATION_POLICY_MISMATCH")
    if adaptive_handoff.get("ranking_policy") != RANKING_POLICY_ID:
        raise ValidationRankingError("FAIL_CLOSED_RANKING_POLICY_MISMATCH")
    combined = [dict(row) for row in expanded_results] + [dict(row) for row in adaptive_results]
    ids = [str(row.get("config_id")) for row in combined]
    if len(ids) != len(set(ids)):
        raise ValidationRankingError("FAIL_CLOSED_DUPLICATE_NUMERIC_CONFIG_ID")
    groups: dict[str, list[str]] = defaultdict(list)
    for row in combined:
        if row.get("symbol") != selected:
            raise ValidationRankingError("FAIL_CLOSED_CROSS_SYMBOL_RESULT")
        groups[str(_required(row, "behavioral_signature"))].append(str(_required(row, "config_id")))
    cluster_rows = adaptive_clusters.get("clusters")
    if adaptive_clusters.get("artifact") != "ADAPTIVE_BEHAVIORAL_CLUSTERS" or not isinstance(cluster_rows, list):
        raise ValidationRankingError("FAIL_CLOSED_ADAPTIVE_CLUSTER_ARTIFACT_INVALID")
    cluster_by_signature = {str(row.get("behavioral_signature")): row for row in cluster_rows}
    if set(cluster_by_signature) != set(groups) or len(cluster_by_signature) != len(cluster_rows):
        raise ValidationRankingError("FAIL_CLOSED_ADAPTIVE_CLUSTER_TOPOLOGY_MISMATCH")
    for signature, member_ids in groups.items():
        cluster = cluster_by_signature[signature]
        if sorted(str(item) for item in cluster.get("member_config_ids", [])) != sorted(member_ids):
            raise ValidationRankingError("FAIL_CLOSED_ADAPTIVE_CLUSTER_MEMBERSHIP_MISMATCH")
        if str(cluster.get("representative_config_id")) not in member_ids:
            raise ValidationRankingError("FAIL_CLOSED_ADAPTIVE_CLUSTER_REPRESENTATIVE_MISMATCH")
    handoff_clusters = adaptive_handoff.get("clusters")
    if not isinstance(handoff_clusters, list) or {
        str(row.get("behavioral_signature")) for row in handoff_clusters
    } != set(groups):
        raise ValidationRankingError("FAIL_CLOSED_ADAPTIVE_HANDOFF_CLUSTER_MISMATCH")
    validation_fp, ranking_fp = policy_fingerprints(policy)
    metadata = {
        "symbol": selected, "profile": profile,
        "dataset_fingerprint": dataset_fingerprint,
        "calibration_split_fingerprint": split_fingerprints["calibration"],
        "validation_split_fingerprint": split_fingerprints["validation"],
        "validation_policy_fingerprint": validation_fp,
        "ranking_policy_fingerprint": ranking_fp,
        "parameter_registry_fingerprint": parameter_registry_fingerprint,
        "range_handoff_fingerprint": range_fingerprint,
        "expanded_search_fingerprint": expanded_fingerprint,
        "adaptive_handoff_fingerprint": _file_sha256(adaptive_handoff_path),
        "adaptive_clusters_fingerprint": _file_sha256(adaptive_clusters_path),
        "adaptive_results_fingerprint": _file_sha256(adaptive_results_path),
        "source_history_start": manifest.get("source_history_start"),
        "source_history_end": manifest.get("source_history_end"),
        "source_history_actual_days": manifest.get("source_history_actual_days"),
        "cross_symbol_rows": dataset_counts["cross_symbol_rows"],
        "reconstructed_rows_used": dataset_counts["reconstructed_rows_used"],
    }
    return combined, manifest, metadata, validation_policy_payload(policy)


def _write_outputs(
    *, output: Path, rankings: Mapping[str, Any], metadata: Mapping[str, Any],
    policy_payload: Mapping[str, Any], symbol_audit: Mapping[str, Any],
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    eligible_numeric = rankings["eligible_numeric"]
    descriptive_numeric = rankings["descriptive_numeric"]
    eligible_behavioral = rankings["eligible_behavioral"]
    descriptive_behavioral = rankings["descriptive_behavioral"]
    handoff = {
        "artifact": "VALIDATION_RANKING_HANDOFF", "schema_version": SCHEMA_VERSION,
        **{key: metadata[key] for key in (
            "symbol", "profile", "dataset_fingerprint", "calibration_split_fingerprint",
            "validation_split_fingerprint", "validation_policy_fingerprint",
            "ranking_policy_fingerprint", "parameter_registry_fingerprint",
            "range_handoff_fingerprint", "expanded_search_fingerprint",
            "adaptive_handoff_fingerprint", "adaptive_clusters_fingerprint",
            "adaptive_results_fingerprint",
        )},
        "validation_policy": dict(policy_payload),
        "ranking_policy": ranking_policy_payload(),
        "eligible_numeric_count": len(eligible_numeric),
        "eligible_behavioral_count": len(eligible_behavioral),
        "descriptive_numeric_count": len(descriptive_numeric),
        "descriptive_behavioral_count": len(descriptive_behavioral),
        "eligible_behavioral_candidates": eligible_behavioral,
        "eligible_behavioral_representatives": eligible_behavioral,
        "descriptive_non_eligible_ranking": descriptive_behavioral,
        "holdout_reads": 0, "holdout_opened": False,
        "finalist_freeze_executed": False, "promotion_eligible": False,
    }
    handoff["validation_ranking_handoff_fingerprint"] = validation_ranking_handoff_fingerprint(handoff)
    numeric_artifact = {
        "artifact": "VALIDATION_NUMERIC_RANKING", "schema_version": SCHEMA_VERSION,
        "canonical_ranking_comparator": CANONICAL_RANKING_COMPARATOR,
        "eligible_validation_ranking": eligible_numeric,
        "descriptive_non_eligible_ranking": descriptive_numeric,
    }
    behavioral_artifact = {
        "artifact": "VALIDATION_BEHAVIORAL_RANKING", "schema_version": SCHEMA_VERSION,
        "representative_rule": "HIGHEST_CANONICAL_RANKED_NUMERIC_MEMBER_WITHIN_ELIGIBILITY_LANE",
        "eligible_validation_ranking": eligible_behavioral,
        "descriptive_non_eligible_ranking": descriptive_behavioral,
    }
    robustness = {
        "artifact": "VALIDATION_ROBUSTNESS", "schema_version": SCHEMA_VERSION,
        "eligibility_gates_unchanged": True, "diagnostics_add_no_gate": True,
        "eligible_behavioral": [
            {
                "behavioral_signature": row["behavioral_signature"],
                "representative_config_id": row["representative_config_id"],
                "robustness_diagnostics": row["robustness_diagnostics"],
            }
            for row in eligible_behavioral
        ],
        "descriptive_behavioral": [
            {
                "behavioral_signature": row["behavioral_signature"],
                "representative_config_id": row["representative_config_id"],
                "robustness_diagnostics": row["robustness_diagnostics"],
            }
            for row in descriptive_behavioral
        ],
    }
    top_eligible = eligible_behavioral[0] if eligible_behavioral else None
    top_descriptive = descriptive_behavioral[0] if descriptive_behavioral else None
    status = {
        "FINAL_STATUS": "PASS",
        "FINAL_VERDICT": "PASS_ELIGIBILITY_FIRST_VALIDATION_RANKING_HANDOFF_CREATED",
        "state": "COMPLETED",
        "updated_at": metadata["source_history_end"],
        "symbol": metadata["symbol"],
        "research_phase": "VALIDATION_RANKING",
        "holdout_status": "UNTOUCHED",
        "finalists_frozen": False,
        "finalist_count": 0,
        "holdout_opened": False,
        "holdout_evaluated": False,
        "SYMBOL": metadata["symbol"], "PROFILE": metadata["profile"],
        "SYMBOL_AUTHORITY_SOURCE": symbol_audit["symbol_authority_source"],
        "RUNTIME_SYMBOL_HARDCODES": symbol_audit["RUNTIME_SYMBOL_HARDCODES"],
        "RUNTIME_SYMBOL_DEFAULTS": symbol_audit["RUNTIME_SYMBOL_DEFAULTS"],
        "RUNTIME_SYMBOL_BRANCHES": symbol_audit["RUNTIME_SYMBOL_BRANCHES"],
        "SOURCE_HISTORY_START": metadata["source_history_start"],
        "SOURCE_HISTORY_END": metadata["source_history_end"],
        "SOURCE_HISTORY_ACTUAL_DAYS": metadata["source_history_actual_days"],
        "VALIDATION_POLICY_SOURCE": "config/research/research_parameters.yaml:ranking",
        "VALIDATION_MINIMUM_TRADES": policy_payload["minimum_validation_trades"],
        "MINIMUM_INDEPENDENT_PERIODS": policy_payload["minimum_independent_periods"],
        "INDEPENDENT_PERIOD_UNIT": policy_payload["independent_period_unit"],
        "CANONICAL_RANKING_COMPARATOR": CANONICAL_RANKING_COMPARATOR,
        "TOTAL_NUMERIC_CONFIGS": len(eligible_numeric) + len(descriptive_numeric),
        "TOTAL_BEHAVIORAL_CLUSTERS": len({
            row["behavioral_signature"] for row in [*eligible_numeric, *descriptive_numeric]
        }),
        "ELIGIBLE_NUMERIC_CONFIGS": len(eligible_numeric),
        "ELIGIBLE_BEHAVIORAL_CLUSTERS": len(eligible_behavioral),
        "DESCRIPTIVE_NUMERIC_CONFIGS": len(descriptive_numeric),
        "DESCRIPTIVE_BEHAVIORAL_CLUSTERS": len(descriptive_behavioral),
        "POSITIVE_NUMERIC_CONFIGS": rankings["positive_numeric_count"],
        "POSITIVE_BEHAVIORAL_CLUSTERS": rankings["positive_behavioral_count"],
        "TOP_ELIGIBLE_CONFIG": None if top_eligible is None else top_eligible["representative_config_id"],
        "TOP_ELIGIBLE_SIGNATURE": None if top_eligible is None else top_eligible["behavioral_signature"],
        "TOP_DESCRIPTIVE_CONFIG": None if top_descriptive is None else top_descriptive["representative_config_id"],
        "TOP_DESCRIPTIVE_SIGNATURE": None if top_descriptive is None else top_descriptive["behavioral_signature"],
        "TOP_DESCRIPTIVE_TRADES": None if top_descriptive is None else top_descriptive["validation_trade_count"],
        "TOP_DESCRIPTIVE_PERIODS": None if top_descriptive is None else top_descriptive["independent_periods"],
        "TOP_DESCRIPTIVE_NET_PNL": None if top_descriptive is None else top_descriptive["net_pnl"],
        "TOP_DESCRIPTIVE_STORED_PF": None if top_descriptive is None else top_descriptive["stored_profit_factor"],
        "TOP_DESCRIPTIVE_PF_AVAILABLE": None if top_descriptive is None else top_descriptive["profit_factor_available"],
        "TOP_DESCRIPTIVE_PF_RANKING_VALUE": None if top_descriptive is None else top_descriptive["profit_factor_ranking_value"],
        "ZERO_LOSS_RANKING_SURROGATE_SEMANTICS": "wins>0 AND losses=0 AND net_pnl>0 AND stored_PF=NOT_AVAILABLE => ranking-only +INFINITY",
        "STORED_PF_MUTATED": False,
        "EXPECTANCY_AVAILABILITY": "NOT_AVAILABLE_PRESERVED_WHERE_SOURCE_IS_NULL",
        "VALIDATION_RANKING_HANDOFF_CREATED": True,
        "validation_ranking_eligible_numeric": len(eligible_numeric),
        "validation_ranking_eligible_behavioral": len(eligible_behavioral),
        "validation_ranking_descriptive_behavioral": len(descriptive_behavioral),
        "validation_ranking_top_eligible": None if top_eligible is None else top_eligible["representative_config_id"],
        "validation_ranking_top_descriptive": None if top_descriptive is None else top_descriptive["representative_config_id"],
        "VALIDATION_RANKING_HANDOFF_FINGERPRINT": handoff["validation_ranking_handoff_fingerprint"],
        "HOLDOUT_READS": 0, "HOLDOUT_OPENED": False,
        "FINALIST_FREEZE_EXECUTED": False, "ADAPTIVE_REFINEMENT_EXECUTED": False,
        "EXPANDED_SEARCH_RERUN": False, "RANKING_CHANGED": False,
        "VALIDATION_20_3_CHANGED": False, "SCHEMA_VIOLATIONS": 0,
        "GATE_FALLBACKS": 0, "CROSS_SYMBOL_ROWS": metadata["cross_symbol_rows"],
        "RECONSTRUCTED_ROWS_USED": metadata["reconstructed_rows_used"],
        "PROMOTION_ELIGIBLE": False, "LIVE_STATE": False,
        "BINANCE_ORDER_CALLS": 0, "PRODUCTION_MUTATIONS": 0,
        "RESUME_GUARDS": [
            "symbol", "profile", "dataset_fingerprint", "calibration_split_fingerprint",
            "validation_split_fingerprint", "validation_policy_fingerprint",
            "ranking_policy_fingerprint", "parameter_registry_fingerprint",
            "range_handoff_fingerprint", "expanded_search_fingerprint",
            "adaptive_handoff_fingerprint", "adaptive_clusters_fingerprint",
            "adaptive_results_fingerprint",
        ],
    }
    report = "\n".join([
        "# Validation Ranking", "",
        f"- Symbol/profile: `{metadata['symbol']}` / `{metadata['profile']}`",
        f"- Eligible numeric/behavioral: `{len(eligible_numeric)}` / `{len(eligible_behavioral)}`",
        f"- Descriptive numeric/behavioral: `{len(descriptive_numeric)}` / `{len(descriptive_behavioral)}`",
        f"- Top eligible: `{status['TOP_ELIGIBLE_CONFIG'] or 'NONE'}`",
        f"- Top descriptive: `{status['TOP_DESCRIPTIVE_CONFIG'] or 'NONE'}`",
        f"- Readiness gates: trades `{policy_payload['minimum_validation_trades']}`, periods `{policy_payload['minimum_independent_periods']}` `{policy_payload['independent_period_unit']}`",
        "- Holdout: `NOT OPENED`; Finalist Freeze: `NOT EXECUTED`", "",
    ])
    DEFAULT_ARTIFACT_WRITER.atomic_text(
        output / "VALIDATION_ELIGIBILITY.jsonl",
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rankings["eligibility"]),
        operation="validation_eligibility",
    )
    for name, value in (
        ("VALIDATION_NUMERIC_RANKING.json", numeric_artifact),
        ("VALIDATION_BEHAVIORAL_RANKING.json", behavioral_artifact),
        ("VALIDATION_ROBUSTNESS.json", robustness),
        ("VALIDATION_RANKING_HANDOFF.json", handoff),
        ("STATUS.json", status),
    ):
        DEFAULT_ARTIFACT_WRITER.atomic_json(output / name, value, operation="validation_ranking")
    DEFAULT_ARTIFACT_WRITER.atomic_text(output / "REPORT.md", report, operation="validation_ranking_report")
    return {"status": status, "handoff": handoff, "output": str(output)}


def run_validation_ranking(
    *, symbol: object, profile: str, output: Path,
    range_handoff_path: Path, expanded_config_path: Path,
    expanded_handoff_path: Path, expanded_clusters_path: Path,
    expanded_results_path: Path, normalization_path: Path,
    adaptive_config_path: Path, adaptive_handoff_path: Path,
    adaptive_clusters_path: Path, adaptive_results_path: Path,
    dataset_path: Path, dataset_manifest_path: Path,
    research_parameters_path: Path = RESEARCH_PATH,
) -> dict[str, Any]:
    rows, _manifest, metadata, policy_payload = _validate_campaign(
        symbol=symbol, profile=profile, research_parameters_path=research_parameters_path,
        range_handoff_path=range_handoff_path, expanded_config_path=expanded_config_path,
        expanded_handoff_path=expanded_handoff_path, expanded_clusters_path=expanded_clusters_path,
        expanded_results_path=expanded_results_path, normalization_path=normalization_path,
        adaptive_config_path=adaptive_config_path, adaptive_handoff_path=adaptive_handoff_path,
        adaptive_clusters_path=adaptive_clusters_path, adaptive_results_path=adaptive_results_path,
        dataset_path=dataset_path, dataset_manifest_path=dataset_manifest_path,
    )
    policy = load_validation_sample_policy(research_parameters_path)
    rankings = build_validation_rankings(rows, policy)
    symbol_audit = build_symbol_runtime_authority_audit()
    if symbol_audit["symbol_binding_status"] != "PASS":
        raise ValidationRankingError("FAIL_CLOSED_RUNTIME_SYMBOL_AUTHORITY")
    return _write_outputs(
        output=output, rankings=rankings, metadata=metadata,
        policy_payload=policy_payload, symbol_audit=symbol_audit,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--profile", default="trade-5m-v2")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--range-handoff", type=Path, required=True)
    parser.add_argument("--expanded-config", type=Path, required=True)
    parser.add_argument("--expanded-handoff", type=Path, required=True)
    parser.add_argument("--expanded-clusters", type=Path, required=True)
    parser.add_argument("--expanded-results", type=Path, required=True)
    parser.add_argument("--normalization", type=Path, required=True)
    parser.add_argument("--adaptive-config", type=Path, required=True)
    parser.add_argument("--adaptive-handoff", type=Path, required=True)
    parser.add_argument("--adaptive-clusters", type=Path, required=True)
    parser.add_argument("--adaptive-results", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--research-parameters", type=Path, default=RESEARCH_PATH)
    args = parser.parse_args(argv)
    result = run_validation_ranking(
        symbol=args.symbol, profile=args.profile, output=args.output,
        range_handoff_path=args.range_handoff, expanded_config_path=args.expanded_config,
        expanded_handoff_path=args.expanded_handoff, expanded_clusters_path=args.expanded_clusters,
        expanded_results_path=args.expanded_results, normalization_path=args.normalization,
        adaptive_config_path=args.adaptive_config, adaptive_handoff_path=args.adaptive_handoff,
        adaptive_clusters_path=args.adaptive_clusters, adaptive_results_path=args.adaptive_results,
        dataset_path=args.dataset, dataset_manifest_path=args.dataset_manifest,
        research_parameters_path=args.research_parameters,
    )
    print(json.dumps(result["status"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
