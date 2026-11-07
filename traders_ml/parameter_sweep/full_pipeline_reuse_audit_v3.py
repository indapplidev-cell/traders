"""Control-boundary parity audit for reusing enriched v3 analysis evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .full_pipeline import (
    FullPipelineCalibrationRequestV2,
    RaggedDatasetManifestV2,
    fingerprint,
)
from .full_pipeline_candidate_v3 import (
    _analysis_reuse_safe_v3,
    native_candidate_decisions_v3,
)
from .full_pipeline_ragged import _closed_boundary_count
from .full_pipeline_v3 import _sha256, _write_json


def _controls(path: Path, *, expected: int, holdout_start_ms: int) -> tuple[int, ...]:
    chosen: set[int] = set()
    ready: int | None = None
    previous = -1
    count = 0
    with path.open(encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            row = json.loads(line)
            boundary = int(row["boundary_ms"])
            if boundary <= previous or boundary >= holdout_start_ms:
                raise ValueError("V3_REUSE_CONTROL_SOURCE_NOT_CAUSAL")
            previous = boundary
            if index in {0, expected // 2, expected - 1}:
                chosen.add(boundary)
            if ready is None and row["statuses"].get("paper_status") == "PAPER_PLAN_READY":
                ready = boundary
            count = index + 1
    if count != expected:
        raise ValueError("V3_REUSE_CONTROL_SOURCE_COUNT_MISMATCH")
    if ready is not None:
        chosen.add(ready)
    return tuple(sorted(chosen))


def audit_enriched_analysis_reuse_v3(
    request_path: Path, dataset: Path, cache: Path, output: Path,
    changes: dict[str, Any],
) -> dict[str, Any]:
    """Compare full native and cached-analysis stages at controls for all symbols."""
    if not _analysis_reuse_safe_v3(changes):
        raise ValueError("V3_REUSE_AUDIT_REQUIRES_DOWNSTREAM_CHANGE")
    request = FullPipelineCalibrationRequestV2.model_validate_json(
        request_path.read_text(encoding="utf-8"))
    frozen = RaggedDatasetManifestV2.model_validate_json(
        (dataset / "DATASET_MANIFEST.json").read_text(encoding="utf-8"))
    source = json.loads((cache / "FEATURE_CACHE_MANIFEST.json").read_text(encoding="utf-8"))
    holdout_start = next(window.start_ms for window in request.windows
                         if window.role == "INTERNAL_HOLDOUT")
    expected = sum(_closed_boundary_count(segment.start_ms,
                   min(segment.end_ms, holdout_start), 300_000)
                   for symbol in frozen.symbols if symbol.status != "UNUSABLE"
                   for segment in symbol.segments if segment.start_ms < holdout_start)
    if (frozen.status != "FROZEN" or frozen.request_hash != request.identity
            or source.get("dataset_hash") != frozen.dataset_hash
            or source.get("request_hash") != request.identity
            or source.get("status") != "COMPLETE"
            or source.get("holdout_evaluated") is not False
            or source.get("completed_boundaries") != expected
            or len(source.get("partitions", [])) != len(request.symbols)):
        raise ValueError("V3_REUSE_AUDIT_SOURCE_NOT_COMPLETE_PREHOLDOUT")
    identity = {"version": "analysis-reuse-controls/3",
                "dataset_hash": frozen.dataset_hash,
                "request_hash": request.identity,
                "source_cache_hash": fingerprint(source),
                "changes_hash": fingerprint(changes),
                "holdout_evaluated": False}
    if output.exists():
        previous = json.loads(output.read_text(encoding="utf-8"))
        if any(previous.get(key) != value for key, value in identity.items()):
            raise ValueError("V3_REUSE_AUDIT_RESUME_IDENTITY_CHANGED")
        completed = {row["symbol"]: row for row in previous["symbols"]}
    else:
        completed = {}
    for part in source["partitions"]:
        symbol = part["symbol"]
        partition = cache / "symbols" / symbol / str(part["segment_start_ms"])
        path = partition / "FEATURES.jsonl"
        if _sha256(path) != part["sha256"]:
            raise ValueError("V3_REUSE_AUDIT_SOURCE_HASH_MISMATCH")
        if symbol in completed:
            if completed[symbol].get("source_sha256") != part["sha256"]:
                raise ValueError("V3_REUSE_AUDIT_COMPLETED_SOURCE_CHANGED")
            continue
        controls = _controls(path, expected=int(part["boundaries"]),
                             holdout_start_ms=holdout_start)
        selected = frozenset(controls)
        full = list(native_candidate_decisions_v3(
            request_path, dataset, cache, partition, changes,
            selected_boundaries=selected))
        reused = list(native_candidate_decisions_v3(
            request_path, dataset, cache, partition, changes,
            selected_boundaries=selected, reuse_enriched_analysis=True))
        if len(full) != len(controls) or len(reused) != len(controls):
            raise ValueError("V3_REUSE_AUDIT_CONTROL_BOUNDARY_MISSING")
        mismatches = []
        for before, after in zip(full, reused):
            fields = {
                "boundary": before.boundary_ms == after.boundary_ms,
                "analysis_context": before.analysis.get("analysis_context") == after.analysis.get("analysis_context"),
                "statuses": before.statuses == after.statuses,
                "first_rejection": before.first_rejection == after.first_rejection,
                "strategy_score": before.strategy.get("strategy_score") == after.strategy.get("strategy_score"),
                "plan_geometry": tuple(before.paper.get(key) for key in (
                    "hypothetical_entry_reference", "hypothetical_stop_level",
                    "hypothetical_target_level")) == tuple(after.paper.get(key) for key in (
                    "hypothetical_entry_reference", "hypothetical_stop_level",
                    "hypothetical_target_level")),
            }
            if not all(fields.values()):
                mismatches.append({"boundary_ms": before.boundary_ms,
                                   "fields": [key for key, equal in fields.items() if not equal]})
        completed[symbol] = {"symbol": symbol, "segment_start_ms": part["segment_start_ms"],
                             "source_sha256": part["sha256"], "control_boundaries": controls,
                             "mismatches": mismatches}
        _write_json(output, {**identity, "status": "IN_PROGRESS",
                             "symbols": list(completed.values()),
                             "train_eligible": False})
    result = {**identity,
              "status": ("PASS_CONTROLS" if all(not row["mismatches"]
                                               for row in completed.values())
                         else "FAIL_CONTROLS"),
              "symbols": list(completed.values()), "train_eligible": False}
    _write_json(output, result)
    return result
