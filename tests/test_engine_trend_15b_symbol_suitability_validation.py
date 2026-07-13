from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path("reports/engine_trend/symbol_suitability_validation")
AVAILABILITY = ROOT / "ENGINE_TREND_15B_SYMBOL_AVAILABILITY.json"
SUITABILITY = ROOT / "ENGINE_TREND_15B_SYMBOL_SUITABILITY_MATRIX.json"
WINDOWS = ROOT / "ENGINE_TREND_15B_EXPANDED_VALIDATION_WINDOWS.json"
MATRIX = ROOT / "ENGINE_TREND_15B_EXPANDED_VALIDATION_MATRIX.json"
MATRIX_CSV = ROOT / "ENGINE_TREND_15B_EXPANDED_VALIDATION_MATRIX.csv"
SUMMARY = ROOT / "ENGINE_TREND_15B_SYMBOL_SUITABILITY_SUMMARY.md"
MANIFEST = ROOT / "ENGINE_TREND_15B_ARTIFACT_MANIFEST.json"
REPORT = Path("reports/engine_trend/engine_trend_15b_symbol_suitability_expanded_validation_report.md")
LABELS = {"EXPECTED_UP", "EXPECTED_DOWN", "EXPECTED_FLAT", "EXPECTED_UNKNOWN_OR_MIXED", "RECENT_BASELINE", "HIGH_VOLATILITY_CHOP", "EXPECTED_BREAKOUT_OR_FAKEOUT"}
STATUSES = {"MATCH", "ACCEPTABLE_UNKNOWN", "QUESTIONABLE_UNKNOWN", "MISMATCH", "NEEDS_REVIEW"}
FORBIDDEN = {"BUY", "SELL", "LONG", "SHORT"}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_required_artifacts_exist_and_are_valid() -> None:
    required = (AVAILABILITY, SUITABILITY, WINDOWS, MATRIX, MATRIX_CSV, SUMMARY, MANIFEST, REPORT,
                ROOT / "ENGINE_TREND_15B_SYMBOL_SUITABILITY_MATRIX.csv")
    for path in required:
        assert path.is_file(), path
    for path in (AVAILABILITY, SUITABILITY, WINDOWS, MATRIX, MANIFEST):
        assert load(path)["stage"] == "ENGINE-TREND-15B"


def test_expanded_scope_labels_and_safety_contract() -> None:
    windows = load(WINDOWS)["windows"]; rows = load(MATRIX)["rows"]
    assert len(windows) >= 30
    assert len(rows) == len(windows)
    symbols = {row["symbol"] for row in rows}
    discovered = set(load(MANIFEST)["symbols_discovered"])
    if discovered == {"BTCUSDT", "ETHUSDT", "SOLUSDT"}:
        assert symbols == discovered
    for row in rows:
        assert row["interval"] == "15m"
        assert row["window_length"] == 96
        assert row["reference_label"] in LABELS
        assert row["reference_label"] not in FORBIDDEN
        assert row["match_status"] in STATUSES
        assert row["trade_signal"] == "NOT_EVALUATED"
        assert row["safe_for_runtime_trading"] is False
        assert row["live_trading_connected"] is False
        assert Path(row["preview_artifact"]).is_file()
        assert Path(row["result_artifact"]).is_file()


def test_manifest_checksums_flags_and_references() -> None:
    manifest = load(MANIFEST); rows = load(MATRIX)["rows"]
    assert manifest["window_count"] == len(rows)
    assert manifest["safety_summary"]["violations"] == 0
    assert manifest["no_trading_claims"] is True
    assert manifest["core_changed"] is False
    assert manifest["adapter_changed"] is False
    assert manifest["db_cli_changed"] is False
    referenced = {row[key] for row in rows for key in ("preview_artifact", "result_artifact")}
    assert referenced <= set(manifest["per_window_artifact_paths"])
    for name, expected in manifest["sha256_checksums"].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected


def test_artifacts_contain_no_unmasked_database_url_or_secret() -> None:
    payload = "\n".join(path.read_text(encoding="utf-8") for path in ROOT.rglob("*") if path.is_file())
    assert not re.search(r"postgresql(?:\+psycopg2?|)://", payload, re.IGNORECASE)
    assert not re.search(r"(?:POSTGRES_PASSWORD|DATABASE_URL)\s*=", payload)
    assert "db_url" not in MANIFEST.read_text(encoding="utf-8").lower()
