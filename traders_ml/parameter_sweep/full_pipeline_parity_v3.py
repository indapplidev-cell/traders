"""Pre-holdout native stage parity diagnostics; never grants train eligibility."""

from __future__ import annotations

import json
from itertools import zip_longest
from pathlib import Path
from typing import Any

from .full_pipeline import FullPipelineCalibrationRequestV2, RaggedDatasetManifestV2
from .full_pipeline_v3 import _sha256, _write_json


def _geometry(paper: dict[str, Any]) -> tuple[Any, Any, Any]:
    return tuple(paper.get(key) for key in (
        "hypothetical_entry_reference", "hypothetical_stop_level",
        "hypothetical_target_level"))


def audit_native_stage_parity_v3(
    request_path: Path, dataset: Path, cache: Path, signals: Path,
    output: Path,
) -> dict[str, Any]:
    """Compare aligned stage outcomes without opening the locked holdout."""
    request = FullPipelineCalibrationRequestV2.model_validate_json(
        request_path.read_text(encoding="utf-8"))
    frozen = RaggedDatasetManifestV2.model_validate_json(
        (dataset / "DATASET_MANIFEST.json").read_text(encoding="utf-8"))
    base = json.loads((cache / "FEATURE_CACHE_MANIFEST.json").read_text(encoding="utf-8"))
    candidate = json.loads((signals / "CANDIDATE_SIGNAL_MANIFEST.json").read_text(encoding="utf-8"))
    holdout_start = next(window.start_ms for window in request.windows
                         if window.role == "INTERNAL_HOLDOUT")
    if (frozen.status != "FROZEN" or frozen.request_hash != request.identity
            or base.get("dataset_hash") != frozen.dataset_hash
            or candidate.get("dataset_hash") != frozen.dataset_hash
            or base.get("holdout_evaluated") is not False
            or candidate.get("holdout_evaluated") is not False
            or candidate.get("status") != "COMPLETE_PREHOLDOUT"
            or candidate.get("completed_boundaries") != base.get("completed_boundaries")):
        raise ValueError("V3_PARITY_INPUTS_NOT_CERTIFIED_PREHOLDOUT")
    source_parts = {(part["symbol"], int(part["segment_start_ms"])): part
                    for part in base["partitions"]}
    signal_parts = {(part["symbol"], int(part["segment_start_ms"])): part
                    for part in candidate["partitions"]}
    if source_parts.keys() != signal_parts.keys():
        raise ValueError("V3_PARITY_PARTITION_SET_MISMATCH")
    totals = {"boundaries": 0, "stage_status_mismatches": 0,
              "first_rejection_mismatches": 0, "ready_geometry_mismatches": 0}
    by_symbol: dict[str, dict[str, int]] = {}
    examples: list[dict[str, Any]] = []
    for symbol, start_ms in sorted(source_parts):
        source = cache / "symbols" / symbol / str(start_ms) / "FEATURES.jsonl"
        target = signals / "symbols" / symbol / str(start_ms) / "SIGNALS.jsonl"
        if (_sha256(source) != source_parts[(symbol, start_ms)]["sha256"]
                or _sha256(target) != signal_parts[(symbol, start_ms)]["sha256"]):
            raise ValueError("V3_PARITY_PARTITION_HASH_MISMATCH")
        counts = {key: 0 for key in totals}
        with source.open(encoding="utf-8") as old, target.open(encoding="utf-8") as new:
            for old_line, new_line in zip_longest(old, new):
                if old_line is None or new_line is None:
                    raise ValueError("V3_PARITY_BOUNDARY_COUNT_MISMATCH")
                before, after = json.loads(old_line), json.loads(new_line)
                boundary = int(before["boundary_ms"])
                if (before["symbol"] != symbol or after["symbol"] != symbol
                        or boundary != int(after["boundary_ms"])
                        or boundary >= holdout_start):
                    raise ValueError("V3_PARITY_BOUNDARY_ID_OR_HOLDOUT_MISMATCH")
                counts["boundaries"] += 1
                differences = []
                if before["statuses"] != after["statuses"]:
                    differences.append("stage_status_mismatches")
                if before.get("first_rejection") != after.get("first_rejection"):
                    differences.append("first_rejection_mismatches")
                if (before["statuses"].get("paper_status") == "PAPER_PLAN_READY"
                        and after["statuses"].get("paper_status") == "PAPER_PLAN_READY"
                        and _geometry(before["paper"]) != _geometry(after["paper"])):
                    differences.append("ready_geometry_mismatches")
                for name in differences:
                    counts[name] += 1
                if differences and len(examples) < 100:
                    examples.append({"symbol": symbol, "boundary_ms": boundary,
                                     "differences": differences,
                                     "baseline_statuses": before["statuses"],
                                     "candidate_statuses": after["statuses"]})
        if counts["boundaries"] != int(source_parts[(symbol, start_ms)]["boundaries"]):
            raise ValueError("V3_PARITY_RECEIPT_COUNT_MISMATCH")
        by_symbol[symbol] = counts
        for name, value in counts.items():
            totals[name] += value
    if totals["boundaries"] != int(base["completed_boundaries"]):
        raise ValueError("V3_PARITY_TOTAL_COUNT_MISMATCH")
    result = {"version": "native-stage-parity/3", "status": "DIAGNOSTIC_ONLY",
              "train_eligible": False, "dataset_hash": frozen.dataset_hash,
              "holdout_evaluated": False, "totals": totals,
              "by_symbol": by_symbol, "first_mismatches": examples}
    _write_json(output, result)
    return result
