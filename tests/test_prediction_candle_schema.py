from app.api.schemas import PredictionCandleInput
from app.features.feature_builder import FeatureBuilder
from app.prediction.predictor import Predictor


def test_prediction_candle_schema_accepts_optional_binance_volume_fields() -> None:
    payload = PredictionCandleInput(
        open_time="2026-06-08T10:00:00Z",
        open="70000.0",
        high="70100.0",
        low="69850.0",
        close="70050.0",
        volume="123.45",
        quote_asset_volume="999.12",
        number_of_trades=123,
        taker_buy_base_volume="12.34",
        taker_buy_quote_volume="567.89",
    )

    assert payload.taker_buy_base_volume == "12.34"
    assert payload.taker_buy_quote_volume == "567.89"


def test_predictor_does_not_fake_taker_buy_volume() -> None:
    candle = {
        "open_time": "2026-06-08T10:00:00Z",
        "open": "70000.0",
        "high": "70100.0",
        "low": "69850.0",
        "close": "70050.0",
        "volume": "123.45",
    }

    converted = Predictor._to_candle_objects([candle])[0]
    features = FeatureBuilder().build([converted], symbol="BTCUSDT", interval="15m", feature_version="fv1")[0]

    assert converted.taker_buy_base_volume is None
    assert features.features_json["taker_buy_ratio"] is None
