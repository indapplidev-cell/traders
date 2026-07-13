from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path("reports/engine_trend/historical_validation")
WINDOWS = ROOT / "ENGINE_TREND_15_VALIDATION_WINDOWS.json"
MATRIX_JSON = ROOT / "ENGINE_TREND_15_VALIDATION_MATRIX.json"
MATRIX_CSV = ROOT / "ENGINE_TREND_15_VALIDATION_MATRIX.csv"
SUMMARY = ROOT / "ENGINE_TREND_15_VALIDATION_SUMMARY.md"
MANIFEST = ROOT / "ENGINE_TREND_15_ARTIFACT_MANIFEST.json"
REPORT = Path("reports/engine_trend/engine_trend_15_historical_market_reading_validation_report.md")
SYMBOLS = {"BTCUSDT", "ETHUSDT", "SOLUSDT"}
LABELS = {"EXPECTED_UP", "EXPECTED_DOWN", "EXPECTED_FLAT", "EXPECTED_UNKNOWN_OR_MIXED", "EXPECTED_BREAKOUT_OR_FAKEOUT"}
STATUSES = {"MATCH", "ACCEPTABLE_UNKNOWN", "QUESTIONABLE_UNKNOWN", "MISMATCH", "NEEDS_REVIEW"}
FORBIDDEN_LABELS = {"BUY", "SELL", "LONG", "SHORT", "ENTER", "EXIT", "TAKE_PROFIT", "STOP_LOSS"}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_required_pack_files_exist_and_are_valid() -> None:
    for path in (WINDOWS, MATRIX_JSON, MATRIX_CSV, SUMMARY, MANIFEST, REPORT):
        assert path.is_file(), path
    assert load(WINDOWS)["stage"] == "ENGINE-TREND-15"
    assert load(MATRIX_JSON)["stage"] == "ENGINE-TREND-15"
    assert load(MANIFEST)["stage"] == "ENGINE-TREND-15"
    assert MATRIX_CSV.read_text(encoding="utf-8").startswith("window_id,")


def test_windows_and_matrix_obey_validation_scope() -> None:
    windows = load(WINDOWS)["windows"]
    rows = load(MATRIX_JSON)["rows"]
    assert len(windows) >= 9
    assert len(rows) == len(windows)
    assert {row["symbol"] for row in rows} == SYMBOLS
    for row in rows:
        assert row["symbol"] in SYMBOLS
        assert row["interval"] == "15m"
        assert row["window_length"] == 96
        assert row["reference_label"] in LABELS
        assert row["reference_label"] not in FORBIDDEN_LABELS
        assert row["match_status"] in STATUSES
        assert row["trade_signal"] == "NOT_EVALUATED"
        assert row["safe_for_runtime_trading"] is False
        assert row["live_trading_connected"] is False
        assert Path(row["preview_artifact"]).is_file()
        assert Path(row["result_artifact"]).is_file()


def test_manifest_checksums_and_safety_are_complete() -> None:
    manifest = load(MANIFEST)
    rows = load(MATRIX_JSON)["rows"]
    assert manifest["window_count"] == len(rows)
    assert manifest["no_trading_claims"] is True
    assert manifest["safety_summary"]["violations"] == 0
    referenced = {row[key] for row in rows for key in ("preview_artifact", "result_artifact")}
    assert referenced <= set(manifest["per_window_artifact_paths"])
    for name, expected in manifest["sha256_checksums"].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected


def test_manifest_and_artifacts_contain_no_database_secret() -> None:
    payload = "\n".join(path.read_text(encoding="utf-8") for path in ROOT.rglob("*") if path.is_file())
    assert not re.search(r"postgresql(?:\+psycopg2?|)://", payload, re.IGNORECASE)
    assert not re.search(r"(?:POSTGRES_PASSWORD|DATABASE_URL)\s*=", payload)
    manifest_text = MANIFEST.read_text(encoding="utf-8")
    assert "db_url" not in manifest_text.lower()
