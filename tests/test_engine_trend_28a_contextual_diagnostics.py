from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.market_reader.engine_trend.contextual_diagnostics import (
    ContextualDiagnosticInput,
    DiagnosticTag,
    DiagnosticZone,
    diagnose_context,
)


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = (
    ROOT
    / "reports"
    / "engine_trend"
    / "engine_trend_28a_contextual_unknown_zone_diagnostics"
)


def _unknown(**overrides: object) -> ContextualDiagnosticInput:
    values: dict[str, object] = {
        "symbol": "TESTUSDT",
        "timeframe": "15m",
        "as_of": "2026-07-14T10:00:00Z",
        "source_regime": "UNKNOWN",
        "source_confidence": 0.25,
        "last_close": 100.0,
    }
    values.update(overrides)
    return ContextualDiagnosticInput(**values)  # type: ignore[arg-type]


def _assert_safe(payload: dict[str, object]) -> None:
    assert payload["action"] == "NO_ACTION"
    assert payload["source_regime"] == "UNKNOWN"
    safety = payload["safety"]
    assert isinstance(safety, dict)
    assert safety == {
        "source_regime_preserved": True,
        "setup_created": False,
        "trade_signal_created": False,
        "diagnostics_only": True,
    }


def test_unknown_source_regime_stays_unknown_and_tags_never_create_action() -> None:
    payload = diagnose_context(_unknown())
    _assert_safe(payload)
    assert DiagnosticTag.WAIT_FOR_CONFIRMATION.value in payload["diagnostic_tags"]
    assert DiagnosticTag.NO_ACTION.value in payload["diagnostic_tags"]


@pytest.mark.parametrize(
    ("zone", "expected", "forbidden_action"),
    [
        (DiagnosticZone("RESISTANCE", 100.1, 100.3, "pivot", 2), "NEAR_RESISTANCE", "SHORT"),
        (DiagnosticZone("SUPPORT", 99.7, 99.9, "pivot", 2), "NEAR_SUPPORT", "LONG"),
    ],
)
def test_near_zone_does_not_imply_trade(
    zone: DiagnosticZone, expected: str, forbidden_action: str
) -> None:
    payload = diagnose_context(_unknown(zones=(zone,), atr=1.0))
    _assert_safe(payload)
    assert expected in payload["diagnostic_tags"]
    assert payload["action"] != forbidden_action


def test_breakout_not_confirmed_blocks_long_but_does_not_create_short() -> None:
    payload = diagnose_context(
        _unknown(
            zones=(DiagnosticZone("RESISTANCE", 99.9, 100.2, "pivot_cluster", 3),),
            breakout_status="ATTEMPT",
            breakout_direction="UPWARD",
        )
    )
    _assert_safe(payload)
    assert "BREAKOUT_NOT_CONFIRMED" in payload["diagnostic_tags"]
    assert payload["action"] != "SHORT"


def test_higher_tf_bearish_risk_and_indicator_pressure_remain_no_action() -> None:
    payload = diagnose_context(
        _unknown(
            structure="SIDEWAYS_STRUCTURE",
            indicator_direction="BULLISH",
            bullish_votes=4,
            bearish_votes=1,
            timeframe_regimes={"15m": "UNKNOWN", "1h": "UNKNOWN", "4h": "DOWN"},
        )
    )
    _assert_safe(payload)
    assert "HIGHER_TF_BEARISH_RISK" in payload["diagnostic_tags"]
    assert "INDICATOR_PRESSURE_WITHOUT_CAUSAL_TRIGGER" in payload["diagnostic_tags"]
    assert payload["action"] != "SHORT"


def test_ethusdt_live_case_has_expected_context_without_signal() -> None:
    payload = json.loads(
        (REPORT_DIR / "ENGINE_TREND_28A_ETHUSDT_LIVE_CASE_DIAGNOSTIC.json").read_text(
            encoding="utf-8"
        )
    )
    expected = {
        "LOCAL_RANGE_UNCONFIRMED",
        "NEAR_RESISTANCE",
        "BREAKOUT_NOT_CONFIRMED",
        "HIGHER_TF_BEARISH_RISK",
        "WAIT_FOR_CONFIRMATION",
    }
    assert expected <= set(payload["diagnostic_tags"])
    _assert_safe(payload)


def _validate_schema_subset(instance: object, schema: dict[str, object], root: dict[str, object]) -> None:
    if "$ref" in schema:
        target: object = root
        for part in str(schema["$ref"]).removeprefix("#/").split("/"):
            assert isinstance(target, dict)
            target = target[part]
        assert isinstance(target, dict)
        _validate_schema_subset(instance, target, root)
        return
    if "oneOf" in schema:
        matches = 0
        for option in schema["oneOf"]:  # type: ignore[union-attr]
            try:
                _validate_schema_subset(instance, option, root)
            except (AssertionError, KeyError, TypeError):
                continue
            matches += 1
        assert matches == 1
        return
    if "const" in schema:
        assert instance == schema["const"]
    if "enum" in schema:
        assert instance in schema["enum"]  # type: ignore[operator]
    expected_type = schema.get("type")
    if isinstance(expected_type, list):
        if instance is None:
            assert "null" in expected_type
            return
        expected_type = next(item for item in expected_type if item != "null")
    type_map = {"object": dict, "array": list, "string": str, "number": (int, float), "integer": int, "null": type(None)}
    if expected_type:
        assert isinstance(instance, type_map[str(expected_type)])
    if expected_type == "object":
        assert isinstance(instance, dict)
        for key in schema.get("required", []):  # type: ignore[union-attr]
            assert key in instance
        properties = schema.get("properties", {})
        assert isinstance(properties, dict)
        for key, value in instance.items():
            if key in properties:
                _validate_schema_subset(value, properties[key], root)
    elif expected_type == "array":
        assert isinstance(instance, list)
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for item in instance:
                _validate_schema_subset(item, item_schema, root)


def test_schema_validates_sample_payload() -> None:
    schema = json.loads(
        (REPORT_DIR / "ENGINE_TREND_28A_CONTEXTUAL_DIAGNOSTICS_SCHEMA.json").read_text(
            encoding="utf-8"
        )
    )
    payload = json.loads(
        (REPORT_DIR / "ENGINE_TREND_28A_ETHUSDT_LIVE_CASE_DIAGNOSTIC.json").read_text(
            encoding="utf-8"
        )
    )
    _validate_schema_subset(payload, schema, schema)


def test_known_flat_range_is_context_only_and_creates_no_setup() -> None:
    payload = diagnose_context(
        ContextualDiagnosticInput(
            symbol="SOLUSDT",
            timeframe="15m",
            as_of="2026-07-08T23:45:00Z",
            source_regime="FLAT",
            source_confidence=0.6897,
            last_close=150.0,
            range_confirmed=True,
            range_lower=148.0,
            range_upper=152.0,
            confirmed_hypotheses=("CONFIRMED_RANGE",),
        )
    )
    assert payload["source_regime"] == "FLAT"
    assert payload["action"] == "NO_ACTION"
    assert "CONFIRMED_RANGE_CONTEXT" in payload["diagnostic_tags"]
    assert payload["safety"]["setup_created"] is False


def test_decision_record_forbids_profitability_or_paper_ready_status() -> None:
    record = json.loads(
        (REPORT_DIR / "ENGINE_TREND_28A_DECISION_RECORD.json").read_text(encoding="utf-8")
    )
    assert record["final_status"] == "ENGINE_TREND_28A_COMPLETED_CONTEXTUAL_DIAGNOSTICS"
    assert record["final_status"] not in {
        "PROFITABLE_SYSTEM_VALIDATED",
        "PAPER_TRADING_READY",
        "TRADING_SIGNAL_ENABLED",
    }
    assert record["diagnostics_only"] is True
