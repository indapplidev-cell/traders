import json
from pathlib import Path

from app.diagnostics.diagnostics_service import DiagnosticsService
from app.registry.artifact_storage import ArtifactStorage


def test_stage_ml12_summary_recommends_latest_eligible_model(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        reports_dir / "feature_diagnostics_v2_BTCUSDT_15m_fv2_regime.json",
        {"total_rows": 100, "feature_count": 77},
    )
    _write_json(
        reports_dir / "dataset_summary_btcusdt_15m_h16_fv2_regime_lv_h16_thr03_tp15_sl10.json",
        {"label_version": "lv_h16_thr03_tp15_sl10", "dataset_rows": 1500},
    )
    _write_json(
        reports_dir / "dataset_summary_btcusdt_15m_h16_fv2_regime_lv_h16_thr03_tp10_sl10.json",
        {"label_version": "lv_h16_thr03_tp10_sl10", "dataset_rows": 1400},
    )
    _write_json(
        reports_dir / "model_vs_baseline_mv_newer.json",
        {
            "model_version": "mv_newer",
            "baseline_name": "ema_9_21_direction",
            "model_global_total_r": 18.0,
            "model_global_profit_factor": 1.6,
            "model_global_expectancy_r": 0.2,
            "model_beats_baseline_by_total_r": True,
            "model_beats_baseline_by_profit_factor": True,
            "recommendation_allowed": True,
            "reject_reasons": [],
        },
    )
    _write_json(
        reports_dir / "model_vs_baseline_mv_old.json",
        {
            "model_version": "mv_old",
            "baseline_name": "ema_9_21_direction",
            "model_global_total_r": 6.0,
            "model_global_profit_factor": 0.9,
            "model_global_expectancy_r": 0.01,
            "model_beats_baseline_by_total_r": False,
            "model_beats_baseline_by_profit_factor": False,
            "recommendation_allowed": False,
            "reject_reasons": ["model_total_r_not_above_baseline"],
        },
    )
    _write_walk_forward(
        reports_dir / "walk_forward_eval_mv_newer.json",
        model_version="mv_newer",
        total_r=18.0,
        profit_factor=1.6,
        expectancy=0.2,
        short_count=40,
        dominant_class_ratio=0.72,
    )
    _write_walk_forward(
        reports_dir / "walk_forward_eval_mv_old.json",
        model_version="mv_old",
        total_r=6.0,
        profit_factor=0.9,
        expectancy=0.01,
        short_count=5,
        dominant_class_ratio=0.88,
    )

    service = DiagnosticsService(
        dataset_builder=object(),
        feature_repository=object(),
        label_repository=object(),
        candle_repository=object(),
        model_registry_repository=FakeModelRegistryRepository(
            [
                _model_row("mv_very_old", "2026-06-09T10:00:00+00:00"),
                _model_row("mv_old", "2026-06-09T11:00:00+00:00"),
                _model_row("mv_newer", "2026-06-09T12:00:00+00:00"),
            ]
        ),
        artifact_storage=ArtifactStorage(base_dir=tmp_path / "artifacts"),
        reports_dir=reports_dir,
    )

    result = service.stage_ml12_summary(symbol="BTCUSDT", interval="15m")

    assert result["models_trained"] == ["mv_newer", "mv_old"]
    assert result["best_model_version"] == "mv_newer"
    assert result["best_baseline"] == "ema_9_21_direction"
    assert result["model_beats_baseline"] is True
    assert result["short_signals_restored"] is True
    assert result["dominant_class_ratio_improved"] is True
    assert result["recommended_model_version"] == "mv_newer"
    assert result["recommended_next_action"] == "prepare_manual_activation_review"
    assert result["feature_diagnostics_report"].endswith("feature_diagnostics_v2_BTCUSDT_15m_fv2_regime.json")


class FakeModelRegistryRepository:
    def __init__(self, rows):
        self._rows = rows

    def list_all(self):
        return list(self._rows)


def _model_row(model_version: str, created_at: str) -> dict[str, str | bool | None]:
    return {
        "model_version": model_version,
        "model_name": "candle_mlp",
        "symbol": "BTCUSDT",
        "interval": "15m",
        "horizon_candles": 16,
        "feature_version": "fv2_regime",
        "label_version": "lv_h16_thr03_tp15_sl10",
        "accuracy": None,
        "brier_score": None,
        "is_active": False,
        "artifact_path": "artifacts/models",
        "created_at": created_at,
    }


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_walk_forward(
    path: Path,
    model_version: str,
    total_r: float,
    profit_factor: float,
    expectancy: float,
    short_count: int,
    dominant_class_ratio: float,
) -> None:
    _write_json(
        path,
        {
            "model_version": model_version,
            "folds": [
                {"selected_gate": {"gate_type": "max_prob", "threshold": 0.4}},
                {"selected_gate": {"gate_type": "max_prob", "threshold": 0.4}},
                {"selected_gate": {"gate_type": "max_prob", "threshold": 0.4}},
                {"selected_gate": {"gate_type": "max_prob", "threshold": 0.4}},
            ],
            "summary": {
                "fold_count": 4,
                "folds_with_selected_gate": 4,
                "total_test_signal_count": 120,
                "global_total_r": total_r,
                "global_profit_factor": profit_factor,
                "global_expectancy_r": expectancy,
                "profitable_fold_ratio": 0.75,
                "dominant_class_ratio_max": dominant_class_ratio,
                "long_total_count": 80,
                "short_total_count": short_count,
            },
        },
    )
