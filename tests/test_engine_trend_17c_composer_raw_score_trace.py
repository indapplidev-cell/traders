import csv
import json
import re
from pathlib import Path

ROOT = Path("reports/engine_trend/composer_raw_score_trace")
REPORT = Path("reports/engine_trend/engine_trend_17c_composer_raw_score_trace_exposure_report.md")


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def test_behavior_lock_contract():
    lock = read("ENGINE_TREND_17C_BEHAVIOR_LOCK.json")
    assert lock["window_count"] >= 60
    assert lock["behavior_changed"] is False
    assert lock["market_regime_counts"] == {"UNKNOWN": 60}
    assert lock["confidence_counts"] == {"0.3": 60}
    assert lock["safety_violations"] == 0


def test_matrices_and_decision_contracts():
    raw = read("ENGINE_TREND_17C_RAW_SCORE_MATRIX.json")
    coverage = read("ENGINE_TREND_17C_COMPOSER_TRACE_COVERAGE_MATRIX.json")
    assert raw["window_count"] >= 60 and len(raw["rows"]) >= 60
    assert coverage["window_count"] >= 60 and len(coverage["rows"]) >= 60
    for name in ("ENGINE_TREND_17C_RAW_SCORE_MATRIX.csv", "ENGINE_TREND_17C_COMPOSER_TRACE_COVERAGE_MATRIX.csv"):
        with (ROOT / name).open(encoding="utf-8") as handle:
            assert len(list(csv.DictReader(handle))) >= 60
    missing = read("ENGINE_TREND_17C_MISSING_COMPOSER_TRACE_FIELDS.json")
    assert isinstance(missing["can_proceed_to_tuning"], bool)
    if not missing["can_proceed_to_tuning"]:
        assert "17D" in missing["next_stage"]
    assert (ROOT / "ENGINE_TREND_17C_TRACE_READINESS_DECISION.md").exists()


def test_all_windows_and_per_window_contracts():
    all_windows = (ROOT / "ENGINE_TREND_17C_ALL_WINDOWS_TRACE_REVIEW.md").read_text(encoding="utf-8")
    assert len(re.findall(r"^## Window \d{3} — ", all_windows, re.MULTILINE)) >= 60
    assert all_windows.count("### Composer raw score trace") >= 60
    json_files = list((ROOT / "json").glob("*_composer_trace.json"))
    md_files = list((ROOT / "markdown").glob("*_composer_trace.md"))
    assert len(json_files) >= 60 and len(md_files) >= 60
    for path in json_files:
        value = json.loads(path.read_text(encoding="utf-8"))
        assert "composer_trace" in value
        assert "raw_scores" in value["composer_trace"] and "clamped_scores" in value["composer_trace"]
        final = value["final_result"]
        assert final["market_regime"] == "UNKNOWN" and final["confidence"] == 0.3
    for path in md_files:
        body = path.read_text(encoding="utf-8")
        assert "### Composer raw score trace" in body
        assert "Raw score" in body and "Clamped score" in body


def test_manifest_stage_report_and_no_credentials():
    manifest = read("ENGINE_TREND_17C_ARTIFACT_MANIFEST.json")
    assert manifest["window_count"] >= 60
    assert manifest["core_behavior_changed"] is False
    assert manifest["adapter_changed"] is False and manifest["db_cli_changed"] is False
    assert manifest["runtime_trading_allowed"] is False
    assert manifest["trading_claims_allowed"] is False
    assert len(manifest["per_window_json_files"]) >= 60
    assert len(manifest["per_window_markdown_files"]) >= 60
    assert REPORT.exists()
    pattern = re.compile(r"postgresql(?:\+psycopg2?)?://|DATABASE_URL\s*=|POSTGRES_PASSWORD\s*=|password\s*[:=]", re.I)
    for path in ROOT.rglob("*"):
        if path.is_file():
            assert not pattern.search(path.read_text(encoding="utf-8")), path

