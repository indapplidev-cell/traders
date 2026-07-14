from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import pytest

from app.market_reader.engine_trend.contextual_diagnostics import (
    ContextualDiagnosticInput,
    DiagnosticZone,
    diagnose_context,
)
from app.market_reader.engine_trend.offline_report_diagnostics import (
    _assert_post_decision_invariants,
    attach_contextual_diagnostics,
)
from scripts.engine_trend_18_hypothesis_replay import markdown


ROOT = Path(__file__).resolve().parents[1]
REPLAY = ROOT / "reports" / "engine_trend" / "hypothesis_replay" / "json"
AUDIT = (
    ROOT
    / "reports"
    / "engine_trend"
    / "engine_trend_29_unified_contextual_diagnostics_audit"
)


def _load_replay(name: str) -> dict[str, Any]:
    return json.loads((REPLAY / name).read_text(encoding="utf-8"))


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
        "number": (int, float),
        "boolean": bool,
        "null": type(None),
    }
    if expected:
        assert isinstance(instance, types[expected])
    if expected == "object":
        for key in schema.get("required", []):
            assert key in instance
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties")
        for key, value in instance.items():
            if key in properties:
                _validate(value, properties[key], root)
            elif isinstance(additional, dict):
                _validate(value, additional, root)
    if expected == "array":
        if schema.get("uniqueItems"):
            assert len(instance) == len(set(instance))
        if "items" in schema:
            for value in instance:
                _validate(value, schema["items"], root)


def test_diagnostics_are_post_decision_only() -> None:
    source = _load_replay("btc_15m_expected_unknown_or_mixed_001.json")
    source["setup_eligibility"] = {"eligible": False, "reason": "source_contract"}
    source["trade_decision"] = "NO_TRADE"
    before = deepcopy(source)

    enriched = attach_contextual_diagnostics(source)
    preserved = deepcopy(enriched)
    diagnostics = preserved.pop("contextual_diagnostics")

    assert source == before
    assert preserved == before
    assert enriched["composer"]["regime"] == before["composer"]["regime"]
    assert enriched["comparison"]["new_regime"] == before["comparison"]["new_regime"]
    assert enriched["composer"]["selected_hypothesis"] == before["composer"]["selected_hypothesis"]
    assert enriched["setup_eligibility"] == before["setup_eligibility"]
    assert enriched["trade_decision"] == before["trade_decision"]
    assert diagnostics["safety"]["setup_created"] is False
    assert diagnostics["safety"]["trade_signal_created"] is False


def test_unknown_no_action_and_wait_remains_unknown() -> None:
    source = _load_replay("btc_15m_expected_unknown_or_mixed_001.json")
    enriched = attach_contextual_diagnostics(source)
    diagnostics = enriched["contextual_diagnostics"]

    assert enriched["composer"]["regime"] == "UNKNOWN"
    assert {"NO_ACTION", "WAIT_FOR_CONFIRMATION"} <= set(diagnostics["observed_tags"])
    assert diagnostics["action"] == "NO_ACTION"
    assert diagnostics["safety"]["setup_created"] is False
    assert diagnostics["safety"]["trade_signal_created"] is False


def test_flat_confirmed_range_context_remains_flat() -> None:
    source = _load_replay("sol_15m_expected_flat_001.json")
    enriched = attach_contextual_diagnostics(source)

    assert enriched["composer"]["regime"] == "FLAT"
    assert "CONFIRMED_RANGE_CONTEXT" in enriched["contextual_diagnostics"]["observed_tags"]
    assert enriched["contextual_diagnostics"]["action"] == "NO_ACTION"
    assert enriched["contextual_diagnostics"]["safety"]["setup_created"] is False
    assert enriched["contextual_diagnostics"]["safety"]["trade_signal_created"] is False


def test_missing_historical_fields_remain_not_observable() -> None:
    diagnostics = attach_contextual_diagnostics(
        _load_replay("btc_15m_expected_unknown_or_mixed_001.json")
    )["contextual_diagnostics"]

    expected = {"price_context", "zone_proximity", "indicator_pressure", "multi_timeframe"}
    assert expected <= set(diagnostics["not_observable_fields"])
    assert diagnostics["observability"]["price_position"] == "not_observable"
    assert diagnostics["observability"]["zone_proximity"] == "not_observable"
    assert diagnostics["observability"]["indicators"] == "not_observable"
    assert diagnostics["observability"]["multi_timeframe"] == "not_observable"
    assert False not in diagnostics["observability"].values()
    assert diagnostics["decision_impact"]["risk_reduced_by_missing_data"] is False
    assert diagnostics["decision_impact"]["confirmation_created_by_missing_data"] is False


def test_report_exposure_is_offline_json_and_markdown_only() -> None:
    enriched = attach_contextual_diagnostics(
        _load_replay("btc_15m_expected_unknown_or_mixed_001.json")
    )
    rendered = markdown(enriched)

    assert "contextual_diagnostics" in enriched
    assert "Contextual diagnostics (offline / no signal)" in rendered
    assert "diagnostic version: 2.0.0" in rendered
    assert "generated for stage: ENGINE-TREND-29" in rendered
    assert "not observable fields:" in rendered
    assert "decision impact:" in rendered
    assert enriched["contextual_diagnostics"]["artifact_contract"]["outputs"] == (
        "offline_replay_json_and_markdown_only"
    )
    imported_by = []
    for path in (ROOT / "app").rglob("*.py"):
        if path.name in {"contextual_diagnostics.py", "offline_report_diagnostics.py"}:
            continue
        if "contextual_diagnostics" in path.read_text(encoding="utf-8"):
            imported_by.append(path)
    assert imported_by == []


def test_schema_validates_generated_and_partial_historical_diagnostics() -> None:
    schema = json.loads(
        (AUDIT / "ENGINE_TREND_29_CONTEXTUAL_DIAGNOSTICS_SCHEMA.json").read_text(
            encoding="utf-8"
        )
    )
    generated = diagnose_context(
        ContextualDiagnosticInput(
            symbol="TESTUSDT",
            timeframe="15m",
            as_of="2026-07-14T00:00:00Z",
            source_regime="UNKNOWN",
            source_confidence=0.2,
            last_close=100.0,
        )
    )
    historical = attach_contextual_diagnostics(
        _load_replay("btc_15m_expected_unknown_or_mixed_001.json")
    )["contextual_diagnostics"]

    _validate(generated, schema, schema)
    _validate(historical, schema, schema)
    assert "not_observable" in schema["$defs"]["diagnosticState"]["enum"]
    assert len(schema["$defs"]["diagnosticState"]["enum"]) == 5


def test_strong_looking_diagnostic_tags_do_not_mutate_decisions() -> None:
    payload = diagnose_context(
        ContextualDiagnosticInput(
            symbol="CONTROLUSDT",
            timeframe="15m",
            as_of="2026-07-14T00:00:00Z",
            source_regime="UNKNOWN",
            source_confidence=0.1,
            last_close=100.0,
            zones=(
                DiagnosticZone("SUPPORT", 99.9, 100.0, "control"),
                DiagnosticZone("RESISTANCE", 100.0, 100.1, "control"),
            ),
            indicator_direction="BULLISH",
            timeframe_regimes={"15m": "UNKNOWN", "1h": "UP", "4h": "DOWN"},
        )
    )
    expected = {
        "NEAR_SUPPORT",
        "NEAR_RESISTANCE",
        "HIGHER_TF_BULLISH_RISK",
        "HIGHER_TF_BEARISH_RISK",
        "INDICATOR_PRESSURE_WITHOUT_CAUSAL_TRIGGER",
    }

    assert expected <= set(payload["observed_tags"])
    assert payload["source_regime"] == "UNKNOWN"
    assert payload["action"] == "NO_ACTION"
    assert payload["safety"]["setup_created"] is False
    assert payload["safety"]["trade_signal_created"] is False


def test_offline_guard_rejects_decision_mutation() -> None:
    before = {"composer": {"regime": "UNKNOWN"}}
    after = {"composer": {"regime": "UP"}, "contextual_diagnostics": {"source_regime": "UP"}}
    with pytest.raises(RuntimeError, match="mutated the finalized artifact"):
        _assert_post_decision_invariants(before, after)


def test_machine_readable_audits_preserve_known_cases() -> None:
    cases = json.loads(
        (AUDIT / "ENGINE_TREND_29_KNOWN_CASES_AUDIT.json").read_text(encoding="utf-8")
    )
    safety = json.loads(
        (AUDIT / "ENGINE_TREND_29_NO_ACTION_SAFETY_AUDIT.json").read_text(encoding="utf-8")
    )

    assert len(cases["cases"]) == 4
    assert all(case["decision_changed"] is False for case in cases["cases"])
    assert all(case["setup_created"] is False for case in cases["cases"])
    assert all(case["trade_signal_created"] is False for case in cases["cases"])
    assert safety["observability_summary"]["cases_where_diagnostics_changed_decision"] == 0
    assert safety["observability_summary"]["cases_where_diagnostics_created_setup"] == 0
    assert safety["observability_summary"]["cases_where_diagnostics_created_trade_signal"] == 0
