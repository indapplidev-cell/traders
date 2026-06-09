from __future__ import annotations

from typing import Any

from app.prediction.predictor import Predictor


class PredictionService:
    def __init__(self, predictor: Predictor) -> None:
        self._predictor = predictor

    def predict(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._predictor.predict(
            symbol=payload["symbol"],
            interval=payload["interval"],
            horizon_candles=payload["horizon_candles"],
            candles=payload["candles"],
            context=payload.get("context"),
            model_version=payload.get("model_version"),
        )
