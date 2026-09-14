from hashlib import sha256
import json

import pytest

from traders_ml.parameter_sweep.search_history import HistoryProvider, validate_candles
from traders_ml.parameter_sweep.result_search import fingerprint


def candle(t):
    return dict(kind="CANDLE", symbol="BTCUSDT", timeframe="1m", open_time_ms=t,
                close_time_ms=t+59999, open="10", high="12", low="9", close="11", volume="1")


def test_closed_candle_causal_windows_separate_exit_tail_and_symbol():
    rows = [candle(t) for t in [0, 60000, 120000]]
    rows.append(candle(0) | {"symbol": "ETHUSDT"})
    assert HistoryProvider.causal_window(rows, "BTCUSDT", "1m", 60000) == [rows[0]]
    assert HistoryProvider.causal_window(rows, "BTCUSDT", "1m", 59999) == []


def test_missing_gaps_duplicates_and_incomplete_tail():
    result = validate_candles([candle(60000), candle(60000), candle(180000)], 60000, 0, 360000)
    assert result["duplicates"] == 1
    assert result["gaps"] == 1
    assert result["start_missing"] and result["tail_missing"]


def test_complete_history_and_invalid_price():
    rows = [candle(0), candle(60000)]
    good = validate_candles(rows, 60000, 0, 120000)
    assert not any(good[k] for k in ["gaps", "duplicates", "start_missing", "tail_missing", "invalid_candles", "future_rows"])
    assert validate_candles([candle(0) | {"high": "8"}], 60000, 0, 60000)["invalid_candles"] == 1


def test_frozen_dataset_reload_and_tamper(tmp_path):
    content = json.dumps(candle(0)).encode() + b"\n"
    manifest = {"content_sha256": sha256(content).hexdigest(), "source": "TEST_ONLY"}
    manifest["fingerprint"] = fingerprint(manifest)
    (tmp_path / "HISTORY.jsonl").write_bytes(content)
    (tmp_path / "DATASET_MANIFEST.json").write_text(json.dumps(manifest))
    assert HistoryProvider.load(tmp_path) == HistoryProvider.load(tmp_path)
    manifest["source"] = "tampered"
    (tmp_path / "DATASET_MANIFEST.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="MANIFEST_FINGERPRINT"):
        HistoryProvider.load(tmp_path)
    (tmp_path / "HISTORY.jsonl").write_bytes(b'{}\n')
    with pytest.raises(ValueError, match="DATASET_CHECKSUM"):
        HistoryProvider.load(tmp_path)
