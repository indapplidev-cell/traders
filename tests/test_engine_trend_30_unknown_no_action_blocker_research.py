from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from app.market_reader.engine_trend.offline_report_diagnostics import (
    attach_contextual_diagnostics,
)
from app.market_reader.engine_trend.offline_unknown_blocker_dataset import (
    BLOCKER_CODES,
    NOT_OBSERVABLE_BLOCKERS,
    blocker_schema,
    build_blocker_ranking,
    build_dataset,
    normalize_artifact,
)


ROOT = Path(__file__).resolve().parents[1]
REPLAY = ROOT / "reports" / "engine_trend" / "hypothesis_replay" / "json"
AUDIT_29 = (
    ROOT
    / "reports"
    / "engine_trend"
    / "engine_trend_29_unified_contextual_diagnostics_audit"
    / "ENGINE_TREND_29_KNOWN_CASES_AUDIT.json"
)
REPORT_30 = (
    ROOT
    / "reports"
    / "engine_trend"
    / "engine_trend_30_unknown_no_action_blocker_research"
)


def _load(name: str) -> dict[str, Any]:
    return json.loads((REPLAY / name).read_text(encoding="utf-8"))


def _unknown_row() -> dict[str, Any]:
    source = _load("btc_15m_expected_unknown_or_mixed_001.json")
    return normalize_artifact(
        attach_contextual_diagnostics(source),
        source_artifact="fixture:btc_unknown",
    )


def _validate(instance: Any, schema: dict[str, Any], root: dict[str, Any]) -> None:
    if "$ref" in schema:
        target: Any = root
        for part in schema["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        _validate(instance, target, root)
        return
    if "const" in schema:
        assert instance == schema["const"]
    if "enum" in schema:
        assert instance in schema["enum"]
    expected = schema.get("type")
    types = {
        "object": dict,
        "array": list,
        "string": str,
        "integer": int,
        "boolean": bool,
        "null": type(None),
    }
    if isinstance(expected, list):
        assert any(isinstance(instance, types[item]) for item in expected)
    elif expected:
        assert isinstance(instance, types[expected])
    if expected == "object":
        assert all(key in instance for key in schema.get("required", []))
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, value in instance.items():
            if key in properties:
                _validate(value, properties[key], root)
            elif isinstance(additional, dict):
                _validate(value, additional, root)
            else:
                assert additional is not False
    if expected == "array":
        if schema.get("uniqueItems"):
            comparable = [json.dumps(value, sort_keys=True) for value in instance]
            assert len(comparable) == len(set(comparable))
        for value in instance:
            _validate(value, schema.get("items", {}), root)


def test_dataset_rows_are_generated_from_enriched_offline_artifacts() -> None:
    source = _load("btc_15m_expected_unknown_or_mixed_001.json")
    before = deepcopy(source)
    rows = build_dataset(
        [("hypothesis_replay/btc_unknown.json", attach_contextual_diagnostics(source))]
    )

    assert source == before
    assert len(rows) == 1
    assert rows[0]["case_id"] == "btc_15m_expected_unknown_or_mixed_001"
    assert rows[0]["source_artifact"] == "hypothesis_replay/btc_unknown.json"
    assert rows[0]["hypothesis_statuses"]["PENDING"] == 1


def test_blocker_codes_are_stable_and_normalized() -> None:
    row = _unknown_row()

    assert len(BLOCKER_CODES) == len(set(BLOCKER_CODES))
    assert row["blocker_codes"] == [
        code for code in BLOCKER_CODES if code in row["blocker_codes"]
    ]
    assert "NO_CONFIRMED_CAUSAL_HYPOTHESIS" in row["blocker_codes"]
    assert "ONLY_PENDING_HYPOTHESES" in row["blocker_codes"]


def test_not_observable_is_not_treated_as_false() -> None:
    row = _unknown_row()

    assert row["missing_data_policy"] == "NOT_OBSERVABLE_SEPARATE_FROM_FALSE"
    assert set(row["not_observable_fields"]) == {
        "indicator_pressure", "multi_timeframe", "price_context", "zone_proximity"
    }
    assert NOT_OBSERVABLE_BLOCKERS <= set(row["blocker_codes"])
    assert row["zone_context"]["observable"] is False


def test_unknown_no_action_remains_unchanged() -> None:
    row = _unknown_row()

    assert row["source_regime"] == row["final_regime"] == "UNKNOWN"
    assert row["no_action"] is True
    assert row["wait_for_confirmation"] is True
    assert row["setup_created"] is False
    assert row["trade_signal_created"] is False
    assert row["decision_changed_by_diagnostics"] is False


def test_flat_confirmed_range_context_remains_unchanged() -> None:
    row = normalize_artifact(
        attach_contextual_diagnostics(_load("sol_15m_expected_flat_001.json"))
    )

    assert row["source_regime"] == row["final_regime"] == "FLAT"
    assert "CONFIRMED_RANGE_CONTEXT" in row["blocker_codes"]
    assert row["setup_created"] is False
    assert row["trade_signal_created"] is False
    assert row["decision_changed_by_diagnostics"] is False


def test_blocker_ranking_counts_expected_codes_and_safety() -> None:
    unknown = _unknown_row()
    flat = normalize_artifact(
        attach_contextual_diagnostics(_load("sol_15m_expected_flat_001.json"))
    )
    ranking = build_blocker_ranking([unknown, flat])
    counts = {
        item["blocker_code"]: item["count"]
        for item in ranking["blocker_frequency"]
    }

    assert counts["SETUP_BLOCKED_BY_NO_ACTION"] == 2
    assert counts["NO_CONFIRMED_CAUSAL_HYPOTHESIS"] == 1
    assert counts["CONFIRMED_RANGE_CONTEXT"] == 1
    assert ranking["safety_counts"] == {
        "diagnostics_changed_decision": 0,
        "diagnostics_created_setup": 0,
        "diagnostics_created_trade_signal": 0,
    }


def test_schema_validates_generated_dataset_and_ranking() -> None:
    rows = [_unknown_row()]
    dataset = {"stage": "ENGINE-TREND-30", "dataset_version": "1.0.0", "rows": rows}
    ranking = build_blocker_ranking(rows)
    schema = blocker_schema()

    _validate(dataset, schema["$defs"]["dataset"], schema)
    _validate(ranking, schema["$defs"]["ranking"], schema)


def test_known_cases_are_represented_when_stage_29_audit_is_available() -> None:
    audit = json.loads(AUDIT_29.read_text(encoding="utf-8"))
    rows = build_dataset([(str(AUDIT_29.relative_to(ROOT)), audit)])

    assert len(rows) == 4
    cases = {(row["symbol"], row["timestamp"], row["final_regime"]): row for row in rows}
    assert ("ETHUSDT", "2026-07-14T10:00:00Z", "UNKNOWN") in cases
    assert ("BTCUSDT", "2026-07-13T16:00:00Z", "UNKNOWN") in cases
    assert "RANGE_TREND_CONFLICT" in cases[
        ("SOLUSDT", "2026-07-08T18:30:00Z", "UNKNOWN")
    ]["blocker_codes"]
    assert "CONFIRMED_RANGE_CONTEXT" in cases[
        ("SOLUSDT", "2026-07-08T23:45:00Z", "FLAT")
    ]["blocker_codes"]
    assert all(row["candidate_next_research"] for row in rows)
    assert all(row["decision_changed_by_diagnostics"] is False for row in rows)
    assert all(row["setup_created"] is False for row in rows)
    assert all(row["trade_signal_created"] is False for row in rows)


def test_committed_artifacts_match_schema_and_dataset() -> None:
    dataset = json.loads(
        (REPORT_30 / "ENGINE_TREND_30_BLOCKER_DATASET.json").read_text(encoding="utf-8")
    )
    ranking = json.loads(
        (REPORT_30 / "ENGINE_TREND_30_BLOCKER_RANKING.json").read_text(encoding="utf-8")
    )
    schema = json.loads(
        (REPORT_30 / "ENGINE_TREND_30_BLOCKER_SCHEMA.json").read_text(encoding="utf-8")
    )

    _validate(dataset, schema["$defs"]["dataset"], schema)
    _validate(ranking, schema["$defs"]["ranking"], schema)
    assert ranking["case_count"] == len(dataset["rows"])
    assert ranking["safety_counts"]["diagnostics_changed_decision"] == 0
    assert ranking["safety_counts"]["diagnostics_created_trade_signal"] == 0
