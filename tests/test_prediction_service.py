from app.prediction.prediction_service import PredictionService


def test_prediction_service_delegates_to_predictor() -> None:
    predictor = FakePredictor()
    service = PredictionService(predictor=predictor)

    result = service.predict(
        {
            "symbol": "BTCUSDT",
            "interval": "15m",
            "horizon_candles": 8,
            "candles": [],
            "context": {"risk_profile": "normal"},
            "model_version": "mv1",
        }
    )

    assert result["ml_available"] is False
    assert predictor.calls[0]["model_version"] == "mv1"


class FakePredictor:
    def __init__(self) -> None:
        self.calls = []

    def predict(self, **kwargs):
        self.calls.append(kwargs)
        return {"ml_available": False, "reason": "not_enough_candles"}
