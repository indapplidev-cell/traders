import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import typer
from sqlalchemy import text

from app import __version__
from app.baseline.baseline_service import BaselineService
from app.config.settings import get_settings
from app.data.binance_client import BinanceClient
from app.data.candle_gap_checker import CandleGapChecker
from app.data.historical_loader import HistoricalLoader
from app.dataset.dataset_builder import DatasetBuilder
from app.dataset.gap_aware_dataset_filter import GapAwareDatasetFilter
from app.diagnostics.gap_quality_diagnostics import GapQualityDiagnostics
from app.diagnostics.feature_group_quality import FeatureGroupQualityScorer
from app.diagnostics.feature_leakage_guard import FeatureLeakageGuard
from app.diagnostics.feature_quality_diagnostics import FeatureQualityDiagnostics
from app.diagnostics.collapse_diagnostics_v2 import CollapseDiagnosticsV2
from app.diagnostics.real_feature_diagnostics_service import RealFeatureDiagnosticsService
from app.diagnostics.regime_feature_diagnostics import RegimeFeatureDiagnostics
from app.diagnostics.walk_forward_profit_diagnostics import WalkForwardProfitDiagnostics
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
from app.experiments.label_grid_experiment_runner import (
    LabelGridExperimentConfig,
    LabelGridExperimentRunner,
)
from app.experiments.label_grid_experiment_reporter import (
    LabelGridExperimentReporter,
)
from app.experiments.label_grid_search import LabelGridSearchService
from app.experiments.label_grid_result_analyzer import LabelGridResultAnalyzer
from app.experiments.label_grid_result_reporter import LabelGridResultReporter
from app.experiments.feature_regime_experiment_runner import (
    FeatureRegimeExperimentConfig,
    FeatureRegimeExperimentRunner,
)
from app.experiments.feature_regime_result_analyzer import FeatureRegimeResultAnalyzer
from app.experiments.feature_regime_experiment_reporter import (
    FeatureRegimeExperimentReporter,
)
from app.experiments.multi_symbol_feature_regime_analyzer import (
    MultiSymbolFeatureRegimeAnalyzer,
)
from app.experiments.multi_symbol_feature_regime_reporter import (
    MultiSymbolFeatureRegimeReporter,
)
from app.experiments.ml31_grid_improvement_analyzer import ML31GridImprovementAnalyzer
from app.experiments.ml31_grid_improvement_reporter import ML31GridImprovementReporter
from app.experiments.regime_experiment_planner import RegimeExperimentPlanner
from app.evaluation.gate_policy_replay_evaluator import GatePolicyReplayEvaluator
from app.evaluation.gate_policy_replay_reporter import GatePolicyReplayReporter
from app.evaluation.anti_collapse_validator import AntiCollapseValidator
from app.evaluation.candidate_acceptance_thresholds import (
    default_candidate_acceptance_thresholds,
)
from app.evaluation.model_candidate_selector import ModelCandidateSelector
from app.evaluation.model_quality_reporter import ModelQualityReporter
from app.evaluation.model_quality_validator import validate_model_quality
from app.features.feature_pipeline import FeaturePipeline
from app.features.feature_engineering_plan import FeatureEngineeringPlan
from app.features.feature_models import feature_names_for_version
from app.labels.label_config import LabelConfig
from app.registry.artifact_storage import ArtifactStorage
from app.registry.model_loader import ModelLoader
from app.registry.model_registry import ModelRegistry
from app.labels.label_builder import LabelBuilder
from app.labels.label_quality_grid import LabelQualityGridPlanner
from app.labels.regime_label_builder import RegimeLabelBuilder
from app.labels.regime_label_config import RegimeLabelConfigPlanner
from app.labels.regime_label_integration_status import RegimeLabelIntegrationStatus
from app.prediction.predictor import Predictor
from app.replay.historical_replay_engine import HistoricalReplayEngine
from app.replay.replay_service import ReplayService
from app.training.training_service import TrainingService
from app.training.anti_collapse_training_plan import AntiCollapseTrainingPlan
from app.training.training_pipeline_reporter import TrainingPipelineReporter
from app.training.training_pipeline_runner import (
    LongHistoryTrainingPipelineRunner,
    TrainingPipelineConfig,
)
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
from app.gates.gate_policy_prediction_runtime_binding import (
    bind_prediction_payload_to_gate_policy,
)
from app.gates.gate_policy_prediction_runtime_binding_reporter import (
    GatePolicyPredictionRuntimeBindingReporter,
)
from app.gates.gate_policy_prediction_runtime_adapter_contract_reporter import (
    GatePolicyPredictionRuntimeAdapterContractReporter,
)
from app.audit.final_readiness_reporter import FinalReadinessReporter


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


def build_gate_policy_runtime_binding_preview_payload() -> dict[str, object]:
    """Build a safe sample runtime binding preview payload."""

    sample_payload = {
        "prob_up": 0.61,
        "prob_down": 0.21,
        "prob_flat": 0.18,
        "confidence": 0.72,
        "tp_before_sl_probability": 0.64,
        "risk_score": 0.31,
        "expected_move_atr": 1.45,
        "regime": "trend_up",
        "model_version": "sample_model_v1",
        "symbol": "BTCUSDT",
        "interval": "15m",
    }

    reporter = GatePolicyPredictionRuntimeBindingReporter()
    result = bind_prediction_payload_to_gate_policy(sample_payload)

    return reporter.result_to_dict(result)


def export_gate_policy_runtime_binding_summary_report(
    output_path: str | Path = Path("reports/gate_policy_runtime_binding_summary.json"),
) -> dict[str, object]:
    """Export runtime binding summary/report JSON."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    reporter = GatePolicyPredictionRuntimeBindingReporter()
    sample_result = build_gate_policy_runtime_binding_preview_payload()
    summary = reporter.summary_to_dict()
    payload = {
        "binding_name": summary["binding_name"],
        "binding_version": summary["binding_version"],
        "summary": summary,
        "sample_result": sample_result,
        "sample_direction": sample_result["direction"],
        "sample_is_valid": sample_result["is_valid"],
        "database_connected": summary["database_connected"],
        "traders_core_connected": summary["traders_core_connected"],
        "live_trading_connected": summary["live_trading_connected"],
        "orders_enabled": summary["orders_enabled"],
    }

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
        "binding_name": payload["binding_name"],
        "binding_version": payload["binding_version"],
        "sample_direction": payload["sample_direction"],
        "sample_is_valid": payload["sample_is_valid"],
        "database_connected": payload["database_connected"],
        "traders_core_connected": payload["traders_core_connected"],
        "live_trading_connected": payload["live_trading_connected"],
        "orders_enabled": payload["orders_enabled"],
    }


def build_gate_policy_replay_evaluate_preview_payload() -> dict[str, object]:
    """Build a compact preview for GatePolicy replay evaluation."""

    payloads = [
        {
            "timestamp": "2026-06-11T12:00:00Z",
            "symbol": "BTCUSDT",
            "interval": "15m",
            "model_version": "sample_model_v1",
            "prob_up": 0.61,
            "prob_down": 0.21,
            "prob_flat": 0.18,
            "confidence": 0.72,
            "tp_before_sl_probability": 0.64,
            "risk_score": 0.31,
            "expected_move_atr": 1.45,
            "regime": "trend_up",
        },
        {
            "timestamp": "2026-06-11T12:15:00Z",
            "symbol": "BTCUSDT",
            "interval": "15m",
            "model_version": "sample_model_v1",
            "prob_up": 0.15,
            "prob_down": 0.67,
            "prob_flat": 0.18,
            "confidence": 0.67,
            "tp_before_sl_probability": 0.63,
            "risk_score": 0.25,
            "expected_move_atr": 1.20,
            "regime": "trend_down",
        },
        {
            "timestamp": "2026-06-11T12:30:00Z",
            "symbol": "BTCUSDT",
            "interval": "15m",
            "model_version": "sample_model_v1",
            "prob_up": 0.20,
            "prob_down": 0.18,
            "prob_flat": 0.62,
            "confidence": 0.62,
            "tp_before_sl_probability": 0.59,
            "risk_score": 0.20,
            "expected_move_atr": 0.60,
            "regime": "trend_up",
        },
        {
            "timestamp": "2026-06-11T12:45:00Z",
            "symbol": "BTCUSDT",
            "interval": "15m",
            "model_version": "sample_model_v1",
            "prob_up": 0.40,
            "prob_down": 0.40,
            "prob_flat": 0.20,
            "confidence": 0.40,
            "tp_before_sl_probability": 0.50,
            "risk_score": 0.40,
            "expected_move_atr": 0.80,
            "regime": "trend_up",
        },
        {
            "timestamp": "2026-06-11T13:00:00Z",
            "symbol": "BTCUSDT",
            "interval": "15m",
            "model_version": "sample_model_v1",
            "prob_up": 0.55,
            "prob_flat": 0.45,
            "confidence": 0.55,
            "tp_before_sl_probability": 0.58,
            "regime": "trend_up",
        },
    ]

    evaluator = GatePolicyReplayEvaluator()
    reporter = GatePolicyReplayReporter()

    summary = evaluator.evaluate(payloads)

    return reporter.compact_summary_to_dict(summary)


def export_gate_policy_replay_evaluation_summary_report(
    output_path: str | Path = Path("reports/gate_policy_replay_evaluation_summary.json"),
) -> dict[str, object]:
    """Export GatePolicy replay evaluation compact summary."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = build_gate_policy_replay_evaluate_preview_payload()
    export_payload = {
        **payload,
        "runtime_binding_used": payload["integration_status"]["runtime_binding_used"],
        "gate_policy_used": payload["integration_status"]["gate_policy_used"],
        "prediction_service_required": payload["integration_status"][
            "prediction_service_required"
        ],
        "database_connected": payload["integration_status"]["database_connected"],
        "database_writes": payload["integration_status"]["database_writes"],
        "traders_core_connected": payload["integration_status"][
            "traders_core_connected"
        ],
        "live_trading_connected": payload["integration_status"][
            "live_trading_connected"
        ],
        "orders_enabled": payload["integration_status"]["orders_enabled"],
    }

    path.write_text(
        json.dumps(
            export_payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    return {
        "status": "ok",
        "output_path": str(path),
        "evaluator_name": payload["evaluator_name"],
        "evaluator_version": payload["evaluator_version"],
        "total_records": payload["total_records"],
        "valid_records": payload["valid_records"],
        "invalid_records": payload["invalid_records"],
        "gate_policy_allowed_count": payload["gate_policy_allowed_count"],
        "gate_policy_blocked_count": payload["gate_policy_blocked_count"],
        "orders_enabled": export_payload["orders_enabled"],
        "live_trading_connected": export_payload["live_trading_connected"],
        "traders_core_connected": export_payload["traders_core_connected"],
        "database_writes": export_payload["database_writes"],
    }


def build_final_readiness_audit_preview_payload() -> dict[str, object]:
    """Build a compact preview for the final standalone readiness audit."""

    reporter = FinalReadinessReporter()
    return reporter.build_compact_summary()


def export_final_readiness_audit_report(
    output_path: str | Path = Path("reports/final_standalone_readiness_audit.json"),
) -> dict[str, object]:
    """Export the full standalone readiness audit report."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    reporter = FinalReadinessReporter()
    full_report = reporter.build_full_report()
    compact_summary = reporter.build_compact_summary()

    path.write_text(
        reporter.full_report_to_json(),
        encoding="utf-8",
    )

    return {
        "status": "ok",
        "output_path": str(path),
        "audit_name": full_report["audit_name"],
        "audit_version": full_report["audit_version"],
        "readiness_status": full_report["status"],
        "ready_component_count": compact_summary["ready_component_count"],
        "needs_attention_component_count": compact_summary[
            "needs_attention_component_count"
        ],
        "standalone_ml_service_ready": compact_summary[
            "standalone_ml_service_ready"
        ],
        "traders_core_connected": compact_summary["traders_core_connected"],
        "live_trading_connected": compact_summary["live_trading_connected"],
        "orders_enabled": compact_summary["orders_enabled"],
    }


def build_model_anti_collapse_preview_payload() -> dict[str, object]:
    """Build a deterministic anti-collapse preview from the latest bad run profile."""

    probability_report = {
        "actual_direction_counts": {"UP": 3661, "DOWN": 3787, "FLAT": 2449},
        "predicted_direction_counts": {"UP": 8516, "DOWN": 421, "FLAT": 960},
        "avg_prob_up": 0.35053143812825466,
        "avg_prob_down": 0.3242517144370226,
        "avg_prob_flat": 0.3252168477448813,
        "max_prob_q90": 0.3655545234680176,
        "max_prob_q50": 0.34978190064430237,
        "margin_q90": 0.04313697814941406,
        "margin_q50": 0.020096540451049805,
        "rows_above_thresholds": {"0.45": 0},
    }
    return AntiCollapseValidator().validate_probability_report(probability_report)


def export_model_anti_collapse_preview(
    output_path: str | Path = Path("reports/model_anti_collapse_preview.json"),
) -> dict[str, object]:
    """Export deterministic anti-collapse preview JSON."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_model_anti_collapse_preview_payload()
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return {
        "status": "ok",
        "output_path": str(path),
        "collapse_detected": payload["collapse_detected"],
        "collapse_type": payload["collapse_type"],
    }


def build_label_quality_grid_preview_payload() -> dict[str, object]:
    """Build a reusable ML30 label-quality grid preview."""

    return LabelQualityGridPlanner().build_grid()


def export_label_quality_grid_preview(
    output_path: str | Path = Path("reports/label_quality_grid_preview.json"),
) -> dict[str, object]:
    """Export label-quality grid preview JSON."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_label_quality_grid_preview_payload()
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return {
        "status": "ok",
        "output_path": str(path),
        "config_count": payload["config_count"],
    }


def build_label_grid_experiment_preview_payload() -> dict[str, object]:
    """Build a reusable ML28 label-grid experiment preview."""

    return LabelGridExperimentRunner().build_preview()


def build_gap_aware_filter_preview_payload() -> dict[str, object]:
    """Build a deterministic ML30 gap-aware dataset filter preview."""

    rows = [
        {"candle_open_time": f"2025-03-01T0{hour}:00:00+00:00", "row_id": hour}
        for hour in range(6)
    ]
    filtered_rows, summary = GapAwareDatasetFilter().apply(
        rows=rows,
        symbol="BTCUSDT",
        interval="15m",
        gap_count=1,
        missing_open_times=["2025-03-01T02:30:00+00:00"],
        lookback_bars=1,
        lookahead_bars=1,
    )
    return {
        **summary,
        "excluded_row_ids": [
            row["row_id"] for row in rows if row not in filtered_rows
        ],
        "remaining_row_ids": [row["row_id"] for row in filtered_rows],
    }


def build_feature_quality_preview_payload() -> dict[str, object]:
    """Build a deterministic ML30 feature quality diagnostic preview."""

    rows = [
        {
            "direction_label": "UP",
            "features_json": {"trend_strength": 1.20, "volatility": 0.55, "flat_bias": 0.10},
        },
        {
            "direction_label": "UP",
            "features_json": {"trend_strength": 1.05, "volatility": 0.58, "flat_bias": 0.10},
        },
        {
            "direction_label": "DOWN",
            "features_json": {"trend_strength": -0.85, "volatility": 0.61, "flat_bias": 0.10},
        },
        {
            "direction_label": "DOWN",
            "features_json": {"trend_strength": -1.10, "volatility": None, "flat_bias": 0.10},
        },
        {
            "direction_label": "FLAT",
            "features_json": {"trend_strength": 0.05, "volatility": 0.20, "flat_bias": 0.10},
        },
    ]
    return FeatureQualityDiagnostics().analyze(rows)


def build_anti_collapse_training_plan_preview_payload() -> dict[str, object]:
    """Build a deterministic ML30 anti-collapse training plan preview."""

    return AntiCollapseTrainingPlan().build_plan()


def build_candidate_thresholds_preview_payload() -> dict[str, object]:
    """Build a deterministic ML30 candidate threshold preview."""

    thresholds = default_candidate_acceptance_thresholds()
    return {
        "threshold_name": "candidate_acceptance_thresholds",
        "threshold_version": "ml30",
        "thresholds": thresholds.to_dict(),
        "gap_examples": {
            "MODERATE_allowed": thresholds.gap_severity_allowed("MODERATE"),
            "HIGH_allowed": thresholds.gap_severity_allowed("HIGH"),
        },
        "candidate_status_preview": build_model_candidate_selection_preview_payload()[
            "candidate_status"
        ],
    }


def _build_ml32_regime_sample_rows() -> list[dict[str, object]]:
    return [
        {
            "direction_label": "UP",
            "features_json": {
                "trend_strength": 1.20,
                "ema_21_to_ema_50": 0.14,
                "volume_ratio_20": 1.30,
                "rsi_14": 61.0,
                "regime_trend_up": 1.0,
                "regime_trend_down": 0.0,
                "regime_range": 0.0,
                "regime_high_volatility": 0.0,
                "regime_low_volatility": 1.0,
            },
        },
        {
            "direction_label": "UP",
            "features_json": {
                "trend_strength": 1.05,
                "ema_21_to_ema_50": 0.11,
                "volume_ratio_20": 1.10,
                "rsi_14": 58.0,
                "regime_trend_up": 1.0,
                "regime_trend_down": 0.0,
                "regime_range": 0.0,
                "regime_high_volatility": 0.0,
                "regime_low_volatility": 1.0,
            },
        },
        {
            "direction_label": "DOWN",
            "features_json": {
                "trend_strength": -0.95,
                "ema_21_to_ema_50": -0.12,
                "volume_ratio_20": 1.35,
                "rsi_14": 38.0,
                "regime_trend_up": 0.0,
                "regime_trend_down": 1.0,
                "regime_range": 0.0,
                "regime_high_volatility": 1.0,
                "regime_low_volatility": 0.0,
            },
        },
        {
            "direction_label": "FLAT",
            "features_json": {
                "trend_strength": 0.05,
                "ema_21_to_ema_50": 0.01,
                "volume_ratio_20": None,
                "rsi_14": 49.0,
                "regime_trend_up": 0.0,
                "regime_trend_down": 0.0,
                "regime_range": 1.0,
                "regime_high_volatility": 0.0,
                "regime_low_volatility": 1.0,
            },
        },
        {
            "direction_label": "DOWN",
            "features_json": {
                "trend_strength": -0.70,
                "ema_21_to_ema_50": -0.08,
                "volume_ratio_20": 1.05,
                "rsi_14": 42.0,
                "regime_trend_up": 0.0,
                "regime_trend_down": 1.0,
                "regime_range": 0.0,
                "regime_high_volatility": 1.0,
                "regime_low_volatility": 0.0,
            },
        },
        {
            "direction_label": "FLAT",
            "features_json": {
                "trend_strength": 0.02,
                "ema_21_to_ema_50": 0.0,
                "volume_ratio_20": 0.95,
                "rsi_14": 50.0,
                "regime_trend_up": 0.0,
                "regime_trend_down": 0.0,
                "regime_range": 0.0,
                "regime_high_volatility": 0.0,
                "regime_low_volatility": 0.0,
            },
        },
    ]


def build_regime_feature_diagnostics_preview_payload() -> dict[str, object]:
    """Build a deterministic ML32 regime-aware feature diagnostic preview."""

    payload = RegimeFeatureDiagnostics().analyze(_build_ml32_regime_sample_rows())
    payload.update(
        {
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "orders_enabled": False,
            "traders_core_connected": False,
        }
    )
    return payload


def build_feature_group_quality_preview_payload() -> dict[str, object]:
    """Build a deterministic ML32 feature-group quality preview."""

    payload = FeatureGroupQualityScorer().analyze(_build_ml32_regime_sample_rows())
    payload.update(
        {
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "orders_enabled": False,
            "traders_core_connected": False,
        }
    )
    return payload


def build_regime_label_config_preview_payload() -> dict[str, object]:
    """Build a deterministic ML32 regime-label config preview."""

    payload = RegimeLabelConfigPlanner().build_configs()
    payload.update(
        {
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "orders_enabled": False,
            "traders_core_connected": False,
        }
    )
    return payload


def build_regime_experiment_plan_preview_payload() -> dict[str, object]:
    """Build a deterministic ML32 regime-experiment plan preview."""

    return RegimeExperimentPlanner().build_plan(
        symbol="BTCUSDT",
        interval="15m",
        start_date="2025-01-01",
        regime_data_available=True,
    )


def build_feature_leakage_guard_preview_payload() -> dict[str, object]:
    """Build a deterministic ML32 feature-leakage guard preview."""

    payload = FeatureLeakageGuard().check(
        [
            "trend_strength",
            "volume_ratio_20",
            "return_future_1",
            "target_score",
        ]
    )
    payload.update(
        {
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "orders_enabled": False,
            "traders_core_connected": False,
        }
    )
    return payload


def build_feature_regime_experiment_preview_payload() -> dict[str, object]:
    """Build a deterministic ML33 feature/regime experiment preview."""

    return FeatureRegimeExperimentRunner().build_preview()


def build_gap_quality_preview_payload() -> dict[str, object]:
    """Build an ML34 gap-quality preview using real data when available."""

    symbol = "BTCUSDT"
    interval = "15m"
    start_date = "2025-01-01"
    end_date = date.today().isoformat()
    start_at, end_at = LongHistoryTrainingPipelineRunner._build_utc_date_range(
        LongHistoryTrainingPipelineRunner._parse_date(start_date),
        LongHistoryTrainingPipelineRunner._parse_date(end_date),
    )
    with get_session() as session:
        candles = CandleRepository(session).get_range(
            symbol=symbol,
            interval=interval,
            start_at=start_at,
            end_at=end_at,
        )
    if candles:
        gap_stage = CandleGapChecker().check(
            candles=candles,
            interval=interval,
            start_at=start_at,
            end_at=end_at,
            symbol=symbol,
        )
        payload = GapQualityDiagnostics().analyze(
            symbol=symbol,
            interval=interval,
            start_date=start_date,
            end_date=end_date,
            gap_count=int(gap_stage.get("gap_count", 0)),
            missing_open_times=list(gap_stage.get("missing_open_times", [])),
            last_open_time=gap_stage.get("last_open_time"),
            real_gap_count=gap_stage.get("real_gap_count"),
            real_missing_open_times=list(gap_stage.get("real_missing_open_times", [])),
            trailing_incomplete_count=gap_stage.get("trailing_incomplete_count"),
            trailing_incomplete_open_times=list(gap_stage.get("trailing_incomplete_open_times", [])),
            trailing_incomplete_range_detected=gap_stage.get("trailing_incomplete_range_detected"),
        )
    else:
        payload = GapQualityDiagnostics().analyze(
            symbol=symbol,
            interval=interval,
            start_date=start_date,
            end_date=end_date,
            gap_count=0,
        )
        payload["degraded_mode"] = True
        payload["warnings"] = list(dict.fromkeys(list(payload.get("warnings", [])) + ["no_candles_loaded"]))
    payload.update(
        {
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "orders_enabled": False,
            "traders_core_connected": False,
        }
    )
    return payload


def build_real_feature_diagnostics_preview_payload() -> dict[str, object]:
    """Build an ML34 real-feature-diagnostics preview."""

    symbol = "BTCUSDT"
    interval = "15m"
    feature_version = "fv2"
    label_version = "lv2_h08_thr04_tp10_sl10"
    horizon_candles = 8
    with get_session() as session:
        dataset_builder = DatasetBuilder(
            feature_repository=FeatureRepository(session),
            label_repository=LabelRepository(session),
        )
        service = RealFeatureDiagnosticsService()
        try:
            rows, _summary = dataset_builder.build_rows(
                symbol=symbol,
                interval=interval,
                horizon_candles=horizon_candles,
                feature_version=feature_version,
                label_version=label_version,
            )
        except Exception as exc:
            payload = service.analyze(
                symbol=symbol,
                interval=interval,
                feature_version=feature_version,
                label_version=label_version,
                rows=[],
                source="dataset_builder",
                reason=f"dataset_rows_unavailable:{exc}",
            )
        else:
            payload = service.analyze(
                symbol=symbol,
                interval=interval,
                feature_version=feature_version,
                label_version=label_version,
                rows=rows,
                source="dataset_builder",
                reason="dataset_rows_unavailable" if not rows else None,
            )
    payload.update(
        {
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "orders_enabled": False,
            "traders_core_connected": False,
        }
    )
    return payload


def build_feature_regime_integration_preview_payload() -> dict[str, object]:
    """Build an ML34 feature/regime integration preview."""

    feature_version = "fv2"
    required_regime_features = {
        "regime_trend_up",
        "regime_trend_down",
        "regime_range",
        "regime_high_volatility",
        "regime_low_volatility",
        "regime_unknown",
    }
    try:
        feature_names = feature_names_for_version(feature_version)
    except ValueError:
        feature_names = []
        feature_version_available = False
    else:
        feature_version_available = True

    attached = required_regime_features.issubset(set(feature_names))
    status = RegimeLabelIntegrationStatus().build_status(
        regime_specific_labeling_available=RegimeLabelConfigPlanner().build_configs()["config_count"] > 0,
        regime_features_attached=attached,
        regime_feature_count=len([name for name in feature_names if name.startswith("regime_")]),
        training_pipeline_supports_regime_labels=True,
    )
    payload = {
        "feature_version_available": feature_version_available,
        "feature_version_used": feature_version,
        "regime_features_attached": attached,
        "regime_feature_count": len([name for name in feature_names if name.startswith("regime_")]),
        "regime_specific_labeling_available": status["regime_specific_labeling_available"],
        "regime_specific_training_applied": status["regime_specific_training_applied"],
        "missing_requirements": status["missing_requirements"],
        "next_steps": status["next_steps"],
        "approved_for_live_trading": False,
        "approved_for_auto_activation": False,
        "orders_enabled": False,
        "traders_core_connected": False,
    }
    return payload


def build_collapse_diagnostics_preview_payload() -> dict[str, object]:
    """Build a deterministic ML36 collapse diagnostics preview."""

    payload = CollapseDiagnosticsV2().analyze(
        probability_report={
            "actual_direction_counts": {"UP": 360, "DOWN": 300, "FLAT": 340},
            "predicted_direction_counts": {"UP": 900, "DOWN": 80, "FLAT": 20},
            "avg_prob_up": 0.36,
            "avg_prob_down": 0.33,
            "avg_prob_flat": 0.31,
            "max_prob_q50": 0.38,
            "max_prob_q90": 0.39,
            "rows_above_thresholds": {"0.45": 0},
            "margin_q50": 0.02,
            "margin_q90": 0.04,
        },
        symbol="BTCUSDT",
        feature_version="fv2",
        label_version="lv2_h08_thr04_tp10_sl10",
        accuracy_edge=0.018072,
        walk_forward_summary={"walk_forward_status": "UNSTABLE"},
    )
    payload.update(
        {
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "orders_enabled": False,
            "traders_core_connected": False,
        }
    )
    return payload


def build_regime_label_builder_preview_payload() -> dict[str, object]:
    """Build a deterministic ML36 regime-label-builder preview."""

    candles = [
        SimpleNamespace(
            open_time=datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=15 * index),
            open=100.0 + (index * 2.0),
            high=101.8 + (index * 2.0),
            low=99.2 + (index * 2.0),
            close=101.2 + (index * 2.0),
        )
        for index in range(40)
    ]
    feature_rows = []
    for index, candle in enumerate(candles):
        feature_rows.append(
            SimpleNamespace(
                candle_open_time=candle.open_time,
                features_json={
                    "regime_trend_up": 1.0 if index % 3 == 0 else 0.0,
                    "regime_trend_down": 1.0 if index % 3 == 1 else 0.0,
                    "regime_range": 1.0 if index % 3 == 2 else 0.0,
                    "regime_high_volatility": 1.0 if index % 4 == 0 else 0.0,
                    "regime_low_volatility": 1.0 if index % 4 != 0 else 0.0,
                    "regime_unknown": 0.0,
                },
            )
        )
    result = RegimeLabelBuilder().build(
        candles=candles,
        symbol="BTCUSDT",
        interval="15m",
        feature_rows=feature_rows,
        base_config=LabelConfig(
            label_version="lv2_h12_thr05_tp15_sl10",
            horizon_candles=12,
            direction_atr_threshold=0.5,
            take_profit_atr=1.5,
            stop_loss_atr=1.0,
            flat_class_enabled=True,
        ),
    ).to_dict()
    result.update(
        {
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "orders_enabled": False,
            "traders_core_connected": False,
        }
    )
    return result


def build_walk_forward_profit_diagnostics_preview_payload() -> dict[str, object]:
    """Build a deterministic ML36 walk-forward/profit diagnostics preview."""

    payload = WalkForwardProfitDiagnostics().analyze(
        symbol="BTCUSDT",
        feature_version="fv2",
        model_version="ml36_preview_model",
        walk_forward_summary={
            "walk_forward_status": "UNSTABLE",
            "summary": {
                "fold_count": 4,
                "folds_with_selected_gate": 4,
                "folds_profitable_on_test": 1,
                "global_total_r": -2.4,
                "global_profit_factor": 0.96,
            },
            "folds": [
                {"fold_index": 0, "selected_gate": {"gate_type": "confidence", "threshold": 0.55}, "test_result": {"signal_count": 12, "resolved_signal_count": 12, "profit_factor": 1.08, "total_r": 0.9}},
                {"fold_index": 1, "selected_gate": {"gate_type": "confidence", "threshold": 0.55}, "test_result": {"signal_count": 3, "resolved_signal_count": 3, "profit_factor": 0.91, "total_r": -0.8}},
                {"fold_index": 2, "selected_gate": {"gate_type": "confidence", "threshold": 0.60}, "test_result": {"signal_count": 4, "resolved_signal_count": 4, "profit_factor": 0.88, "total_r": -1.1}},
                {"fold_index": 3, "selected_gate": {"gate_type": "margin", "threshold": 0.12}, "test_result": {"signal_count": 2, "resolved_signal_count": 2, "profit_factor": 0.72, "total_r": -1.4}},
            ],
        },
        profit_aware_summary={
            "gate_results": [
                {"gate_type": "confidence", "threshold": 0.55, "resolved_signal_count": 20, "profit_factor": 0.99, "total_r": -0.5},
                {"gate_type": "margin", "threshold": 0.12, "resolved_signal_count": 16, "profit_factor": 1.04, "total_r": 0.3},
            ]
        },
    )
    payload.update(
        {
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "orders_enabled": False,
            "traders_core_connected": False,
        }
    )
    return payload


def run_label_grid_experiment(
    *,
    symbol: str,
    interval: str,
    start_date: str,
    end_date: str | None = None,
    experiment_id: str | None = None,
    feature_version: str = "fv1",
    label_config_ids: list[str] | None = None,
    max_configs: int | None = None,
    dry_run: bool = False,
    sample_mode: bool = False,
    run_training: bool = True,
    run_walk_forward: bool = True,
    run_gate_policy_replay: bool = True,
    output_dir: Path = Path("reports/label_grid_experiments"),
) -> dict[str, object]:
    """Run the ML28 label-grid experiment session."""

    config = LabelGridExperimentConfig(
        symbol=symbol,
        interval=interval,
        start_date=start_date,
        end_date=end_date,
        experiment_id=experiment_id,
        feature_version=feature_version,
        label_config_ids=tuple(label_config_ids or ()),
        max_configs=max_configs,
        dry_run=dry_run,
        sample_mode=sample_mode,
        run_training=run_training,
        run_walk_forward=run_walk_forward,
        run_gate_policy_replay=run_gate_policy_replay,
        output_dir=output_dir,
    )
    result = LabelGridExperimentRunner().run(config)
    return LabelGridExperimentReporter().compact_summary_to_dict(result)


def analyze_label_grid_results(
    *,
    experiment_dir: str | Path | None = None,
    latest: bool = False,
    export_report: bool = True,
) -> dict[str, object]:
    """Analyze label-grid experiment outputs and export ML29 analysis artifacts."""

    if experiment_dir is None and not latest:
        raise ValueError("Provide --latest or --experiment-dir.")

    analyzer = LabelGridResultAnalyzer()
    reporter = LabelGridResultReporter()
    resolved_dir = (
        Path(experiment_dir)
        if experiment_dir is not None
        else analyzer.latest_experiment_dir()
    )
    summary = analyzer.load_summary(resolved_dir)
    analysis = analyzer.analyze(summary)
    plan = {
        "planner_name": analysis["planner_name"],
        "planner_version": analysis["planner_version"],
        "experiment_id": analysis["experiment_id"],
        "recommendations": analysis["recommendations"],
        "next_experiment_plan": analysis["next_experiment_plan"],
    }

    analysis_json_path = resolved_dir / "label_grid_result_analysis.json"
    analysis_markdown_path = resolved_dir / "label_grid_result_analysis.md"
    plan_json_path = resolved_dir / "next_label_experiment_plan.json"
    plan_markdown_path = resolved_dir / "next_label_experiment_plan.md"

    if export_report:
        reporter.write_analysis_json(analysis, analysis_json_path)
        reporter.write_analysis_markdown(analysis, analysis_markdown_path)
        reporter.write_plan_json(plan, plan_json_path)
        reporter.write_plan_markdown(plan, plan_markdown_path)

    payload = reporter.compact_summary_to_dict(
        analysis,
        analysis_json_path=str(analysis_json_path) if export_report else None,
        analysis_markdown_path=str(analysis_markdown_path) if export_report else None,
    )
    payload["plan_json_path"] = str(plan_json_path) if export_report else None
    payload["plan_markdown_path"] = str(plan_markdown_path) if export_report else None
    return payload


def analyze_ml31_grid_improvement(
    *,
    current_experiment_dir: str | Path | None = None,
    previous_experiment_dir: str | Path | None = None,
    latest: bool = False,
    export_report: bool = True,
) -> dict[str, object]:
    """Compare the current ML31 experiment with an optional previous baseline."""

    if current_experiment_dir is None and not latest:
        raise ValueError("Provide --latest or --current-experiment-dir.")

    analyzer = ML31GridImprovementAnalyzer()
    reporter = ML31GridImprovementReporter()
    resolved_current_dir = (
        Path(current_experiment_dir)
        if current_experiment_dir is not None
        else analyzer.latest_experiment_dir()
    )
    current_summary = analyzer.load_summary(resolved_current_dir)
    current_analysis = analyzer.load_analysis(resolved_current_dir)
    previous_payload = None
    if previous_experiment_dir is not None:
        resolved_previous_dir = Path(previous_experiment_dir)
        previous_analysis_path = resolved_previous_dir / "label_grid_result_analysis.json"
        previous_payload = (
            analyzer.load_analysis(resolved_previous_dir)
            if previous_analysis_path.exists()
            else analyzer.load_summary(resolved_previous_dir)
        )

    analysis = analyzer.analyze(
        current_experiment_summary=current_summary,
        current_analysis=current_analysis,
        previous_baseline_summary=previous_payload,
    )

    json_path = Path("reports/ml31_grid_improvement_analysis.json")
    markdown_path = Path("reports/ml31_grid_improvement_analysis.md")
    if export_report:
        reporter.write_analysis_json(analysis, json_path)
        reporter.write_analysis_markdown(analysis, markdown_path)

    return reporter.compact_summary_to_dict(
        analysis,
        json_path=str(json_path) if export_report else None,
        markdown_path=str(markdown_path) if export_report else None,
    )


def run_feature_regime_experiment(
    *,
    symbol: str,
    interval: str,
    start_date: str,
    end_date: str | None = None,
    experiment_id: str | None = None,
    feature_version: str = "fv2",
    base_label_config_ids: list[str] | None = None,
    regime_config_ids: list[str] | None = None,
    max_configs: int | None = None,
    dry_run: bool = False,
    sample_mode: bool = False,
    run_training: bool = True,
    run_regime_diagnostics: bool = True,
    run_feature_diagnostics: bool = True,
    run_leakage_guard: bool = True,
    run_candidate_selection: bool = True,
    output_dir: Path = Path("reports/feature_regime_experiments"),
) -> dict[str, object]:
    """Run the ML33 feature/regime-aware experiment flow."""

    config = FeatureRegimeExperimentConfig(
        symbol=symbol,
        interval=interval,
        start_date=start_date,
        end_date=end_date,
        experiment_id=experiment_id,
        feature_version=feature_version,
        base_label_config_ids=tuple(base_label_config_ids or ()),
        regime_config_ids=tuple(regime_config_ids or ()),
        max_configs=max_configs,
        dry_run=dry_run,
        sample_mode=sample_mode,
        run_training=run_training,
        run_regime_diagnostics=run_regime_diagnostics,
        run_feature_diagnostics=run_feature_diagnostics,
        run_leakage_guard=run_leakage_guard,
        run_candidate_selection=run_candidate_selection,
        output_dir=output_dir,
    )
    result = FeatureRegimeExperimentRunner().run(config)
    return FeatureRegimeExperimentReporter().compact_summary_to_dict(result)


def analyze_feature_regime_results(
    *,
    experiment_dir: str | Path | None = None,
    latest: bool = False,
) -> dict[str, object]:
    """Analyze an ML33 feature/regime experiment result."""

    if experiment_dir is None and not latest:
        raise ValueError("Provide --latest or --experiment-dir.")

    analyzer = FeatureRegimeResultAnalyzer()
    resolved_dir = (
        Path(experiment_dir)
        if experiment_dir is not None
        else analyzer.latest_experiment_dir()
    )
    summary = analyzer.load_summary(resolved_dir)
    analysis = analyzer.analyze(current_result=summary)
    payload = {
        "status": "ok",
        "experiment_id": summary.get("experiment_id"),
        "experiment_status": summary.get("experiment_status"),
        "config_count": summary.get("config_count"),
        "candidate_count": summary.get("candidate_count"),
        "accepted_candidate_count": summary.get("accepted_candidate_count"),
        "rejected_candidate_count": summary.get("rejected_candidate_count"),
        "best_candidate_config_id": summary.get("best_candidate_config_id"),
        "best_candidate_score": summary.get("best_candidate_score"),
        "feature_version_used": summary.get("feature_version_used"),
        "real_feature_diagnostics_used": summary.get("real_feature_diagnostics_used"),
        "real_feature_diagnostics_row_count": summary.get("real_feature_diagnostics_row_count"),
        "feature_weak_signal_detected": dict(summary.get("feature_quality_summary", {})).get("weak_signal_detected"),
        "regime_data_available": dict(summary.get("regime_feature_summary", {})).get("regime_data_available"),
        "regime_features_attached": summary.get("regime_features_attached"),
        "regime_feature_count": summary.get("regime_feature_count"),
        "regime_specific_labeling_available": summary.get("regime_specific_labeling_available"),
        "regime_training_applied": summary.get("regime_training_applied"),
        "regime_specific_training_applied": summary.get("regime_specific_training_applied"),
        "effective_gap_count_for_training": summary.get("effective_gap_count_for_training"),
        "gap_severity_for_training": summary.get("gap_severity_for_training"),
        "feature_leakage_risk_detected": dict(summary.get("feature_leakage_summary", {})).get("leakage_risk_detected"),
        "output_dir": summary.get("output_dir"),
        "summary_json_path": summary.get("summary_json_path"),
        "summary_markdown_path": summary.get("summary_markdown_path"),
        "overall_status": analysis.get("overall_status"),
        "score_delta": analysis.get("score_delta"),
        "recommendations": analysis.get("recommendations"),
        "approved_for_live_trading": False,
        "approved_for_auto_activation": False,
        "orders_enabled": False,
        "traders_core_connected": False,
    }
    return payload


def analyze_multi_symbol_feature_regime(
    *,
    experiments_root: str | Path = Path("reports/feature_regime_experiments"),
    symbols: list[str] | tuple[str, ...] = ("BTCUSDT", "ETHUSDT", "SOLUSDT"),
    latest_per_symbol: bool = False,
    export_report: bool = True,
) -> dict[str, object]:
    """Analyze multiple feature/regime experiment summaries together."""

    analyzer = MultiSymbolFeatureRegimeAnalyzer()
    reporter = MultiSymbolFeatureRegimeReporter()
    resolved_symbols = [item.strip() for item in symbols if item.strip()]
    if not resolved_symbols:
        raise ValueError("Provide at least one symbol.")

    if latest_per_symbol:
        summary_paths = analyzer.latest_summary_paths_by_symbol(
            root_dir=experiments_root,
            symbols=resolved_symbols,
        )
    else:
        summary_paths = analyzer.summary_paths_from_root(
            root_dir=experiments_root,
            symbols=resolved_symbols,
        )

    analysis = analyzer.analyze(summary_paths)
    json_path = Path("reports/multi_symbol_feature_regime_analysis.json")
    markdown_path = Path("reports/multi_symbol_feature_regime_analysis.md")
    if export_report:
        reporter.write_analysis_json(analysis, json_path)
        reporter.write_analysis_markdown(analysis, markdown_path)

    return reporter.compact_summary_to_dict(
        analysis,
        json_path=str(json_path) if export_report else None,
        markdown_path=str(markdown_path) if export_report else None,
    )


def build_model_candidate_selection_preview_payload() -> dict[str, object]:
    """Build a deterministic candidate-selection preview from the latest bad run profile."""

    gap_quality = GapQualityDiagnostics().analyze(
        symbol="BTCUSDT",
        interval="15m",
        start_date="2025-01-01",
        end_date="2026-06-12",
        gap_count=79,
    )
    anti_collapse = build_model_anti_collapse_preview_payload()
    profit_aware_summary = {
        "gate_results": [
            {
                "gate_type": "max_prob",
                "threshold": 0.34,
                "resolved_signal_count": 615,
                "total_r": -385.25,
                "profit_factor": 0.916,
            },
            {
                "gate_type": "max_prob",
                "threshold": 0.36,
                "resolved_signal_count": 164,
                "total_r": -95.13,
                "profit_factor": 0.918,
            },
            {
                "gate_type": "margin",
                "threshold": 0.02,
                "resolved_signal_count": 431,
                "total_r": -172.75,
                "profit_factor": 0.936,
            },
        ],
    }
    walk_forward_summary = {
        "summary": {
            "fold_count": 48,
            "folds_with_selected_gate": 26,
            "folds_profitable_on_test": 16,
            "global_total_r": -28.89,
            "global_profit_factor": 0.9888,
            "global_expectancy_r": -0.00607,
            "total_test_signal_count": 4756,
        }
    }
    gate_policy_replay_summary = {
        "gate_policy_replay_status": "SAMPLE_ONLY",
        "total_records": 5,
        "valid_records": 4,
        "invalid_records": 1,
    }
    return ModelCandidateSelector().select(
        model_version="ml_candle_mlp_v1_2026_06_12_040449",
        quality_status="QUALITY_REJECTED",
        gap_quality=gap_quality,
        anti_collapse=anti_collapse,
        calibration_status="ACCEPTABLE",
        profit_aware_summary=profit_aware_summary,
        walk_forward_summary=walk_forward_summary,
        gate_policy_replay_summary=gate_policy_replay_summary,
        model_accuracy=0.3724360917449732,
        baseline_accuracy=0.3699100737597252,
        accuracy_edge=0.0025260179852480413,
    )


def export_model_candidate_selection_preview(
    output_path: str | Path = Path("reports/model_candidate_selection_preview.json"),
) -> dict[str, object]:
    """Export deterministic candidate-selection preview JSON."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_model_candidate_selection_preview_payload()
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return {
        "status": "ok",
        "output_path": str(path),
        "candidate_status": payload["candidate_status"],
        "candidate_decision": payload["candidate_decision"],
    }


def build_model_quality_validation_result_sample():
    """Build a deterministic sample-only model quality validation result."""

    training_summary = {
        "model_version": "ml_candle_mlp_sample_v1",
        "run_id": "sample_training_run_ml25",
        "dataset_summary": {
            "dataset_rows": 8433,
            "train_rows": 5903,
            "validation_rows": 1265,
            "test_rows": 1265,
        },
        "test_metrics": {
            "accuracy": 0.3927,
        },
        "collapse_detected": False,
        "sample_mode": True,
        "real_training_executed": False,
    }
    baseline_summary = {
        "baselines": {
            "majority_class": {
                "test": {
                    "accuracy": 0.3783,
                }
            }
        }
    }
    probability_diagnostics = {
        "total_rows": 1265,
        "predicted_direction_ratios": {
            "UP": 0.39,
            "DOWN": 0.34,
            "FLAT": 0.27,
        },
    }
    calibration_summary = {
        "calibration_status": "ACCEPTABLE_SAMPLE",
        "expected_calibration_error": 0.061,
        "brier_score": 0.612,
    }
    profit_aware_summary = {
        "profit_aware_status": "NEEDS_MORE_DATA",
    }
    walk_forward_summary = {
        "walk_forward_status": "NEEDS_MORE_DATA",
        "summary": {
            "fold_count": 1,
            "total_test_signal_count": 5,
        },
    }
    gate_policy_replay_summary = {
        "gate_policy_replay_status": "SAMPLE_ONLY",
        "total_records": 5,
        "valid_records": 4,
        "invalid_records": 1,
        "gate_policy_allowed_count": 2,
        "gate_policy_blocked_count": 3,
    }
    return validate_model_quality(
        training_summary=training_summary,
        baseline_summary=baseline_summary,
        probability_diagnostics=probability_diagnostics,
        calibration_summary=calibration_summary,
        profit_aware_summary=profit_aware_summary,
        walk_forward_summary=walk_forward_summary,
        gate_policy_replay_summary=gate_policy_replay_summary,
        gap_quality_summary=GapQualityDiagnostics().analyze(
            symbol="BTCUSDT",
            interval="15m",
            start_date="2025-01-01",
            end_date="2026-06-11",
            gap_count=0,
        ),
        label_config_summary={
            "label_version": "lv1",
            "horizon_candles": 8,
            "direction_atr_threshold": 0.5,
            "take_profit_atr": 1.5,
            "stop_loss_atr": 1.0,
            "flat_class_enabled": True,
        },
        feature_config_summary={"feature_version": "fv1", "model_name": "candle_mlp"},
    )


def build_model_quality_validation_preview_payload() -> dict[str, object]:
    """Build a deterministic compact model quality validation preview."""

    reporter = ModelQualityReporter()
    result = build_model_quality_validation_result_sample()
    return reporter.build_compact_quality_summary(result)


def export_model_quality_validation_report(
    output_path: str | Path = Path("reports/model_quality_validation_report.json"),
) -> dict[str, object]:
    """Export the deterministic full model quality validation report."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    reporter = ModelQualityReporter()
    result = build_model_quality_validation_result_sample()
    full_report = reporter.build_full_quality_report(result)
    compact_summary = reporter.build_compact_quality_summary(result)

    path.write_text(
        reporter.full_report_to_json(result),
        encoding="utf-8",
    )

    return {
        "status": "ok",
        "output_path": str(path),
        "validator_name": full_report["validator_name"],
        "validator_version": full_report["validator_version"],
        "quality_status": full_report["quality_status"],
        "approved_for_traders_core_integration": full_report[
            "approved_for_traders_core_integration"
        ],
        "approved_for_live_trading": full_report["approved_for_live_trading"],
        "approved_for_auto_activation": full_report[
            "approved_for_auto_activation"
        ],
        "sample_mode": compact_summary["sample_mode"],
    }


def run_train_quality_pipeline(
    *,
    symbol: str,
    interval: str,
    start_date: str,
    end_date: str | None = None,
    run_id: str | None = None,
    feature_version: str = "fv1",
    dry_run: bool = False,
    sample_mode: bool = False,
    run_gate_policy_replay: bool = True,
    export_report: bool = True,
    output_dir: Path = Path("reports/training_pipeline_runs"),
) -> dict[str, object]:
    """Run the long-history training quality pipeline."""

    config = TrainingPipelineConfig(
        symbol=symbol,
        interval=interval,
        start_date=start_date,
        end_date=end_date,
        run_id=run_id,
        feature_version=feature_version,
        dry_run=dry_run,
        sample_mode=sample_mode,
        run_gate_policy_replay=run_gate_policy_replay,
        export_report=export_report,
        output_dir=output_dir,
    )
    runner = LongHistoryTrainingPipelineRunner()
    reporter = TrainingPipelineReporter()
    result = runner.run(config)
    return reporter.compact_summary_to_dict(result)


@cli.command("gate-policy-runtime-binding-preview")
def gate_policy_runtime_binding_preview() -> None:
    """Show PredictionService to GatePolicy runtime binding preview JSON."""

    payload = build_gate_policy_runtime_binding_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("gate-policy-replay-evaluate-preview")
def gate_policy_replay_evaluate_preview() -> None:
    """Show GatePolicy replay evaluation compact preview JSON."""

    payload = build_gate_policy_replay_evaluate_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("gate-policy-replay-evaluate-export")
def gate_policy_replay_evaluate_export(
    output_path: Path = typer.Option(
        Path("reports/gate_policy_replay_evaluation_summary.json"),
        "--output-path",
        help="Path for GatePolicy replay evaluation compact summary export.",
    ),
) -> None:
    """Export GatePolicy replay evaluation compact summary JSON."""

    payload = export_gate_policy_replay_evaluation_summary_report(output_path)

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("final-readiness-audit-preview")
def final_readiness_audit_preview() -> None:
    """Show the final standalone readiness audit compact summary JSON."""

    payload = build_final_readiness_audit_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("final-readiness-audit-export")
def final_readiness_audit_export(
    output_path: Path = typer.Option(
        Path("reports/final_standalone_readiness_audit.json"),
        "--output-path",
        help="Path for final standalone readiness audit export.",
    ),
) -> None:
    """Export the full final standalone readiness audit JSON."""

    payload = export_final_readiness_audit_report(output_path)

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("model-quality-validation-preview")
def model_quality_validation_preview() -> None:
    """Show deterministic model quality validation preview JSON."""

    payload = build_model_quality_validation_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("model-quality-validation-export")
def model_quality_validation_export(
    output_path: Path = typer.Option(
        Path("reports/model_quality_validation_report.json"),
        "--output-path",
        help="Path for model quality validation export.",
    ),
) -> None:
    """Export deterministic model quality validation JSON."""

    payload = export_model_quality_validation_report(output_path)

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("model-anti-collapse-preview")
def model_anti_collapse_preview() -> None:
    """Show deterministic anti-collapse preview JSON."""

    payload = build_model_anti_collapse_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("model-anti-collapse-export")
def model_anti_collapse_export(
    output_path: Path = typer.Option(
        Path("reports/model_anti_collapse_preview.json"),
        "--output-path",
        help="Path for anti-collapse preview export.",
    ),
) -> None:
    """Export deterministic anti-collapse preview JSON."""

    payload = export_model_anti_collapse_preview(output_path)

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("model-candidate-select-preview")
def model_candidate_select_preview() -> None:
    """Show deterministic candidate-selection preview JSON."""

    payload = build_model_candidate_selection_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("model-candidate-select-export")
def model_candidate_select_export(
    output_path: Path = typer.Option(
        Path("reports/model_candidate_selection_preview.json"),
        "--output-path",
        help="Path for candidate-selection preview export.",
    ),
) -> None:
    """Export deterministic candidate-selection preview JSON."""

    payload = export_model_candidate_selection_preview(output_path)

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("label-quality-grid-preview")
def label_quality_grid_preview() -> None:
    """Show deterministic ML30 label-quality grid preview JSON."""

    payload = build_label_quality_grid_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("label-quality-grid-export")
def label_quality_grid_export(
    output_path: Path = typer.Option(
        Path("reports/label_quality_grid_preview.json"),
        "--output-path",
        help="Path for label-quality grid preview export.",
    ),
) -> None:
    """Export deterministic ML30 label-quality grid preview JSON."""

    payload = export_label_quality_grid_preview(output_path)

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("label-grid-experiment-preview")
def label_grid_experiment_preview() -> None:
    """Show deterministic ML28 label-grid experiment preview JSON."""

    payload = build_label_grid_experiment_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("gap-aware-filter-preview")
def gap_aware_filter_preview() -> None:
    """Show deterministic ML30 gap-aware dataset filter preview JSON."""

    payload = build_gap_aware_filter_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("feature-quality-preview")
def feature_quality_preview() -> None:
    """Show deterministic ML30 feature quality diagnostic preview JSON."""

    payload = build_feature_quality_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("anti-collapse-training-plan-preview")
def anti_collapse_training_plan_preview() -> None:
    """Show deterministic ML30 anti-collapse training plan preview JSON."""

    payload = build_anti_collapse_training_plan_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("candidate-thresholds-preview")
def candidate_thresholds_preview() -> None:
    """Show deterministic ML30 candidate acceptance threshold preview JSON."""

    payload = build_candidate_thresholds_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("regime-feature-diagnostics-preview")
def regime_feature_diagnostics_preview() -> None:
    """Show deterministic ML32 regime-aware feature diagnostic preview JSON."""

    payload = build_regime_feature_diagnostics_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("feature-group-quality-preview")
def feature_group_quality_preview() -> None:
    """Show deterministic ML32 feature-group quality preview JSON."""

    payload = build_feature_group_quality_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("regime-label-config-preview")
def regime_label_config_preview() -> None:
    """Show deterministic ML32 regime-label config preview JSON."""

    payload = build_regime_label_config_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("regime-experiment-plan-preview")
def regime_experiment_plan_preview() -> None:
    """Show deterministic ML32 regime-experiment plan preview JSON."""

    payload = build_regime_experiment_plan_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("feature-leakage-guard-preview")
def feature_leakage_guard_preview() -> None:
    """Show deterministic ML32 feature-leakage guard preview JSON."""

    payload = build_feature_leakage_guard_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("feature-regime-experiment-preview")
def feature_regime_experiment_preview() -> None:
    """Show deterministic ML33 feature/regime experiment preview JSON."""

    payload = build_feature_regime_experiment_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("gap-quality-preview")
def gap_quality_preview() -> None:
    """Show ML34 gap-quality preview JSON."""

    payload = build_gap_quality_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("real-feature-diagnostics-preview")
def real_feature_diagnostics_preview() -> None:
    """Show ML34 real-feature-diagnostics preview JSON."""

    payload = build_real_feature_diagnostics_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("collapse-diagnostics-preview")
def collapse_diagnostics_preview() -> None:
    """Show ML36 collapse diagnostics preview JSON."""

    payload = build_collapse_diagnostics_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("regime-label-builder-preview")
def regime_label_builder_preview() -> None:
    """Show ML36 regime label builder preview JSON."""

    payload = build_regime_label_builder_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("walk-forward-profit-diagnostics-preview")
def walk_forward_profit_diagnostics_preview() -> None:
    """Show ML36 walk-forward/profit diagnostics preview JSON."""

    payload = build_walk_forward_profit_diagnostics_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("feature-regime-integration-preview")
def feature_regime_integration_preview() -> None:
    """Show ML34 feature/regime integration preview JSON."""

    payload = build_feature_regime_integration_preview_payload()

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("feature-engineering-plan-preview")
def feature_engineering_plan_preview() -> None:
    """Show ML34 feature-engineering plan preview JSON."""

    payload = FeatureEngineeringPlan().build_plan()
    payload.update(
        {
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "orders_enabled": False,
            "traders_core_connected": False,
        }
    )

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("label-grid-experiment-run")
def label_grid_experiment_run_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    start_date: str = typer.Option(..., "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
    experiment_id: str | None = typer.Option(None, "--experiment-id"),
    feature_version: str = typer.Option("fv1", "--feature-version"),
    label_config_ids: list[str] | None = typer.Option(None, "--label-config-id"),
    max_configs: int | None = typer.Option(None, "--max-configs"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    sample_mode: bool = typer.Option(False, "--sample-mode"),
    run_training: bool = typer.Option(True, "--run-training/--no-run-training"),
    run_walk_forward: bool = typer.Option(
        True,
        "--run-walk-forward/--no-run-walk-forward",
    ),
    run_gate_policy_replay: bool = typer.Option(
        True,
        "--run-gate-policy-replay/--no-run-gate-policy-replay",
    ),
    output_dir: Path = typer.Option(
        Path("reports/label_grid_experiments"),
        "--output-dir",
    ),
) -> None:
    """Run ML28 label-grid experiments over the configured label grid."""

    payload = run_label_grid_experiment(
        symbol=symbol,
        interval=interval,
        start_date=start_date,
        end_date=end_date,
        experiment_id=experiment_id,
        feature_version=feature_version,
        label_config_ids=label_config_ids,
        max_configs=max_configs,
        dry_run=dry_run,
        sample_mode=sample_mode,
        run_training=run_training,
        run_walk_forward=run_walk_forward,
        run_gate_policy_replay=run_gate_policy_replay,
        output_dir=output_dir,
    )

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("label-grid-results-analyze")
def label_grid_results_analyze_command(
    experiment_dir: Path | None = typer.Option(None, "--experiment-dir"),
    latest: bool = typer.Option(False, "--latest"),
    export_report: bool = typer.Option(
        True,
        "--export-report/--no-export-report",
    ),
) -> None:
    """Analyze ML28 label-grid results and export ML29 analysis artifacts."""

    payload = analyze_label_grid_results(
        experiment_dir=experiment_dir,
        latest=latest,
        export_report=export_report,
    )

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("ml31-grid-improvement-analyze")
def ml31_grid_improvement_analyze_command(
    current_experiment_dir: Path | None = typer.Option(None, "--current-experiment-dir"),
    previous_experiment_dir: Path | None = typer.Option(None, "--previous-experiment-dir"),
    latest: bool = typer.Option(False, "--latest"),
    export_report: bool = typer.Option(
        True,
        "--export-report/--no-export-report",
    ),
) -> None:
    """Analyze ML31 grid improvement against an optional previous baseline."""

    payload = analyze_ml31_grid_improvement(
        current_experiment_dir=current_experiment_dir,
        previous_experiment_dir=previous_experiment_dir,
        latest=latest,
        export_report=export_report,
    )

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("feature-regime-experiment-run")
def feature_regime_experiment_run_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    start_date: str = typer.Option(..., "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
    experiment_id: str | None = typer.Option(None, "--experiment-id"),
    feature_version: str = typer.Option("fv2", "--feature-version"),
    base_label_config_ids: list[str] | None = typer.Option(None, "--base-label-config-id"),
    regime_config_ids: list[str] | None = typer.Option(None, "--regime-config-id"),
    max_configs: int | None = typer.Option(None, "--max-configs"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    sample_mode: bool = typer.Option(False, "--sample-mode"),
    run_training: bool = typer.Option(True, "--run-training/--no-run-training"),
    run_regime_diagnostics: bool = typer.Option(
        True,
        "--run-regime-diagnostics/--no-run-regime-diagnostics",
    ),
    run_feature_diagnostics: bool = typer.Option(
        True,
        "--run-feature-diagnostics/--no-run-feature-diagnostics",
    ),
    run_leakage_guard: bool = typer.Option(
        True,
        "--run-leakage-guard/--no-run-leakage-guard",
    ),
    run_candidate_selection: bool = typer.Option(
        True,
        "--run-candidate-selection/--no-run-candidate-selection",
    ),
    output_dir: Path = typer.Option(
        Path("reports/feature_regime_experiments"),
        "--output-dir",
    ),
) -> None:
    """Run the ML33 feature/regime-aware experiment cycle."""

    payload = run_feature_regime_experiment(
        symbol=symbol,
        interval=interval,
        start_date=start_date,
        end_date=end_date,
        experiment_id=experiment_id,
        feature_version=feature_version,
        base_label_config_ids=base_label_config_ids,
        regime_config_ids=regime_config_ids,
        max_configs=max_configs,
        dry_run=dry_run,
        sample_mode=sample_mode,
        run_training=run_training,
        run_regime_diagnostics=run_regime_diagnostics,
        run_feature_diagnostics=run_feature_diagnostics,
        run_leakage_guard=run_leakage_guard,
        run_candidate_selection=run_candidate_selection,
        output_dir=output_dir,
    )

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("feature-regime-results-analyze")
def feature_regime_results_analyze_command(
    experiment_dir: Path | None = typer.Option(None, "--experiment-dir"),
    latest: bool = typer.Option(False, "--latest"),
) -> None:
    """Analyze the latest or explicit ML33 feature/regime experiment result."""

    payload = analyze_feature_regime_results(
        experiment_dir=experiment_dir,
        latest=latest,
    )

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("multi-symbol-feature-regime-analyze")
def multi_symbol_feature_regime_analyze_command(
    experiments_root: Path = typer.Option(
        Path("reports/feature_regime_experiments"),
        "--experiments-root",
    ),
    symbols: str = typer.Option(
        "BTCUSDT,ETHUSDT,SOLUSDT",
        "--symbols",
    ),
    latest_per_symbol: bool = typer.Option(
        False,
        "--latest-per-symbol",
    ),
    export_report: bool = typer.Option(
        True,
        "--export-report/--no-export-report",
    ),
) -> None:
    """Analyze multiple feature/regime experiment summaries together."""

    payload = analyze_multi_symbol_feature_regime(
        experiments_root=experiments_root,
        symbols=tuple(item.strip() for item in symbols.split(",") if item.strip()),
        latest_per_symbol=latest_per_symbol,
        export_report=export_report,
    )

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("train-quality-pipeline")
def train_quality_pipeline_command(
    symbol: str = typer.Option(..., "--symbol"),
    interval: str = typer.Option(..., "--interval"),
    start_date: str = typer.Option(..., "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
    run_id: str | None = typer.Option(None, "--run-id"),
    feature_version: str = typer.Option("fv1", "--feature-version"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    sample_mode: bool = typer.Option(False, "--sample-mode"),
    run_gate_policy_replay: bool = typer.Option(
        True,
        "--run-gate-policy-replay/--no-run-gate-policy-replay",
    ),
    export_report: bool = typer.Option(
        True,
        "--export-report/--no-export-report",
    ),
    output_dir: Path = typer.Option(
        Path("reports/training_pipeline_runs"),
        "--output-dir",
        help="Base output directory for training pipeline runtime artifacts.",
    ),
) -> None:
    """Run the long-history training pipeline with logs and reports."""

    payload = run_train_quality_pipeline(
        symbol=symbol,
        interval=interval,
        start_date=start_date,
        end_date=end_date,
        run_id=run_id,
        feature_version=feature_version,
        dry_run=dry_run,
        sample_mode=sample_mode,
        run_gate_policy_replay=run_gate_policy_replay,
        export_report=export_report,
        output_dir=output_dir,
    )

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@cli.command("gate-policy-runtime-binding-export")
def gate_policy_runtime_binding_export(
    output_path: Path = typer.Option(
        Path("reports/gate_policy_runtime_binding_summary.json"),
        "--output-path",
        help="Path for compact PredictionService to GatePolicy runtime binding export.",
    ),
) -> None:
    """Export PredictionService to GatePolicy runtime binding JSON summary."""

    payload = export_gate_policy_runtime_binding_summary_report(output_path)

    typer.echo(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )



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
