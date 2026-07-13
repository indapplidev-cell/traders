import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/engine_trend/validation_review"


def read_json(name):
    path = OUT / name
    assert path.exists()
    return json.loads(path.read_text(encoding="utf-8"))


def test_review_artifacts_and_contract():
    matrix = read_json("ENGINE_TREND_16_TRACE_REVIEW_MATRIX.json")
    assert (OUT / "ENGINE_TREND_16_TRACE_REVIEW_MATRIX.csv").exists()
    reason = read_json("ENGINE_TREND_16_REASON_CODE_SUMMARY.json")
    confidence = read_json("ENGINE_TREND_16_CONFIDENCE_DIAGNOSTICS.json")
    decision = read_json("ENGINE_TREND_16_DECISION_RECORD.json")
    manifest = read_json("ENGINE_TREND_16_ARTIFACT_MANIFEST.json")
    assert (OUT / "ENGINE_TREND_16_UNKNOWN_CAUSE_DIAGNOSIS.md").exists()
    assert (OUT / "ENGINE_TREND_16_CORE_TUNING_DECISION.md").exists()
    assert (ROOT / "reports/engine_trend/engine_trend_16_historical_validation_review_core_tuning_decision_report.md").exists()
    assert len(matrix["rows"]) >= 60 == reason["total_windows_reviewed"] == confidence["total_windows_reviewed"]
    review = decision["validation_review"]
    assert review["windows_reviewed"] == len(matrix["rows"])
    assert review["unknown_count"] == review["windows_reviewed"]
    assert review["safety_violations"] == 0
    assert decision["selected_decision"] and decision["next_stage"]
    assert decision["runtime_trading_allowed"] is False
    assert decision["trading_claims_allowed"] is False
    assert manifest["core_changed"] is False
    assert manifest["adapter_changed"] is False
    assert manifest["db_cli_changed"] is False


def test_generated_artifacts_contain_no_unmasked_database_url():
    paths = list(OUT.glob("*.json")) + list(OUT.glob("*.md")) + list(OUT.glob("*.csv"))
    paths.append(ROOT / "reports/engine_trend/engine_trend_16_historical_validation_review_core_tuning_decision_report.md")
    url = re.compile(r"postgresql(?:\+psycopg2?|)://[^\s\"']+", re.IGNORECASE)
    assert not [(path, url.findall(path.read_text(encoding="utf-8"))) for path in paths if url.search(path.read_text(encoding="utf-8"))]
