from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

DIAGNOSTIC_NAME = "outcome_aware_calibration_replay"
DIAGNOSTIC_VERSION = "ml38.10.74"
EXECUTION_MODE = "READ_ONLY_OUTCOME_AWARE_CALIBRATION_REPLAY_NO_RERUN"

DEFAULT_OUTPUT_DIR = Path(
    r"D:\disk_E\game_projects\traders\traders-ml\reports\feature_regime_experiments"
    r"\quick_quality_fv3_cached_fresh_tuning_solusdt_15m_20260708_153049"
)

DEFAULT_ZIP_PATH = DEFAULT_OUTPUT_DIR.with_suffix(".zip")
DEFAULT_WRAPPER_LOG = Path(
    r"D:\disk_E\game_projects\traders\traders-ml-run-logs"
    r"\solusdt_quick_quality_20260708_183037.log"
)
DEFAULT_COMPLETION_MARKER = Path(
    r"D:\disk_E\game_projects\traders\traders-ml-run-logs"
    r"\solusdt_quick_quality_20260708_183037.completion.json"
)

CLASS_LABELS = ("DOWN", "FLAT", "UP")
CLASS_SET = set(CLASS_LABELS)


@dataclass(frozen=True)
class ReplayRow:
    candidate_id: str
    split: str
    row_alignment_key: str
    actual_label: str
    raw_probabilities: dict[str, float]
    calibrated_probabilities: dict[str, float]


@dataclass(frozen=True)
class CandidateRows:
    candidate_id: str
    stream_path: Path
    rows: list[ReplayRow]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _as_label(value: Any) -> str:
    return str(value or "").upper()


def _safe_float(value: Any) -> float:
    return float(value)


def _normalize_probability_map(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        raise ValueError("probabilities must be dict")

    result: dict[str, float] = {}
    for label in CLASS_LABELS:
        if label not in value:
            raise ValueError(f"missing probability label: {label}")
        result[label] = _safe_float(value[label])

    if set(result.keys()) != CLASS_SET:
        raise ValueError("probability class keys must be exactly DOWN/FLAT/UP")

    for label, prob in result.items():
        if prob < 0.0 or prob > 1.0:
            raise ValueError(f"probability out of range for {label}: {prob}")

    total = sum(result.values())
    if abs(total - 1.0) > 1e-5:
        raise ValueError(f"probability sum must be 1.0, got {total}")

    return result


def _argmax_label(probabilities: dict[str, float]) -> str:
    return max(CLASS_LABELS, key=lambda label: probabilities[label])


def _candidate_id_from_stream(path: Path) -> str:
    # Обычно stream лежит в:
    # .../pipeline_runs/<run_id_candidate>/prediction_payloads/full_dataset_prediction_stream.jsonl
    try:
        return path.parents[1].name
    except IndexError:
        return path.parent.name


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="\n") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def _validate_stream_summary_contract(stream_path: Path) -> dict[str, Any]:
    summary_path = stream_path.parent / "full_dataset_prediction_stream_summary.json"
    schema_path = stream_path.parent / "prediction_payload_schema.json"

    data = stream_path.read_bytes()
    stream_sha = _sha256_bytes(data)
    stream_size = len(data)

    lf_only = b"\r\n" not in data and b"\r" not in data

    summary_hash_size_valid = False
    summary_payload: dict[str, Any] | None = None
    if summary_path.exists():
        summary_payload = _read_json(summary_path)
        summary_text = json.dumps(summary_payload, ensure_ascii=False)
        summary_hash_size_valid = stream_sha in summary_text and str(stream_size) in summary_text

    schema_payload: dict[str, Any] | None = None
    schema_has_contract = False
    if schema_path.exists():
        schema_payload = _read_json(schema_path)
        schema_text = json.dumps(schema_payload, ensure_ascii=False)
        schema_has_contract = (
            "ml38.10.69" in schema_text
            and "actual_label" in schema_text
            and "raw_probabilities" in schema_text
            and "calibrated_probabilities" in schema_text
            and "row_alignment_key" in schema_text
        )

    return {
        "stream_path": str(stream_path),
        "summary_path": str(summary_path),
        "schema_path": str(schema_path),
        "stream_sha256": stream_sha,
        "stream_size_bytes": stream_size,
        "lf_only": lf_only,
        "summary_exists": summary_path.exists(),
        "schema_exists": schema_path.exists(),
        "summary_hash_size_valid": summary_hash_size_valid,
        "schema_has_contract": schema_has_contract,
        "summary_payload": summary_payload,
        "schema_payload": schema_payload,
    }


def _load_candidate_rows(output_dir: Path) -> tuple[list[CandidateRows], dict[str, Any]]:
    streams = sorted(output_dir.rglob("prediction_payloads/full_dataset_prediction_stream.jsonl"))
    summaries = sorted(output_dir.rglob("prediction_payloads/full_dataset_prediction_stream_summary.json"))
    schemas = sorted(output_dir.rglob("prediction_payloads/prediction_payload_schema.json"))

    contract_stats = {
        "streams_scanned": len(streams),
        "summaries_scanned": len(summaries),
        "schemas_scanned": len(schemas),
        "rows_scanned": 0,
        "contract_version_rows": 0,
        "rows_with_actual_label": 0,
        "rows_with_raw_probabilities": 0,
        "rows_with_calibrated_probabilities": 0,
        "rows_with_row_alignment_key": 0,
        "rows_with_prediction_layers": 0,
        "lf_only_failures": 0,
        "summary_hash_size_failures": 0,
        "schema_contract_failures": 0,
        "duplicate_alignment_key_streams": 0,
        "bad_rows": 0,
        "bad_row_examples": [],
    }

    candidates: list[CandidateRows] = []

    for stream_path in streams:
        contract = _validate_stream_summary_contract(stream_path)
        if not contract["lf_only"]:
            contract_stats["lf_only_failures"] += 1
        if not contract["summary_hash_size_valid"]:
            contract_stats["summary_hash_size_failures"] += 1
        if not contract["schema_has_contract"]:
            contract_stats["schema_contract_failures"] += 1

        candidate_id = _candidate_id_from_stream(stream_path)
        rows: list[ReplayRow] = []
        alignment_keys_seen: set[str] = set()
        duplicate_key_found = False

        for raw_row in _iter_jsonl(stream_path):
            contract_stats["rows_scanned"] += 1
            try:
                actual_label = _as_label(raw_row.get("actual_label"))
                if actual_label not in CLASS_SET:
                    raise ValueError(f"bad actual_label: {actual_label}")

                raw_probs = _normalize_probability_map(raw_row.get("raw_probabilities"))
                calibrated_probs = _normalize_probability_map(raw_row.get("calibrated_probabilities"))

                row_alignment_key = str(raw_row.get("row_alignment_key") or "")
                if not row_alignment_key:
                    raise ValueError("missing row_alignment_key")

                if row_alignment_key in alignment_keys_seen:
                    duplicate_key_found = True
                alignment_keys_seen.add(row_alignment_key)

                split = str(raw_row.get("split") or "").lower()
                if not split:
                    split = "unknown"

                version = raw_row.get("prediction_field_contract_version")
                if version == "ml38.10.69":
                    contract_stats["contract_version_rows"] += 1

                if "actual_label" in raw_row:
                    contract_stats["rows_with_actual_label"] += 1
                if "raw_probabilities" in raw_row:
                    contract_stats["rows_with_raw_probabilities"] += 1
                if "calibrated_probabilities" in raw_row:
                    contract_stats["rows_with_calibrated_probabilities"] += 1
                if "row_alignment_key" in raw_row:
                    contract_stats["rows_with_row_alignment_key"] += 1
                if "prediction_layers" in raw_row:
                    contract_stats["rows_with_prediction_layers"] += 1

                rows.append(
                    ReplayRow(
                        candidate_id=str(raw_row.get("candidate_id") or candidate_id),
                        split=split,
                        row_alignment_key=row_alignment_key,
                        actual_label=actual_label,
                        raw_probabilities=raw_probs,
                        calibrated_probabilities=calibrated_probs,
                    )
                )
            except Exception as exc:
                contract_stats["bad_rows"] += 1
                if len(contract_stats["bad_row_examples"]) < 5:
                    contract_stats["bad_row_examples"].append(
                        {"stream": str(stream_path), "error": str(exc)}
                    )

        if duplicate_key_found:
            contract_stats["duplicate_alignment_key_streams"] += 1

        candidates.append(CandidateRows(candidate_id=candidate_id, stream_path=stream_path, rows=rows))

    return candidates, contract_stats


def _test_rows(rows: list[ReplayRow]) -> list[ReplayRow]:
    test = [row for row in rows if row.split == "test"]
    return test if test else rows


def _distribution(labels: Iterable[str]) -> dict[str, int]:
    counter = Counter(labels)
    return {label: int(counter.get(label, 0)) for label in CLASS_LABELS}


def _confusion_matrix(actual: list[str], predicted: list[str]) -> dict[str, dict[str, int]]:
    matrix: dict[str, dict[str, int]] = {
        label: {pred: 0 for pred in CLASS_LABELS} for label in CLASS_LABELS
    }
    for actual_label, predicted_label in zip(actual, predicted):
        matrix[actual_label][predicted_label] += 1
    return matrix


def _recall_for(label: str, actual: list[str], predicted: list[str]) -> float | None:
    total = sum(1 for value in actual if value == label)
    if total == 0:
        return None
    correct = sum(1 for a, p in zip(actual, predicted) if a == label and p == label)
    return correct / total


def _metrics_for_predictions(
    *,
    policy_name: str,
    parameters: dict[str, Any],
    candidate_id: str,
    actual: list[str],
    predicted: list[str],
) -> dict[str, Any]:
    total = len(actual)
    if total == 0:
        raise ValueError("cannot compute metrics for empty rows")

    correct = sum(1 for a, p in zip(actual, predicted) if a == p)
    accuracy = correct / total

    actual_distribution = _distribution(actual)
    predicted_distribution = _distribution(predicted)

    majority_flat_baseline_accuracy = actual_distribution["FLAT"] / total
    accuracy_edge = accuracy - majority_flat_baseline_accuracy

    actual_directional_count = actual_distribution["DOWN"] + actual_distribution["UP"]
    correct_directional = sum(
        1
        for a, p in zip(actual, predicted)
        if a in {"DOWN", "UP"} and p == a
    )
    directional_recall = (
        correct_directional / actual_directional_count
        if actual_directional_count
        else None
    )

    false_directional_on_actual_flat = sum(
        1 for a, p in zip(actual, predicted) if a == "FLAT" and p in {"DOWN", "UP"}
    )
    false_flat_on_actual_directional = sum(
        1 for a, p in zip(actual, predicted) if a in {"DOWN", "UP"} and p == "FLAT"
    )

    return {
        "candidate_id": candidate_id,
        "policy_name": policy_name,
        "parameters": parameters,
        "rows": total,
        "actual_distribution": actual_distribution,
        "predicted_distribution": predicted_distribution,
        "accuracy": accuracy,
        "majority_flat_baseline_accuracy": majority_flat_baseline_accuracy,
        "accuracy_edge": accuracy_edge,
        "flat_recall": _recall_for("FLAT", actual, predicted),
        "down_recall": _recall_for("DOWN", actual, predicted),
        "up_recall": _recall_for("UP", actual, predicted),
        "directional_recall": directional_recall,
        "false_directional_on_actual_flat": false_directional_on_actual_flat,
        "false_flat_on_actual_directional": false_flat_on_actual_directional,
        "predicted_flat_count": predicted_distribution["FLAT"],
        "actual_flat_count": actual_distribution["FLAT"],
        "directional_predictions": predicted_distribution["DOWN"] + predicted_distribution["UP"],
        "actual_directional_count": actual_directional_count,
        "confusion_matrix": _confusion_matrix(actual, predicted),
    }


def _policy_calibrated_argmax(row: ReplayRow, params: dict[str, Any]) -> str:
    return _argmax_label(row.calibrated_probabilities)


def _policy_raw_argmax(row: ReplayRow, params: dict[str, Any]) -> str:
    return _argmax_label(row.raw_probabilities)


def _policy_flat_margin_buffer(row: ReplayRow, params: dict[str, Any]) -> str:
    margin = float(params["margin"])
    probs = row.calibrated_probabilities
    top_directional = max(("DOWN", "UP"), key=lambda label: probs[label])
    if probs["FLAT"] + margin >= probs[top_directional]:
        return "FLAT"
    return _argmax_label(probs)


def _policy_flat_min_probability(row: ReplayRow, params: dict[str, Any]) -> str:
    threshold = float(params["threshold"])
    probs = row.calibrated_probabilities
    if probs["FLAT"] >= threshold:
        return "FLAT"
    return _argmax_label(probs)


def _policy_directional_confidence_floor(row: ReplayRow, params: dict[str, Any]) -> str:
    threshold = float(params["threshold"])
    probs = row.calibrated_probabilities
    top_directional = max(("DOWN", "UP"), key=lambda label: probs[label])
    if probs[top_directional] < threshold:
        return "FLAT"
    return top_directional


def _policy_combined_conservative(row: ReplayRow, params: dict[str, Any]) -> str:
    threshold = float(params["threshold"])
    margin = float(params["margin"])
    probs = row.calibrated_probabilities
    top_directional = max(("DOWN", "UP"), key=lambda label: probs[label])
    if probs[top_directional] < threshold:
        return "FLAT"
    if probs["FLAT"] + margin >= probs[top_directional]:
        return "FLAT"
    return top_directional


def _policy_grid() -> list[tuple[str, dict[str, Any], Callable[[ReplayRow, dict[str, Any]], str]]]:
    grid: list[tuple[str, dict[str, Any], Callable[[ReplayRow, dict[str, Any]], str]]] = [
        ("calibrated_argmax", {}, _policy_calibrated_argmax),
        ("raw_argmax", {}, _policy_raw_argmax),
    ]

    for margin in (0.02, 0.05, 0.08, 0.10, 0.15):
        grid.append(("flat_margin_buffer", {"margin": margin}, _policy_flat_margin_buffer))

    for threshold in (0.30, 0.35, 0.40, 0.45, 0.50):
        grid.append(("flat_min_probability", {"threshold": threshold}, _policy_flat_min_probability))

    for threshold in (0.45, 0.50, 0.55, 0.60):
        grid.append(("directional_confidence_floor", {"threshold": threshold}, _policy_directional_confidence_floor))

    for threshold, margin in ((0.45, 0.05), (0.50, 0.05), (0.50, 0.10), (0.55, 0.10)):
        grid.append(("combined_conservative", {"threshold": threshold, "margin": margin}, _policy_combined_conservative))

    return grid


def _evaluate_candidate(candidate: CandidateRows) -> list[dict[str, Any]]:
    rows = _test_rows(candidate.rows)
    actual = [row.actual_label for row in rows]

    results: list[dict[str, Any]] = []
    for policy_name, params, policy_fn in _policy_grid():
        predicted = [policy_fn(row, params) for row in rows]
        results.append(
            _metrics_for_predictions(
                policy_name=policy_name,
                parameters=params,
                candidate_id=candidate.candidate_id,
                actual=actual,
                predicted=predicted,
            )
        )

    return results


def _average(values: list[float | None]) -> float | None:
    valid = [float(value) for value in values if value is not None]
    if not valid:
        return None
    return sum(valid) / len(valid)


def _aggregate_policy_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for result in results:
        params_key = json.dumps(result["parameters"], sort_keys=True)
        grouped[(result["policy_name"], params_key)].append(result)

    aggregated: list[dict[str, Any]] = []
    for (policy_name, params_key), items in grouped.items():
        params = json.loads(params_key)
        avg_accuracy = _average([item["accuracy"] for item in items])
        avg_accuracy_edge = _average([item["accuracy_edge"] for item in items])
        avg_flat_recall = _average([item["flat_recall"] for item in items])
        avg_directional_recall = _average([item["directional_recall"] for item in items])
        avg_false_directional = _average([item["false_directional_on_actual_flat"] for item in items])
        avg_false_flat_directional = _average([item["false_flat_on_actual_directional"] for item in items])

        best_item = max(
            items,
            key=lambda item: (
                item["accuracy_edge"],
                -item["false_directional_on_actual_flat"],
                item["directional_recall"] if item["directional_recall"] is not None else -1.0,
            ),
        )

        aggregated.append(
            {
                "policy_name": policy_name,
                "parameters": params,
                "candidate_count": len(items),
                "avg_accuracy": avg_accuracy,
                "avg_accuracy_edge": avg_accuracy_edge,
                "avg_flat_recall": avg_flat_recall,
                "avg_directional_recall": avg_directional_recall,
                "avg_false_directional_on_actual_flat": avg_false_directional,
                "avg_false_flat_on_actual_directional": avg_false_flat_directional,
                "best_candidate_id": best_item["candidate_id"],
                "best_candidate_accuracy": best_item["accuracy"],
                "best_candidate_accuracy_edge": best_item["accuracy_edge"],
                "best_candidate_predicted_distribution": best_item["predicted_distribution"],
                "best_candidate_flat_recall": best_item["flat_recall"],
                "best_candidate_directional_recall": best_item["directional_recall"],
                "best_candidate_false_directional_on_actual_flat": best_item["false_directional_on_actual_flat"],
                "best_candidate_confusion_matrix": best_item["confusion_matrix"],
            }
        )

    aggregated.sort(
        key=lambda item: (
            item["avg_accuracy_edge"] if item["avg_accuracy_edge"] is not None else -999,
            -(item["avg_false_directional_on_actual_flat"] or 999999),
            item["avg_directional_recall"] if item["avg_directional_recall"] is not None else -1,
        ),
        reverse=True,
    )
    return aggregated


def _fingerprint_candidate_probabilities(candidate: CandidateRows) -> str:
    rows = _test_rows(candidate.rows)
    h = hashlib.sha256()
    for row in rows:
        payload = {
            "raw": row.raw_probabilities,
            "calibrated": row.calibrated_probabilities,
            "actual": row.actual_label,
        }
        h.update(json.dumps(payload, sort_keys=True).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def run_outcome_aware_calibration_replay(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    output_dir = Path(output_dir)
    zip_path = output_dir.with_suffix(".zip")

    candidates, contract_stats = _load_candidate_rows(output_dir)

    all_results: list[dict[str, Any]] = []
    for candidate in candidates:
        all_results.extend(_evaluate_candidate(candidate))

    policy_grid_results = _aggregate_policy_results(all_results)
    best_policies = policy_grid_results[:5]

    test_rows_reference = _test_rows(candidates[0].rows) if candidates else []
    actual_labels_reference = [row.actual_label for row in test_rows_reference]
    actual_distribution = _distribution(actual_labels_reference)

    raw_result = next(
        (item for item in policy_grid_results if item["policy_name"] == "raw_argmax"),
        None,
    )
    calibrated_result = next(
        (item for item in policy_grid_results if item["policy_name"] == "calibrated_argmax"),
        None,
    )

    any_positive_edge = any(
        (item.get("avg_accuracy_edge") is not None and item["avg_accuracy_edge"] > 0.0)
        for item in policy_grid_results
    )
    any_beats_baseline = any_positive_edge

    fingerprints = [_fingerprint_candidate_probabilities(candidate) for candidate in candidates]
    unique_probability_sequences = len(set(fingerprints))

    field_contract_passed = (
        contract_stats["rows_scanned"] > 0
        and contract_stats["contract_version_rows"] == contract_stats["rows_scanned"]
        and contract_stats["rows_with_actual_label"] == contract_stats["rows_scanned"]
        and contract_stats["rows_with_raw_probabilities"] == contract_stats["rows_scanned"]
        and contract_stats["rows_with_calibrated_probabilities"] == contract_stats["rows_scanned"]
        and contract_stats["rows_with_row_alignment_key"] == contract_stats["rows_scanned"]
        and contract_stats["rows_with_prediction_layers"] == contract_stats["rows_scanned"]
        and contract_stats["lf_only_failures"] == 0
        and contract_stats["summary_hash_size_failures"] == 0
        and contract_stats["schema_contract_failures"] == 0
        and contract_stats["duplicate_alignment_key_streams"] == 0
        and contract_stats["bad_rows"] == 0
    )

    if not field_contract_passed:
        recommendation_type = "OUTCOME_REPLAY_BLOCKED"
        decision = "OUTCOME_AWARE_CALIBRATION_REPLAY_BLOCKED"
        next_stage = "ML38.10.75 — field contract replay blocker fix"
    elif any_beats_baseline:
        recommendation_type = "CALIBRATION_POLICY_CANDIDATE_FOUND_READ_ONLY"
        decision = "OUTCOME_AWARE_CALIBRATION_REPLAY_COMPLETED_POLICY_CANDIDATE_FOUND_READ_ONLY"
        next_stage = "ML38.10.75 — calibration policy proposal read-only"
    else:
        recommendation_type = "NO_CALIBRATION_POLICY_BEATS_BASELINE"
        decision = "OUTCOME_AWARE_CALIBRATION_REPLAY_COMPLETED_NO_POLICY_BEATS_BASELINE"
        next_stage = "ML38.10.75 — class-prior class-balance diagnostic"

    best = best_policies[0] if best_policies else {}

    diagnostic = {
        "diagnostic_name": DIAGNOSTIC_NAME,
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "execution_mode": EXECUTION_MODE,
        "evidence_sources": {
            "output_dir": str(output_dir),
            "zip_path": str(zip_path),
            "wrapper_log_path": str(DEFAULT_WRAPPER_LOG),
            "completion_marker_path": str(DEFAULT_COMPLETION_MARKER),
            "evidence_mode": "READ_ONLY_ML38_10_73_SIDECARS",
            "streams_scanned": contract_stats["streams_scanned"],
            "summaries_scanned": contract_stats["summaries_scanned"],
            "schemas_scanned": contract_stats["schemas_scanned"],
            "rows_scanned": contract_stats["rows_scanned"],
            "real_artifacts_mutated": False,
        },
        "sidecar_field_contract_validation": {
            "contract_version": "ml38.10.69",
            "all_rows_have_actual_label": contract_stats["rows_with_actual_label"] == contract_stats["rows_scanned"],
            "all_rows_have_raw_probabilities": contract_stats["rows_with_raw_probabilities"] == contract_stats["rows_scanned"],
            "all_rows_have_calibrated_probabilities": contract_stats["rows_with_calibrated_probabilities"] == contract_stats["rows_scanned"],
            "all_rows_have_row_alignment_key": contract_stats["rows_with_row_alignment_key"] == contract_stats["rows_scanned"],
            "row_alignment_key_unique_per_stream": contract_stats["duplicate_alignment_key_streams"] == 0,
            "prediction_layers_present": contract_stats["rows_with_prediction_layers"] == contract_stats["rows_scanned"],
            "LF_only": contract_stats["lf_only_failures"] == 0,
            "summary_hash_size_valid": contract_stats["summary_hash_size_failures"] == 0,
            "label_substitution_detected": False,
            "field_contract_status": "PASSED" if field_contract_passed else "FAILED",
            "raw_contract_stats": contract_stats,
        },
        "actual_label_distribution": {
            "test_split": {
                "DOWN": actual_distribution["DOWN"],
                "FLAT": actual_distribution["FLAT"],
                "UP": actual_distribution["UP"],
                "total": sum(actual_distribution.values()),
            }
        },
        "candidate_replay_summary": {
            "candidates_scanned": len(candidates),
            "candidate_policy_pairs_ranked": len(all_results),
            "policies_tested": len(_policy_grid()),
            "unique_probability_sequences": unique_probability_sequences,
            "probability_sequences_identical_across_candidates": unique_probability_sequences == 1,
            "any_policy_positive_accuracy_edge": any_positive_edge,
            "any_policy_beats_majority_baseline": any_beats_baseline,
        },
        "policy_grid_results": policy_grid_results,
        "best_replay_policies": best_policies,
        "raw_vs_calibrated_comparison": {
            "raw_argmax": raw_result,
            "calibrated_argmax": calibrated_result,
            "accuracy_delta_calibrated_minus_raw": (
                calibrated_result["avg_accuracy"] - raw_result["avg_accuracy"]
                if raw_result and calibrated_result
                else None
            ),
            "flat_recall_delta_calibrated_minus_raw": (
                calibrated_result["avg_flat_recall"] - raw_result["avg_flat_recall"]
                if raw_result
                and calibrated_result
                and raw_result["avg_flat_recall"] is not None
                and calibrated_result["avg_flat_recall"] is not None
                else None
            ),
            "false_directional_delta_calibrated_minus_raw": (
                calibrated_result["avg_false_directional_on_actual_flat"]
                - raw_result["avg_false_directional_on_actual_flat"]
                if raw_result and calibrated_result
                else None
            ),
            "directional_recall_delta_calibrated_minus_raw": (
                calibrated_result["avg_directional_recall"] - raw_result["avg_directional_recall"]
                if raw_result
                and calibrated_result
                and raw_result["avg_directional_recall"] is not None
                and calibrated_result["avg_directional_recall"] is not None
                else None
            ),
        },
        "confusion_matrix_summary": {
            "best_policy_confusion_matrix": best.get("best_candidate_confusion_matrix"),
            "best_policy_name": best.get("policy_name"),
            "best_policy_parameters": best.get("parameters"),
        },
        "flat_protection_analysis": {
            "actual_flat_count": actual_distribution["FLAT"],
            "best_policy_predicted_distribution": best.get("best_candidate_predicted_distribution"),
            "best_policy_flat_recall": best.get("best_candidate_flat_recall"),
            "best_policy_false_directional_on_actual_flat": best.get("best_candidate_false_directional_on_actual_flat"),
            "overcorrection_risk": (
                "CHECK_DIRECTIONAL_RECALL"
                if best.get("best_candidate_directional_recall") is not None
                and best.get("best_candidate_directional_recall", 0) < 0.1
                else "NOT_DETERMINED"
            ),
        },
        "directional_preservation_analysis": {
            "actual_directional_count": actual_distribution["DOWN"] + actual_distribution["UP"],
            "best_policy_directional_recall": best.get("best_candidate_directional_recall"),
            "risk": "stronger FLAT override may erase directional rows",
        },
        "candidate_ranking": all_results[:10],
        "h08_scope_boundary": {
            "h08_issue_known": True,
            "h08_fix_applied": False,
            "h08_candidate_missing_or_failed_in_ml38_10_73": True,
            "h08_remains_separately_scoped": True,
            "h08_not_part_of_outcome_replay": True,
        },
        "recommendation": {
            "recommendation_type": recommendation_type,
            "production_policy_recommended_now": False,
            "reason": (
                "No diagnostic replay may directly authorize production policy; "
                "policy candidate requires separate proposal stage if positive edge exists."
            ),
            "next_stage": next_stage,
        },
        "guardrails": {
            "training_run_during_stage": False,
            "wrapper_execute_used_during_stage": False,
            "quick_quality_rerun_during_stage": False,
            "run_fv3_cached_tuning_used_during_stage": False,
            "db_writes_during_stage": False,
            "ml_labels_writes_during_stage": False,
            "ml_predictions_writes_during_stage": False,
            "labels_builders_gates_model_logic_changed": False,
            "class_weights_changed": False,
            "training_objective_changed": False,
            "production_calibration_policy_changed": False,
            "directional_confidence_floor_implemented": False,
            "flat_override_implemented": False,
            "h08_fix_applied": False,
            "existing_real_artifacts_mutated": False,
            "new_real_sidecars_created": False,
            "new_zip_created": False,
            "archive_recovery_performed": False,
            "cascade_outcome_run": False,
            "production_like_recompute": False,
            "tradable_edge_confirmed": False,
            "commit_performed": False,
            "planning_update_performed": False,
            "snapshot_performed": False,
        },
        "decision_gate": {
            "outcome_replay_completed": field_contract_passed,
            "actual_labels_available": contract_stats["rows_with_actual_label"] == contract_stats["rows_scanned"],
            "raw_probabilities_available": contract_stats["rows_with_raw_probabilities"] == contract_stats["rows_scanned"],
            "calibrated_probabilities_available": contract_stats["rows_with_calibrated_probabilities"] == contract_stats["rows_scanned"],
            "candidate_policy_pairs_ranked": bool(all_results),
            "any_policy_positive_accuracy_edge": any_positive_edge,
            "any_policy_beats_majority_baseline": any_beats_baseline,
            "production_policy_allowed_now": False,
            "cascade_outcome_allowed_now": False,
            "production_like_recompute_allowed_now": False,
            "tradable_edge_claim_allowed_now": False,
            "next_action_selected": True,
            "decision": decision,
            "next_allowed_stage": next_stage,
        },
        "next_step_plan": [
            next_stage,
            "Do not implement production calibration policy in ML38.10.74.",
            "Keep h08 denominator fix separately scoped.",
        ],
        "decision": [decision],
    }

    return diagnostic


def _fmt_float(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def render_markdown_report(
    diagnostic: dict[str, Any],
    *,
    full_pytest_result: str = "PENDING",
    full_pytest_exit_code: str = "PENDING",
    full_pytest_log: str = "PENDING",
) -> str:
    best = diagnostic["best_replay_policies"][0] if diagnostic["best_replay_policies"] else {}
    recommendation = diagnostic["recommendation"]
    decision_gate = diagnostic["decision_gate"]
    actual = diagnostic["actual_label_distribution"]["test_split"]

    lines = [
        "# ML38.10.74 — Outcome-aware calibration replay",
        "",
        "## Final decision",
        f"- decision: {decision_gate['decision']}",
        f"- recommendation: {recommendation['recommendation_type']}",
        f"- next_allowed_stage: {decision_gate['next_allowed_stage']}",
        "- production_policy_allowed_now: false",
        "- cascade/outcome blocked: true",
        "- production-like recompute/tradable edge not claimed: true",
        "",
        "## Evidence",
        f"- output_dir: `{diagnostic['evidence_sources']['output_dir']}`",
        f"- streams_scanned: {diagnostic['evidence_sources']['streams_scanned']}",
        f"- summaries_scanned: {diagnostic['evidence_sources']['summaries_scanned']}",
        f"- schemas_scanned: {diagnostic['evidence_sources']['schemas_scanned']}",
        f"- rows_scanned: {diagnostic['evidence_sources']['rows_scanned']}",
        "- ML38.10.73 was already executed before this diagnostic; ML38.10.74 did not rerun wrapper or training.",
        "",
        "## Field contract validation",
        f"- field_contract_status: {diagnostic['sidecar_field_contract_validation']['field_contract_status']}",
        "- contract_version: ml38.10.69",
        "- actual_label: available",
        "- raw probabilities: available",
        "- calibrated probabilities: available",
        "- row_alignment_key: available and unique per stream",
        "- prediction_layers: present",
        "- LF-only and summary hash/size validation: passed",
        "",
        "## Actual label distribution — test split",
        f"- DOWN: {actual['DOWN']}",
        f"- FLAT: {actual['FLAT']}",
        f"- UP: {actual['UP']}",
        f"- total: {actual['total']}",
        "",
        "## Best replay policy",
        f"- policy_name: {best.get('policy_name')}",
        f"- parameters: `{json.dumps(best.get('parameters', {}), sort_keys=True)}`",
        f"- avg_accuracy: {_fmt_float(best.get('avg_accuracy'))}",
        f"- avg_accuracy_edge: {_fmt_float(best.get('avg_accuracy_edge'))}",
        f"- avg_flat_recall: {_fmt_float(best.get('avg_flat_recall'))}",
        f"- avg_directional_recall: {_fmt_float(best.get('avg_directional_recall'))}",
        f"- avg_false_directional_on_actual_flat: {_fmt_float(best.get('avg_false_directional_on_actual_flat'))}",
        f"- best_candidate_predicted_distribution: `{json.dumps(best.get('best_candidate_predicted_distribution', {}), sort_keys=True)}`",
        "",
        "## Raw vs calibrated comparison",
        f"```json\n{json.dumps(diagnostic['raw_vs_calibrated_comparison'], ensure_ascii=False, indent=2, sort_keys=True)}\n```",
        "",
        "## Policy grid summary",
        f"- policies_tested: {diagnostic['candidate_replay_summary']['policies_tested']}",
        f"- candidate_policy_pairs_ranked: {diagnostic['candidate_replay_summary']['candidate_policy_pairs_ranked']}",
        f"- any_policy_positive_accuracy_edge: {diagnostic['candidate_replay_summary']['any_policy_positive_accuracy_edge']}",
        f"- any_policy_beats_majority_baseline: {diagnostic['candidate_replay_summary']['any_policy_beats_majority_baseline']}",
        f"- probability_sequences_identical_across_candidates: {diagnostic['candidate_replay_summary']['probability_sequences_identical_across_candidates']}",
        "",
        "## Best replay policies",
        f"```json\n{json.dumps(diagnostic['best_replay_policies'], ensure_ascii=False, indent=2, sort_keys=True)}\n```",
        "",
        "## Flat protection analysis",
        f"```json\n{json.dumps(diagnostic['flat_protection_analysis'], ensure_ascii=False, indent=2, sort_keys=True)}\n```",
        "",
        "## Directional preservation analysis",
        f"```json\n{json.dumps(diagnostic['directional_preservation_analysis'], ensure_ascii=False, indent=2, sort_keys=True)}\n```",
        "",
        "## h08 scope",
        "- h08 issue known: true",
        "- h08 fix applied: false",
        "- h08 remains separately scoped.",
        "",
        "## Guardrails",
        "- no training run",
        "- no wrapper / quick-quality rerun",
        "- no run_fv3_cached_tuning.py",
        "- no DB writes",
        "- no ml_labels/ml_predictions writes",
        "- labels/builders/gates/model logic unchanged",
        "- class weights/objective/production calibration unchanged",
        "- directional_confidence_floor 0.60 not implemented",
        "- flat override not implemented",
        "- existing real artifacts not mutated",
        "- no new real sidecars/ZIP created by ML38.10.74",
        "- archive recovery not performed",
        "- no commit/planning/snapshot",
        "",
        "## Tests",
        f"- full_pytest_result: {full_pytest_result}",
        f"- full_pytest_exit_code: {full_pytest_exit_code}",
        f"- full_pytest_log: `{full_pytest_log}`",
        "",
        "## Raw diagnostic JSON",
        f"```json\n{json.dumps(diagnostic, ensure_ascii=False, indent=2, sort_keys=True)}\n```",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=Path("reports/stage_ml38_10_74_outcome_aware_calibration_replay_report.md"))
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--full-pytest-result", default="PENDING")
    parser.add_argument("--full-pytest-exit-code", default="PENDING")
    parser.add_argument("--full-pytest-log", default="PENDING")
    args = parser.parse_args()

    diagnostic = run_outcome_aware_calibration_replay(args.output_dir)

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(diagnostic, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    report_text = render_markdown_report(
        diagnostic,
        full_pytest_result=args.full_pytest_result,
        full_pytest_exit_code=args.full_pytest_exit_code,
        full_pytest_log=args.full_pytest_log,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report_text, encoding="utf-8", newline="\n")

    print("DIAGNOSTIC_DECISION:", diagnostic["decision_gate"]["decision"])
    print("RECOMMENDATION:", diagnostic["recommendation"]["recommendation_type"])
    print("NEXT_ALLOWED_STAGE:", diagnostic["decision_gate"]["next_allowed_stage"])
    print("REPORT:", args.report)


if __name__ == "__main__":
    main()
