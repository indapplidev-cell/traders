from __future__ import annotations

import json
import re
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DECISION_ROOT = REPOSITORY_ROOT / "reports" / "engine_trend" / "decision_gate"
KNOWN_LIMITATIONS_PATH = DECISION_ROOT / "ENGINE_TREND_14_KNOWN_LIMITATIONS.md"
DECISION_GATE_PATH = DECISION_ROOT / "ENGINE_TREND_14_DECISION_GATE.md"
VALIDATION_PLAN_PATH = DECISION_ROOT / "ENGINE_TREND_14_VALIDATION_PLAN.md"
DECISION_RECORD_PATH = DECISION_ROOT / "ENGINE_TREND_14_DECISION_RECORD.json"


def load_decision_record() -> dict[str, object]:
    assert DECISION_RECORD_PATH.is_file()
    return json.loads(DECISION_RECORD_PATH.read_text(encoding="utf-8"))


def test_required_decision_documents_exist() -> None:
    for path in (
        KNOWN_LIMITATIONS_PATH,
        DECISION_GATE_PATH,
        VALIDATION_PLAN_PATH,
        DECISION_RECORD_PATH,
    ):
        assert path.is_file(), f"missing decision artifact: {path}"


def test_decision_record_contract() -> None:
    record = load_decision_record()
    assert record["stage"] == "ENGINE-TREND-14"
    assert record["selected_decision"] == "C"
    assert "ENGINE-TREND-15" in record["next_stage"]
    assert record["core_changes_allowed_before_validation"] is False
    assert record["trading_claims_allowed"] is False
    assert record["runtime_trading_allowed"] is False


def test_decision_record_includes_missing_labeled_history_limitation() -> None:
    limitations = load_decision_record()["known_limitations"]
    assert "no_labeled_historical_windows" in limitations


def test_validation_plan_has_minimum_scope_and_labels() -> None:
    text = VALIDATION_PLAN_PATH.read_text(encoding="utf-8")
    for token in (
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
        "15m",
        "EXPECTED_UP",
        "EXPECTED_DOWN",
        "EXPECTED_FLAT",
        "EXPECTED_UNKNOWN_OR_MIXED",
    ):
        assert token in text


def test_decision_artifacts_contain_no_unmasked_database_url() -> None:
    for path in DECISION_ROOT.iterdir():
        if path.suffix in {".md", ".json"}:
            text = path.read_text(encoding="utf-8")
            assert not re.search(
                r"postgresql(?:\+psycopg2?)?://[^\s`\"]+",
                text,
                re.IGNORECASE,
            ), f"unmasked database URL in {path}"
