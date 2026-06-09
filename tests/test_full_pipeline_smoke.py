from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.db.models  # noqa: F401
from app.dataset.dataset_builder import DatasetBuilder
from app.dataset.dataset_exporter import DatasetExporter
from app.db.base import Base
from app.db.repositories.candle_repository import CandleRepository
from app.db.repositories.feature_repository import FeatureRepository
from app.db.repositories.label_repository import LabelRepository
from app.db.repositories.model_registry_repository import ModelRegistryRepository
from app.db.repositories.prediction_repository import PredictionRepository
from app.db.repositories.replay_repository import ReplayRepository
from app.db.repositories.training_run_repository import TrainingRunRepository
from app.features.feature_pipeline import FeaturePipeline
from app.labels.label_builder import LabelBuilder
from app.prediction.predictor import Predictor
from app.registry.artifact_storage import ArtifactStorage
from app.registry.model_loader import ModelLoader
from app.registry.model_registry import ModelRegistry
from app.replay.historical_replay_engine import HistoricalReplayEngine
from app.replay.replay_service import ReplayService
from app.training.training_service import TrainingService


def test_full_pipeline_smoke(tmp_path: Path) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    candles = _build_candles(2200)

    with Session(engine) as session:
        candle_repository = CandleRepository(session)
        candle_repository.upsert_many(candles)

        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        feature_pipeline = FeaturePipeline(candle_repository=candle_repository, feature_repository=feature_repository)
        feature_result = feature_pipeline.build_and_store(symbol="BTCUSDT", interval="15m", feature_version="fv1")
        assert feature_result["built"] == 2200

        label_builder = LabelBuilder()
        label_records = label_builder.build(
            candles=candle_repository.get_all(symbol="BTCUSDT", interval="15m"),
            symbol="BTCUSDT",
            interval="15m",
            horizon_candles=8,
            label_version="lv1",
        )
        assert label_repository.upsert_many([record.to_dict() for record in label_records]) > 0

        dataset_builder = DatasetBuilder(
            feature_repository=feature_repository,
            label_repository=label_repository,
            dataset_exporter=DatasetExporter(reports_dir=tmp_path / "reports"),
        )
        dataset_summary = dataset_builder.build(
            symbol="BTCUSDT",
            interval="15m",
            horizon_candles=8,
            feature_version="fv1",
            label_version="lv1",
            train_end=datetime(2025, 1, 10, tzinfo=timezone.utc).date(),
            validation_end=datetime(2025, 1, 16, tzinfo=timezone.utc).date(),
        )
        assert dataset_summary["dataset_rows"] > 0

        artifact_storage = ArtifactStorage(base_dir=tmp_path / "artifacts")
        model_registry_repository = ModelRegistryRepository(session)
        training_run_repository = TrainingRunRepository(session)
        model_registry = ModelRegistry(repository=model_registry_repository, artifact_storage=artifact_storage)
        training_service = TrainingService(
            dataset_builder=dataset_builder,
            model_registry=model_registry,
            training_run_repository=training_run_repository,
            artifact_storage=artifact_storage,
        )
        train_result = training_service.train(
            symbol="BTCUSDT",
            interval="15m",
            horizon_candles=8,
            feature_version="fv1",
            label_version="lv1",
            model_name="candle_mlp",
            epochs=1,
            train_end=datetime(2025, 1, 10, tzinfo=timezone.utc).date(),
            validation_end=datetime(2025, 1, 16, tzinfo=timezone.utc).date(),
        )
        model_version = train_result["model_version"]
        assert artifact_storage.exists(model_version) is True

        activate_result = model_registry.activate(model_version)
        assert activate_result["activated"] is True

        prediction_repository = PredictionRepository(session)
        predictor = Predictor(
            model_registry_repository=model_registry_repository,
            prediction_repository=prediction_repository,
            artifact_storage=artifact_storage,
            model_loader=ModelLoader(artifact_storage=artifact_storage),
        )
        prediction = predictor.predict(
            symbol="BTCUSDT",
            interval="15m",
            horizon_candles=8,
            candles=[
                {
                    "open_time": candle["open_time"].isoformat(),
                    "open": str(candle["open"]),
                    "high": str(candle["high"]),
                    "low": str(candle["low"]),
                    "close": str(candle["close"]),
                    "volume": str(candle["volume"]),
                    "quote_asset_volume": str(candle["quote_asset_volume"]),
                    "number_of_trades": candle["number_of_trades"],
                    "taker_buy_base_volume": str(candle["taker_buy_base_volume"]),
                    "taker_buy_quote_volume": str(candle["taker_buy_quote_volume"]),
                }
                for candle in candles[-220:]
            ],
            context={},
        )
        assert prediction["ml_available"] is True

        replay_repository = ReplayRepository(session)
        replay_engine = HistoricalReplayEngine(
            candle_repository=candle_repository,
            predictor=predictor,
            replay_repository=replay_repository,
            reports_dir=tmp_path / "reports",
        )
        replay_service = ReplayService(
            replay_engine=replay_engine,
            replay_repository=replay_repository,
            model_registry_repository=model_registry_repository,
        )
        replay_result = replay_service.replay(
            model_version=model_version,
            symbol="BTCUSDT",
            interval="15m",
            start_at=datetime(2025, 1, 16, tzinfo=timezone.utc),
            end_at=datetime(2025, 1, 18, tzinfo=timezone.utc),
            horizon_candles=8,
        )
        assert replay_result["results_written"] > 0


def _build_candles(count: int) -> list[dict]:
    candles = []
    start_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for index in range(count):
        price = 100 + (index * 0.15)
        open_time = start_at + timedelta(minutes=15 * index)
        candles.append(
            {
                "symbol": "BTCUSDT",
                "interval": "15m",
                "open_time": open_time,
                "close_time": open_time + timedelta(minutes=14, seconds=59),
                "open": price,
                "high": price + 2.0,
                "low": price - 1.5,
                "close": price + 0.7,
                "volume": 1000 + index,
                "quote_asset_volume": 50000 + index,
                "number_of_trades": 100 + index,
                "taker_buy_base_volume": 450 + index,
                "taker_buy_quote_volume": 22000 + index,
                "source": "test",
            }
        )
    return candles
