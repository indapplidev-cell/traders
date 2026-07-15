import json
from pathlib import Path


def test_manifest_locks_stage_contract():
    data = json.loads((Path(__file__).parents[1] / "app/engine_market_data/ENGINE_MARKET_DATA_02_MANIFEST.json").read_text())
    assert data["database"] == "postgresql" and data["closed_candle_only"]
    assert len(data["tables"]) == 6 and data["downloads_only_missing_candles"]
    assert not data["future_bars_used"] and not data["creates_synthetic_candles"]
