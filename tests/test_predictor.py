from types import SimpleNamespace

import torch

from app.prediction.predictor import Predictor


def test_predictor_returns_fallback_when_active_model_not_found() -> None:
    predictor = Predictor(
        model_registry_repository=FakeModelRegistryRepository(active_model=None),
        prediction_repository=FakePredictionRepository(),
        artifact_storage=FakeArtifactStorage(True),
        model_loader=FakeModelLoader(),
    )

    result = predictor.predict(
        symbol="BTCUSDT",
        interval="15m",
        horizon_candles=8,
        candles=[_candle_payload(index) for index in range(210)],
        context={},
    )

    assert result == {"ml_available": False, "reason": "active_model_not_found"}


def test_predictor_returns_prediction_and_logs_it() -> None:
    prediction_repository = FakePredictionRepository()
    predictor = Predictor(
        model_registry_repository=FakeModelRegistryRepository(active_model=SimpleNamespace(model_version="mv1", feature_version="fv1")),
        prediction_repository=prediction_repository,
        artifact_storage=FakeArtifactStorage(True),
        model_loader=FakeModelLoader(),
    )

    result = predictor.predict(
        symbol="BTCUSDT",
        interval="15m",
        horizon_candles=8,
        candles=[_candle_payload(index) for index in range(210)],
        context={"market_regime": "TREND_UP"},
    )

    assert result["ml_available"] is True
    assert result["direction"] == "UP"
    assert prediction_repository.created_payloads


class FakeArtifactStorage:
    def __init__(self, exists: bool) -> None:
        self._exists = exists

    def exists(self, model_version: str) -> bool:
        return self._exists


class FakeModelRegistryRepository:
    def __init__(self, active_model) -> None:
        self._active_model = active_model

    def get_active_model(self, symbol: str, interval: str, horizon_candles: int):
        return self._active_model

    def get_by_model_version(self, model_version: str):
        return self._active_model


class FakePredictionRepository:
    def __init__(self) -> None:
        self.created_payloads = []

    def create(self, payload):
        self.created_payloads.append(payload)
        return payload


class FakeModelLoader:
    def load(self, model_version: str):
        model = FakeModel()
        scaler = {"mean": [0.0] * 34, "std": [1.0] * 34}
        feature_columns = [
            "body_size", "upper_wick", "lower_wick", "candle_range", "body_to_range_ratio", "close_position_in_range",
            "return_1", "return_3", "return_5", "return_10", "log_return_1", "atr_14", "atr_28", "range_percent",
            "rolling_volatility_20", "rolling_volatility_50", "ema_9", "ema_21", "ema_50", "ema_200",
            "close_to_ema_9", "close_to_ema_21", "close_to_ema_50", "ema_9_to_ema_21", "ema_21_to_ema_50",
            "trend_strength", "rsi_14", "macd", "macd_signal", "macd_histogram", "volume_sma_20", "volume_ratio_20",
            "volume_spike", "taker_buy_ratio",
        ]
        return model, scaler, feature_columns, {"model_name": "candle_mlp"}, {}


class FakeModel:
    def eval(self):
        return self

    def __call__(self, tensor):
        return {
            "direction_logits": torch.tensor([[2.0, 1.0, 0.5]], dtype=torch.float32),
            "tp_sl_logits": torch.tensor([0.3], dtype=torch.float32),
            "expected_move_atr": torch.tensor([1.25], dtype=torch.float32),
            "risk_score": torch.tensor([0.4], dtype=torch.float32),
        }


def _candle_payload(index: int) -> dict[str, str]:
    minute = index * 15
    hour = (minute // 60) % 24
    day = 1 + ((minute // 60) // 24)
    minute_of_hour = minute % 60
    price = 100 + index
    return {
        "open_time": f"2026-01-{day:02d}T{hour:02d}:{minute_of_hour:02d}:00Z",
        "open": str(price),
        "high": str(price + 2),
        "low": str(price - 1),
        "close": str(price + 1),
        "volume": str(1000 + index),
        "taker_buy_base_volume": str(500 + index),
    }
