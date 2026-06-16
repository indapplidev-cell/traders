from app.experiments.ml38_2_fv3_tuning_matrix import (
    ML382FV3TuningMatrix,
    ML38_5_ANTI_COLLAPSE_CONFIG_IDS,
)


def test_ml38_5_fv3_matrix_includes_anti_collapse_configs() -> None:
    payload = ML382FV3TuningMatrix().build()

    assert payload["missing_configs"] == []
    assert payload["config_count"] == 14
    assert payload["anti_collapse_stage"] == "ML38.5"
    assert payload["anti_collapse_config_count"] == 6
    assert set(ML38_5_ANTI_COLLAPSE_CONFIG_IDS).issubset(set(payload["config_ids"]))
