import json
import re
from pathlib import Path


ROOT = Path("reports/engine_trend/composer_threshold_review")


def loaded(name: str):
    path = ROOT / name
    assert path.exists()
    return json.loads(path.read_text(encoding="utf-8"))


def test_required_review_artifacts_exist_and_are_valid() -> None:
    baseline = loaded("ENGINE_TREND_17_BASELINE_SUMMARY.json")
    after = loaded("ENGINE_TREND_17_AFTER_VALIDATION_MATRIX.json")
    comparison = loaded("ENGINE_TREND_17_BEFORE_AFTER_COMPARISON.json")
    candidate = loaded("ENGINE_TREND_17_THRESHOLD_CANDIDATE_ANALYSIS.json")
    decision = loaded("ENGINE_TREND_17_DECISION_RECORD.json")
    manifest = loaded("ENGINE_TREND_17_ARTIFACT_MANIFEST.json")
    assert baseline["before_windows"] == baseline["before_unknown_count"] == 60
    assert candidate["windows_analyzed"] == 60
    assert len(after["rows"]) >= 60 and len(comparison["rows"]) >= 60
    assert decision["after_validation"]["windows_replayed"] >= 60
    assert decision["after_validation"]["after_safety_violations"] == 0
    assert decision["runtime_trading_allowed"] is False
    assert decision["trading_claims_allowed"] is False
    assert manifest["adapter_changed"] is False and manifest["db_cli_changed"] is False
    assert manifest["safety_summary"]["violations"] == 0


def test_required_markdown_csv_and_stage_report_exist() -> None:
    for name in (
        "ENGINE_TREND_17_COMPOSER_RULE_REVIEW.md",
        "ENGINE_TREND_17_AFTER_VALIDATION_MATRIX.csv",
        "ENGINE_TREND_17_BEFORE_AFTER_COMPARISON.csv",
        "ENGINE_TREND_17_TUNING_DECISION.md",
    ):
        assert (ROOT / name).is_file()
    assert Path("reports/engine_trend/engine_trend_17_conservative_composer_threshold_review_report.md").is_file()


def test_artifacts_contain_no_unmasked_database_url_or_secret_assignment() -> None:
    payload = "\n".join(path.read_text(encoding="utf-8") for path in ROOT.rglob("*") if path.is_file())
    assert not re.search(r"postgresql(?:\+psycopg2?|)://(?!<user>)", payload, re.I)
    assert not re.search(r"(?:POSTGRES_PASSWORD|DATABASE_URL)\s*=", payload)


def test_rejected_candidate_is_not_claimed_as_composer_change() -> None:
    decision = loaded("ENGINE_TREND_17_DECISION_RECORD.json")
    manifest = loaded("ENGINE_TREND_17_ARTIFACT_MANIFEST.json")
    assert decision["status"] == "REJECTED_TUNING_ATTEMPT"
    assert decision["decision"]["accepted"] is False
    assert manifest["composer_changed"] is False
    assert manifest["composer_changed_files"] == []
