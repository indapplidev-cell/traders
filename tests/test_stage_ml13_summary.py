import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from app.diagnostics.diagnostics_service import DiagnosticsService
from app.meta_label.meta_dataset_builder import MetaDatasetBuilder
from app.meta_label.meta_label_models import MetaLabelRecord
from app.registry.artifact_storage import ArtifactStorage


def test_stage_ml13_summary_returns_recommended_next_action(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        reports_dir / "baseline_by_regime_BTCUSDT_15m_fv2_regime.json",
        {
            "best_baseline_overall": {
                "baseline_name": "ema_9_21_direction",
                "total_r": 10.0,
                "global_profit_factor": 1.2,
            },
            "regimes_where_ema_9_21_works": ["regime_trend_up"],
            "regimes_where_ema_9_21_fails": ["regime_range"],
        },
    )
    _write_json(reports_dir / "regime_segment_diagnostics_BTCUSDT_15m_fv2_regime.json", {"segments": {}})
    _write_json(reports_dir / "ema_meta_labels_BTCUSDT_15m_meta_ema_9_21_tp15_sl10.json", {"rows": []})
    _write_json(reports_dir / "meta_label_diagnostics_BTCUSDT_15m_meta_ema_9_21_tp15_sl10.json", {"warnings": []})
    _write_json(
        reports_dir / "meta_dataset_BTCUSDT_15m_meta_ema_9_21_tp15_sl10.json",
        {"meta_dataset_valid": True, "dataset_rows": 1500, "long_rows": 700, "short_rows": 800},
    )
    _write_json(
        reports_dir / "meta_baselines_BTCUSDT_15m_meta_ema_9_21_tp15_sl10.json",
        {
            "baselines": {
                "take_all_ema_signals": {
                    "summary": {"total_r": 12.0, "global_profit_factor": 1.1}
                }
            }
        },
    )
    _write_json(
        reports_dir / "meta_training_BTCUSDT_15m_meta_ema_9_21_tp15_sl10.json",
        {"meta_training_skipped": False, "model_version": "meta_v1"},
    )
    _write_json(
        reports_dir / "walk_forward_meta_eval_meta_v1.json",
        {
            "folds": [
                {"selected_gate": {"gate_type": "prob_win", "threshold": 0.55}},
                {"selected_gate": {"gate_type": "prob_win", "threshold": 0.55}},
            ],
            "summary": {
                "global_total_r": 18.0,
                "global_profit_factor": 1.4,
                "total_test_signal_count": 80,
                "long_total_count": 40,
                "short_total_count": 40,
                "profitable_fold_ratio": 1.0,
            },
        },
    )

    service = DiagnosticsService(
        dataset_builder=object(),
        feature_repository=object(),
        label_repository=object(),
        candle_repository=object(),
        model_registry_repository=FakeModelRegistryRepository(),
        artifact_storage=ArtifactStorage(base_dir=tmp_path / "artifacts"),
        reports_dir=reports_dir,
    )

    result = service.stage_ml13_summary(symbol="BTCUSDT", interval="15m")

    assert result["recommended_model_version"] == "meta_v1"
    assert result["recommended_meta_threshold"] == 0.55
    assert result["recommended_next_action"] == "prepare_manual_activation_review"


def test_train_meta_skips_when_dataset_invalid(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    feature_row = SimpleNamespace(
        symbol="BTCUSDT",
        interval="15m",
        candle_open_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        features_json={"f1": 1.0},
    )
    meta_label = MetaLabelRecord(
        symbol="BTCUSDT",
        interval="15m",
        candle_open_time=feature_row.candle_open_time,
        feature_version="fv2_regime",
        label_version="meta_ema_9_21_tp15_sl10",
        horizon_candles=16,
        ema_signal_direction="LONG",
        ema_signal_strength_atr=0.5,
        meta_label="WIN",
        meta_target_win=1,
        meta_trade_r=1.0,
        meta_same_candle_ambiguous=False,
    )
    _write_json(
        reports_dir / "ema_meta_labels_BTCUSDT_15m_meta_ema_9_21_tp15_sl10.json",
        {"rows": [meta_label.to_summary_dict()]},
    )
    meta_dataset_builder = FakeMetaDatasetBuilder()
    service = DiagnosticsService(
        dataset_builder=object(),
        feature_repository=FakeFeatureRepository([feature_row]),
        label_repository=object(),
        model_registry_repository=FakeModelRegistryRepository(),
        artifact_storage=ArtifactStorage(base_dir=tmp_path / "artifacts"),
        reports_dir=reports_dir,
        meta_dataset_builder=meta_dataset_builder,
        meta_training_service=FakeMetaTrainingService(),
    )

    result = service.train_meta(
        symbol="BTCUSDT",
        interval="15m",
        horizon_candles=16,
        feature_version="fv2_regime",
        label_version="meta_ema_9_21_tp15_sl10",
    )

    assert result["meta_training_skipped"] is True
    assert result["reason"] == "meta_dataset_invalid"


class FakeFeatureRepository:
    def __init__(self, rows):
        self._rows = rows

    def get_all(self, **kwargs):
        return list(self._rows)


class FakeMetaDatasetBuilder:
    def build_rows(self, feature_rows, meta_labels, feature_version):
        return [], {
            "dataset_rows": 0,
            "positive_class_ratio": 0.0,
            "negative_class_ratio": 0.0,
            "long_rows": 0,
            "short_rows": 0,
            "excluded_no_trade": 0,
            "excluded_ambiguous": 0,
            "excluded_no_exit": 0,
            "meta_dataset_valid": False,
        }

    def split_rows(self, dataset_rows):
        return {"train": [], "validation": [], "test": []}


class FakeMetaTrainingService:
    def train(self, **kwargs):
        return {"meta_training_skipped": True, "reason": "meta_dataset_invalid"}


class FakeModelRegistryRepository:
    def create(self, payload):
        raise AssertionError("create must not be called for invalid meta dataset")


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
