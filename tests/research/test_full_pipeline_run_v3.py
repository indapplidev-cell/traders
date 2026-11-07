from __future__ import annotations

from pathlib import Path

import pytest

from traders_ml.parameter_sweep.full_pipeline import FullPipelineCalibrationRequestV2
from traders_ml.parameter_sweep.full_pipeline_run_v3 import (
    preholdout_role_windows_v3,
    run_preholdout_role_v3,
)

REQUEST = Path(__file__).parents[2] / "config/research/full_pipeline_calibration_v2.json"


def test_role_windows_exclude_validation_from_train_and_stop_at_holdout() -> None:
    request = FullPipelineCalibrationRequestV2.model_validate_json(REQUEST.read_text())
    roles = preholdout_role_windows_v3(request)
    validation = [window for window in request.windows if window.role == "VALIDATION"]
    holdout = next(window for window in request.windows if window.role == "INTERNAL_HOLDOUT")
    assert set(roles).isdisjoint({"INTERNAL_HOLDOUT", "NOVEMBER_2026"})
    assert all(end <= holdout.start_ms for _, end in roles.values())
    assert all(roles[window.name] == (window.start_ms, window.end_ms)
               for window in validation)
    assert all(not (start < window.end_ms and end > window.start_ms)
               for name, (start, end) in roles.items() if name.startswith("TRAIN_")
               for window in validation)


def test_locked_holdout_role_rejected_before_any_source_read(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset"
    cache = tmp_path / "cache"
    signals = tmp_path / "signals"
    with pytest.raises(ValueError, match="V3_UNKNOWN_PREHOLDOUT_ROLE"):
        run_preholdout_role_v3(REQUEST, dataset, cache, signals,
                               tmp_path / "result.json", "INTERNAL_HOLDOUT", {})
    assert not (tmp_path / "result.json").exists()
