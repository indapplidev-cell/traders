from app.experiments.ml38_2_fv3_tuning_matrix import ML38_9_FLAT_BIAS_CONFIG_IDS
from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix
from app.labels.label_quality_grid import LabelQualityGridPlanner


def test_ml38_9_label_grid_contains_flat_bias_configs() -> None:
    payload = LabelQualityGridPlanner().build_grid()
    config_ids = {item["config_id"] for item in payload["configs"]}

    for config_id in ML38_9_FLAT_BIAS_CONFIG_IDS:
        assert config_id in config_ids


def test_ml38_9_fv3_matrix_includes_flat_bias_configs() -> None:
    payload = ML382FV3TuningMatrix().build()

    assert payload["flat_bias_stage"] == "ML38.9"
    assert payload["flat_bias_config_count"] == len(ML38_9_FLAT_BIAS_CONFIG_IDS)
    for config_id in ML38_9_FLAT_BIAS_CONFIG_IDS:
        assert config_id in payload["config_ids"]
