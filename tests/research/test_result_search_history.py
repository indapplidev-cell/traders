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


def test_partitions_keep_exit_and_independent_data_out_of_search(tmp_path):
    rows = [candle(t) for t in range(0, 420000, 60000)]
    content = b"".join(json.dumps(r).encode() + b"\n" for r in rows)
    manifest = {"content_sha256": sha256(content).hexdigest(),
                "intervals": {"search_start_ms": 60000, "search_end_ms": 180000,
                              "exit_tail_end_ms": 240000, "independent_evaluation": [240000, 360000],
                              "acquisition_end_ms": 420000}}
    manifest["fingerprint"] = fingerprint(manifest)
    (tmp_path / "HISTORY.jsonl").write_bytes(content)
    (tmp_path / "DATASET_MANIFEST.json").write_text(json.dumps(manifest))
    assert HistoryProvider.search_view(tmp_path)[1] == rows[:3]
    for name, expected in [("warmup", rows[:1]), ("search", rows[1:3]),
                           ("exit_tail", rows[3:4]), ("independent_evaluation", rows[4:6]),
                           ("independent_exit_tail", rows[6:])]:
        assert HistoryProvider.partition(tmp_path, name) == expected


def test_bundle_rejects_modified_statistics(tmp_path):
    statistics = {"outcomes": [], "evidence_quality": "ASSUMPTION_BASED"}
    statistics["fingerprint"] = fingerprint(statistics)
    encoded = json.dumps(statistics).encode()
    manifest = {"content_sha256": sha256(b"").hexdigest(),
                "statistics": {"content_sha256": sha256(encoded).hexdigest(),
                               "fingerprint": statistics["fingerprint"]}}
    manifest["fingerprint"] = fingerprint(manifest)
    (tmp_path / "HISTORY.jsonl").write_bytes(b"")
    (tmp_path / "STATISTICS.json").write_bytes(encoded)
    (tmp_path / "DATASET_MANIFEST.json").write_text(json.dumps(manifest))
    assert HistoryProvider.load(tmp_path)[0] == manifest
    (tmp_path / "STATISTICS.json").write_bytes(encoded + b" ")
    with pytest.raises(ValueError, match="STATISTICS_CHECKSUM"):
        HistoryProvider.load(tmp_path)


def test_insufficient_warmup_rejected_before_source_access(tmp_path):
    with pytest.raises(ValueError, match="WARMUP_BELOW"):
        HistoryProvider().freeze(None, tmp_path / "uncreated", warmup_bars=1)
