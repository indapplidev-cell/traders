from __future__ import annotations

import json
from pathlib import Path

from traders_ml.parameter_sweep.full_pipeline import RaggedDatasetManifestV2
from traders_ml.parameter_sweep.full_pipeline_parity_v3 import (
    audit_native_stage_parity_v3,
)
from traders_ml.parameter_sweep.full_pipeline_v3 import _sha256

ROOT = Path(__file__).resolve().parents[2]
REQUEST = ROOT / "config/research/full_pipeline_calibration_v2.json"
DATASET = ROOT / "artifacts/full_pipeline_calibration/ragged_freeze_20261102_v1"


def test_stage_parity_reports_mismatch_without_granting_train(tmp_path) -> None:
    frozen = RaggedDatasetManifestV2.model_validate_json(
        (DATASET / "DATASET_MANIFEST.json").read_text(encoding="utf-8"))
    cache = tmp_path / "cache"
    signals = tmp_path / "signals"
    source = cache / "symbols/BTCUSDT/1000/FEATURES.jsonl"
    target = signals / "symbols/BTCUSDT/1000/SIGNALS.jsonl"
    source.parent.mkdir(parents=True)
    target.parent.mkdir(parents=True)
    old = [{"symbol": "BTCUSDT", "boundary_ms": value,
            "statuses": {"paper_status": status},
            "first_rejection": reason, "paper": {}}
           for value, status, reason in ((1000, "NO_PLAN", "NO_SETUP"),
                                         (301000, "NO_PLAN", "NO_SETUP"))]
    new = [dict(row) for row in old]
    new[1] = {**new[1], "first_rejection": "LOW_CONFIDENCE"}
    source.write_text("".join(json.dumps(row) + "\n" for row in old), encoding="utf-8")
    target.write_text("".join(json.dumps(row) + "\n" for row in new), encoding="utf-8")
    common = {"dataset_hash": frozen.dataset_hash, "holdout_evaluated": False,
              "completed_boundaries": 2}
    (cache / "FEATURE_CACHE_MANIFEST.json").write_text(json.dumps({
        **common, "partitions": [{"symbol": "BTCUSDT", "segment_start_ms": 1000,
                                  "boundaries": 2, "sha256": _sha256(source)}]}), encoding="utf-8")
    (signals / "CANDIDATE_SIGNAL_MANIFEST.json").write_text(json.dumps({
        **common, "status": "COMPLETE_PREHOLDOUT",
        "partitions": [{"symbol": "BTCUSDT", "segment_start_ms": 1000,
                        "boundaries": 2, "sha256": _sha256(target)}]}), encoding="utf-8")
    result = audit_native_stage_parity_v3(
        REQUEST, DATASET, cache, signals, tmp_path / "PARITY.json")
    assert result["totals"]["boundaries"] == 2
    assert result["totals"]["first_rejection_mismatches"] == 1
    assert result["train_eligible"] is False
    assert result["holdout_evaluated"] is False
