from __future__ import annotations

from pathlib import Path

from app.dataset.dataset_builder import DatasetBuilder
from app.dataset.dataset_exporter import DatasetExporter
from app.registry.artifact_storage import ArtifactStorage
from app.registry.model_registry import ModelRegistry
from app.training.trainer import Trainer
from app.training.training_service import TrainingService
from tests.test_training_service import FakeFeatureRepository
from tests.test_training_service import FakeLabelRepository
from tests.test_training_service import FakeModelRegistryRepository
from tests.test_training_service import FakeTrainingRunRepository


def test_training_service_persists_threshold_control_configuration(tmp_path: Path) -> None:
    dataset_builder = DatasetBuilder(
        feature_repository=FakeFeatureRepository(),
        label_repository=FakeLabelRepository(),
        dataset_exporter=DatasetExporter(reports_dir=tmp_path / "reports"),
    )
    registry_repository = FakeModelRegistryRepository()
    training_run_repository = FakeTrainingRunRepository()
    artifact_storage = ArtifactStorage(base_dir=tmp_path / "artifacts")
    model_registry = ModelRegistry(repository=registry_repository, artifact_storage=artifact_storage)
    service = TrainingService(
        dataset_builder=dataset_builder,
        model_registry=model_registry,
        training_run_repository=training_run_repository,
        artifact_storage=artifact_storage,
        trainer=Trainer(epochs=1),
    )

    result = service.train(
        symbol="BTCUSDT",
        interval="15m",
        horizon_candles=8,
        feature_version="fv1",
        label_version="lv16_h08_trade_two_stage",
        model_name="candle_mlp",
        training_objective="trade_two_stage",
        opportunity_probability_threshold=0.60,
        opportunity_threshold_sweep_enabled=True,
        opportunity_threshold_candidates=(0.50, 0.60, 0.70),
        opportunity_min_precision=0.25,
        opportunity_min_recall=0.50,
        opportunity_max_predicted_trade_rate=0.20,
        opportunity_max_predicted_to_actual_trade_rate_ratio=3.0,
        opportunity_max_false_positive_rate=0.50,
    )

    assert result["opportunity_threshold_sweep_enabled"] is True
    assert result["opportunity_threshold_candidates"] == [0.50, 0.60, 0.70]
    assert result["selected_opportunity_threshold"] in (0.50, 0.60, 0.70)
    assert isinstance(result["opportunity_threshold_selection"], dict)
    assert result["test_metrics"]["opportunity_probability_threshold"] == result["selected_opportunity_threshold"]

    training_config = artifact_storage.load_json(result["model_version"], "training_config.json")
    assert training_config["opportunity_threshold_sweep_enabled"] is True
    assert training_config["selected_opportunity_threshold"] in [0.50, 0.60, 0.70]
    assert isinstance(training_config["opportunity_threshold_selection"], dict)
