import json
from pathlib import Path

from app.diagnostics.diagnostics_service import DiagnosticsService
from app.registry.artifact_storage import ArtifactStorage


def test_robust_summary_does_not_recommend_model_when_fold_count_is_too_low(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    _write_walk_forward_report(reports_dir, fold_count=2, profitable_fold_ratio=1.0, signal_count=100)

    service = _service(tmp_path, reports_dir)
    result = service.robust_experiment_summary(symbol="BTCUSDT", interval="15m")

    assert result["robust_recommended_model_version"] is None
    assert "fold_count_lt_3" in result["reject_reasons"]


def test_robust_summary_does_not_recommend_model_when_profitable_ratio_is_too_low(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    _write_walk_forward_report(reports_dir, fold_count=4, profitable_fold_ratio=0.5, signal_count=100)

    service = _service(tmp_path, reports_dir)
    result = service.robust_experiment_summary(symbol="BTCUSDT", interval="15m")

    assert result["robust_recommended_model_version"] is None
    assert "profitable_fold_ratio_lt_0_60" in result["reject_reasons"]


def test_robust_summary_does_not_recommend_model_when_signal_count_is_too_low(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    _write_walk_forward_report(reports_dir, fold_count=4, profitable_fold_ratio=0.75, signal_count=20)

    service = _service(tmp_path, reports_dir)
    result = service.robust_experiment_summary(symbol="BTCUSDT", interval="15m")

    assert result["robust_recommended_model_version"] is None
    assert "total_test_signal_count_lt_50" in result["reject_reasons"]


def test_robust_summary_respects_require_both_directions_flag(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    _write_walk_forward_report(reports_dir, fold_count=4, profitable_fold_ratio=0.75, signal_count=100, short_total_count=0)

    service = _service(tmp_path, reports_dir)
    result_required = service.robust_experiment_summary(symbol="BTCUSDT", interval="15m", require_both_directions=True)
    result_optional = service.robust_experiment_summary(symbol="BTCUSDT", interval="15m", require_both_directions=False)

    assert "no_short_signals" in result_required["reject_reasons"]
    assert "no_short_signals" not in result_optional["reject_reasons"]


def _write_walk_forward_report(
    reports_dir: Path,
    fold_count: int,
    profitable_fold_ratio: float,
    signal_count: int,
    short_total_count: int = 10,
) -> None:
    (reports_dir / "walk_forward_eval_mv1.json").write_text(
        json.dumps(
            {
                "model_version": "mv1",
                "label_version": "lv1",
                "folds": [
                    {"selected_gate": {"threshold": 0.4, "gate_type": "max_prob"}}
                    for _ in range(fold_count)
                ],
                "summary": {
                    "fold_count": fold_count,
                    "folds_with_selected_gate": max(2, fold_count - 1),
                    "total_test_signal_count": signal_count,
                    "total_test_r": 10.0,
                    "avg_test_profit_factor": 1.5,
                    "avg_test_expectancy_r": 0.2,
                    "global_total_r": 10.0,
                    "global_profit_factor": 1.5,
                    "global_expectancy_r": 0.2,
                    "global_win_rate": 0.6,
                    "global_max_drawdown_r": 2.0,
                    "profitable_fold_ratio": profitable_fold_ratio,
                    "stable_gate_types": {"max_prob": 3},
                    "dominant_class_ratio_max": 0.5,
                    "bias_warnings": [],
                    "long_total_count": signal_count,
                    "short_total_count": short_total_count,
                },
            }
        ),
        encoding="utf-8",
    )


def _service(tmp_path: Path, reports_dir: Path) -> DiagnosticsService:
    return DiagnosticsService(
        dataset_builder=object(),
        feature_repository=object(),
        label_repository=object(),
        candle_repository=object(),
        model_registry_repository=object(),
        artifact_storage=ArtifactStorage(base_dir=tmp_path / "artifacts"),
        reports_dir=reports_dir,
    )
