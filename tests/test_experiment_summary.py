import json
from pathlib import Path

from app.diagnostics.diagnostics_service import DiagnosticsService
from app.registry.artifact_storage import ArtifactStorage


def test_experiment_summary_does_not_recommend_model_when_profit_factor_is_not_positive(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "label_grid_search_btcusdt_15m.json").write_text(
        json.dumps({"candidates": [{"label_version": "lv1", "reject_reason": "ok", "candidate_score": 1.0}]}),
        encoding="utf-8",
    )
    (reports_dir / "model_comparison_btcusdt_15m_h8.json").write_text(
        json.dumps(
            {
                "label_version": "lv1",
                "best_baseline": {"test_metrics": {"accuracy": 0.3}},
                "model_results": [{"model_version": "mv1", "accuracy": 0.4, "brier_score": 0.6}],
            }
        ),
        encoding="utf-8",
    )
    (reports_dir / "profit_eval_mv1.json").write_text(
        json.dumps({"model_version": "mv1", "thresholds": [{"threshold": 0.5, "profit_factor": 1.0, "signal_count": 100, "total_r": 5.0}]}),
        encoding="utf-8",
    )
    (reports_dir / "calibration_eval_mv1.json").write_text(
        json.dumps({"model_version": "mv1", "expected_calibration_error": 0.1, "brier_score": 0.6}),
        encoding="utf-8",
    )

    service = DiagnosticsService(
        dataset_builder=object(),
        feature_repository=object(),
        label_repository=object(),
        candle_repository=object(),
        model_registry_repository=object(),
        artifact_storage=ArtifactStorage(base_dir=tmp_path / "artifacts"),
        reports_dir=reports_dir,
    )

    result = service.experiment_summary(symbol="BTCUSDT", interval="15m")

    assert result["recommended_model_version"] is None
    assert result["warnings"]
