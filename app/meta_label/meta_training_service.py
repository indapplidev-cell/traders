from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

import torch
from torch import nn

from app.features.feature_models import feature_names_for_version
from app.models.model_factory import ModelFactory
from app.registry.artifact_storage import ArtifactStorage
from app.registry.model_loader import ModelLoader


@dataclass(slots=True)
class MetaTrainingArtifacts:
    model_version: str
    feature_columns: list[str]
    scaler: dict[str, list[float]]
    training_config: dict[str, Any]
    metrics: dict[str, Any]


class MetaTrainingService:
    def __init__(
        self,
        artifact_storage: ArtifactStorage,
        model_factory: ModelFactory | None = None,
        model_loader: ModelLoader | None = None,
    ) -> None:
        self._artifact_storage = artifact_storage
        self._model_factory = model_factory or ModelFactory()
        self._model_loader = model_loader or ModelLoader(artifact_storage=artifact_storage, model_factory=self._model_factory)

    def train(
        self,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
        dataset_rows: list[Any],
        dataset_summary: dict[str, Any],
        split_rows: dict[str, list[Any]],
        epochs: int = 20,
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-4,
    ) -> dict[str, Any]:
        if not dataset_summary.get("meta_dataset_valid", False):
            return {
                "meta_training_skipped": True,
                "reason": "meta_dataset_invalid",
                "dataset_summary": dataset_summary,
            }
        if not split_rows["train"] or not split_rows["test"]:
            return {
                "meta_training_skipped": True,
                "reason": "meta_train_or_test_empty",
                "dataset_summary": dataset_summary,
            }

        feature_columns = self.feature_columns(feature_version)
        scaler = self.fit_scaler(split_rows["train"], feature_columns)
        train_tensors = self.rows_to_tensors(split_rows["train"], feature_columns, scaler)
        validation_tensors = self.rows_to_tensors(split_rows["validation"], feature_columns, scaler)
        test_tensors = self.rows_to_tensors(split_rows["test"], feature_columns, scaler)

        model_version = self._build_model_version()
        torch.manual_seed(42)
        model = self._model_factory.create(model_name="ema_meta_mlp_v1", input_dim=len(feature_columns))
        loss_fn = nn.BCEWithLogitsLoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate, weight_decay=weight_decay)

        training_history = self._train_loop(
            model=model,
            optimizer=optimizer,
            loss_fn=loss_fn,
            train_tensors=train_tensors,
            validation_tensors=validation_tensors,
            epochs=epochs,
        )
        train_metrics = self.evaluate_tensors(model, train_tensors)
        validation_metrics = self.evaluate_tensors(model, validation_tensors)
        test_metrics = self.evaluate_tensors(model, test_tensors)
        training_config = {
            "model_name": "ema_meta_mlp_v1",
            "model_version": model_version,
            "symbol": symbol,
            "interval": interval,
            "horizon_candles": horizon_candles,
            "feature_version": feature_version,
            "label_version": label_version,
            "epochs": epochs,
            "learning_rate": learning_rate,
            "weight_decay": weight_decay,
        }
        metrics = {
            "train": train_metrics,
            "validation": validation_metrics,
            "test": test_metrics,
            "training": training_history,
            "dataset_summary": dataset_summary,
        }
        artifact_path = self._artifact_storage.save(
            model_version=model_version,
            model=model,
            scaler=scaler,
            feature_columns=feature_columns,
            training_config=training_config,
            metrics=metrics,
        )
        return {
            "meta_training_skipped": False,
            "model_version": model_version,
            "artifact_path": artifact_path,
            "test_metrics": test_metrics,
            "dataset_summary": dataset_summary,
        }

    def load(self, model_version: str):
        return self._model_loader.load(model_version)

    def build_prediction_rows(
        self,
        model_version: str,
        dataset_rows: list[Any],
    ) -> list[dict[str, Any]]:
        model, scaler, feature_columns, _, _ = self.load(model_version)
        if not dataset_rows:
            return []
        features = self._transform_features(dataset_rows, feature_columns, scaler)
        with torch.no_grad():
            logits = model(features)
            probabilities = torch.sigmoid(logits).tolist()
        predictions = []
        for row, probability in zip(dataset_rows, probabilities):
            predictions.append(
                {
                    "candle_open_time": row.candle_open_time.isoformat(),
                    "ema_signal_direction": row.ema_signal_direction,
                    "meta_target_win": row.meta_target_win,
                    "meta_trade_r": row.meta_trade_r,
                    "prob_win": float(probability),
                    "prob_loss": float(1.0 - probability),
                }
            )
        return predictions

    @staticmethod
    def feature_columns(feature_version: str) -> list[str]:
        columns = feature_names_for_version(feature_version)
        return columns + ["ema_signal_direction_encoded", "ema_signal_strength_atr"]

    @staticmethod
    def fit_scaler(rows: list[Any], feature_columns: list[str]) -> dict[str, list[float]]:
        means: list[float] = []
        stds: list[float] = []
        for column in feature_columns:
            values = [float(row.features_json[column]) for row in rows]
            mean = sum(values) / len(values)
            variance = sum((value - mean) ** 2 for value in values) / len(values)
            std = variance ** 0.5
            means.append(mean)
            stds.append(std if std > 1e-12 else 1.0)
        return {"mean": means, "std": stds}

    @classmethod
    def rows_to_tensors(cls, rows: list[Any], feature_columns: list[str], scaler: dict[str, list[float]]) -> dict[str, torch.Tensor]:
        if not rows:
            return {
                "features": torch.zeros((0, len(feature_columns)), dtype=torch.float32),
                "target": torch.zeros((0,), dtype=torch.float32),
            }
        features = cls._transform_features(rows, feature_columns, scaler)
        target = torch.tensor([float(row.meta_target_win) for row in rows], dtype=torch.float32)
        return {"features": features, "target": target}

    @staticmethod
    def evaluate_tensors(model: torch.nn.Module, tensors: dict[str, torch.Tensor]) -> dict[str, Any]:
        features = tensors["features"]
        target = tensors["target"]
        if len(target) == 0:
            return {"accuracy": None, "precision": None, "recall": None, "brier_score": None, "rows": 0}
        with torch.no_grad():
            logits = model(features)
            probabilities = torch.sigmoid(logits)
        predictions = (probabilities >= 0.5).float()
        rows = int(target.shape[0])
        true_positive = int(((predictions == 1.0) & (target == 1.0)).sum().item())
        false_positive = int(((predictions == 1.0) & (target == 0.0)).sum().item())
        false_negative = int(((predictions == 0.0) & (target == 1.0)).sum().item())
        accuracy = float((predictions == target).float().mean().item())
        precision = (true_positive / (true_positive + false_positive)) if (true_positive + false_positive) else None
        recall = (true_positive / (true_positive + false_negative)) if (true_positive + false_negative) else None
        brier_score = float(torch.mean((probabilities - target) ** 2).item())
        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "brier_score": brier_score,
            "rows": rows,
        }

    @staticmethod
    def _transform_features(rows: list[Any], feature_columns: list[str], scaler: dict[str, list[float]]) -> torch.Tensor:
        feature_matrix = []
        for row in rows:
            values = [float(row.features_json[column]) for column in feature_columns]
            scaled = [
                (value - scaler["mean"][index]) / scaler["std"][index]
                for index, value in enumerate(values)
            ]
            feature_matrix.append(scaled)
        return torch.tensor(feature_matrix, dtype=torch.float32)

    @staticmethod
    def _build_model_version() -> str:
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y_%m_%d_%H%M%S")
        return f"ema_meta_mlp_v1_{timestamp}"

    @classmethod
    def _train_loop(
        cls,
        model: torch.nn.Module,
        optimizer: torch.optim.Optimizer,
        loss_fn,
        train_tensors: dict[str, torch.Tensor],
        validation_tensors: dict[str, torch.Tensor],
        epochs: int,
    ) -> dict[str, Any]:
        history = {"train_loss": [], "validation_loss": []}
        for _ in range(epochs):
            model.train()
            optimizer.zero_grad()
            train_logits = model(train_tensors["features"])
            train_loss = loss_fn(train_logits, train_tensors["target"])
            train_loss.backward()
            optimizer.step()

            model.eval()
            with torch.no_grad():
                if len(validation_tensors["target"]) > 0:
                    validation_logits = model(validation_tensors["features"])
                    validation_loss = loss_fn(validation_logits, validation_tensors["target"])
                    history["validation_loss"].append(float(validation_loss.item()))
                else:
                    history["validation_loss"].append(None)
            history["train_loss"].append(float(train_loss.item()))
        return history
