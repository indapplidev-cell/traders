import json
from pathlib import Path

from app.diagnostics.diagnostics_service import DiagnosticsService
from app.registry.artifact_storage import ArtifactStorage


def test_experiment_summary_v2_does_not_recommend_model_when_signal_count_is_too_low(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    _write_common_reports(reports_dir, signal_count=20, profit_factor=1.5, total_r=5.0, expectancy_r=0.25)

    service = _build_service(tmp_path, reports_dir)
    result = service.experiment_summary_v2(symbol="BTCUSDT", interval="15m")

    assert result["recommended_model_version"] is None
    assert "signal_count_lt_50" in result["reject_reasons"]


def test_experiment_summary_v2_does_not_recommend_model_when_profit_factor_is_not_positive(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    _write_common_reports(reports_dir, signal_count=100, profit_factor=1.0, total_r=5.0, expectancy_r=0.05)

    service = _build_service(tmp_path, reports_dir)
    result = service.experiment_summary_v2(symbol="BTCUSDT", interval="15m")

    assert result["recommended_model_version"] is None
    assert "profit_factor_not_above_1" in result["reject_reasons"]


def test_experiment_summary_v2_recommends_model_only_when_all_conditions_hold(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    _write_common_reports(reports_dir, signal_count=120, profit_factor=1.8, total_r=12.0, expectancy_r=0.1)

    service = _build_service(tmp_path, reports_dir)
    result = service.experiment_summary_v2(symbol="BTCUSDT", interval="15m")

    assert result["recommended_model_version"] == "mv1"
    assert result["recommended_gate_type"] == "directional_edge"
    assert result["recommended_gate_threshold"] == 0.05
    assert result["recommended_label_version"] == "lv1"


def _write_common_reports(reports_dir: Path, signal_count: int, profit_factor: float, total_r: float, expectancy_r: float) -> None:
    (reports_dir / "probability_diagnostics_mv1.json").write_text(
        json.dumps(
            {
                "model_version": "mv1",
                "predicted_direction_counts": {"UP": 60, "DOWN": 40, "FLAT": 0},
                "predicted_direction_ratios": {"UP": 0.6, "DOWN": 0.4, "FLAT": 0.0},
                "avg_prob_up": 0.4,
                "avg_prob_down": 0.35,
                "avg_prob_flat": 0.25,
                "collapse_v2": {"collapse_detected": False, "dominant_class_ratio": 0.6},
            }
        ),
        encoding="utf-8",
    )
    (reports_dir / "profit_eval_v2_mv1.json").write_text(
        json.dumps(
            {
                "model_version": "mv1",
                "gate_results": [
                    {
                        "gate_type": "directional_edge",
                        "threshold": 0.05,
                        "signal_count": signal_count,
                        "profit_factor": profit_factor,
                        "total_r": total_r,
                        "expectancy_r": expectancy_r,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (reports_dir / "calibration_eval_mv1.json").write_text(
        json.dumps({"model_version": "mv1", "expected_calibration_error": 0.05, "brier_score": 0.6}),
        encoding="utf-8",
    )
    (reports_dir / "model_comparison_btcusdt_15m_h8.json").write_text(
        json.dumps(
            {
                "label_version": "lv1",
                "best_baseline": {"test_metrics": {"accuracy": 0.3}},
                "model_results": [{"model_version": "mv1", "accuracy": 0.45, "brier_score": 0.6}],
            }
        ),
        encoding="utf-8",
    )


def _build_service(tmp_path: Path, reports_dir: Path) -> DiagnosticsService:
    return DiagnosticsService(
        dataset_builder=object(),
        feature_repository=object(),
        label_repository=object(),
        candle_repository=object(),
        model_registry_repository=object(),
        artifact_storage=ArtifactStorage(base_dir=tmp_path / "artifacts"),
        reports_dir=reports_dir,
    )
