from __future__ import annotations

from datetime import datetime, timezone
import importlib
import json
from pathlib import Path

import pytest

from app.experiments.feature_regime_experiment_reporter import FeatureRegimeExperimentReporter
from app.experiments.multi_symbol_feature_regime_reporter import MultiSymbolFeatureRegimeReporter
from app.experiments.multi_symbol_feature_regime_analyzer import MultiSymbolFeatureRegimeAnalyzer
from app.experiments.prediction_sidecar_exporter import validate_prediction_sidecar_rows
from app.experiments.prediction_sidecar_wiring import (
    build_full_dataset_prediction_sidecar_rows,
    build_ml38_10_54_sidecar_wiring_decision,
    build_sidecar_wiring_metadata,
    validate_full_dataset_prediction_sidecar_ready,
    write_full_dataset_prediction_sidecar_for_candidate,
)


IDENTITY = {
    "config_id": "synthetic_config",
    "candidate_id": "synthetic_candidate",
    "run_id": "synthetic_run",
    "model_version": "synthetic_model_v1",
    "feature_version": "synthetic_fv",
    "label_version": "synthetic_lv",
    "horizon_candles": 12,
    "symbol": "SYNTHUSDT",
    "interval": "15m",
}


def _source_row(index: int) -> dict:
    return {
        "candle_open_time": datetime(2026, 1, 1, 0, index, tzinfo=timezone.utc),
        "setup_quality_score": 0.5,
        "direction_label": "DOWN",  # target is deliberately unrelated to model argmax
    }


def _rows() -> list[dict]:
    return build_full_dataset_prediction_sidecar_rows(
        split_rows={
            "train": [_source_row(0), _source_row(1)],
            "validation": [_source_row(2)],
            "test": [_source_row(3)],
        },
        split_probabilities={
            "train": [[0.8, 0.1, 0.1], [0.1, 0.8, 0.1]],
            "validation": [[0.1, 0.1, 0.8]],
            "test": [[0.7, 0.2, 0.1]],
        },
        split_direction_logits={
            "train": [[2.0, 0.0, -1.0], [0.0, 2.0, -1.0]],
            "validation": [[0.0, -1.0, 2.0]],
            "test": [[2.0, 0.0, -1.0]],
        },
        model_name="synthetic_classifier",
        **IDENTITY,
    )


def _validate(rows: list[dict], **overrides) -> dict:
    identity = {**IDENTITY, **overrides}
    return validate_full_dataset_prediction_sidecar_ready(
        rows,
        expected_row_count=len(rows),
        denominator_scope="SYNTHETIC_FULL_DATASET",
        **identity,
    )


def test_build_rows_covers_train_val_test_and_uses_probability_argmax() -> None:
    rows = _rows()
    assert [row["split_name"] for row in rows] == ["train", "train", "val", "test"]
    assert [row["predicted_label"] for row in rows] == ["UP", "DOWN", "FLAT", "UP"]
    assert all(row["predicted_label_source"] == "model_probability_argmax" for row in rows)


def test_valid_synthetic_full_dataset_stream_writes_only_to_tmp_path(tmp_path: Path) -> None:
    result = write_full_dataset_prediction_sidecar_for_candidate(
        tmp_path,
        _rows(),
        expected_row_count=4,
        denominator_scope="SYNTHETIC_FULL_DATASET",
        **IDENTITY,
    )
    assert result["status"] == "PREDICTION_SIDECAR_ARTIFACTS_WRITTEN"
    assert all(Path(path).is_file() for path in result["paths"].values())
    assert all("reports" not in {part.lower() for part in Path(path).parts} for path in result["paths"].values())


def test_test_only_973_boundary_is_rejected_for_full_dataset_6481() -> None:
    row = _rows()[-1]
    row["dataset_row_index"] = 0
    row["split_row_index"] = 0
    row["split_total_rows"] = 973
    validation = validate_prediction_sidecar_rows(
        [row],
        expected_row_count=6481,
        denominator_scope="FULL_DATASET_6481",
        expected_config_id=IDENTITY["config_id"],
    )
    assert validation["status"] == "PREDICTION_SIDECAR_INVALID"
    assert any("test-only" in error or "row_count 1" in error for error in validation["errors"])


@pytest.mark.parametrize(
    ("field", "message"),
    [("split_name", "split_name is required"), ("candle_open_time", "candle_open_time is required")],
)
def test_missing_required_identity_fails_closed(field: str, message: str) -> None:
    rows = _rows()
    rows[0].pop(field)
    assert any(message in error for error in _validate(rows)["errors"])


def test_duplicate_join_key_fails_closed() -> None:
    rows = _rows()
    rows[1]["candle_open_time"] = rows[0]["candle_open_time"]
    assert _validate(rows)["duplicate_join_key_count"] == 1


@pytest.mark.parametrize(
    "source",
    ["actual_label", "target_label", "ml_labels.direction_label"],
)
def test_actual_target_or_ml_labels_prediction_source_fails_closed(source: str) -> None:
    rows = _rows()
    rows[0]["prediction_source_stage"] = source
    assert _validate(rows)["forbidden_substitution_check"]["status"] == "FAILED"


@pytest.mark.parametrize(
    ("identity_field", "wrong_value"),
    [
        ("config_id", "wrong_config"),
        ("candidate_id", "wrong_candidate"),
        ("run_id", "wrong_run"),
        ("symbol", "WRONGUSDT"),
        ("interval", "5m"),
        ("horizon_candles", 99),
        ("model_version", "wrong_model"),
        ("feature_version", "wrong_feature"),
        ("label_version", "wrong_label"),
    ],
)
def test_expected_identity_mismatch_fails_closed(identity_field: str, wrong_value: object) -> None:
    validation = _validate(_rows(), **{identity_field: wrong_value})
    assert validation["status"] == "PREDICTION_SIDECAR_INVALID"
    assert validation["config_consistency"][identity_field]["matches"] is False


def test_overwrite_is_blocked_by_default(tmp_path: Path) -> None:
    kwargs = {
        "expected_row_count": 4,
        "denominator_scope": "SYNTHETIC_FULL_DATASET",
        **IDENTITY,
    }
    write_full_dataset_prediction_sidecar_for_candidate(tmp_path, _rows(), **kwargs)
    with pytest.raises(FileExistsError, match="overwrite is disabled"):
        write_full_dataset_prediction_sidecar_for_candidate(tmp_path, _rows(), **kwargs)


def test_reporter_analyzer_metadata_is_wired_not_executed() -> None:
    metadata = build_sidecar_wiring_metadata()
    decisions = build_ml38_10_54_sidecar_wiring_decision()
    payload = {
        "full_dataset_prediction_sidecar_wiring": metadata,
        "ml38_10_54_sidecar_quick_quality_wiring_decision": decisions,
    }
    feature = FeatureRegimeExperimentReporter().compact_summary_to_dict(payload)
    multi = MultiSymbolFeatureRegimeReporter().compact_summary_to_dict(payload)
    assert feature["full_dataset_prediction_sidecar_wiring"]["implementation_status"] == "WIRED_NOT_EXECUTED"
    assert multi["full_dataset_prediction_sidecar_wiring"]["implementation_status"] == "WIRED_NOT_EXECUTED"
    assert metadata["real_quick_quality_run_executed"] is False
    assert metadata["real_full_dataset_stream_created"] is False
    assert "REPORTER_ANALYZER_METADATA_WIRED" in decisions


def test_analyzer_emits_wiring_metadata(tmp_path: Path) -> None:
    summary = {
        "experiment_id": "synthetic_exp",
        "symbol": "SYNTHUSDT",
        "interval": "15m",
        "status": "COMPLETED",
        "experiment_status": "COMPLETED_NO_ACCEPTED_CANDIDATE",
        "candidate_count": 0,
        "evaluated_candidate_count": 0,
        "failed_candidate_count": 0,
        "accepted_candidate_count": 0,
        "rejected_candidate_count": 0,
        "feature_version_used": "synthetic_fv",
        "real_feature_diagnostics_used": True,
        "real_feature_diagnostics_row_count": 4,
        "effective_gap_count_for_training": 0,
        "gap_training_safe": True,
        "regime_features_attached": True,
        "candidate_results": [],
        "configs_ranked": [],
    }
    path = tmp_path / "summary.json"
    path.write_text(json.dumps(summary), encoding="utf-8")
    analysis = MultiSymbolFeatureRegimeAnalyzer().analyze([path])
    assert analysis["full_dataset_prediction_sidecar_wiring"]["implementation_status"] == "WIRED_NOT_EXECUTED"
    assert "SIDECAR_QUICK_QUALITY_WIRING_IMPLEMENTED" in analysis[
        "ml38_10_54_sidecar_quick_quality_wiring_decision"
    ]


def test_internal_quick_quality_wiring_modules_are_importable() -> None:
    for module_name in (
        "app.cli.commands",
        "app.experiments.feature_regime_experiment_runner",
        "app.experiments.label_grid_experiment_runner",
        "app.training.training_pipeline_runner",
    ):
        assert importlib.import_module(module_name) is not None


def test_builder_rejects_missing_model_probabilities_instead_of_using_labels() -> None:
    with pytest.raises(ValueError, match="row/probability count mismatch"):
        build_full_dataset_prediction_sidecar_rows(
            split_rows={"train": [_source_row(0)], "validation": [], "test": []},
            split_probabilities={"train": [], "validation": [], "test": []},
            split_direction_logits={"train": [[1.0, 0.0, -1.0]], "validation": [], "test": []},
            model_name="synthetic_classifier",
            **IDENTITY,
        )
