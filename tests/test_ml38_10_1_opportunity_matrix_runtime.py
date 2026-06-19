from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix
from app.labels.label_quality_grid import LabelQualityGridPlanner
from app.labels.label_config import LABEL_MODE_SETUP_PURE_FIRST_TOUCH


def test_opportunity_first_configs_are_in_grid_and_matrix() -> None:
    grid_payload = LabelQualityGridPlanner().build_grid()
    matrix_payload = ML382FV3TuningMatrix().build()
    grid_configs = {item["config_id"]: item for item in grid_payload["configs"]}

    for config_id in (
        "lv13_h08_opportunity_ft",
        "lv13_h12_opportunity_ft",
        "lv13_h16_opportunity_ft",
    ):
        assert config_id in grid_configs
        assert grid_configs[config_id]["training_objective"] == "opportunity_first"
        assert config_id in matrix_payload["config_ids"]

    assert matrix_payload["opportunity_first_stage"] == "ML38.10.1"
    assert matrix_payload["opportunity_first_config_count"] == 3
    assert grid_configs["lv15_h08_setup_pure_ft"]["label_mode"] == LABEL_MODE_SETUP_PURE_FIRST_TOUCH
