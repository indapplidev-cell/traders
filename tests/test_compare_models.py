from pathlib import Path

from app.dataset.dataset_builder import DatasetBuilder
from app.dataset.dataset_exporter import DatasetExporter
from app.diagnostics import diagnostics_service as diagnostics_service_module
from app.diagnostics.diagnostics_service import DiagnosticsService
from app.registry.artifact_storage import ArtifactStorage


def test_compare_models_does_not_activate_any_model(monkeypatch, tmp_path: Path) -> None:
    class FakeBaselineService:
        def __init__(self, dataset_builder, reports_dir):
            self.dataset_builder = dataset_builder
            self.reports_dir = reports_dir

        def evaluate(self, **kwargs):
            return {
                "baselines": {
                    "always_flat": {"test": {"accuracy": 0.2, "brier_score": 0.9}},
                    "majority_class": {"test": {"accuracy": 0.3, "brier_score": 0.8}},
                }
            }

    monkeypatch.setattr(diagnostics_service_module, "BaselineService", FakeBaselineService)
    monkeypatch.setattr(
        DiagnosticsService,
        "model_report",
        lambda self, model_version, **kwargs: {
            "report_path": str(tmp_path / f"{model_version}.json"),
            "accuracy_test": 0.4 if model_version == "mv_new" else 0.25,
            "brier_score_test": 0.7 if model_version == "mv_new" else 0.85,
            "collapse_detected": False,
            "collapse_reason": None,
            "predicted_counts_test": {"UP": 5, "DOWN": 3, "FLAT": 2},
            "actual_counts_test": {"UP": 4, "DOWN": 4, "FLAT": 2},
        },
    )

    registry_repository = FakeModelRegistryRepository()
    dataset_builder = DatasetBuilder(
        feature_repository=FakeFeatureRepository(),
        label_repository=FakeLabelRepository(),
        dataset_exporter=DatasetExporter(reports_dir=tmp_path / "reports"),
    )
    service = DiagnosticsService(
        dataset_builder=dataset_builder,
        feature_repository=FakeFeatureRepository(),
        model_registry_repository=registry_repository,
        artifact_storage=ArtifactStorage(base_dir=tmp_path / "artifacts"),
        reports_dir=tmp_path / "reports",
    )

    result = service.compare_models(
        symbol="BTCUSDT",
        interval="15m",
        horizon_candles=8,
        feature_version="fv1",
        label_version="lv1",
    )

    assert registry_repository.activation_calls == 0
    assert result["best_model"]["model_version"] == "mv_new"
    assert result["is_best_model_better_than_best_baseline"] is True


class FakeFeatureRepository:
    def get_all(self, symbol: str, interval: str, feature_version: str):
        return []


class FakeLabelRepository:
    def get_all(self, symbol: str, interval: str, horizon_candles: int, label_version: str):
        return []


class FakeModelRegistryRepository:
    def __init__(self) -> None:
        self.activation_calls = 0

    def list_all(self):
        return [
            {
                "model_version": "mv_old",
                "symbol": "BTCUSDT",
                "interval": "15m",
                "horizon_candles": 8,
                "feature_version": "fv1",
                "label_version": "lv1",
                "is_active": True,
            },
            {
                "model_version": "mv_new",
                "symbol": "BTCUSDT",
                "interval": "15m",
                "horizon_candles": 8,
                "feature_version": "fv1",
                "label_version": "lv1",
                "is_active": False,
            },
        ]


def test_compare_models_skips_incompatible_legacy_artifacts(monkeypatch, tmp_path: Path) -> None:
    class FakeBaselineService:
        def __init__(self, dataset_builder, reports_dir):
            self.dataset_builder = dataset_builder
            self.reports_dir = reports_dir

        def evaluate(self, **kwargs):
            return {
                "baselines": {
                    "always_flat": {"test": {"accuracy": 0.2, "brier_score": 0.9}},
                    "majority_class": {"test": {"accuracy": 0.3, "brier_score": 0.8}},
                }
            }

    def fake_model_report(self, model_version, **kwargs):
        if model_version == "mv_old":
            raise RuntimeError("legacy artifact incompatible with ML38.8 CandleMLP")
        return {
            "report_path": str(tmp_path / f"{model_version}.json"),
            "accuracy_test": 0.41,
            "brier_score_test": 0.7,
            "collapse_detected": False,
            "collapse_reason": None,
            "predicted_counts_test": {"UP": 5, "DOWN": 3, "FLAT": 2},
            "actual_counts_test": {"UP": 4, "DOWN": 4, "FLAT": 2},
        }

    monkeypatch.setattr(diagnostics_service_module, "BaselineService", FakeBaselineService)
    monkeypatch.setattr(DiagnosticsService, "model_report", fake_model_report)

    service = DiagnosticsService(
        dataset_builder=DatasetBuilder(
            feature_repository=FakeFeatureRepository(),
            label_repository=FakeLabelRepository(),
            dataset_exporter=DatasetExporter(reports_dir=tmp_path / "reports"),
        ),
        feature_repository=FakeFeatureRepository(),
        model_registry_repository=FakeModelRegistryRepository(),
        artifact_storage=ArtifactStorage(base_dir=tmp_path / "artifacts"),
        reports_dir=tmp_path / "reports",
    )

    result = service.compare_models(
        symbol="BTCUSDT",
        interval="15m",
        horizon_candles=8,
        feature_version="fv1",
        label_version="lv1",
        skip_incompatible_models=True,
    )

    assert result["best_model"]["model_version"] == "mv_new"
    assert result["skipped_model_count"] == 1
    assert result["skipped_model_errors"][0]["model_version"] == "mv_old"
    assert "legacy artifact incompatible" in result["skipped_model_errors"][0]["error"]
