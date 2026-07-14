from __future__ import annotations

import json

import pytest

from app.market_reader.engine_trend.cli_preview import load_candle_payload, main
from app.market_reader.engine_trend.engine import (
    EngineTrendFacadeOutput,
    normalize_candle_row,
    normalize_candles,
    run_engine_trend,
    run_engine_trend_from_rows,
)
from app.market_reader.engine_trend.json_export import (
    build_engine_trend_json_payload,
    build_engine_trend_preview,
    save_engine_trend_json,
)


def sample_rows() -> list[dict[str, object]]:
    return [
        {"timestamp": "2026-01-01T00:00:00", "open": 100, "high": 103, "low": 99, "close": 102, "volume": 1000},
        {"timestamp": "2026-01-01T00:15:00", "open": 102, "high": 106, "low": 101, "close": 105, "volume": 1200},
        {"timestamp": "2026-01-01T00:30:00", "open": 105, "high": 107, "low": 103, "close": 104, "volume": 1100},
        {"timestamp": "2026-01-01T00:45:00", "open": 104, "high": 109, "low": 104, "close": 108, "volume": 1300},
        {"timestamp": "2026-01-01T01:00:00", "open": 108, "high": 112, "low": 107, "close": 111, "volume": 1400},
        {"timestamp": "2026-01-01T01:15:00", "open": 111, "high": 113, "low": 109, "close": 110, "volume": 1000},
        {"timestamp": "2026-01-01T01:30:00", "open": 110, "high": 115, "low": 110, "close": 114, "volume": 1500},
    ]


def test_normalize_candle_row_canonical_alias_and_default() -> None:
    canonical = normalize_candle_row(sample_rows()[0])
    aliased = normalize_candle_row(
        {"time": "t", "o": 1, "h": 3, "l": 0.5, "c": 2, "v": 4}
    )
    defaulted = normalize_candle_row(
        {"open_time": "t", "open": 1, "high": 2, "low": 0.5, "close": 1.5}
    )
    assert canonical.open == 100.0
    assert aliased.to_dict() == {
        "timestamp": "t", "open": 1.0, "high": 3.0, "low": 0.5,
        "close": 2.0, "volume": 4.0,
    }
    assert defaulted.volume == 0.0


@pytest.mark.parametrize(
    "row",
    [
        {"timestamp": "t", "open": 1, "high": 2, "low": 0},
        {"timestamp": "t", "open": "bad", "high": 2, "low": 0, "close": 1},
    ],
)
def test_normalize_candle_row_rejects_invalid_data(row: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        normalize_candle_row(row)


def test_normalize_candles_returns_tuples() -> None:
    candles = normalize_candles(sample_rows())
    assert isinstance(candles, tuple)
    assert len(candles) == 7
    assert normalize_candles([]) == ()


def test_facade_runs_for_candles_and_rows() -> None:
    candles = normalize_candles(sample_rows())
    facade = run_engine_trend("TESTUSDT", "15m", candles)
    from_rows = run_engine_trend_from_rows("TESTUSDT", "15m", sample_rows())
    assert isinstance(facade, EngineTrendFacadeOutput)
    assert facade.preview["symbol"] == "TESTUSDT"
    assert facade.json_payload["service"] == "ENGINE_TREND"
    assert from_rows.composer_output.result.market_regime.value in {
        "UP", "DOWN", "FLAT", "UNKNOWN"
    }
    safety = facade.composer_output.result.safety
    assert safety.trade_signal.value == "NOT_EVALUATED"
    assert safety.safe_for_runtime_trading is False
    assert safety.live_trading_connected is False
    assert facade.to_dict()["composer_output"]


def test_json_payload_preview_and_file_round_trip(tmp_path) -> None:
    output = run_engine_trend_from_rows("TESTUSDT", "15m", sample_rows()).composer_output
    payload = build_engine_trend_json_payload(output)
    assert payload["service"] == "ENGINE_TREND"
    assert payload["contract_version"] == "engine_trend_preview_v2"
    for key in ("result", "decision_trace", "ohlc_integrity", "safety"):
        assert key in payload
    assert "technical_indicators" in payload["analysis_context"]
    assert "hypotheses" in payload["analysis_context"]
    preview = build_engine_trend_preview(output)
    for key in ("symbol", "interval", "market_regime", "confidence", "status"):
        assert key in preview
    assert len(preview["reason_codes_top"]) <= 10
    path = save_engine_trend_json(payload, tmp_path / "nested" / "result.json")
    assert json.loads(path.read_text(encoding="utf-8")) == payload


def test_load_candle_payload_supports_envelope_and_list(tmp_path) -> None:
    envelope = tmp_path / "envelope.json"
    envelope.write_text(json.dumps({"symbol": "X", "interval": "1h", "candles": sample_rows()}), encoding="utf-8")
    direct = tmp_path / "direct.json"
    direct.write_text(json.dumps(sample_rows()), encoding="utf-8")
    assert load_candle_payload(envelope) == ("X", "1h", sample_rows())
    assert load_candle_payload(direct) == (None, None, sample_rows())


def test_cli_valid_output_and_json_stdout(tmp_path, capsys) -> None:
    source = tmp_path / "input.json"
    target = tmp_path / "result.json"
    source.write_text(json.dumps(sample_rows()), encoding="utf-8")
    status = main([
        "--input", str(source), "--symbol", "X", "--interval", "15m",
        "--output", str(target), "--print-json",
    ])
    captured = capsys.readouterr()
    assert status == 0
    assert target.exists()
    assert json.loads(captured.out)["service"] == "ENGINE_TREND"


def test_cli_reports_invalid_path_and_missing_context(tmp_path, capsys) -> None:
    assert main(["--input", str(tmp_path / "missing.json")]) != 0
    source = tmp_path / "input.json"
    source.write_text("[]", encoding="utf-8")
    assert main(["--input", str(source)]) != 0
    assert "error" in capsys.readouterr().err
