from app.labels.label_quality_grid import LabelQualityGridPlanner


LV25_EXPECTED_LABEL_VERSIONS = {
    "lv25_h08_tts_thr065_sqmask060_epq070_sp045_exit_mit": "lv25_h08_tts_epq70_sp45_xmit",
    "lv25_h12_tts_thr065_sqmask060_epq070_sp045_exit_mit": "lv25_h12_tts_epq70_sp45_xmit",
    "lv25_h12_tts_thr065_sqmask060_epq072_sp043_exit_mit_strict": "lv25_h12_tts_epq72_sp43_xmit_strict",
}


def test_ml38_10_17_1_lv25_label_versions_fit_ml_labels_db_limit() -> None:
    grid = LabelQualityGridPlanner().build_grid()
    configs_by_id = {item["config_id"]: item for item in grid["configs"]}

    for config_id, expected_label_version in LV25_EXPECTED_LABEL_VERSIONS.items():
        payload = configs_by_id[config_id]
        assert payload["label_version"] == expected_label_version
        assert len(payload["label_version"]) <= 50


def test_ml38_10_17_1_all_label_versions_fit_current_db_limit() -> None:
    grid = LabelQualityGridPlanner().build_grid()
    too_long = [
        (item["config_id"], item["label_version"], len(item["label_version"]))
        for item in grid["configs"]
        if len(str(item["label_version"])) > 50
    ]
    assert too_long == []
