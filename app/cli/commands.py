import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import typer
from sqlalchemy import text

from app import __version__
from app.baseline.baseline_service import BaselineService
from app.config.settings import get_settings
from app.data.binance_client import BinanceClient
from app.data.candle_gap_checker import CandleGapChecker
from app.data.historical_loader import HistoricalLoader
from app.dataset.dataset_builder import DatasetBuilder
from app.db.repositories.feature_repository import FeatureRepository
from app.db.repositories.label_repository import LabelRepository
from app.db.repositories.candle_repository import CandleRepository
from app.db.repositories.model_registry_repository import ModelRegistryRepository
from app.db.repositories.prediction_repository import PredictionRepository
from app.db.repositories.replay_repository import ReplayRepository
from app.db.repositories.training_run_repository import TrainingRunRepository
from app.db.session import get_session
from app.diagnostics.diagnostics_service import DiagnosticsService
from app.experiments.experiment_reporter import ExperimentReporter
from app.experiments.label_grid_search import LabelGridSearchService
from app.features.feature_pipeline import FeaturePipeline
from app.labels.label_config import LabelConfig
from app.registry.artifact_storage import ArtifactStorage
from app.registry.model_loader import ModelLoader
from app.registry.model_registry import ModelRegistry
from app.labels.label_builder import LabelBuilder
from app.prediction.predictor import Predictor
from app.replay.historical_replay_engine import HistoricalReplayEngine
from app.replay.replay_service import ReplayService
from app.training.training_service import TrainingService
from app.gates.gate_policy_diagnostics import GatePolicyDiagnosticsService
from app.gates.gate_policy_models import GatePolicyInput
from app.gates.gate_policy_reporter import GatePolicyReporter
from app.gates.gate_policy_adapter_diagnostics import (
    GatePolicyAdapterDiagnosticsService,
)
from app.gates.gate_policy_adapter_reporter import GatePolicyAdapterReporter
from app.gates.gate_policy_prediction_contract_reporter import (
    GatePolicyPredictionContractReporter,
)
from app.gates.gate_policy_prediction_discovery import (
    GatePolicyPredictionDiscoveryService,
)
from app.gates.gate_policy_prediction_discovery_reporter import (
    GatePolicyPredictionDiscoveryReporter,
)
from app.gates.gate_policy_prediction_runtime_shape import (
    GatePolicyPredictionRuntimeShapeDiscoveryService,
)
from app.gates.gate_policy_prediction_runtime_shape_reporter import (
    GatePolicyPredictionRuntimeShapeReporter,
)
from app.gates.gate_policy_prediction_mapping_plan_reporter import (
    GatePolicyPredictionMappingPlanReporter,
)
from app.gates.gate_policy_prediction_runtime_adapter_contract_reporter import (
    GatePolicyPredictionRuntimeAdapterContractReporter,
)


cli = typer.Typer(help="traders-ml service CLI.")


def build_health_payload() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.service_name,
        "version": __version__,
    }


@cli.command("health")
def health_command() -> None:
    typer.echo(json.dumps(build_health_payload()))


@cli.command("db-check")
def db_check_command() -> None:
    with get_session() as session:
        session.execute(text("SELECT 1"))
    typer.echo("db-check: ok")


@cli.command("load-candles")
def load_candles_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    start_date: str = typer.Option(..., "--start-date"),
    end_date: str = typer.Option(..., "--end-date"),
) -> None:
    start_at, end_at = _build_utc_date_range(_parse_date(start_date), _parse_date(end_date))
    client = BinanceClient()
    with get_session() as session:
        repository = CandleRepository(session)
        loader = HistoricalLoader(client=client, repository=repository)
        result = loader.load_range(symbol=symbol, interval=interval, start_at=start_at, end_at=end_at)
    typer.echo(json.dumps(result))


@cli.command("check-candle-gaps")
def check_candle_gaps_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    start_date: str = typer.Option(..., "--start-date"),
    end_date: str = typer.Option(..., "--end-date"),
) -> None:
    start_at, end_at = _build_utc_date_range(_parse_date(start_date), _parse_date(end_date))
    checker = CandleGapChecker()
    with get_session() as session:
        repository = CandleRepository(session)
        candles = repository.get_range(symbol=symbol, interval=interval, start_at=start_at, end_at=end_at)
    result = checker.check(candles=candles, interval=interval, start_at=start_at, end_at=end_at, symbol=symbol)
    typer.echo(json.dumps(result))


@cli.command("build-features")
def build_features_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    feature_version: str = typer.Option(..., "--feature-version"),
) -> None:
    with get_session() as session:
        candle_repository = CandleRepository(session)
        feature_repository = FeatureRepository(session)
        pipeline = FeaturePipeline(candle_repository=candle_repository, feature_repository=feature_repository)
        result = pipeline.build_and_store(symbol=symbol, interval=interval, feature_version=feature_version)
    typer.echo(json.dumps(result))


@cli.command("build-labels")
def build_labels_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    horizon_candles: int = typer.Option(..., "--horizon-candles"),
    label_version: str = typer.Option(..., "--label-version"),
    direction_atr_threshold: float = typer.Option(0.5, "--direction-atr-threshold"),
    take_profit_atr: float = typer.Option(1.5, "--take-profit-atr"),
    stop_loss_atr: float = typer.Option(1.0, "--stop-loss-atr"),
    flat_class_enabled: bool = typer.Option(True, "--flat-class-enabled/--no-flat-class"),
) -> None:
    with get_session() as session:
        candle_repository = CandleRepository(session)
        label_repository = LabelRepository(session)
        candles = candle_repository.get_all(symbol=symbol, interval=interval)
        builder = LabelBuilder()
        config = LabelConfig(
            label_version=label_version,
            horizon_candles=horizon_candles,
            direction_atr_threshold=direction_atr_threshold,
            take_profit_atr=take_profit_atr,
            stop_loss_atr=stop_loss_atr,
            flat_class_enabled=flat_class_enabled,
        )
        records = builder.build(
            candles=candles,
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            label_version=label_version,
            config=config,
        )
        inserted_or_updated = label_repository.upsert_many([record.to_dict() for record in records])
        label_counts = builder.summarize(records)
        result = {
            "symbol": symbol,
            "interval": interval,
            "horizon_candles": horizon_candles,
            "label_version": label_version,
            "candles_used": len(candles),
            "built": len(records),
            "inserted_or_updated": inserted_or_updated,
            "direction_counts": label_counts,
            "direction_atr_threshold": direction_atr_threshold,
            "take_profit_atr": take_profit_atr,
            "stop_loss_atr": stop_loss_atr,
            "flat_class_enabled": flat_class_enabled,
            "first_open_time": records[0].candle_open_time.isoformat() if records else None,
            "last_open_time": records[-1].candle_open_time.isoformat() if records else None,
        }
    typer.echo(json.dumps(result))


@cli.command("build-dataset")
def build_dataset_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    horizon_candles: int | None = typer.Option(None, "--horizon-candles"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
    train_end: str | None = typer.Option(None, "--train-end"),
    validation_end: str | None = typer.Option(None, "--validation-end"),
) -> None:
    resolved_horizon = horizon_candles if horizon_candles is not None else _resolve_horizon_from_label_version(label_version)
    with get_session() as session:
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        result = builder.build(
            symbol=symbol,
            interval=interval,
            horizon_candles=resolved_horizon,
            feature_version=feature_version,
            label_version=label_version,
            train_end=_parse_optional_date(train_end),
            validation_end=_parse_optional_date(validation_end),
        )
    typer.echo(json.dumps(result))


@cli.command("train")
def train_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    horizon_candles: int | None = typer.Option(None, "--horizon-candles"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
    model_name: str = typer.Option("candle_mlp", "--model-name"),
    epochs: int = typer.Option(20, "--epochs"),
    learning_rate: float = typer.Option(0.001, "--learning-rate"),
    weight_decay: float = typer.Option(0.0001, "--weight-decay"),
    train_end: str | None = typer.Option(None, "--train-end"),
    validation_end: str | None = typer.Option(None, "--validation-end"),
    disable_class_weights: bool = typer.Option(False, "--disable-class-weights"),
) -> None:
    resolved_horizon = horizon_candles if horizon_candles is not None else _resolve_horizon_from_label_version(label_version)
    with get_session() as session:
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        artifact_storage = ArtifactStorage()
        model_registry_repository = ModelRegistryRepository(session)
        training_run_repository = TrainingRunRepository(session)
        model_registry = ModelRegistry(repository=model_registry_repository, artifact_storage=artifact_storage)
        service = TrainingService(
            dataset_builder=dataset_builder,
            model_registry=model_registry,
            training_run_repository=training_run_repository,
            artifact_storage=artifact_storage,
        )
        result = service.train(
            symbol=symbol,
            interval=interval,
            horizon_candles=resolved_horizon,
            feature_version=feature_version,
            label_version=label_version,
            model_name=model_name,
            epochs=epochs,
            learning_rate=learning_rate,
            weight_decay=weight_decay,
            train_end=_parse_optional_date(train_end),
            validation_end=_parse_optional_date(validation_end),
            disable_class_weights=disable_class_weights,
        )
    typer.echo(json.dumps(result))


@cli.command("evaluate")
def evaluate_command(
    model_version: str = typer.Option(..., "--model-version"),
) -> None:
    with get_session() as session:
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        artifact_storage = ArtifactStorage()
        model_registry_repository = ModelRegistryRepository(session)
        training_run_repository = TrainingRunRepository(session)
        model_registry = ModelRegistry(repository=model_registry_repository, artifact_storage=artifact_storage)
        service = TrainingService(
            dataset_builder=dataset_builder,
            model_registry=model_registry,
            training_run_repository=training_run_repository,
            artifact_storage=artifact_storage,
        )
        result = service.evaluate(model_version=model_version)
    typer.echo(json.dumps(result))


@cli.command("model-list")
def model_list_command() -> None:
    with get_session() as session:
        repository = ModelRegistryRepository(session)
        artifact_storage = ArtifactStorage()
        registry = ModelRegistry(repository=repository, artifact_storage=artifact_storage)
        result = registry.list_models()
    typer.echo(json.dumps(result))


@cli.command("model-activate")
def model_activate_command(
    model_version: str = typer.Option(..., "--model-version"),
) -> None:
    with get_session() as session:
        repository = ModelRegistryRepository(session)
        artifact_storage = ArtifactStorage()
        registry = ModelRegistry(repository=repository, artifact_storage=artifact_storage)
        result = registry.activate(model_version=model_version)
    typer.echo(json.dumps(result))


@cli.command("replay")
def replay_command(
    model_version: str = typer.Option(..., "--model-version"),
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    start_date: str = typer.Option(..., "--start-date"),
    end_date: str = typer.Option(..., "--end-date"),
    horizon_candles: int = typer.Option(..., "--horizon-candles"),
) -> None:
    start_at, end_at = _build_utc_date_range(_parse_date(start_date), _parse_date(end_date))
    with get_session() as session:
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
        service = ReplayService(
            replay_engine=engine,
            replay_repository=replay_repository,
            model_registry_repository=model_registry_repository,
        )
        result = service.replay(
            model_version=model_version,
            symbol=symbol,
            interval=interval,
            start_at=start_at,
            end_at=end_at,
            horizon_candles=horizon_candles,
        )
    typer.echo(json.dumps(result))


@cli.command("predict-sample")
def predict_sample_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    horizon_candles: int = typer.Option(..., "--horizon-candles"),
    limit: int = typer.Option(220, "--limit"),
) -> None:
    with get_session() as session:
        candle_repository = CandleRepository(session)
        prediction_repository = PredictionRepository(session)
        model_registry_repository = ModelRegistryRepository(session)
        artifact_storage = ArtifactStorage()
        model_loader = ModelLoader(artifact_storage=artifact_storage)
        predictor = Predictor(
            model_registry_repository=model_registry_repository,
            prediction_repository=prediction_repository,
            artifact_storage=artifact_storage,
            model_loader=model_loader,
        )
        candles = candle_repository.get_last_n(symbol=symbol, interval=interval, limit=limit)
        result = predictor.predict(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            candles=[
                {
                    "open_time": candle.open_time.isoformat(),
                    "open": str(candle.open),
                    "high": str(candle.high),
                    "low": str(candle.low),
                    "close": str(candle.close),
                    "volume": str(candle.volume),
                    "quote_asset_volume": str(candle.quote_asset_volume),
                    "number_of_trades": candle.number_of_trades,
                    "taker_buy_base_volume": str(candle.taker_buy_base_volume) if candle.taker_buy_base_volume is not None else None,
                    "taker_buy_quote_volume": str(candle.taker_buy_quote_volume) if candle.taker_buy_quote_volume is not None else None,
                }
                for candle in candles
            ],
            context={},
        )
    typer.echo(json.dumps(result))


@cli.command("evaluate-baselines")
def evaluate_baselines_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    horizon_candles: int = typer.Option(..., "--horizon-candles"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
    train_end: str | None = typer.Option(None, "--train-end"),
    validation_end: str | None = typer.Option(None, "--validation-end"),
) -> None:
    with get_session() as session:
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = BaselineService(dataset_builder=dataset_builder)
        result = service.evaluate(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            train_end=_parse_optional_date(train_end),
            validation_end=_parse_optional_date(validation_end),
        )
    typer.echo(json.dumps(result))


@cli.command("dataset-diagnostics")
def dataset_diagnostics_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    horizon_candles: int = typer.Option(..., "--horizon-candles"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
    train_end: str | None = typer.Option(None, "--train-end"),
    validation_end: str | None = typer.Option(None, "--validation-end"),
) -> None:
    with get_session() as session:
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        model_registry_repository = ModelRegistryRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            model_registry_repository=model_registry_repository,
            artifact_storage=ArtifactStorage(),
        )
        result = service.dataset_report(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            train_end=_parse_optional_date(train_end),
            validation_end=_parse_optional_date(validation_end),
        )
    typer.echo(json.dumps(result))


@cli.command("model-diagnostics")
def model_diagnostics_command(
    model_version: str = typer.Option(..., "--model-version"),
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    horizon_candles: int = typer.Option(..., "--horizon-candles"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
    train_end: str | None = typer.Option(None, "--train-end"),
    validation_end: str | None = typer.Option(None, "--validation-end"),
) -> None:
    with get_session() as session:
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        model_registry_repository = ModelRegistryRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            model_registry_repository=model_registry_repository,
            artifact_storage=ArtifactStorage(),
        )
        result = service.model_report(
            model_version=model_version,
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            train_end=_parse_optional_date(train_end),
            validation_end=_parse_optional_date(validation_end),
        )
    typer.echo(json.dumps(result))


@cli.command("overfit-check")
def overfit_check_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    horizon_candles: int = typer.Option(..., "--horizon-candles"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
    rows: int = typer.Option(..., "--rows"),
    epochs: int = typer.Option(..., "--epochs"),
) -> None:
    with get_session() as session:
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        model_registry_repository = ModelRegistryRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            model_registry_repository=model_registry_repository,
            artifact_storage=ArtifactStorage(),
        )
        result = service.overfit_check(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            rows=rows,
            epochs=epochs,
        )
    typer.echo(json.dumps(result))


@cli.command("compare-models")
def compare_models_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    horizon_candles: int = typer.Option(..., "--horizon-candles"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
    train_end: str | None = typer.Option(None, "--train-end"),
    validation_end: str | None = typer.Option(None, "--validation-end"),
) -> None:
    with get_session() as session:
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        model_registry_repository = ModelRegistryRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            model_registry_repository=model_registry_repository,
            artifact_storage=ArtifactStorage(),
        )
        result = service.compare_models(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            train_end=_parse_optional_date(train_end),
            validation_end=_parse_optional_date(validation_end),
        )
    typer.echo(json.dumps(result))


@cli.command("label-diagnostics")
def label_diagnostics_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    horizon_candles: int = typer.Option(..., "--horizon-candles"),
    label_version: str = typer.Option(..., "--label-version"),
) -> None:
    with get_session() as session:
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            model_registry_repository=ModelRegistryRepository(session),
            artifact_storage=ArtifactStorage(),
        )
        result = service.label_report(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            label_version=label_version,
        )
    typer.echo(json.dumps(result))


@cli.command("label-grid-search")
def label_grid_search_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    start_date: str = typer.Option(..., "--start-date"),
    end_date: str = typer.Option(..., "--end-date"),
    feature_version: str = typer.Option(..., "--feature-version"),
) -> None:
    start_at, end_at = _build_utc_date_range(_parse_date(start_date), _parse_date(end_date))
    with get_session() as session:
        candle_repository = CandleRepository(session)
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        baseline_service = BaselineService(dataset_builder=dataset_builder)
        service = LabelGridSearchService(
            candle_repository=candle_repository,
            feature_repository=feature_repository,
            label_repository=label_repository,
            dataset_builder=dataset_builder,
            baseline_service=baseline_service,
            reporter=ExperimentReporter(),
        )
        result = service.run(
            symbol=symbol,
            interval=interval,
            feature_version=feature_version,
            start_at=start_at,
            end_at=end_at,
        )
    typer.echo(json.dumps(result))


@cli.command("confidence-eval")
def confidence_eval_command(
    model_version: str = typer.Option(..., "--model-version"),
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    horizon_candles: int = typer.Option(..., "--horizon-candles"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
    train_end: str | None = typer.Option(None, "--train-end"),
    validation_end: str | None = typer.Option(None, "--validation-end"),
) -> None:
    with get_session() as session:
        candle_repository = CandleRepository(session)
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            candle_repository=candle_repository,
            model_registry_repository=ModelRegistryRepository(session),
            artifact_storage=ArtifactStorage(),
        )
        result = service.confidence_report(
            model_version=model_version,
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            train_end=_parse_optional_date(train_end),
            validation_end=_parse_optional_date(validation_end),
        )
    typer.echo(json.dumps(result))


@cli.command("profit-eval")
def profit_eval_command(
    model_version: str = typer.Option(..., "--model-version"),
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    horizon_candles: int = typer.Option(..., "--horizon-candles"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
    take_profit_atr: float = typer.Option(..., "--take-profit-atr"),
    stop_loss_atr: float = typer.Option(..., "--stop-loss-atr"),
    confidence_thresholds: str = typer.Option(..., "--confidence-thresholds"),
    train_end: str | None = typer.Option(None, "--train-end"),
    validation_end: str | None = typer.Option(None, "--validation-end"),
) -> None:
    with get_session() as session:
        candle_repository = CandleRepository(session)
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            candle_repository=candle_repository,
            model_registry_repository=ModelRegistryRepository(session),
            artifact_storage=ArtifactStorage(),
        )
        result = service.profit_report(
            model_version=model_version,
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            take_profit_atr=take_profit_atr,
            stop_loss_atr=stop_loss_atr,
            confidence_thresholds=[float(value) for value in confidence_thresholds.split(",") if value],
            train_end=_parse_optional_date(train_end),
            validation_end=_parse_optional_date(validation_end),
        )
    typer.echo(json.dumps(result))


@cli.command("calibration-eval")
def calibration_eval_command(
    model_version: str = typer.Option(..., "--model-version"),
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    horizon_candles: int = typer.Option(..., "--horizon-candles"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
    train_end: str | None = typer.Option(None, "--train-end"),
    validation_end: str | None = typer.Option(None, "--validation-end"),
) -> None:
    with get_session() as session:
        candle_repository = CandleRepository(session)
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            candle_repository=candle_repository,
            model_registry_repository=ModelRegistryRepository(session),
            artifact_storage=ArtifactStorage(),
        )
        result = service.calibration_report(
            model_version=model_version,
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            train_end=_parse_optional_date(train_end),
            validation_end=_parse_optional_date(validation_end),
        )
    typer.echo(json.dumps(result))


@cli.command("experiment-summary")
def experiment_summary_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
) -> None:
    with get_session() as session:
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        candle_repository = CandleRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            candle_repository=candle_repository,
            model_registry_repository=ModelRegistryRepository(session),
            artifact_storage=ArtifactStorage(),
        )
        result = service.experiment_summary(symbol=symbol, interval=interval)
    typer.echo(json.dumps(result))


@cli.command("probability-diagnostics")
def probability_diagnostics_command(
    model_version: str = typer.Option(..., "--model-version"),
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
    train_end: str | None = typer.Option(None, "--train-end"),
    validation_end: str | None = typer.Option(None, "--validation-end"),
) -> None:
    with get_session() as session:
        model_registry_repository = ModelRegistryRepository(session)
        horizon_candles = _resolve_model_horizon(model_registry_repository, model_version)
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        candle_repository = CandleRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            candle_repository=candle_repository,
            model_registry_repository=model_registry_repository,
            artifact_storage=ArtifactStorage(),
        )
        result = service.probability_report(
            model_version=model_version,
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            train_end=_parse_optional_date(train_end),
            validation_end=_parse_optional_date(validation_end),
        )
    typer.echo(json.dumps(result))


@cli.command("signal-gate-eval")
def signal_gate_eval_command(
    model_version: str = typer.Option(..., "--model-version"),
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
    train_end: str | None = typer.Option(None, "--train-end"),
    validation_end: str | None = typer.Option(None, "--validation-end"),
) -> None:
    with get_session() as session:
        model_registry_repository = ModelRegistryRepository(session)
        horizon_candles = _resolve_model_horizon(model_registry_repository, model_version)
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        candle_repository = CandleRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            candle_repository=candle_repository,
            model_registry_repository=model_registry_repository,
            artifact_storage=ArtifactStorage(),
        )
        result = service.signal_gate_report(
            model_version=model_version,
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            train_end=_parse_optional_date(train_end),
            validation_end=_parse_optional_date(validation_end),
        )
    typer.echo(json.dumps(result))


@cli.command("profit-eval-v2")
def profit_eval_v2_command(
    model_version: str = typer.Option(..., "--model-version"),
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
    take_profit_atr: float = typer.Option(..., "--take-profit-atr"),
    stop_loss_atr: float = typer.Option(..., "--stop-loss-atr"),
    fee_r: float = typer.Option(0.0, "--fee-r"),
    slippage_r: float = typer.Option(0.0, "--slippage-r"),
    same_candle_policy: str = typer.Option("conservative", "--same-candle-policy"),
    train_end: str | None = typer.Option(None, "--train-end"),
    validation_end: str | None = typer.Option(None, "--validation-end"),
) -> None:
    with get_session() as session:
        model_registry_repository = ModelRegistryRepository(session)
        horizon_candles = _resolve_model_horizon(model_registry_repository, model_version)
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        candle_repository = CandleRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            candle_repository=candle_repository,
            model_registry_repository=model_registry_repository,
            artifact_storage=ArtifactStorage(),
        )
        result = service.profit_report_v2(
            model_version=model_version,
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            take_profit_atr=take_profit_atr,
            stop_loss_atr=stop_loss_atr,
            fee_r=fee_r,
            slippage_r=slippage_r,
            same_candle_policy=same_candle_policy,
            train_end=_parse_optional_date(train_end),
            validation_end=_parse_optional_date(validation_end),
        )
    typer.echo(json.dumps(result))


@cli.command("experiment-summary-v2")
def experiment_summary_v2_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
) -> None:
    with get_session() as session:
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        candle_repository = CandleRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            candle_repository=candle_repository,
            model_registry_repository=ModelRegistryRepository(session),
            artifact_storage=ArtifactStorage(),
        )
        result = service.experiment_summary_v2(symbol=symbol, interval=interval)
    typer.echo(json.dumps(result))


@cli.command("walk-forward-plan")
def walk_forward_plan_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
    mode: str = typer.Option(..., "--mode"),
    train_days: int = typer.Option(..., "--train-days"),
    validation_days: int = typer.Option(..., "--validation-days"),
    test_days: int = typer.Option(..., "--test-days"),
    step_days: int = typer.Option(..., "--step-days"),
    min_train_rows: int = typer.Option(..., "--min-train-rows"),
) -> None:
    with get_session() as session:
        model_registry_repository = ModelRegistryRepository(session)
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            model_registry_repository=model_registry_repository,
            artifact_storage=ArtifactStorage(),
        )
        horizon_candles = _resolve_horizon_from_label_version(label_version)
        result = service.walk_forward_plan(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            mode=mode,
            train_days=train_days,
            validation_days=validation_days,
            test_days=test_days,
            step_days=step_days,
            min_train_rows=min_train_rows,
        )
    typer.echo(json.dumps(result))


@cli.command("walk-forward-eval")
def walk_forward_eval_command(
    model_version: str = typer.Option(..., "--model-version"),
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
    mode: str = typer.Option(..., "--mode"),
    train_days: int = typer.Option(..., "--train-days"),
    validation_days: int = typer.Option(..., "--validation-days"),
    test_days: int = typer.Option(..., "--test-days"),
    step_days: int = typer.Option(..., "--step-days"),
    min_train_rows: int = typer.Option(..., "--min-train-rows"),
    take_profit_atr: float = typer.Option(..., "--take-profit-atr"),
    stop_loss_atr: float = typer.Option(..., "--stop-loss-atr"),
    fee_r: float = typer.Option(0.0, "--fee-r"),
    slippage_r: float = typer.Option(0.0, "--slippage-r"),
    same_candle_policy: str = typer.Option("conservative", "--same-candle-policy"),
) -> None:
    with get_session() as session:
        model_registry_repository = ModelRegistryRepository(session)
        horizon_candles = _resolve_model_horizon(model_registry_repository, model_version)
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        candle_repository = CandleRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            candle_repository=candle_repository,
            model_registry_repository=model_registry_repository,
            artifact_storage=ArtifactStorage(),
        )
        result = service.walk_forward_eval(
            model_version=model_version,
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            mode=mode,
            train_days=train_days,
            validation_days=validation_days,
            test_days=test_days,
            step_days=step_days,
            min_train_rows=min_train_rows,
            take_profit_atr=take_profit_atr,
            stop_loss_atr=stop_loss_atr,
            fee_r=fee_r,
            slippage_r=slippage_r,
            same_candle_policy=same_candle_policy,
        )
    typer.echo(json.dumps(result))


@cli.command("robust-experiment-summary")
def robust_experiment_summary_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    require_both_directions: bool = typer.Option(True, "--require-both-directions/--no-require-both-directions"),
) -> None:
    with get_session() as session:
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        candle_repository = CandleRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            candle_repository=candle_repository,
            model_registry_repository=ModelRegistryRepository(session),
            artifact_storage=ArtifactStorage(),
        )
        result = service.robust_experiment_summary(
            symbol=symbol,
            interval=interval,
            require_both_directions=require_both_directions,
        )
    typer.echo(json.dumps(result))


@cli.command("fold-label-diagnostics")
def fold_label_diagnostics_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
    mode: str = typer.Option(..., "--mode"),
    train_days: int = typer.Option(..., "--train-days"),
    validation_days: int = typer.Option(..., "--validation-days"),
    test_days: int = typer.Option(..., "--test-days"),
    step_days: int = typer.Option(..., "--step-days"),
    min_train_rows: int = typer.Option(..., "--min-train-rows"),
) -> None:
    with get_session() as session:
        horizon_candles = _resolve_horizon_from_label_version(label_version)
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            model_registry_repository=ModelRegistryRepository(session),
            artifact_storage=ArtifactStorage(),
        )
        result = service.fold_label_diagnostics(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            mode=mode,
            train_days=train_days,
            validation_days=validation_days,
            test_days=test_days,
            step_days=step_days,
            min_train_rows=min_train_rows,
        )
    typer.echo(json.dumps(result))


@cli.command("directional-opportunity-diagnostics")
def directional_opportunity_diagnostics_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
    mode: str = typer.Option(..., "--mode"),
    train_days: int = typer.Option(..., "--train-days"),
    validation_days: int = typer.Option(..., "--validation-days"),
    test_days: int = typer.Option(..., "--test-days"),
    step_days: int = typer.Option(..., "--step-days"),
    min_train_rows: int = typer.Option(..., "--min-train-rows"),
    take_profit_atr: float = typer.Option(..., "--take-profit-atr"),
    stop_loss_atr: float = typer.Option(..., "--stop-loss-atr"),
    fee_r: float = typer.Option(0.0, "--fee-r"),
    slippage_r: float = typer.Option(0.0, "--slippage-r"),
    same_candle_policy: str = typer.Option("conservative", "--same-candle-policy"),
) -> None:
    with get_session() as session:
        horizon_candles = _resolve_horizon_from_label_version(label_version)
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        candle_repository = CandleRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            candle_repository=candle_repository,
            model_registry_repository=ModelRegistryRepository(session),
            artifact_storage=ArtifactStorage(),
        )
        result = service.directional_opportunity_diagnostics(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            mode=mode,
            train_days=train_days,
            validation_days=validation_days,
            test_days=test_days,
            step_days=step_days,
            min_train_rows=min_train_rows,
            take_profit_atr=take_profit_atr,
            stop_loss_atr=stop_loss_atr,
            fee_r=fee_r,
            slippage_r=slippage_r,
            same_candle_policy=same_candle_policy,
        )
    typer.echo(json.dumps(result))


@cli.command("directional-baselines")
def directional_baselines_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
    mode: str = typer.Option(..., "--mode"),
    train_days: int = typer.Option(..., "--train-days"),
    validation_days: int = typer.Option(..., "--validation-days"),
    test_days: int = typer.Option(..., "--test-days"),
    step_days: int = typer.Option(..., "--step-days"),
    min_train_rows: int = typer.Option(..., "--min-train-rows"),
    take_profit_atr: float = typer.Option(..., "--take-profit-atr"),
    stop_loss_atr: float = typer.Option(..., "--stop-loss-atr"),
    fee_r: float = typer.Option(0.0, "--fee-r"),
    slippage_r: float = typer.Option(0.0, "--slippage-r"),
    same_candle_policy: str = typer.Option("conservative", "--same-candle-policy"),
    require_both_directions: bool = typer.Option(True, "--require-both-directions/--no-require-both-directions"),
) -> None:
    with get_session() as session:
        horizon_candles = _resolve_horizon_from_label_version(label_version)
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        candle_repository = CandleRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            candle_repository=candle_repository,
            model_registry_repository=ModelRegistryRepository(session),
            artifact_storage=ArtifactStorage(),
        )
        result = service.directional_baselines(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            mode=mode,
            train_days=train_days,
            validation_days=validation_days,
            test_days=test_days,
            step_days=step_days,
            min_train_rows=min_train_rows,
            take_profit_atr=take_profit_atr,
            stop_loss_atr=stop_loss_atr,
            fee_r=fee_r,
            slippage_r=slippage_r,
            same_candle_policy=same_candle_policy,
            require_both_directions=require_both_directions,
        )
    typer.echo(json.dumps(result))


@cli.command("prediction-bias-root-cause")
def prediction_bias_root_cause_command(
    model_version: str = typer.Option(..., "--model-version"),
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
    train_end: str | None = typer.Option(None, "--train-end"),
    validation_end: str | None = typer.Option(None, "--validation-end"),
) -> None:
    with get_session() as session:
        horizon_candles = _resolve_model_horizon(ModelRegistryRepository(session), model_version)
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        candle_repository = CandleRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            candle_repository=candle_repository,
            model_registry_repository=ModelRegistryRepository(session),
            artifact_storage=ArtifactStorage(),
        )
        result = service.prediction_bias_root_cause(
            model_version=model_version,
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            train_end=_parse_optional_date(train_end),
            validation_end=_parse_optional_date(validation_end),
        )
    typer.echo(json.dumps(result))


@cli.command("feature-diagnostics-v2")
def feature_diagnostics_v2_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
) -> None:
    with get_session() as session:
        horizon_candles = _resolve_horizon_from_label_version(label_version)
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            model_registry_repository=ModelRegistryRepository(session),
            artifact_storage=ArtifactStorage(),
        )
        result = service.feature_diagnostics_v2(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
        )
    typer.echo(json.dumps(result))


@cli.command("stage-ml11-summary")
def stage_ml11_summary_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
) -> None:
    with get_session() as session:
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        candle_repository = CandleRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            candle_repository=candle_repository,
            model_registry_repository=ModelRegistryRepository(session),
            artifact_storage=ArtifactStorage(),
        )
        result = service.stage_ml11_summary(symbol=symbol, interval=interval)
    typer.echo(json.dumps(result))


@cli.command("model-vs-baseline")
def model_vs_baseline_command(
    model_version: str = typer.Option(..., "--model-version"),
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
) -> None:
    with get_session() as session:
        model_registry_repository = ModelRegistryRepository(session)
        horizon_candles = _resolve_model_horizon(model_registry_repository, model_version)
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        candle_repository = CandleRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            candle_repository=candle_repository,
            model_registry_repository=model_registry_repository,
            artifact_storage=ArtifactStorage(),
        )
        result = service.model_vs_baseline(
            model_version=model_version,
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
        )
    typer.echo(json.dumps(result))


@cli.command("stage-ml12-summary")
def stage_ml12_summary_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
) -> None:
    with get_session() as session:
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        candle_repository = CandleRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            candle_repository=candle_repository,
            model_registry_repository=ModelRegistryRepository(session),
            artifact_storage=ArtifactStorage(),
        )
        result = service.stage_ml12_summary(symbol=symbol, interval=interval)
    typer.echo(json.dumps(result))


@cli.command("regime-segment-diagnostics")
def regime_segment_diagnostics_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
    take_profit_atr: float = typer.Option(..., "--take-profit-atr"),
    stop_loss_atr: float = typer.Option(..., "--stop-loss-atr"),
    fee_r: float = typer.Option(0.0, "--fee-r"),
    slippage_r: float = typer.Option(0.0, "--slippage-r"),
    same_candle_policy: str = typer.Option("conservative", "--same-candle-policy"),
) -> None:
    with get_session() as session:
        horizon_candles = _resolve_horizon_from_label_version(label_version)
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        candle_repository = CandleRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            candle_repository=candle_repository,
            model_registry_repository=ModelRegistryRepository(session),
            artifact_storage=ArtifactStorage(),
        )
        result = service.regime_segment_diagnostics(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            take_profit_atr=take_profit_atr,
            stop_loss_atr=stop_loss_atr,
            fee_r=fee_r,
            slippage_r=slippage_r,
            same_candle_policy=same_candle_policy,
        )
    typer.echo(json.dumps(result))


@cli.command("baseline-by-regime")
def baseline_by_regime_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
    mode: str = typer.Option(..., "--mode"),
    train_days: int = typer.Option(..., "--train-days"),
    validation_days: int = typer.Option(..., "--validation-days"),
    test_days: int = typer.Option(..., "--test-days"),
    step_days: int = typer.Option(..., "--step-days"),
    min_train_rows: int = typer.Option(..., "--min-train-rows"),
    take_profit_atr: float = typer.Option(..., "--take-profit-atr"),
    stop_loss_atr: float = typer.Option(..., "--stop-loss-atr"),
    fee_r: float = typer.Option(0.0, "--fee-r"),
    slippage_r: float = typer.Option(0.0, "--slippage-r"),
    same_candle_policy: str = typer.Option("conservative", "--same-candle-policy"),
) -> None:
    with get_session() as session:
        horizon_candles = _resolve_horizon_from_label_version(label_version)
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        candle_repository = CandleRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            candle_repository=candle_repository,
            model_registry_repository=ModelRegistryRepository(session),
            artifact_storage=ArtifactStorage(),
        )
        result = service.baseline_by_regime(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            mode=mode,
            train_days=train_days,
            validation_days=validation_days,
            test_days=test_days,
            step_days=step_days,
            min_train_rows=min_train_rows,
            take_profit_atr=take_profit_atr,
            stop_loss_atr=stop_loss_atr,
            fee_r=fee_r,
            slippage_r=slippage_r,
            same_candle_policy=same_candle_policy,
        )
    typer.echo(json.dumps(result))


@cli.command("build-ema-meta-labels")
def build_ema_meta_labels_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
    take_profit_atr: float = typer.Option(..., "--take-profit-atr"),
    stop_loss_atr: float = typer.Option(..., "--stop-loss-atr"),
    fee_r: float = typer.Option(0.0, "--fee-r"),
    slippage_r: float = typer.Option(0.0, "--slippage-r"),
    same_candle_policy: str = typer.Option("conservative", "--same-candle-policy"),
) -> None:
    with get_session() as session:
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        candle_repository = CandleRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            candle_repository=candle_repository,
            model_registry_repository=ModelRegistryRepository(session),
            artifact_storage=ArtifactStorage(),
        )
        result = service.build_ema_meta_labels(
            symbol=symbol,
            interval=interval,
            horizon_candles=_resolve_meta_horizon_from_label_version(label_version),
            feature_version=feature_version,
            label_version=label_version,
            take_profit_atr=take_profit_atr,
            stop_loss_atr=stop_loss_atr,
            fee_r=fee_r,
            slippage_r=slippage_r,
            same_candle_policy=same_candle_policy,
        )
    typer.echo(json.dumps(result))


@cli.command("meta-label-diagnostics")
def meta_label_diagnostics_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
) -> None:
    with get_session() as session:
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            model_registry_repository=ModelRegistryRepository(session),
            artifact_storage=ArtifactStorage(),
        )
        result = service.meta_label_diagnostics(
            symbol=symbol,
            interval=interval,
            feature_version=feature_version,
            label_version=label_version,
        )
    typer.echo(json.dumps(result))


@cli.command("build-meta-dataset")
def build_meta_dataset_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
) -> None:
    with get_session() as session:
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            model_registry_repository=ModelRegistryRepository(session),
            artifact_storage=ArtifactStorage(),
        )
        result = service.build_meta_dataset(
            symbol=symbol,
            interval=interval,
            feature_version=feature_version,
            label_version=label_version,
        )
    typer.echo(json.dumps(result))


@cli.command("meta-baselines")
def meta_baselines_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
    mode: str = typer.Option(..., "--mode"),
    train_days: int = typer.Option(..., "--train-days"),
    validation_days: int = typer.Option(..., "--validation-days"),
    test_days: int = typer.Option(..., "--test-days"),
    step_days: int = typer.Option(..., "--step-days"),
    min_train_rows: int = typer.Option(..., "--min-train-rows"),
) -> None:
    with get_session() as session:
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            model_registry_repository=ModelRegistryRepository(session),
            artifact_storage=ArtifactStorage(),
        )
        result = service.meta_baselines(
            symbol=symbol,
            interval=interval,
            feature_version=feature_version,
            label_version=label_version,
            mode=mode,
            train_days=train_days,
            validation_days=validation_days,
            test_days=test_days,
            step_days=step_days,
            min_train_rows=min_train_rows,
        )
    typer.echo(json.dumps(result))


@cli.command("train-meta")
def train_meta_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
) -> None:
    with get_session() as session:
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            model_registry_repository=ModelRegistryRepository(session),
            artifact_storage=ArtifactStorage(),
        )
        result = service.train_meta(
            symbol=symbol,
            interval=interval,
            horizon_candles=_resolve_meta_horizon_from_label_version(label_version),
            feature_version=feature_version,
            label_version=label_version,
        )
    typer.echo(json.dumps(result))


@cli.command("evaluate-meta")
def evaluate_meta_command(
    model_version: str = typer.Option(..., "--model-version"),
) -> None:
    with get_session() as session:
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            model_registry_repository=ModelRegistryRepository(session),
            artifact_storage=ArtifactStorage(),
        )
        result = service.evaluate_meta(model_version=model_version)
    typer.echo(json.dumps(result))


@cli.command("walk-forward-meta-eval")
def walk_forward_meta_eval_command(
    model_version: str = typer.Option(..., "--model-version"),
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    feature_version: str = typer.Option(..., "--feature-version"),
    label_version: str = typer.Option(..., "--label-version"),
    mode: str = typer.Option(..., "--mode"),
    train_days: int = typer.Option(..., "--train-days"),
    validation_days: int = typer.Option(..., "--validation-days"),
    test_days: int = typer.Option(..., "--test-days"),
    step_days: int = typer.Option(..., "--step-days"),
    min_train_rows: int = typer.Option(..., "--min-train-rows"),
    threshold_grid: str = typer.Option(..., "--threshold-grid"),
) -> None:
    with get_session() as session:
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            model_registry_repository=ModelRegistryRepository(session),
            artifact_storage=ArtifactStorage(),
        )
        result = service.walk_forward_meta_eval(
            model_version=model_version,
            symbol=symbol,
            interval=interval,
            feature_version=feature_version,
            label_version=label_version,
            mode=mode,
            train_days=train_days,
            validation_days=validation_days,
            test_days=test_days,
            step_days=step_days,
            min_train_rows=min_train_rows,
            threshold_grid=_parse_threshold_grid(threshold_grid),
        )
    typer.echo(json.dumps(result))


@cli.command("stage-ml13-summary")
def stage_ml13_summary_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
) -> None:
    with get_session() as session:
        feature_repository = FeatureRepository(session)
        label_repository = LabelRepository(session)
        candle_repository = CandleRepository(session)
        dataset_builder = DatasetBuilder(feature_repository=feature_repository, label_repository=label_repository)
        service = DiagnosticsService(
            dataset_builder=dataset_builder,
            feature_repository=feature_repository,
            label_repository=label_repository,
            candle_repository=candle_repository,
            model_registry_repository=ModelRegistryRepository(session),
            artifact_storage=ArtifactStorage(),
        )
        result = service.stage_ml13_summary(symbol=symbol, interval=interval)
    typer.echo(json.dumps(result))


def _build_utc_date_range(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    if end_date < start_date:
        raise typer.BadParameter("end-date must be greater than or equal to start-date")

    start_at = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end_at = datetime.combine(end_date, time.min, tzinfo=timezone.utc) + timedelta(days=1)
    return start_at, end_at


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter("date must be in YYYY-MM-DD format") from exc


def _parse_optional_date(value: str | None) -> date | None:
    if value is None:
        return None
    return _parse_date(value)


def _resolve_model_horizon(model_registry_repository: ModelRegistryRepository, model_version: str) -> int:
    model_row = model_registry_repository.get_by_model_version(model_version)
    if model_row is None:
        raise typer.BadParameter(f"unknown model-version: {model_version}")
    return int(model_row.horizon_candles)


def _resolve_horizon_from_label_version(label_version: str) -> int:
    if "_h" not in label_version:
        if label_version == "lv1":
            return 8
        raise typer.BadParameter(f"cannot resolve horizon from label-version: {label_version}")
    try:
        marker = label_version.split("_h", 1)[1]
        value = marker.split("_", 1)[0]
        return int(value)
    except (IndexError, ValueError) as exc:
        raise typer.BadParameter(f"cannot resolve horizon from label-version: {label_version}") from exc


def _resolve_meta_horizon_from_label_version(label_version: str) -> int:
    if label_version.startswith("meta_ema_9_21_"):
        return 16
    raise typer.BadParameter(f"cannot resolve horizon from meta label-version: {label_version}")


def _parse_threshold_grid(value: str) -> list[float]:
    try:
        thresholds = [float(item.strip()) for item in value.split(",") if item.strip()]
    except ValueError as exc:
        raise typer.BadParameter("threshold-grid must be comma-separated floats") from exc
    if not thresholds:
        raise typer.BadParameter("threshold-grid must not be empty")
    return thresholds


def build_gate_policy_smoke_payload() -> dict[str, object]:
    """Собрать демонстрационный GatePolicy-отчёт для CLI smoke-проверки."""

    signals = (
        GatePolicyInput(
            regime="trend_up",
            direction="LONG",
            confidence=0.80,
            tp_before_sl_probability=0.70,
            risk_score=0.30,
            sample_count=80,
        ),
        GatePolicyInput(
            regime="trend_down",
            direction="SHORT",
            confidence=0.78,
            tp_before_sl_probability=0.68,
            risk_score=0.28,
            sample_count=75,
        ),
        GatePolicyInput(
            regime="range",
            direction="LONG",
            confidence=0.85,
            tp_before_sl_probability=0.75,
            risk_score=0.25,
            sample_count=90,
        ),
        GatePolicyInput(
            regime="trend_up",
            direction="LONG",
            confidence=0.40,
            tp_before_sl_probability=0.70,
            risk_score=0.20,
            sample_count=70,
        ),
        GatePolicyInput(
            regime="trend_up",
            direction="FLAT",
            confidence=0.90,
            tp_before_sl_probability=0.80,
            risk_score=0.10,
            sample_count=100,
        ),
    )

    diagnostics = GatePolicyDiagnosticsService()
    reporter = GatePolicyReporter()

    report = diagnostics.build_report(signals)

    return reporter.report_to_dict(report)


def export_gate_policy_smoke_report(
    output_path: str | Path = Path("reports/gate_policy_smoke_report.json"),
) -> dict[str, object]:
    """Сохранить демонстрационный GatePolicy-отчёт в JSON-файл."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = build_gate_policy_smoke_payload()

    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    return {
        "status": "ok",
        "output_path": str(path),
        "total": payload["total"],
        "allowed_total": payload["allowed_total"],
        "blocked_total": payload["blocked_total"],
    }


    diagnostics = GatePolicyDiagnosticsService()
    reporter = GatePolicyReporter()

    report = diagnostics.build_report(signals)

    return reporter.report_to_dict(report)


def build_gate_policy_adapter_preview_payload() -> dict[str, object]:
    """Собрать demo JSON payload для предпросмотра GatePolicy adapter."""

    raw_payloads = (
        {
            "regime": "trend_up",
            "direction": "LONG",
            "confidence": 0.80,
            "tp_before_sl_probability": 0.70,
            "risk_score": 0.30,
            "sample_count": 80,
        },
        {
            "market_regime": "trend_down",
            "predicted_direction": "DOWN",
            "model_confidence": "0.78",
            "tp_before_sl_prob": "0.68",
            "model_risk_score": "0.28",
            "samples": "75",
        },
        {
            "regime": "range",
            "direction": "LONG",
            "confidence": 0.85,
            "tp_before_sl_probability": 0.75,
            "risk_score": 0.25,
            "sample_count": 90,
        },
        {
            "regime": "trend_up",
            "direction": "LONG",
            "confidence": 0.40,
            "tp_before_sl_probability": 0.70,
            "risk_score": 0.20,
            "sample_count": 70,
        },
    )

    diagnostics = GatePolicyAdapterDiagnosticsService()
    reporter = GatePolicyAdapterReporter()

    result = diagnostics.evaluate_payloads(raw_payloads)
    payload = reporter.adapter_result_to_dict(result)

    return {
        "raw_payload_count": len(raw_payloads),
        **payload,
    }


def export_gate_policy_adapter_preview_report(
    output_path: str | Path = Path("reports/gate_policy_adapter_preview_report.json"),
) -> dict[str, object]:
    """Сохранить demo GatePolicy adapter preview report в JSON-файл."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = build_gate_policy_adapter_preview_payload()

    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    report = payload["report"]

    return {
        "status": "ok",
        "output_path": str(path),
        "raw_payload_count": payload["raw_payload_count"],
        "input_count": payload["input_count"],
        "result_count": payload["result_count"],
        "total": report["total"],
        "allowed_total": report["allowed_total"],
        "blocked_total": report["blocked_total"],
    }


def build_gate_policy_prediction_contract_preview_payload() -> dict[str, object]:
    """Собрать JSON payload для предпросмотра GatePolicy prediction contract."""

    reporter = GatePolicyPredictionContractReporter()

    return reporter.contract_to_dict()


def export_gate_policy_prediction_contract_report(
    output_path: str | Path = Path("reports/gate_policy_prediction_contract_report.json"),
) -> dict[str, object]:
    """Сохранить GatePolicy prediction payload contract в JSON-файл."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = build_gate_policy_prediction_contract_preview_payload()

    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    return {
        "status": "ok",
        "output_path": str(path),
        "contract_name": payload["contract_name"],
        "version": payload["version"],
        "required_count": payload["required_count"],
        "optional_count": payload["optional_count"],
        "all_field_count": payload["all_field_count"],
        "alias_field_count": payload["alias_field_count"],
        "direction_alias_count": payload["direction_alias_count"],
        "known_regime_count": payload["known_regime_count"],
    }


def build_gate_policy_prediction_discovery_summary_payload(
    root_path: str | Path = Path("."),
) -> dict[str, object]:
    """Собрать compact summary для GatePolicy prediction discovery."""

    discovery = GatePolicyPredictionDiscoveryService()
    reporter = GatePolicyPredictionDiscoveryReporter()

    report = discovery.discover(root_path)

    return reporter.summary_to_dict(report)


def export_gate_policy_prediction_discovery_summary_report(
    root_path: str | Path = Path("."),
    output_path: str | Path = Path("reports/gate_policy_prediction_discovery_summary.json"),
) -> dict[str, object]:
    """Сохранить compact GatePolicy prediction discovery summary в JSON-файл."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = build_gate_policy_prediction_discovery_summary_payload(root_path)

    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    return {
        "status": "ok",
        "output_path": str(path),
        "root_path": payload["root_path"],
        "total_files": payload["total_files"],
        "files_with_content_matches": payload["files_with_content_matches"],
        "unique_name_keyword_count": len(payload["unique_name_keywords"]),
        "unique_content_keyword_count": len(payload["unique_content_keywords"]),
    }


def build_gate_policy_prediction_runtime_shape_summary_payload(
    root_path: str | Path = Path("."),
) -> dict[str, object]:
    """Собрать compact summary для GatePolicy prediction runtime shape discovery."""

    discovery = GatePolicyPredictionRuntimeShapeDiscoveryService()
    reporter = GatePolicyPredictionRuntimeShapeReporter()

    report = discovery.discover(root_path)

    return reporter.summary_to_dict(report)


def export_gate_policy_prediction_runtime_shape_summary_report(
    root_path: str | Path = Path("."),
    output_path: str | Path = Path("reports/gate_policy_prediction_runtime_shape_summary.json"),
) -> dict[str, object]:
    """Сохранить compact GatePolicy prediction runtime shape summary в JSON-файл."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = build_gate_policy_prediction_runtime_shape_summary_payload(root_path)

    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    return {
        "status": "ok",
        "output_path": str(path),
        "root_path": payload["root_path"],
        "total_targets": payload["total_targets"],
        "existing_targets": payload["existing_targets"],
        "missing_targets": payload["missing_targets"],
        "files_with_runtime_shape_signals": payload["files_with_runtime_shape_signals"],
        "unique_class_count": len(payload["unique_class_names"]),
        "unique_function_count": len(payload["unique_function_names"]),
        "unique_keyword_count": len(payload["unique_keywords"]),
    }


def build_gate_policy_prediction_mapping_plan_preview_payload() -> dict[str, object]:
    """Собрать compact preview для GatePolicy prediction mapping plan."""

    reporter = GatePolicyPredictionMappingPlanReporter()
    payload = reporter.summary_to_dict()

    optional_target_fields = payload["optional_target_fields"]

    if payload["optional_target_count"] != len(optional_target_fields):
        raise ValueError(
            "Invalid GatePolicy prediction mapping preview: "
            "optional_target_count does not match optional_target_fields length."
        )

    expected_optional_target_fields = [
        "risk_score",
        "expected_move_atr",
        "model_version",
        "symbol",
        "interval",
    ]

    if optional_target_fields != expected_optional_target_fields:
        raise ValueError(
            "Invalid GatePolicy prediction mapping preview: "
            f"optional_target_fields must be {expected_optional_target_fields}, "
            f"got {optional_target_fields}."
        )

    return payload


def export_gate_policy_prediction_mapping_plan_summary_report(
    output_path: str | Path = Path("reports/gate_policy_prediction_mapping_plan_summary.json"),
) -> dict[str, object]:
    """Сохранить compact GatePolicy prediction mapping plan summary в JSON-файл."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = build_gate_policy_prediction_mapping_plan_preview_payload()

    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    return {
        "status": "ok",
        "output_path": str(path),
        "name": payload["name"],
        "version": payload["version"],
        "required_target_count": payload["required_target_count"],
        "optional_target_count": payload["optional_target_count"],
        "all_target_count": payload["all_target_count"],
        "all_source_count": payload["all_source_count"],
        "mapping_rule_count": payload["mapping_rule_count"],
        "direction_rule_count": payload["direction_rule_count"],
        "runtime_adapter_implemented": payload["integration_status"]["runtime_adapter_implemented"],
    }


def build_gate_policy_runtime_adapter_contract_preview_payload() -> dict[str, object]:
    """Собрать compact preview для GatePolicy prediction runtime adapter contract."""

    reporter = GatePolicyPredictionRuntimeAdapterContractReporter()
    payload = reporter.summary_to_dict()

    if payload["runtime_adapter_implemented"] is not False:
        raise ValueError(
            "Invalid runtime adapter contract preview: "
            "runtime_adapter_implemented must remain false at Stage ML20.3."
        )

    expected_required_numeric_fields = [
        "prob_up",
        "prob_down",
        "prob_flat",
        "confidence",
        "tp_before_sl_probability",
    ]

    if payload["required_numeric_fields"] != expected_required_numeric_fields:
        raise ValueError(
            "Invalid runtime adapter contract preview: "
            f"required_numeric_fields must be {expected_required_numeric_fields}, "
            f"got {payload['required_numeric_fields']}."
        )

    expected_traceability_fields = [
        "model_version",
        "symbol",
        "interval",
    ]

    if payload["traceability_fields"] != expected_traceability_fields:
        raise ValueError(
            "Invalid runtime adapter contract preview: "
            f"traceability_fields must be {expected_traceability_fields}, "
            f"got {payload['traceability_fields']}."
        )

    return payload


def export_gate_policy_runtime_adapter_contract_summary_report(
    output_path: str | Path = Path("reports/gate_policy_runtime_adapter_contract_summary.json"),
) -> dict[str, object]:
    """Сохранить compact GatePolicy runtime adapter contract summary в JSON-файл."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = build_gate_policy_runtime_adapter_contract_preview_payload()

    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    return {
        "status": "ok",
        "output_path": str(path),
        "contract_name": payload["contract_name"],
        "contract_version": payload["contract_version"],
        "required_numeric_count": payload["required_numeric_count"],
        "required_context_count": payload["required_context_count"],
        "optional_numeric_count": payload["optional_numeric_count"],
        "traceability_count": payload["traceability_count"],
        "future_gate_policy_target_count": payload[
            "future_gate_policy_target_count"
        ],
        "runtime_adapter_implemented": payload["runtime_adapter_implemented"],
    }



@cli.command("gate-policy-runtime-adapter-contract-export")
def gate_policy_runtime_adapter_contract_export(
    output_path: Path = typer.Option(
        Path("reports/gate_policy_runtime_adapter_contract_summary.json"),
        "--output-path",
        help="Путь для сохранения compact GatePolicy runtime adapter contract summary.",
    ),
) -> None:
    """Сохранить compact GatePolicy runtime adapter contract summary в JSON-файл."""

    payload = export_gate_policy_runtime_adapter_contract_summary_report(
        output_path=output_path,
    )

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("gate-policy-runtime-adapter-contract-preview")
def gate_policy_runtime_adapter_contract_preview() -> None:
    """Показать compact preview GatePolicy runtime adapter contract в JSON."""

    payload = build_gate_policy_runtime_adapter_contract_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("gate-policy-prediction-mapping-plan-preview")
def gate_policy_prediction_mapping_plan_preview() -> None:
    """Показать compact preview GatePolicy prediction mapping plan в JSON."""

    payload = build_gate_policy_prediction_mapping_plan_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("gate-policy-prediction-mapping-plan-export")
def gate_policy_prediction_mapping_plan_export(
    output_path: Path = typer.Option(
        Path("reports/gate_policy_prediction_mapping_plan_summary.json"),
        "--output-path",
        help="Путь для сохранения compact GatePolicy prediction mapping plan summary.",
    ),
) -> None:
    """Сохранить compact GatePolicy prediction mapping plan summary в JSON-файл."""

    payload = export_gate_policy_prediction_mapping_plan_summary_report(
        output_path=output_path,
    )

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("gate-policy-prediction-runtime-shape-summary")
def gate_policy_prediction_runtime_shape_summary(
    root_path: Path = typer.Option(
        Path("."),
        "--root-path",
        help="Корневой путь проекта для prediction runtime shape discovery.",
    ),
) -> None:
    """Показать compact summary GatePolicy prediction runtime shape discovery в JSON."""

    payload = build_gate_policy_prediction_runtime_shape_summary_payload(root_path)

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("gate-policy-prediction-runtime-shape-export")
def gate_policy_prediction_runtime_shape_export(
    root_path: Path = typer.Option(
        Path("."),
        "--root-path",
        help="Корневой путь проекта для prediction runtime shape discovery.",
    ),
    output_path: Path = typer.Option(
        Path("reports/gate_policy_prediction_runtime_shape_summary.json"),
        "--output-path",
        help="Путь для сохранения compact GatePolicy prediction runtime shape summary.",
    ),
) -> None:
    """Сохранить compact GatePolicy prediction runtime shape summary в JSON-файл."""

    payload = export_gate_policy_prediction_runtime_shape_summary_report(
        root_path=root_path,
        output_path=output_path,
    )

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("gate-policy-prediction-discovery-summary")
def gate_policy_prediction_discovery_summary(
    root_path: Path = typer.Option(
        Path("."),
        "--root-path",
        help="Корневой путь проекта для prediction discovery.",
    ),
) -> None:
    """Показать compact summary GatePolicy prediction discovery в JSON."""

    payload = build_gate_policy_prediction_discovery_summary_payload(root_path)

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("gate-policy-prediction-discovery-export")
def gate_policy_prediction_discovery_export(
    root_path: Path = typer.Option(
        Path("."),
        "--root-path",
        help="Корневой путь проекта для prediction discovery.",
    ),
    output_path: Path = typer.Option(
        Path("reports/gate_policy_prediction_discovery_summary.json"),
        "--output-path",
        help="Путь для сохранения compact GatePolicy prediction discovery summary.",
    ),
) -> None:
    """Сохранить compact GatePolicy prediction discovery summary в JSON-файл."""

    payload = export_gate_policy_prediction_discovery_summary_report(
        root_path=root_path,
        output_path=output_path,
    )

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("gate-policy-prediction-contract-preview")
def gate_policy_prediction_contract_preview() -> None:
    """Показать GatePolicy prediction payload contract в JSON."""

    payload = build_gate_policy_prediction_contract_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("gate-policy-prediction-contract-export")
def gate_policy_prediction_contract_export(
    output_path: Path = typer.Option(
        Path("reports/gate_policy_prediction_contract_report.json"),
        "--output-path",
        help="Путь для сохранения GatePolicy prediction payload contract.",
    ),
) -> None:
    """Сохранить GatePolicy prediction payload contract в JSON-файл."""

    payload = export_gate_policy_prediction_contract_report(output_path)

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

@cli.command("gate-policy-adapter-preview")
def gate_policy_adapter_preview() -> None:
    """Показать demo GatePolicy adapter diagnostics в JSON."""

    payload = build_gate_policy_adapter_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("gate-policy-adapter-export")
def gate_policy_adapter_export(
    output_path: Path = typer.Option(
        Path("reports/gate_policy_adapter_preview_report.json"),
        "--output-path",
        help="Путь для сохранения GatePolicy adapter preview отчёта.",
    ),
) -> None:
    """Сохранить demo GatePolicy adapter preview report в JSON-файл."""

    payload = export_gate_policy_adapter_preview_report(output_path)

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("gate-policy-smoke")
def gate_policy_smoke() -> None:
    """Показать демонстрационный GatePolicy-отчёт в JSON."""

    payload = build_gate_policy_smoke_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("gate-policy-export")
def gate_policy_export(
    output_path: Path = typer.Option(
        Path("reports/gate_policy_smoke_report.json"),
        "--output-path",
        help="Путь для сохранения GatePolicy smoke-отчёта.",
    ),
) -> None:
    """Сохранить демонстрационный GatePolicy-отчёт в JSON-файл."""

    payload = export_gate_policy_smoke_report(output_path)

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    cli()
