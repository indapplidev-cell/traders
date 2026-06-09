from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import torch

from app.features.feature_builder import FeatureBuilder
from app.features.feature_models import FeatureRecord
from app.registry.artifact_storage import ArtifactStorage
from app.registry.model_loader import ModelLoader


@dataclass(slots=True)
class PredictionRuntime:
    model_row: Any
    model: torch.nn.Module
    scaler: dict[str, list[float]]
    feature_columns: list[str]


class Predictor:
    def __init__(
        self,
        model_registry_repository,
        prediction_repository,
        artifact_storage: ArtifactStorage,
        model_loader: ModelLoader,
        feature_builder: FeatureBuilder | None = None,
    ) -> None:
        self._model_registry_repository = model_registry_repository
        self._prediction_repository = prediction_repository
        self._artifact_storage = artifact_storage
        self._model_loader = model_loader
        self._feature_builder = feature_builder or FeatureBuilder()

    def predict(
        self,
        symbol: str,
        interval: str,
        horizon_candles: int,
        candles: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
        model_version: str | None = None,
    ) -> dict[str, Any]:
        runtime = self.prepare_runtime(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            model_version=model_version,
        )
        if runtime is None:
            return {"ml_available": False, "reason": "active_model_not_found"}

        candle_objects = self._to_candle_objects(candles)
        features = self.build_feature_records(
            candles=candle_objects,
            symbol=symbol,
            interval=interval,
            feature_version=runtime.model_row.feature_version,
        )
        if not features:
            return {"ml_available": False, "reason": "not_enough_candles"}

        return self.predict_from_feature_record(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_record=features[-1],
            runtime=runtime,
            candles=candles,
            context=context,
            log_prediction=True,
        )

    def prepare_runtime(
        self,
        symbol: str,
        interval: str,
        horizon_candles: int,
        model_version: str | None = None,
    ) -> PredictionRuntime | None:
        model_row = self._resolve_model(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            model_version=model_version,
        )
        if model_row is None or not self._artifact_storage.exists(model_row.model_version):
            return None

        model, scaler, feature_columns, _, _ = self._model_loader.load(model_row.model_version)
        return PredictionRuntime(
            model_row=model_row,
            model=model,
            scaler=scaler,
            feature_columns=feature_columns,
        )

    def build_feature_records(
        self,
        candles: list[Any],
        symbol: str,
        interval: str,
        feature_version: str,
    ) -> list[FeatureRecord]:
        return self._feature_builder.build(
            candles=candles,
            symbol=symbol,
            interval=interval,
            feature_version=feature_version,
        )

    def predict_from_feature_record(
        self,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_record: FeatureRecord,
        runtime: PredictionRuntime,
        candles: list[dict[str, Any]] | None = None,
        context: dict[str, Any] | None = None,
        log_prediction: bool = True,
    ) -> dict[str, Any]:
        if self._has_incomplete_features(feature_record, runtime.feature_columns):
            return {"ml_available": False, "reason": "incomplete_features"}

        response = self._predict_feature_record(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_record=feature_record,
            runtime=runtime,
        )
        if log_prediction:
            self._prediction_repository.create(
                {
                    "model_version": runtime.model_row.model_version,
                    "symbol": symbol,
                    "interval": interval,
                    "candle_open_time": feature_record.candle_open_time,
                    "horizon_candles": horizon_candles,
                    "prob_up": response["prob_up"],
                    "prob_down": response["prob_down"],
                    "prob_flat": response["prob_flat"],
                    "direction": response["direction"],
                    "tp_before_sl_probability": response["tp_before_sl_probability"],
                    "expected_move_atr": response["expected_move_atr"],
                    "risk_score": response["risk_score"],
                    "confidence": response["confidence"],
                    "request_payload": {
                        "symbol": symbol,
                        "interval": interval,
                        "horizon_candles": horizon_candles,
                        "candles": candles or [],
                        "context": context or {},
                    },
                    "response_payload": response,
                }
            )
        return response

    def _resolve_model(self, symbol: str, interval: str, horizon_candles: int, model_version: str | None):
        if model_version:
            return self._model_registry_repository.get_by_model_version(model_version)
        return self._model_registry_repository.get_active_model(symbol=symbol, interval=interval, horizon_candles=horizon_candles)

    def _predict_feature_record(
        self,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_record: FeatureRecord,
        runtime: PredictionRuntime,
    ) -> dict[str, Any]:
        tensor = self._to_tensor(feature_record.features_json, runtime.feature_columns, runtime.scaler)
        runtime.model.eval()
        with torch.no_grad():
            outputs = runtime.model(tensor)
            direction_probabilities = torch.softmax(outputs["direction_logits"], dim=1).cpu().tolist()[0]
            tp_probability = float(torch.sigmoid(outputs["tp_sl_logits"]).cpu().item())
            expected_move_atr = float(outputs["expected_move_atr"].cpu().item())
            risk_score = float(outputs["risk_score"].cpu().item())

        direction_index = max(range(len(direction_probabilities)), key=lambda index: direction_probabilities[index])
        direction = {0: "UP", 1: "DOWN", 2: "FLAT"}[direction_index]
        confidence = float(max(direction_probabilities))
        return {
            "ml_available": True,
            "symbol": symbol,
            "interval": interval,
            "horizon_candles": horizon_candles,
            "direction": direction,
            "prob_up": float(direction_probabilities[0]),
            "prob_down": float(direction_probabilities[1]),
            "prob_flat": float(direction_probabilities[2]),
            "tp_before_sl_probability": tp_probability,
            "expected_move_atr": expected_move_atr,
            "risk_score": risk_score,
            "confidence": confidence,
            "model_version": runtime.model_row.model_version,
        }

    @staticmethod
    def _has_incomplete_features(feature_record: FeatureRecord, feature_columns: list[str]) -> bool:
        return any(feature_record.features_json.get(column) is None for column in feature_columns)

    @staticmethod
    def _to_tensor(features_json: dict[str, float | None], feature_columns: list[str], scaler: dict[str, list[float]]) -> torch.Tensor:
        scaled = [
            (float(features_json[column]) - scaler["mean"][index]) / scaler["std"][index]
            for index, column in enumerate(feature_columns)
        ]
        return torch.tensor([scaled], dtype=torch.float32)

    @staticmethod
    def _to_candle_objects(candles: list[dict[str, Any]]) -> list[SimpleNamespace]:
        candle_objects: list[SimpleNamespace] = []
        for candle in candles:
            open_time = candle["open_time"]
            if isinstance(open_time, str):
                open_time = datetime.fromisoformat(open_time.replace("Z", "+00:00"))
            open_time = open_time.astimezone(timezone.utc) if open_time.tzinfo else open_time.replace(tzinfo=timezone.utc)
            open_price = float(candle["open"])
            high_price = float(candle["high"])
            low_price = float(candle["low"])
            close_price = float(candle["close"])
            volume = float(candle["volume"])
            candle_objects.append(
                SimpleNamespace(
                    open_time=open_time,
                    open=open_price,
                    high=high_price,
                    low=low_price,
                    close=close_price,
                    volume=volume,
                    taker_buy_base_volume=float(candle["taker_buy_base_volume"]) if candle.get("taker_buy_base_volume") is not None else None,
                )
            )
        return candle_objects
