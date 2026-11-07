"""Fail-closed pre-holdout portfolio replay over certified native signal shards."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config.trade_parameters import load_trade_parameters

from .full_pipeline import (
    FullPipelineCalibrationRequestV2,
    RaggedDatasetManifestV2,
    fingerprint,
)
from .full_pipeline_candidate_v3 import resolve_research_parameter_set_v3
from .full_pipeline_ragged import HistoricalCostModelV1
from .full_pipeline_replay_v3 import ReplayPolicyV3, replay_signal_shards_v3
from .full_pipeline_v3 import NATIVE_PARAMETER_PATHS_V3, _sha256, _write_json


def _signal_source_for_candidate_v3(
    baseline_hash: str, candidate_hash: str, changes: dict[str, Any],
) -> tuple[str, bool]:
    """Reuse native entry signals only when changes affect analytical exit alone."""
    if changes and all(NATIVE_PARAMETER_PATHS_V3.get(name, "").startswith(
            "exit_policy.analytical_exit.") for name in changes):
        return baseline_hash, True
    return candidate_hash, False


def preholdout_role_windows_v3(request: FullPipelineCalibrationRequestV2) -> dict[str, tuple[int, int]]:
    """Separate train spans from every validation interval on the common clock."""
    holdout = next(window for window in request.windows if window.role == "INTERNAL_HOLDOUT")
    validations = sorted((window for window in request.windows if window.role == "VALIDATION"),
                         key=lambda window: window.start_ms)
    result: dict[str, tuple[int, int]] = {}
    cursor = request.data_start_ms
    for index, window in enumerate(validations):
        if window.start_ms < cursor or window.end_ms > holdout.start_ms:
            raise ValueError("V3_VALIDATION_ROLE_OVERLAP_OR_HOLDOUT")
        if cursor < window.start_ms:
            result[f"TRAIN_{index}"] = cursor, window.start_ms
        result[window.name] = window.start_ms, window.end_ms
        cursor = window.end_ms
    if cursor < holdout.start_ms:
        result[f"TRAIN_{len(validations)}"] = cursor, holdout.start_ms
    return result


def run_preholdout_role_v3(
    request_path: Path, dataset: Path, cache: Path, signals: Path,
    output: Path, role_name: str, changes: dict[str, Any],
) -> dict[str, Any]:
    """Replay one isolated role; this diagnostic never grants train eligibility."""
    request = FullPipelineCalibrationRequestV2.model_validate_json(
        request_path.read_text(encoding="utf-8"))
    roles = preholdout_role_windows_v3(request)
    if role_name not in roles:
        raise ValueError("V3_UNKNOWN_PREHOLDOUT_ROLE")
    frozen = RaggedDatasetManifestV2.model_validate_json(
        (dataset / "DATASET_MANIFEST.json").read_text(encoding="utf-8"))
    source = json.loads((cache / "FEATURE_CACHE_MANIFEST.json").read_text(encoding="utf-8"))
    native = json.loads((signals / "CANDIDATE_SIGNAL_MANIFEST.json").read_text(encoding="utf-8"))
    cost_path = cache / "PREVALIDATION_COST_MODEL_V3_2.json"
    cost_receipt = json.loads(cost_path.with_suffix(".receipt.json").read_text(encoding="utf-8"))
    cost_lock = json.loads((signals / "COST_MODEL_LOCK.json").read_text(encoding="utf-8"))
    holdout_start = next(window.start_ms for window in request.windows
                         if window.role == "INTERNAL_HOLDOUT")
    baseline = load_trade_parameters().resolve_scalping_v2_parameter_set()
    candidate = resolve_research_parameter_set_v3(baseline, changes)
    baseline_signal_hash = resolve_research_parameter_set_v3(baseline, {}).resolved_config_hash
    signal_hash, reused_upstream = _signal_source_for_candidate_v3(
        baseline_signal_hash, candidate.resolved_config_hash, changes)
    if (frozen.status != "FROZEN" or frozen.request_hash != request.identity
            or source.get("dataset_hash") != frozen.dataset_hash
            or source.get("request_hash") != request.identity
            or source.get("holdout_evaluated") is not False
            or native.get("dataset_hash") != frozen.dataset_hash
            or native.get("request_hash") != request.identity
            or native.get("source_cache_hash") != fingerprint(source)
            or native.get("configuration_hash") != signal_hash
            or native.get("holdout_evaluated") is not False
            or native.get("status") != "COMPLETE_PREHOLDOUT"
            or native.get("completed_boundaries") != source.get("completed_boundaries")
            or cost_receipt.get("dataset_hash") != frozen.dataset_hash
            or cost_receipt.get("request_hash") != request.identity
            or cost_receipt.get("holdout_evaluated") is not False
            or cost_receipt.get("sha256") != _sha256(cost_path)
            or cost_lock != {"dataset_hash": frozen.dataset_hash,
                             "request_hash": request.identity,
                             "model_hash": cost_receipt.get("model_hash"),
                             "sha256": cost_receipt.get("sha256")}):
        raise ValueError("V3_REPLAY_INPUT_IDENTITY_OR_COMPLETENESS_MISMATCH")
    cost_model = HistoricalCostModelV1.model_validate_json(cost_path.read_text(encoding="utf-8"))
    if cost_model.identity != cost_receipt.get("model_hash"):
        raise ValueError("V3_REPLAY_COST_MODEL_HASH_MISMATCH")
    source_parts = {(part["symbol"], int(part["segment_start_ms"])): part
                    for part in source["partitions"]}
    native_parts = {(part["symbol"], int(part["segment_start_ms"])): part
                    for part in native["partitions"]}
    if source_parts.keys() != native_parts.keys() or len(source_parts) != len(request.symbols):
        raise ValueError("V3_REPLAY_PARTITION_SET_MISMATCH")
    shards: dict[str, tuple[Path, Path]] = {}
    for symbol, start_ms in sorted(source_parts):
        source_part = source_parts[(symbol, start_ms)]
        native_part = native_parts[(symbol, start_ms)]
        if (int(source_part["boundaries"]) != int(native_part["boundaries"])
                or native_part.get("source_sha256") != source_part["sha256"]):
            raise ValueError("V3_REPLAY_PARTITION_SOURCE_OR_COUNT_MISMATCH")
        signal_path = signals / "symbols" / symbol / str(start_ms) / "SIGNALS.jsonl"
        candle_path = cache / "symbols" / symbol / str(start_ms) / "CANDLES.jsonl"
        if (_sha256(signal_path) != native_part["sha256"]
                or _sha256(candle_path) != source_part["candle_sha256"]):
            raise ValueError("V3_REPLAY_PARTITION_HASH_MISMATCH")
        shards[symbol] = signal_path, candle_path
    start_ms, end_ms = roles[role_name]
    result = replay_signal_shards_v3(
        shards, dataset_hash=frozen.dataset_hash,
        policy=ReplayPolicyV3.from_parameters(candidate.parameters),
        cost_model=cost_model, initial_equity=request.initial_equity,
        role_start_ms=start_ms, role_end_ms=end_ms,
        holdout_start_ms=holdout_start,
        analytical_policy=candidate.parameters.exit_policy.analytical_exit)
    result.update({"version": "preholdout-portfolio-replay/3", "role": role_name,
                   "role_start_ms": start_ms, "role_end_ms": end_ms,
                   "dataset_hash": frozen.dataset_hash,
                   "configuration_hash": candidate.resolved_config_hash,
                   "signal_source_configuration_hash": signal_hash,
                   "native_entry_stage_reused": reused_upstream,
                   "reused_native_signal_rows": (
                       result["signal_rows_processed"] if reused_upstream else 0),
                   "cost_model_hash": cost_model.identity})
    _write_json(output, result)
    return result
