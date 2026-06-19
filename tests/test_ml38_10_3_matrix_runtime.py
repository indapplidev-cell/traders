from __future__ import annotations

from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix
from app.labels.label_quality_grid import LabelQualityGridPlanner


def test_class_margin_configs_are_in_grid_and_matrix() -> None:
    grid_payload = LabelQualityGridPlanner().build_grid()
    matrix_payload = ML382FV3TuningMatrix().build()
    grid_configs = {item["config_id"]: item for item in grid_payload["configs"]}

    for config_id in (
        "lv14_h08_cm_setup",
        "lv14_h12_cm_setup",
        "lv14_h16_cm_setup",
    ):
        assert config_id in grid_configs
        assert grid_configs[config_id]["class_margin_objective_enabled"] is True
        assert config_id in matrix_payload["config_ids"]

    assert matrix_payload["class_margin_stage"] == "ML38.10.3"
    assert matrix_payload["class_margin_config_count"] == 3
