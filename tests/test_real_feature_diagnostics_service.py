import json

from app.diagnostics.real_feature_diagnostics_service import RealFeatureDiagnosticsService


def test_real_feature_diagnostics_service_uses_real_row_count() -> None:
    rows = [
        {"direction_label": "UP", "features_json": {"return_1": 0.01, "regime_trend_up": 1.0}},
        {"direction_label": "DOWN", "features_json": {"return_1": -0.01, "regime_trend_up": 0.0}},
    ]

    payload = RealFeatureDiagnosticsService().analyze(
        symbol="BTCUSDT",
        interval="15m",
        feature_version="fv2",
        label_version="lv2_h08_thr04_tp10_sl10",
        rows=rows,
        source="dataset_builder",
    )

    assert payload["sample_mode"] is False
    assert payload["degraded_mode"] is False
    assert payload["real_feature_diagnostics_used"] is True
    assert payload["row_count"] == 2
    assert payload["feature_count"] == 2
    json.dumps(payload, ensure_ascii=False, sort_keys=True)


def test_real_feature_diagnostics_service_marks_sample_mode_explicitly() -> None:
    payload = RealFeatureDiagnosticsService().analyze(
        symbol="BTCUSDT",
        interval="15m",
        feature_version="fv2",
        label_version="lv2_h08_thr04_tp10_sl10",
        rows=[{"direction_label": "UP", "features_json": {"return_1": 0.01}}],
        source="sample_rows",
        sample_mode=True,
    )

    assert payload["sample_mode"] is True
    assert payload["real_feature_diagnostics_used"] is False


def test_real_feature_diagnostics_service_reports_degraded_mode_when_rows_are_unavailable() -> None:
    payload = RealFeatureDiagnosticsService().analyze(
        symbol="BTCUSDT",
        interval="15m",
        feature_version="fv2",
        label_version="lv2_h08_thr04_tp10_sl10",
        rows=[],
        source="dataset_builder",
        reason="dataset_rows_unavailable",
    )

    assert payload["degraded_mode"] is True
    assert payload["row_count"] == 0
    assert payload["real_feature_diagnostics_used"] is False
    assert "dataset_rows_unavailable" in payload["warnings"]
