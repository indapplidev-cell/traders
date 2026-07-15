import json
from pathlib import Path


def test_manifest_safety_contract():
    data = json.loads((Path(__file__).parents[1] / "app/engine_market_data/ENGINE_MARKET_DATA_04_MANIFEST.json").read_text())
    assert data["writes_closed_candles_only"] and not data["uses_private_api"] and data["supports_reboot_recovery"]
