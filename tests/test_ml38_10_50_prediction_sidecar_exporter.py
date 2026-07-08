from __future__ import annotations

import json
from pathlib import Path

from app.experiments.compact_archive_pruner import (
    is_prediction_sidecar_artifact_path,
    should_preserve_prediction_sidecar_artifact,
)
from app.experiments.feature_regime_experiment_reporter import FeatureRegimeExperimentReporter
from app.experiments.multi_symbol_feature_regime_reporter import MultiSymbolFeatureRegimeReporter
from app.experiments.prediction_sidecar_exporter import (
    build_prediction_row_alignment_key,
    build_ml38_10_50_sidecar_export_implementation_decision,
    build_sidecar_export_implementation_metadata,
    validate_prediction_sidecar_row,
    validate_prediction_sidecar_rows,
    write_prediction_sidecar_artifacts,
)


CONFIG_ID = "synthetic_config"
MODEL_VERSION = "synthetic_model_v1"
FEATURE_VERSION = "synthetic_fv"
LABEL_VERSION = "synthetic_lv"


def _row(index: int, *, total: int = 6481) -> dict:
    train_end = 4000 if total == 6481 else total
    val_end = 5200 if total == 6481 else total
    split_name = "train" if index < train_end else "val" if index < val_end else "test"
    split_start = 0 if split_name == "train" else train_end if split_name == "val" else val_end
    split_total = train_end if split_name == "train" else val_end - train_end if split_name == "val" else total - val_end
    label = ("UP", "DOWN", "FLAT")[index % 3]
    probabilities = {
        "DOWN": 0.7 if label == "DOWN" else 0.15,
        "FLAT": 0.7 if label == "FLAT" else 0.15,
        "UP": 0.7 if label == "UP" else 0.15,
    }
    return {
        "sidecar_schema_version": "ml38.10.69",
        "sidecar_writer_version": "ml38.10.69",
        "prediction_field_contract_version": "ml38.10.69",
        "symbol": "SYNTHUSDT",
        "interval": "5m",
        "candle_open_time": f"2026-01-{1 + index // 1440:02d}T{index % 1440 // 60:02d}:{index % 60:02d}:00Z",
        "timestamp": f"2026-01-{1 + index // 1440:02d}T{index % 1440 // 60:02d}:{index % 60:02d}:00Z",
        "dataset_row_index": index,
        "row_index_global": index,
        "split_name": split_name,
        "split": split_name,
        "split_row_index": index - split_start,
        "row_index_split": index - split_start,
        "split_total_rows": split_total,
        "feature_version": FEATURE_VERSION,
        "label_version": LABEL_VERSION,
        "horizon_candles": 12,
        "horizon": 12,
        "config_id": CONFIG_ID,
        "model_name": "synthetic_classifier",
        "model_version": MODEL_VERSION,
        "candidate_id": "synthetic_candidate",
        "row_alignment_key": build_prediction_row_alignment_key(
            candidate_id="synthetic_candidate", symbol="SYNTHUSDT", interval="5m",
            horizon=12, split=split_name, row_index_global=index,
            row_index_split=index - split_start,
            timestamp=f"2026-01-{1 + index // 1440:02d}T{index % 1440 // 60:02d}:{index % 60:02d}:00Z",
        ),
        "actual_label": label,
        "predicted_label": label,
        "current_predicted_label": label,
        "sidecar_argmax_label": label,
        "sidecar_argmax_layer": "calibrated_model_softmax",
        "predicted_label_semantics": "backward-compatible alias of sidecar calibrated argmax",
        "prediction_layer_name": "sidecar_selected",
        "prediction_layer_source": "synthetic_model_inference",
        "prediction_source_stage": "synthetic_model_inference",
        "prob_up": 0.7 if label == "UP" else 0.15,
        "prob_down": 0.7 if label == "DOWN" else 0.15,
        "prob_flat": 0.7 if label == "FLAT" else 0.15,
        "confidence": 0.7,
        "raw_prob_up": probabilities["UP"],
        "raw_prob_down": probabilities["DOWN"],
        "raw_prob_flat": probabilities["FLAT"],
        "raw_probabilities": probabilities,
        "calibrated_prob_up": probabilities["UP"],
        "calibrated_prob_down": probabilities["DOWN"],
        "calibrated_prob_flat": probabilities["FLAT"],
        "calibrated_probabilities": probabilities,
        "prediction_layers": {
            "raw_model_softmax_temperature_1": {"probabilities": probabilities, "argmax_label": label},
            "calibrated_model_softmax": {"probabilities": probabilities, "argmax_label": label},
            "sidecar_selected": {"label": label, "source": "synthetic_model_inference"},
        },
        "downstream_policy_output_available_in_writer": False,
        "downstream_policy_output_reason": "not available at sidecar writer stage",
        "downstream_policy_output_must_not_be_conflated_with_sidecar_argmax": True,
    }


def _validate(rows: list[dict], *, expected_row_count: int | None = None, config_id: str = CONFIG_ID) -> dict:
    return validate_prediction_sidecar_rows(
        rows,
        expected_row_count=len(rows) if expected_row_count is None else expected_row_count,
        denominator_scope="SYNTHETIC_TEST_ROWS",
        expected_config_id=config_id,
        expected_model_version=MODEL_VERSION,
        expected_feature_version=FEATURE_VERSION,
        expected_label_version=LABEL_VERSION,
    )


def test_valid_synthetic_full_dataset_6481_rows_pass_validation() -> None:
    rows = [_row(index) for index in range(6481)]
    validation = validate_prediction_sidecar_rows(
        rows,
        expected_row_count=6481,
        denominator_scope="FULL_DATASET_6481",
        expected_config_id=CONFIG_ID,
        expected_model_version=MODEL_VERSION,
        expected_feature_version=FEATURE_VERSION,
        expected_label_version=LABEL_VERSION,
    )

    assert validation["status"] == "PREDICTION_SIDECAR_VALID"
    assert validation["unique_join_key_count"] == 6481
    assert sum(validation["split_counts"].values()) == 6481


def test_duplicate_join_key_fails_validation() -> None:
    rows = [_row(0, total=2), _row(1, total=2)]
    rows[1]["candle_open_time"] = rows[0]["candle_open_time"]
    assert _validate(rows)["status"] == "PREDICTION_SIDECAR_INVALID"


def test_missing_and_invalid_predicted_label_fail_validation() -> None:
    missing = _row(0, total=1)
    missing.pop("predicted_label")
    invalid = _row(0, total=1)
    invalid["predicted_label"] = "LONG"
    assert any("predicted_label is required" in error for error in validate_prediction_sidecar_row(missing))
    assert any("UP/DOWN/FLAT" in error for error in validate_prediction_sidecar_row(invalid))


def test_probability_sum_outside_tolerance_is_error() -> None:
    row = _row(0, total=1)
    row.update(prob_up=0.8, prob_down=0.8, prob_flat=0.1)
    validation = _validate([row])
    assert validation["status"] == "PREDICTION_SIDECAR_INVALID"
    assert validation["probability_validation"]["invalid_sum_row_count"] == 1


def test_actual_label_is_target_only_and_not_used_as_prediction() -> None:
    row = _row(0, total=1)
    row.update(actual_label="DOWN", actual_label_source="synthetic_target", actual_label_version=LABEL_VERSION)
    validation = _validate([row])
    assert validation["status"] == "PREDICTION_SIDECAR_VALID"
    assert validation["forbidden_substitution_check"]["status"] == "PASSED"


def test_actual_or_ml_labels_prediction_source_fails_closed() -> None:
    for source in ("ml_labels.direction_label", "actual_label target source"):
        row = _row(0, total=1)
        row["prediction_source_stage"] = source
        assert _validate([row])["forbidden_substitution_check"]["status"] == "FAILED"


def test_config_mismatch_fails_closed() -> None:
    validation = _validate([_row(0, total=1)], config_id="different_config")
    assert validation["status"] == "PREDICTION_SIDECAR_INVALID"
    assert validation["config_consistency"]["config_id"]["matches"] is False


def test_mixed_candidate_identity_fails_closed_without_expected_identity() -> None:
    rows = [_row(index, total=2) for index in range(2)]
    rows[1]["candidate_id"] = "different_candidate"
    validation = _validate(rows)
    assert validation["status"] == "PREDICTION_SIDECAR_INVALID"
    assert validation["config_consistency"]["candidate_id"]["matches"] is False


def test_writer_creates_stream_summary_and_schema_in_tmp_path(tmp_path: Path) -> None:
    rows = [_row(index, total=3) for index in range(3)]
    result = write_prediction_sidecar_artifacts(
        tmp_path,
        rows,
        metadata={
            "config_id": CONFIG_ID,
            "model_version": MODEL_VERSION,
            "feature_version": FEATURE_VERSION,
            "label_version": LABEL_VERSION,
        },
        expected_row_count=3,
        denominator_scope="SYNTHETIC_TEST_ROWS",
    )
    paths = {name: Path(path) for name, path in result["paths"].items()}
    assert all(path.is_file() for path in paths.values())
    summary = json.loads(paths["summary_path"].read_text(encoding="utf-8"))
    assert summary["row_count"] == 3
    assert sum(summary["split_counts"].values()) == 3
    assert len(summary["sha256"]) == 64
    assert summary["denominator_scope"] == "SYNTHETIC_TEST_ROWS"


def test_compact_whitelist_is_narrow() -> None:
    sidecar = "prediction_payloads/full_dataset_prediction_stream.jsonl"
    assert is_prediction_sidecar_artifact_path(sidecar)
    assert should_preserve_prediction_sidecar_artifact(sidecar)
    assert not should_preserve_prediction_sidecar_artifact("prediction_payloads/raw_feature_dump.jsonl")
    assert not should_preserve_prediction_sidecar_artifact("raw_features/full_dataset_prediction_stream.jsonl")


def test_implementation_metadata_and_decisions_do_not_claim_execution() -> None:
    metadata = build_sidecar_export_implementation_metadata()
    decisions = build_ml38_10_50_sidecar_export_implementation_decision()
    assert metadata["implementation_status"] == "IMPLEMENTED_NOT_EXECUTED"
    assert metadata["real_full_dataset_stream_created"] is False
    assert "REAL_FULL_6481_STREAM_NOT_CREATED" in decisions
    assert "QUICK_QUALITY_RERUN_REQUIRES_SEPARATE_APPROVAL" in decisions

    feature_summary = FeatureRegimeExperimentReporter().compact_summary_to_dict(
        {
            "full_dataset_prediction_sidecar_export_implementation": metadata,
            "ml38_10_50_sidecar_export_implementation_decision": decisions,
        }
    )
    multi_summary = MultiSymbolFeatureRegimeReporter().compact_summary_to_dict(
        {
            "full_dataset_prediction_sidecar_export_implementation": metadata,
            "ml38_10_50_sidecar_export_implementation_decision": decisions,
        }
    )
    assert feature_summary["full_dataset_prediction_sidecar_export_implementation"] == metadata
    assert multi_summary["ml38_10_50_sidecar_export_implementation_decision"] == decisions
