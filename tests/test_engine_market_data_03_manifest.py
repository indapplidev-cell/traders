import json
from pathlib import Path


def test_manifest_matches_historical_backfill_contract():
    path = Path(__file__).parents[1] / "app/engine_market_data/ENGINE_MARKET_DATA_03_MANIFEST.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["rolling_window_limits"] == {"1m": 10000, "5m": 10000, "15m": 10000,
                                               "1h": 5000, "4h": 3000, "1d": 1500}
    assert data["downloads_only_missing_candles"] and data["restart_safe"]
    assert data["closed_candle_only"] and data["idempotent_upsert"]
    assert not data["uses_private_api"] and not data["uses_api_keys"]
    assert not data["future_bars_used"] and not data["creates_synthetic_candles"]

