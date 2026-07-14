from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / (
    "reports/engine_trend/live_market_checks/"
    "engine_trend_19_btcusdt_2026_07_13_down_audit"
)
AUDIT_JSON = REPORT_DIR / "ENGINE_TREND_19_BTCUSDT_2026_07_13_DOWN_AUDIT.json"
SWEEP_CSV = REPORT_DIR / "ENGINE_TREND_19_BTCUSDT_2026_07_13_WINDOW_SWEEP.csv"
MANIFEST_JSON = REPORT_DIR / "ENGINE_TREND_19_BTCUSDT_2026_07_13_ARTIFACT_MANIFEST.json"
SCRIPT = ROOT / "scripts/engine_trend_19_btcusdt_2026_07_13_down_audit.py"


def test_live_case_reproduces_unknown_without_down_candidate() -> None:
    audit = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))

    assert audit["status"] == "DOWN_RECALL_GAP_TREND_ONLY_CONTINUATION_MISSING"
    assert audit["data_coverage"]["status"] == "PASS"
    assert audit["data_coverage"]["actual_candles"] == 96
    assert audit["data_coverage"]["missing_intervals"] == []
    assert audit["data_coverage"]["duplicates"] == []
    assert audit["composer_trace"]["regime"] == "UNKNOWN"
    assert audit["hypothesis_generation"]["down_continuation_candidate_exists"] is False
    assert audit["hypothesis_generation"]["down_continuation_generation_conditions"] == {
        "structure_matches": False,
        "breakdown_matches": False,
        "confirmed_bearish_continuation_event": False,
        "indicator_matches": True,
        "decision_window_progress_matches": False,
    }
    assert audit["counterfactual"]["hypothetical_trend_only_down_continuation"] is True
    assert audit["safety_audit"]["formal_safety_violation"] is False


def test_window_sweep_and_manifest_are_complete() -> None:
    with SWEEP_CSV.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["window_end"] for row in rows] == [
        "2026-07-13T09:00:00Z",
        "2026-07-13T12:00:00Z",
        "2026-07-13T14:15:00Z",
        "2026-07-13T16:00:00Z",
    ]
    assert {row["regime"] for row in rows} == {"UNKNOWN"}
    assert {row["selected_hypothesis"] for row in rows} == {""}

    manifest = json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))
    assert len(manifest["files"]) == 6
    assert all((ROOT / path).is_file() for path in manifest["files"])
    assert len(manifest["created_files"]) == 8
    assert all((ROOT / path).is_file() for path in manifest["created_files"])
    assert manifest["runtime_code_changed"] is False
    assert manifest["database_writes"] is False


def test_audit_script_has_no_market_data_write_or_backfill_dependency() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "BinanceClient" not in source
    assert "CandleRepository" not in source
    assert ".commit(" not in source
    assert "upsert" not in source.lower()
