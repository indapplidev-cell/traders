from __future__ import annotations

import run_fv3_cached_tuning
from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix
from app.labels.label_quality_grid import LabelQualityGridPlanner


def _matrix_config_ids() -> set[str]:
    payload = ML382FV3TuningMatrix().build()
    assert payload["missing_configs"] == []
    return {str(item) for item in payload["config_ids"]}


def _label_grid_config_ids() -> set[str]:
    payload = LabelQualityGridPlanner().build_grid()
    return {str(item["config_id"]) for item in payload["configs"]}


def test_ml38_10_27_1_fast_debug_configs_are_registered_in_label_grid_and_fv3_matrix() -> None:
    label_ids = _label_grid_config_ids()
    matrix_ids = _matrix_config_ids()

    missing_from_label_grid = [
        config_id
        for config_id in run_fv3_cached_tuning.FAST_DEBUG_CONFIGS
        if config_id not in label_ids
    ]
    missing_from_matrix = [
        config_id
        for config_id in run_fv3_cached_tuning.FAST_DEBUG_CONFIGS
        if config_id not in matrix_ids
    ]

    assert missing_from_label_grid == []
    assert missing_from_matrix == []


def test_ml38_10_27_1_quick_quality_configs_are_registered_in_label_grid_and_fv3_matrix() -> None:
    label_ids = _label_grid_config_ids()
    matrix_ids = _matrix_config_ids()

    missing_from_label_grid = [
        config_id
        for config_id in run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS
        if config_id not in label_ids
    ]
    missing_from_matrix = [
        config_id
        for config_id in run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS
        if config_id not in matrix_ids
    ]

    assert missing_from_label_grid == []
    assert missing_from_matrix == []


def test_ml38_10_27_1_runtime_counts_stay_expected_after_registration_fix() -> None:
    fast_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(
        run_fv3_cached_tuning.parse_args(["--fast-debug"])
    )
    quick_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(
        run_fv3_cached_tuning.parse_args(
            ["--quick-quality", "--quick-quality-symbol", "SOLUSDT"]
        )
    )

    assert len(run_fv3_cached_tuning.FAST_DEBUG_CONFIGS) == 18
    assert len(run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS) == 38
    assert fast_wrapper._expected_candidate_count() == 36
    assert quick_wrapper._expected_candidate_count() == 38


def test_ml38_10_27_1_wrapper_preflight_config_validation_passes_for_runtime_shortlists() -> None:
    fast_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(
        run_fv3_cached_tuning.parse_args(["--fast-debug"])
    )
    quick_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(
        run_fv3_cached_tuning.parse_args(
            ["--quick-quality", "--quick-quality-symbol", "SOLUSDT"]
        )
    )

    fast_wrapper._validate_selected_config_ids_registered()
    quick_wrapper._validate_selected_config_ids_registered()
