from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import math
from pathlib import Path

import pytest

from app.experiments.prediction_sidecar_exporter import (
    PREDICTION_FIELD_CONTRACT_VERSION,
    SIDECAR_SCHEMA_VERSION,
    WRITER_CONTRACT_VERSION,
    build_prediction_row_alignment_key,
    validate_prediction_sidecar_rows,
    write_prediction_sidecar_artifacts,
)
from app.experiments.prediction_sidecar_wiring import (
    build_full_dataset_prediction_sidecar_rows,
)


IDENTITY = {
    "symbol": "SYNTHUSDT",
    "interval": "15m",
    "feature_version": "fv-test",
    "label_version": "lv-test",
    "horizon_candles": 12,
    "config_id": "cfg-test",
    "model_name": "synthetic-model",
    "model_version": "model-test",
    "run_id": "run-test",
    "candidate_id": "candidate-test",
}


def _source(index: int, label: str) -> dict:
    return {
        "candle_open_time": datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=15 * index),
        "direction_label": label,
    }


def _rows() -> list[dict]:
    return build_full_dataset_prediction_sidecar_rows(
        split_rows={
            "train": [_source(0, "DOWN"), _source(1, "UP")],
            "validation": [_source(2, "FLAT")],
            "test": [_source(3, "DOWN")],
        },
        split_probabilities={
            "train": [[0.60, 0.30, 0.10], [0.20, 0.70, 0.10]],
            "validation": [[0.15, 0.15, 0.70]],
            "test": [[0.10, 0.80, 0.10]],
        },
        split_direction_logits={
            "train": [[1.0, 2.0, 0.0], [2.0, 1.0, 0.0]],
            "validation": [[0.0, 0.0, 2.0]],
            "test": [[0.0, 2.0, 0.0]],
        },
        **IDENTITY,
    )


def _validation(rows: list[dict]) -> dict:
    return validate_prediction_sidecar_rows(
        rows,
        expected_row_count=len(rows),
        denominator_scope="SYNTHETIC_FIELD_CONTRACT",
        expected_config_id=IDENTITY["config_id"],
        expected_candidate_id=IDENTITY["candidate_id"],
        expected_run_id=IDENTITY["run_id"],
        expected_model_version=IDENTITY["model_version"],
        expected_feature_version=IDENTITY["feature_version"],
        expected_label_version=IDENTITY["label_version"],
        expected_symbol=IDENTITY["symbol"],
        expected_interval=IDENTITY["interval"],
        expected_horizon_candles=IDENTITY["horizon_candles"],
        require_field_contract=True,
    )


def test_versions_and_complete_synthetic_row_contract() -> None:
    assert SIDECAR_SCHEMA_VERSION == WRITER_CONTRACT_VERSION == PREDICTION_FIELD_CONTRACT_VERSION == "ml38.10.69"
    rows = _rows()
    required = {
        "actual_label", "raw_prob_down", "raw_prob_flat", "raw_prob_up", "raw_probabilities",
        "calibrated_prob_down", "calibrated_prob_flat", "calibrated_prob_up",
        "calibrated_probabilities", "row_alignment_key", "prediction_layers",
        "sidecar_argmax_label", "current_predicted_label", "prediction_field_contract_version",
    }
    assert required <= set(rows[0])
    assert [row["actual_label"] for row in rows] == ["DOWN", "UP", "FLAT", "DOWN"]
    assert _validation(rows)["status"] == "PREDICTION_SIDECAR_VALID"


def test_raw_softmax_and_calibrated_alias_semantics() -> None:
    row = _rows()[0]
    denominator = math.exp(-1.0) + 1.0 + math.exp(-2.0)
    expected = {"UP": math.exp(-1.0) / denominator, "DOWN": 1.0 / denominator, "FLAT": math.exp(-2.0) / denominator}
    assert set(row["raw_probabilities"]) == {"DOWN", "FLAT", "UP"}
    assert set(row["calibrated_probabilities"]) == {"DOWN", "FLAT", "UP"}
    assert row["raw_probabilities"] == pytest.approx(expected)
    assert sum(row["raw_probabilities"].values()) == pytest.approx(1.0)
    assert sum(row["calibrated_probabilities"].values()) == pytest.approx(1.0)
    assert row["calibrated_probabilities"] == {"DOWN": 0.30, "FLAT": 0.10, "UP": 0.60}
    assert (row["prob_down"], row["prob_flat"], row["prob_up"]) == (
        row["calibrated_prob_down"], row["calibrated_prob_flat"], row["calibrated_prob_up"]
    )


def test_alignment_key_is_deterministic_sensitive_and_unique() -> None:
    first = _rows()
    second = _rows()
    assert [row["row_alignment_key"] for row in first] == [row["row_alignment_key"] for row in second]
    assert len({row["row_alignment_key"] for row in first}) == len(first)
    variants = []
    for field, value in (
        ("candidate_id", "other-candidate"), ("symbol", "OTHERUSDT"),
        ("interval", "5m"), ("horizon_candles", 24),
    ):
        identity = {**IDENTITY, field: value}
        variants.append(build_full_dataset_prediction_sidecar_rows(
            split_rows={"train": [_source(0, "DOWN")]},
            split_probabilities={"train": [[0.6, 0.3, 0.1]]},
            split_direction_logits={"train": [[1.0, 2.0, 0.0]]},
            **identity,
        )[0]["row_alignment_key"])
    assert all(key != first[0]["row_alignment_key"] for key in variants)
    base = {
        "candidate_id": "candidate-test", "symbol": "SYNTHUSDT", "interval": "15m",
        "horizon": 12, "split": "train", "row_index_global": 0,
        "row_index_split": 0, "timestamp": "2026-01-01T00:00:00+00:00",
    }
    base_key = build_prediction_row_alignment_key(**base)
    for field, value in (
        ("split", "val"), ("row_index_global", 1), ("row_index_split", 1),
        ("timestamp", "2026-01-01T00:15:00+00:00"), ("candidate_id", "other"),
    ):
        assert build_prediction_row_alignment_key(**{**base, field: value}) != base_key


def test_prediction_layers_are_explicit_and_policy_is_unavailable() -> None:
    row = _rows()[0]
    assert set(row["prediction_layers"]) == {
        "raw_model_softmax_temperature_1", "calibrated_model_softmax", "sidecar_selected"
    }
    assert row["downstream_policy_output_available_in_writer"] is False
    assert row["downstream_policy_output_must_not_be_conflated_with_sidecar_argmax"] is True
    assert row["sidecar_argmax_layer"] == "calibrated_model_softmax"


@pytest.mark.parametrize(
    "field",
    ["actual_label", "split", "candidate_id", "row_index_global", "row_index_split", "row_alignment_key"],
)
def test_missing_required_fields_fail_closed(field: str) -> None:
    rows = _rows()
    rows[0].pop(field)
    validation = _validation(rows)
    assert validation["status"] == "PREDICTION_SIDECAR_INVALID"
    assert any(f"{field} is required" in error for error in validation["errors"])


def test_missing_direction_logits_fails_closed_in_builder() -> None:
    with pytest.raises(ValueError, match="row/direction_logits count mismatch"):
        build_full_dataset_prediction_sidecar_rows(
            split_rows={"train": [_source(0, "DOWN")]},
            split_probabilities={"train": [[0.6, 0.3, 0.1]]},
            split_direction_logits={"train": []},
            **IDENTITY,
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda row: row["raw_probabilities"].update(DOWN=float("nan")), "numeric and finite"),
        (lambda row: row["raw_probabilities"].update(DOWN=-0.1), "non-negative"),
        (lambda row: row["raw_probabilities"].update(DOWN=0.9), "probability sum"),
        (lambda row: row.update(raw_probabilities={"DOWN": 0.5, "UP": 0.5}), "keys must be exactly"),
    ],
)
def test_invalid_probability_contract_fails_closed(mutation, message: str) -> None:
    rows = deepcopy(_rows())
    mutation(rows[0])
    validation = _validation(rows)
    assert validation["status"] == "PREDICTION_SIDECAR_INVALID"
    assert any(message in error for error in validation["errors"])


def test_duplicate_alignment_key_fails_closed() -> None:
    rows = _rows()
    rows[1]["row_alignment_key"] = rows[0]["row_alignment_key"]
    validation = _validation(rows)
    assert validation["duplicate_row_alignment_key_count"] == 1
    assert validation["status"] == "PREDICTION_SIDECAR_INVALID"


def test_writer_emits_complete_lf_exact_byte_schema_and_summary_contract(tmp_path: Path) -> None:
    rows = _rows()
    result = write_prediction_sidecar_artifacts(
        tmp_path, rows, metadata=IDENTITY, expected_row_count=4,
        denominator_scope="SYNTHETIC_FIELD_CONTRACT",
    )
    paths = {name: Path(value) for name, value in result["paths"].items()}
    exact = paths["stream_path"].read_bytes()
    emitted = [json.loads(line) for line in exact.decode("utf-8").splitlines()]
    assert exact.endswith(b"\n") and b"\r" not in exact
    assert result["summary"]["sha256"] == sha256(exact).hexdigest()
    assert result["summary"]["size_bytes"] == len(exact)
    assert all("actual_label" in row and "prediction_layers" in row for row in emitted)
    assert result["schema"]["schema_version"] == "ml38.10.69"
    assert "raw_probabilities" in result["schema"]["properties"]
    for field in (
        "raw_probabilities_present", "actual_label_present", "row_alignment_key_unique",
        "prediction_layers_present", "calibrated_probabilities_present",
    ):
        assert result["summary"][field] is True
    assert result["summary"]["h08_denominator_fix_applied"] is False


def test_writer_rejects_invalid_rows_before_creating_artifacts(tmp_path: Path) -> None:
    rows = _rows()
    rows[0].pop("actual_label")
    with pytest.raises(ValueError, match="actual_label is required"):
        write_prediction_sidecar_artifacts(
            tmp_path, rows, metadata=IDENTITY, expected_row_count=4,
            denominator_scope="SYNTHETIC_FIELD_CONTRACT",
        )
    assert not (tmp_path / "prediction_payloads").exists()
