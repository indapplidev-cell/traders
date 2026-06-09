from sqlalchemy.orm import Session

from app.db.repositories.candle_repository import CandleRepository
from app.db.repositories.model_registry_repository import ModelRegistryRepository
from app.db.repositories.prediction_repository import PredictionRepository
from app.db.repositories.replay_repository import ReplayRepository
from app.prediction.prediction_service import PredictionService
from app.prediction.predictor import Predictor
from app.registry.artifact_storage import ArtifactStorage
from app.registry.model_loader import ModelLoader
from app.registry.model_registry import ModelRegistry
from app.replay.historical_replay_engine import HistoricalReplayEngine
from app.replay.replay_service import ReplayService


def get_prediction_service(session: Session) -> PredictionService:
    model_registry_repository = ModelRegistryRepository(session)
    prediction_repository = PredictionRepository(session)
    artifact_storage = ArtifactStorage()
    model_loader = ModelLoader(artifact_storage=artifact_storage)
    predictor = Predictor(
        model_registry_repository=model_registry_repository,
        prediction_repository=prediction_repository,
        artifact_storage=artifact_storage,
        model_loader=model_loader,
    )
    return PredictionService(predictor=predictor)


def get_model_registry(session: Session) -> ModelRegistry:
    repository = ModelRegistryRepository(session)
    artifact_storage = ArtifactStorage()
    return ModelRegistry(repository=repository, artifact_storage=artifact_storage)


def get_replay_service(session: Session) -> ReplayService:
    candle_repository = CandleRepository(session)
    replay_repository = ReplayRepository(session)
    model_registry_repository = ModelRegistryRepository(session)
    prediction_repository = PredictionRepository(session)
    artifact_storage = ArtifactStorage()
    model_loader = ModelLoader(artifact_storage=artifact_storage)
    predictor = Predictor(
        model_registry_repository=model_registry_repository,
        prediction_repository=prediction_repository,
        artifact_storage=artifact_storage,
        model_loader=model_loader,
    )
    engine = HistoricalReplayEngine(
        candle_repository=candle_repository,
        predictor=predictor,
        replay_repository=replay_repository,
    )
    return ReplayService(
        replay_engine=engine,
        replay_repository=replay_repository,
        model_registry_repository=model_registry_repository,
    )
