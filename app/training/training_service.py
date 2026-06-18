from __future__ import annotations

import re
from uuid import uuid4

from dataclasses import dataclass
from datetime import date
from datetime import datetime, timezone
from typing import Any

import torch

from app.dataset.dataset_builder import DatasetBuilder
from app.dataset.dataset_models import DatasetRow
from app.diagnostics.direction_head_separation_diagnostics import DirectionHeadSeparationDiagnostics
from app.diagnostics.direction_head_separation_diagnostics import LabelNoiseDiagnostics
from app.diagnostics.direction_head_separation_diagnostics import direction_sample_weight_for_row
from app.features.feature_models import FEATURE_NAMES, feature_names_for_version
from app.models.model_factory import ModelFactory
from app.registry.artifact_storage import ArtifactStorage
from app.registry.model_loader import ModelLoader
from app.registry.model_registry import ModelRegistry
from app.training.evaluator import Evaluator
from app.training.loss import MultiTaskLoss
from app.training.probability_calibration import DEFAULT_TEMPERATURE_GRID
from app.training.probability_calibration import fit_direction_temperature_for_model
from app.training.model_version_builder import build_unique_model_version
from app.training.trainer import Trainer


@dataclass(slots=True)
class TrainingConfig:
    symbol: str
    interval: str
    horizon_candles: int
    feature_version: str
    label_version: str
    model_name: str
    model_version: str
    epochs: int = 20
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    direction_loss_name: str = "cross_entropy"
    focal_gamma: float = 2.0
    label_smoothing: float = 0.0
    confidence_margin_weight: float = 0.0
    confidence_margin_target: float = 0.12
    probability_temperature_enabled: bool = True
    direction_loss_weight: float = 1.0
    tp_sl_loss_weight: float = 1.0
    move_loss_weight: float = 1.0
    risk_loss_weight: float = 1.0
    direction_logit_gap_weight: float = 0.0
    direction_logit_gap_target: float = 0.35
    direction_distribution_loss_weight: float = 0.0
    flat_probability_floor_weight: float = 0.0
    flat_probability_floor_target: float = 0.18
    min_class_probability_floor: float = 0.04
    label_noise_hardening_enabled: bool = True


def _safe_run_id_part(value: object) -> str:
    text = str(value or "unknown")
    text = re.sub(r"[^A-Za-z0-9_]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "unknown"


def build_training_run_id(
    *,
    model_version: str,
    symbol: str,
    interval: str,
    horizon_candles: int,
    label_version: str,
    max_length: int = 100,
) -> str:
    suffix = uuid4().hex[:8]
    base = "_".join(
        [
            "train",
            _safe_run_id_part(model_version),
            _safe_run_id_part(symbol),
            _safe_run_id_part(interval),
            f"h{int(horizon_candles)}",
            _safe_run_id_part(label_version),
            suffix,
        ]
    )

    if len(base) <= max_length:
        return base

    shorter = "_".join(
        [
            "train",
            _safe_run_id_part(model_version),
            _safe_run_id_part(symbol),
            _safe_run_id_part(interval),
            f"h{int(horizon_candles)}",
            suffix,
        ]
    )

    if len(shorter) <= max_length:
        return shorter

    return f"{shorter[: max_length - 9]}_{suffix}"


class TrainingService:
    def __init__(
        self,
        dataset_builder: DatasetBuilder,
        model_registry: ModelRegistry,
        training_run_repository,
        artifact_storage: ArtifactStorage,
        trainer: Trainer | None = None,
        evaluator: Evaluator | None = None,
        model_factory: ModelFactory | None = None,
        model_loader: ModelLoader | None = None,
    ) -> None:
        self._dataset_builder = dataset_builder
        self._model_registry = model_registry
        self._training_run_repository = training_run_repository
        self._artifact_storage = artifact_storage
        self._trainer = trainer or Trainer()
        self._evaluator = evaluator or Evaluator()
        self._model_factory = model_factory or ModelFactory()
        self._model_loader = model_loader or ModelLoader(artifact_storage=self._artifact_storage, model_factory=self._model_factory)

    def train(
        self,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
        model_name: str,
        epochs: int = 20,
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-4,
        train_end: date | None = None,
        validation_end: date | None = None,
        disable_class_weights: bool = False,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        direction_loss_name: str = "cross_entropy",
        focal_gamma: float = 2.0,
        label_smoothing: float = 0.0,
        confidence_margin_weight: float = 0.0,
        confidence_margin_target: float = 0.12,
        probability_temperature_enabled: bool = True,
        direction_loss_weight: float = 1.0,
        tp_sl_loss_weight: float = 1.0,
        move_loss_weight: float = 1.0,
        risk_loss_weight: float = 1.0,
        direction_logit_gap_weight: float = 0.0,
        direction_logit_gap_target: float = 0.35,
        direction_distribution_loss_weight: float = 0.0,
        flat_probability_floor_weight: float = 0.0,
        flat_probability_floor_target: float = 0.18,
        min_class_probability_floor: float = 0.04,
        label_noise_hardening_enabled: bool = True,
    ) -> dict[str, Any]:
        model_version = self._build_model_version(
            model_name=model_name,
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            label_version=label_version,
        )
        config = TrainingConfig(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            model_name=model_name,
            model_version=model_version,
            epochs=epochs,
            learning_rate=learning_rate,
            weight_decay=weight_decay,
            direction_loss_name=direction_loss_name,
            focal_gamma=focal_gamma,
            label_smoothing=label_smoothing,
            confidence_margin_weight=confidence_margin_weight,
            confidence_margin_target=confidence_margin_target,
            probability_temperature_enabled=probability_temperature_enabled,
            direction_loss_weight=direction_loss_weight,
            tp_sl_loss_weight=tp_sl_loss_weight,
            move_loss_weight=move_loss_weight,
            risk_loss_weight=risk_loss_weight,
            direction_logit_gap_weight=direction_logit_gap_weight,
            direction_logit_gap_target=direction_logit_gap_target,
            direction_distribution_loss_weight=direction_distribution_loss_weight,
            flat_probability_floor_weight=flat_probability_floor_weight,
            flat_probability_floor_target=flat_probability_floor_target,
            min_class_probability_floor=min_class_probability_floor,
            label_noise_hardening_enabled=label_noise_hardening_enabled,
        )
        started_at = datetime.now(tz=timezone.utc)
        run_id = build_training_run_id(
            model_version=model_version,
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            label_version=label_version,
        )
        self._training_run_repository.create(
            {
                "run_id": run_id,
                "model_name": model_name,
                "symbol": symbol,
                "interval": interval,
                "horizon_candles": horizon_candles,
                "status": "running",
                "started_at": started_at,
            }
        )

        try:
            dataset_rows, dataset_summary = self._dataset_builder.build_rows(
                symbol=symbol,
                interval=interval,
                horizon_candles=horizon_candles,
                feature_version=feature_version,
                label_version=label_version,
                start_at=start_at,
                end_at=end_at,
            )
            if not dataset_rows:
                raise ValueError("No dataset rows available for training.")

            split_rows = self._dataset_builder.split_rows(
                dataset_rows,
                train_end=train_end,
                validation_end=validation_end,
            )
            if not split_rows["train"] or not split_rows["test"]:
                raise ValueError("Train/test dataset is empty.")
            
            label_noise_diagnostics = LabelNoiseDiagnostics().build_by_split(split_rows)

            feature_columns = self.feature_columns(feature_version)
            scaler = self.fit_scaler(split_rows["train"], feature_columns)
            train_dataset = self.rows_to_tensors(split_rows["train"], feature_columns, scaler)
            validation_dataset = self.rows_to_tensors(split_rows["validation"], feature_columns, scaler)
            test_dataset = self.rows_to_tensors(split_rows["test"], feature_columns, scaler)
            direction_class_weights = None if disable_class_weights else self.compute_direction_class_weights(split_rows["train"])

            torch.manual_seed(42)
            model = self._model_factory.create(model_name=model_name, input_dim=len(feature_columns))
            trainer = Trainer(
                epochs=config.epochs,
                learning_rate=config.learning_rate,
                weight_decay=config.weight_decay,
                loss_fn=MultiTaskLoss(
                    direction_class_weights=direction_class_weights,
                    direction_loss_name=config.direction_loss_name,
                    focal_gamma=config.focal_gamma,
                    label_smoothing=config.label_smoothing,
                    direction_loss_weight=config.direction_loss_weight,
                    tp_sl_loss_weight=config.tp_sl_loss_weight,
                    move_loss_weight=config.move_loss_weight,
                    risk_loss_weight=config.risk_loss_weight,
                    confidence_margin_weight=config.confidence_margin_weight,
                    confidence_margin_target=config.confidence_margin_target,
                    direction_distribution_loss_weight=config.direction_distribution_loss_weight,
                    flat_probability_floor_weight=config.flat_probability_floor_weight,
                    flat_probability_floor_target=config.flat_probability_floor_target,
                    min_class_probability_floor=config.min_class_probability_floor,
                ),
            )
            training_result = trainer.train(model=model, train_dataset=train_dataset, validation_dataset=validation_dataset)
            direction_head_diagnostics = DirectionHeadSeparationDiagnostics().build_for_splits(
                model=model,
                datasets={
                    "train": train_dataset,
                    "validation": validation_dataset,
                    "test": test_dataset,
                },
            )
            if config.probability_temperature_enabled:
                temperature_report = fit_direction_temperature_for_model(
                    model=model,
                    validation_dataset=validation_dataset,
                    candidate_temperatures=DEFAULT_TEMPERATURE_GRID,
                )
            else:
                temperature_report = fit_direction_temperature_for_model(
                    model=model,
                    validation_dataset=TrainingService.empty_tensors(len(feature_columns)),
                    candidate_temperatures=(1.0,),
                )
            probability_calibration = temperature_report.to_dict()
            direction_temperature = float(probability_calibration.get("selected_temperature") or 1.0)
            raw_train_metrics = self._evaluator.evaluate(model, train_dataset, direction_temperature=1.0)
            raw_validation_metrics = self._evaluator.evaluate(model, validation_dataset, direction_temperature=1.0)
            raw_test_metrics = self._evaluator.evaluate(model, test_dataset, direction_temperature=1.0)

            train_metrics = self._evaluator.evaluate(model, train_dataset, direction_temperature=direction_temperature)
            validation_metrics = self._evaluator.evaluate(model, validation_dataset, direction_temperature=direction_temperature)
            test_metrics = self._evaluator.evaluate(model, test_dataset, direction_temperature=direction_temperature)

            training_config = {
                "model_name": model_name,
                "model_version": model_version,
                "symbol": symbol,
                "interval": interval,
                "horizon_candles": horizon_candles,
                "feature_version": feature_version,
                "label_version": label_version,
                "epochs": config.epochs,
                "learning_rate": config.learning_rate,
                "weight_decay": config.weight_decay,
                "train_end": train_end.isoformat() if train_end is not None else None,
                "validation_end": validation_end.isoformat() if validation_end is not None else None,
                "disable_class_weights": disable_class_weights,
                "start_at": start_at.isoformat() if start_at is not None else None,
                "end_at": end_at.isoformat() if end_at is not None else None,
                "date_range_limited": start_at is not None and end_at is not None,
                "direction_class_weights": direction_class_weights,
                "direction_loss_name": config.direction_loss_name,
                "focal_gamma": config.focal_gamma,
                "label_smoothing": config.label_smoothing,
                "confidence_margin_weight": config.confidence_margin_weight,
                "confidence_margin_target": config.confidence_margin_target,
                "probability_temperature_enabled": config.probability_temperature_enabled,
                "probability_calibration": probability_calibration,
                "direction_loss_weight": config.direction_loss_weight,
                "tp_sl_loss_weight": config.tp_sl_loss_weight,
                "move_loss_weight": config.move_loss_weight,
                "risk_loss_weight": config.risk_loss_weight,
                "direction_logit_gap_weight": config.direction_logit_gap_weight,
                "direction_logit_gap_target": config.direction_logit_gap_target,
                "direction_distribution_loss_weight": config.direction_distribution_loss_weight,
                "flat_probability_floor_weight": config.flat_probability_floor_weight,
                "flat_probability_floor_target": config.flat_probability_floor_target,
                "min_class_probability_floor": config.min_class_probability_floor,
                "label_noise_hardening_enabled": config.label_noise_hardening_enabled,
            }
            combined_metrics = {
                "train": train_metrics,
                "validation": validation_metrics,
                "test": test_metrics,
                "training": training_result,
                "dataset_summary": dataset_summary,
                "direction_class_weights": direction_class_weights,
                "raw_train": raw_train_metrics,
                "raw_validation": raw_validation_metrics,
                "raw_test": raw_test_metrics,
                "probability_calibration": probability_calibration,
                "direction_head_diagnostics": direction_head_diagnostics,
                "label_noise_diagnostics": label_noise_diagnostics,
            }
            artifact_path = self._artifact_storage.save(
                model_version=model_version,
                model=model,
                scaler=scaler,
                feature_columns=feature_columns,
                training_config=training_config,
                metrics=combined_metrics,
            )

            self._model_registry.register(
                {
                    "model_name": model_name,
                    "model_version": model_version,
                    "symbol": symbol,
                    "interval": interval,
                    "horizon_candles": horizon_candles,
                    "feature_version": feature_version,
                    "label_version": label_version,
                    "artifact_path": artifact_path,
                    "train_start_at": split_rows["train"][0].candle_open_time,
                    "train_end_at": split_rows["train"][-1].candle_open_time,
                    "validation_start_at": split_rows["validation"][0].candle_open_time if split_rows["validation"] else split_rows["train"][-1].candle_open_time,
                    "validation_end_at": split_rows["validation"][-1].candle_open_time if split_rows["validation"] else split_rows["train"][-1].candle_open_time,
                    "test_start_at": split_rows["test"][0].candle_open_time,
                    "test_end_at": split_rows["test"][-1].candle_open_time,
                    "accuracy": test_metrics["accuracy"],
                    "precision_up": test_metrics["precision_up"],
                    "precision_down": test_metrics["precision_down"],
                    "brier_score": test_metrics["brier_score"],
                    "tp_before_sl_accuracy": test_metrics["tp_before_sl_accuracy"],
                    "profit_factor": None,
                    "max_drawdown": None,
                    "is_active": False,
                }
            )
            finished_at = datetime.now(tz=timezone.utc)
            self._training_run_repository.finish(
                run_id=run_id,
                status="completed",
                finished_at=finished_at,
                metrics_json=combined_metrics,
                error_message=None,
            )
            return {
                "run_id": run_id,
                "model_version": model_version,
                "artifact_path": artifact_path,
                "test_metrics": test_metrics,
                "raw_test_metrics": raw_test_metrics,
                "probability_calibration": probability_calibration,
                "direction_temperature": direction_temperature,
                "direction_loss_name": config.direction_loss_name,
                "focal_gamma": config.focal_gamma,
                "label_smoothing": config.label_smoothing,
                "confidence_margin_weight": config.confidence_margin_weight,
                "confidence_margin_target": config.confidence_margin_target,
                "probability_temperature_enabled": config.probability_temperature_enabled,
                "direction_distribution_loss_weight": config.direction_distribution_loss_weight,
                "flat_probability_floor_weight": config.flat_probability_floor_weight,
                "flat_probability_floor_target": config.flat_probability_floor_target,
                "min_class_probability_floor": config.min_class_probability_floor,
            }
        except Exception as exc:
            finished_at = datetime.now(tz=timezone.utc)
            self._training_run_repository.finish(
                run_id=run_id,
                status="failed",
                finished_at=finished_at,
                metrics_json=None,
                error_message=str(exc),
            )
            raise

    def evaluate(self, model_version: str) -> dict[str, Any]:
        model_row = self._model_registry._repository.get_by_model_version(model_version)
        if model_row is None:
            raise ValueError(f"Unknown model_version: {model_version}")

        model, scaler, feature_columns, training_config, _ = self._model_loader.load(model_version)
        dataset_rows, dataset_summary = self._dataset_builder.build_rows(
            symbol=model_row.symbol,
            interval=model_row.interval,
            horizon_candles=model_row.horizon_candles,
            feature_version=model_row.feature_version,
            label_version=model_row.label_version,
        )
        split_rows = self._dataset_builder.split_rows(dataset_rows)
        test_dataset = self.rows_to_tensors(split_rows["test"], feature_columns, scaler)
        test_metrics = self._evaluator.evaluate(model, test_dataset)
        return {
            "model_version": model_version,
            "model_name": training_config["model_name"],
            "test_metrics": test_metrics,
            "dataset_summary": dataset_summary,
        }

    @staticmethod
    def _build_model_version(
        *,
        model_name: str,
        symbol: str,
        interval: str,
        horizon_candles: int,
        label_version: str,
    ) -> str:
        return build_unique_model_version(
            model_name=model_name,
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            label_version=label_version,
        )

    @staticmethod
    def feature_columns(feature_version: str = "fv1") -> list[str]:
        if feature_version == "fv1":
            return list(FEATURE_NAMES)
        return feature_names_for_version(feature_version)

    @staticmethod
    def fit_scaler(rows: list[DatasetRow], feature_columns: list[str]) -> dict[str, list[float]]:
        means: list[float] = []
        stds: list[float] = []
        for column in feature_columns:
            values = [float(row.features_json[column]) for row in rows]
            mean = sum(values) / len(values)
            variance = sum((value - mean) ** 2 for value in values) / len(values)
            std = variance ** 0.5
            means.append(mean)
            stds.append(std if std > 1e-12 else 1.0)
        return {
            "mean": means,
            "std": stds,
        }

    @staticmethod
    def empty_tensors(feature_count: int) -> dict[str, torch.Tensor]:
        empty_features = torch.zeros((0, feature_count), dtype=torch.float32)
        empty_long = torch.zeros((0,), dtype=torch.long)
        empty_float = torch.zeros((0,), dtype=torch.float32)
        return {
            "features": empty_features,
            "direction_target": empty_long,
            "direction_sample_weight": empty_float,
            "tp_sl_target": empty_float,
            "tp_sl_mask": empty_float,
            "move_target": empty_float,
            "risk_target": empty_float,
        }

    @staticmethod
    def rows_to_tensors(rows: list[DatasetRow], feature_columns: list[str], scaler: dict[str, list[float]]) -> dict[str, torch.Tensor]:
        if not rows:
            return TrainingService.empty_tensors(len(feature_columns))

        feature_matrix: list[list[float]] = []
        direction_targets: list[int] = []
        direction_sample_weights: list[float] = []
        tp_targets: list[float] = []
        tp_masks: list[float] = []
        move_targets: list[float] = []
        risk_targets: list[float] = []

        for row in rows:
            feature_values = [float(row.features_json[column]) for column in feature_columns]
            scaled = [
                (value - scaler["mean"][index]) / scaler["std"][index]
                for index, value in enumerate(feature_values)
            ]
            feature_matrix.append(scaled)
            direction_targets.append({"UP": 0, "DOWN": 1, "FLAT": 2}[row.direction_label])
            direction_sample_weights.append(direction_sample_weight_for_row(row))
            if row.tp_before_sl is None:
                tp_targets.append(0.0)
                tp_masks.append(0.0)
            else:
                tp_targets.append(1.0 if row.tp_before_sl else 0.0)
                tp_masks.append(1.0)
            move_targets.append(float(row.future_move_atr))
            risk_targets.append(float(row.max_adverse_move_atr))

        return {
            "features": torch.tensor(feature_matrix, dtype=torch.float32),
            "direction_target": torch.tensor(direction_targets, dtype=torch.long),
            "direction_sample_weight": torch.tensor(direction_sample_weights, dtype=torch.float32),
            "tp_sl_target": torch.tensor(tp_targets, dtype=torch.float32),
            "tp_sl_mask": torch.tensor(tp_masks, dtype=torch.float32),
            "move_target": torch.tensor(move_targets, dtype=torch.float32),
            "risk_target": torch.tensor(risk_targets, dtype=torch.float32),
        }

    @staticmethod
    def compute_direction_class_weights(rows: list[DatasetRow]) -> list[float]:
        label_counts = {"UP": 0, "DOWN": 0, "FLAT": 0}
        for row in rows:
            label_counts[row.direction_label] += 1
        total = len(rows)
        num_classes = len(label_counts)
        weights: list[float] = []
        for label in ["UP", "DOWN", "FLAT"]:
            count = label_counts[label]
            if count == 0:
                weights.append(0.0)
            else:
                weights.append(total / (num_classes * count))
        return weights
