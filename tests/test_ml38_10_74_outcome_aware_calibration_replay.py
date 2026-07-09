from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.diagnostics.outcome_aware_calibration_replay import (
    DIAGNOSTIC_VERSION,
    EXECUTION_MODE,
    run_outcome_aware_calibration_replay,
)


def _write_sidecar_fixture(base: Path, candidate_id: str, rows: list[dict]) -> None:
    payload_dir = base / "pipeline_runs" / candidate_id / "prediction_payloads"
    payload_dir.mkdir(parents=True, exist_ok=True)

    stream = payload_dir / "full_dataset_prediction_stream.jsonl"
    data = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows).encode("utf-8")
    stream.write_bytes(data)

    summary = {
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
        "row_count": len(rows),
        "prediction_field_contract_version": "ml38.10.69",
    }
    (payload_dir / "full_dataset_prediction_stream_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
        newline="\n",
    )

    schema = {
        "prediction_field_contract_version": "ml38.10.69",
        "fields": [
            "actual_label",
            "raw_probabilities",
            "calibrated_probabilities",
            "row_alignment_key",
            "prediction_layers",
        ],
    }
    (payload_dir / "prediction_payload_schema.json").write_text(
        json.dumps(schema, indent=2, sort_keys=True),
        encoding="utf-8",
        newline="\n",
    )


def _row(
    *,
    candidate_id: str,
    index: int,
    actual: str,
    raw: dict[str, float],
    calibrated: dict[str, float],
) -> dict:
    sidecar_argmax = max(calibrated, key=calibrated.get)
    return {
        "sidecar_schema_version": "ml38.10.69",
        "sidecar_writer_version": "ml38.10.69",
        "prediction_field_contract_version": "ml38.10.69",
        "candidate_id": candidate_id,
        "symbol": "SOLUSDT",
        "interval": "15m",
        "horizon": 12,
        "split": "test",
        "row_index_global": index,
        "row_index_split": index,
        "row_alignment_key": f"{candidate_id}:test:{index}",
        "actual_label": actual,
        "current_predicted_label": sidecar_argmax,
        "sidecar_argmax_label": sidecar_argmax,
        "raw_prob_down": raw["DOWN"],
        "raw_prob_flat": raw["FLAT"],
        "raw_prob_up": raw["UP"],
        "raw_probabilities": raw,
        "calibrated_prob_down": calibrated["DOWN"],
        "calibrated_prob_flat": calibrated["FLAT"],
        "calibrated_prob_up": calibrated["UP"],
        "calibrated_probabilities": calibrated,
        "prediction_layers": {
            "raw": {"probabilities": raw},
            "calibrated": {"probabilities": calibrated},
            "sidecar_selected": {"label": sidecar_argmax},
        },
    }


def test_outcome_aware_replay_returns_required_sections(tmp_path: Path) -> None:
    candidate_id = "fixture_candidate"
    rows = [
        _row(
            candidate_id=candidate_id,
            index=0,
            actual="FLAT",
            raw={"DOWN": 0.30, "FLAT": 0.40, "UP": 0.30},
            calibrated={"DOWN": 0.35, "FLAT": 0.30, "UP": 0.35},
        ),
        _row(
            candidate_id=candidate_id,
            index=1,
            actual="DOWN",
            raw={"DOWN": 0.70, "FLAT": 0.20, "UP": 0.10},
            calibrated={"DOWN": 0.60, "FLAT": 0.30, "UP": 0.10},
        ),
        _row(
            candidate_id=candidate_id,
            index=2,
            actual="UP",
            raw={"DOWN": 0.10, "FLAT": 0.20, "UP": 0.70},
            calibrated={"DOWN": 0.15, "FLAT": 0.25, "UP": 0.60},
        ),
    ]
    _write_sidecar_fixture(tmp_path, candidate_id, rows)

    diagnostic = run_outcome_aware_calibration_replay(tmp_path)

    assert diagnostic["diagnostic_version"] == DIAGNOSTIC_VERSION
    assert diagnostic["execution_mode"] == EXECUTION_MODE
    assert diagnostic["sidecar_field_contract_validation"]["field_contract_status"] == "PASSED"
    assert diagnostic["decision_gate"]["actual_labels_available"] is True
    assert diagnostic["decision_gate"]["raw_probabilities_available"] is True
    assert diagnostic["decision_gate"]["calibrated_probabilities_available"] is True
    assert diagnostic["decision_gate"]["production_policy_allowed_now"] is False
    assert diagnostic["decision_gate"]["cascade_outcome_allowed_now"] is False
    assert diagnostic["decision_gate"]["tradable_edge_claim_allowed_now"] is False


def test_policy_grid_contains_required_policy_families(tmp_path: Path) -> None:
    candidate_id = "fixture_candidate"
    rows = [
        _row(
            candidate_id=candidate_id,
            index=0,
            actual="FLAT",
            raw={"DOWN": 0.30, "FLAT": 0.40, "UP": 0.30},
            calibrated={"DOWN": 0.36, "FLAT": 0.34, "UP": 0.30},
        ),
        _row(
            candidate_id=candidate_id,
            index=1,
            actual="DOWN",
            raw={"DOWN": 0.80, "FLAT": 0.10, "UP": 0.10},
            calibrated={"DOWN": 0.70, "FLAT": 0.20, "UP": 0.10},
        ),
    ]
    _write_sidecar_fixture(tmp_path, candidate_id, rows)

    diagnostic = run_outcome_aware_calibration_replay(tmp_path)
    policy_names = {item["policy_name"] for item in diagnostic["policy_grid_results"]}

    assert "calibrated_argmax" in policy_names
    assert "raw_argmax" in policy_names
    assert "flat_margin_buffer" in policy_names
    assert "flat_min_probability" in policy_names
    assert "directional_confidence_floor" in policy_names
    assert "combined_conservative" in policy_names

    for item in diagnostic["policy_grid_results"]:
        assert "avg_accuracy" in item
        assert "avg_accuracy_edge" in item
        assert "avg_flat_recall" in item
        assert "avg_directional_recall" in item
        assert "avg_false_directional_on_actual_flat" in item


def test_guardrails_block_production_changes(tmp_path: Path) -> None:
    candidate_id = "fixture_candidate"
    rows = [
        _row(
            candidate_id=candidate_id,
            index=0,
            actual="FLAT",
            raw={"DOWN": 0.20, "FLAT": 0.60, "UP": 0.20},
            calibrated={"DOWN": 0.25, "FLAT": 0.50, "UP": 0.25},
        )
    ]
    _write_sidecar_fixture(tmp_path, candidate_id, rows)

    diagnostic = run_outcome_aware_calibration_replay(tmp_path)
    guardrails = diagnostic["guardrails"]

    assert guardrails["training_run_during_stage"] is False
    assert guardrails["wrapper_execute_used_during_stage"] is False
    assert guardrails["quick_quality_rerun_during_stage"] is False
    assert guardrails["production_calibration_policy_changed"] is False
    assert guardrails["directional_confidence_floor_implemented"] is False
    assert guardrails["flat_override_implemented"] is False
    assert guardrails["h08_fix_applied"] is False
    assert guardrails["existing_real_artifacts_mutated"] is False
    assert guardrails["commit_performed"] is False
    assert guardrails["planning_update_performed"] is False
    assert guardrails["snapshot_performed"] is False
