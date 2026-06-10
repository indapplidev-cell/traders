import json

from app.gates.gate_policy_prediction_mapping_plan import (
    PLAN_NAME,
    PLAN_VERSION,
    DirectionMappingRule,
    PredictionMappingRule,
    PredictionPayloadMappingPlan,
)


def test_prediction_mapping_rule_to_dict() -> None:
    rule = PredictionMappingRule(
        target_field="confidence",
        source_fields=("confidence",),
        mapping_type="direct_float",
        required=True,
        description="Map confidence directly.",
        fallback="0.0",
    )

    payload = rule.to_dict()

    assert payload == {
        "target_field": "confidence",
        "source_fields": ["confidence"],
        "mapping_type": "direct_float",
        "required": True,
        "description": "Map confidence directly.",
        "fallback": "0.0",
    }


def test_direction_mapping_rule_to_dict() -> None:
    rule = DirectionMappingRule(
        output_direction="LONG",
        condition="prob_up is greatest",
        source_fields=("prob_up", "prob_down", "prob_flat"),
        description="Map bullish probability to LONG.",
    )

    payload = rule.to_dict()

    assert payload == {
        "output_direction": "LONG",
        "condition": "prob_up is greatest",
        "source_fields": ["prob_up", "prob_down", "prob_flat"],
        "description": "Map bullish probability to LONG.",
    }


def test_prediction_payload_mapping_plan_documents_required_and_optional_fields() -> None:
    plan = PredictionPayloadMappingPlan()

    assert plan.name == PLAN_NAME
    assert plan.version == PLAN_VERSION

    assert plan.required_target_fields == (
        "direction",
        "confidence",
        "tp_before_sl_probability",
        "regime",
    )

    assert plan.optional_target_fields == (
        "risk_score",
        "expected_move_atr",
        "model_version",
        "symbol",
        "interval",
    )

    assert plan.all_target_fields == (
        "direction",
        "confidence",
        "tp_before_sl_probability",
        "risk_score",
        "expected_move_atr",
        "regime",
        "model_version",
        "symbol",
        "interval",
    )


def test_prediction_payload_mapping_plan_documents_source_fields() -> None:
    plan = PredictionPayloadMappingPlan()

    assert plan.all_source_fields == (
        "confidence",
        "detected_regime",
        "expected_move_atr",
        "interval",
        "market_regime",
        "model_version",
        "prob_down",
        "prob_flat",
        "prob_up",
        "regime",
        "risk_score",
        "symbol",
        "tp_before_sl_probability",
    )


def test_prediction_payload_mapping_plan_finds_rule_by_target() -> None:
    plan = PredictionPayloadMappingPlan()

    direction_rule = plan.rule_for_target("direction")

    assert direction_rule is not None
    assert direction_rule.source_fields == ("prob_up", "prob_down", "prob_flat")
    assert direction_rule.mapping_type == "probability_argmax"
    assert direction_rule.required is True

    missing_rule = plan.rule_for_target("missing")

    assert missing_rule is None


def test_prediction_payload_mapping_plan_documents_direction_rules() -> None:
    plan = PredictionPayloadMappingPlan()

    directions = tuple(rule.output_direction for rule in plan.direction_rules)

    assert directions == (
        "LONG",
        "SHORT",
        "FLAT",
        "NONE",
    )

    long_rule = plan.direction_rules[0]
    short_rule = plan.direction_rules[1]
    flat_rule = plan.direction_rules[2]
    none_rule = plan.direction_rules[3]

    assert long_rule.source_fields == ("prob_up", "prob_down", "prob_flat")
    assert "prob_up" in long_rule.condition

    assert short_rule.source_fields == ("prob_up", "prob_down", "prob_flat")
    assert "prob_down" in short_rule.condition

    assert flat_rule.source_fields == ("prob_up", "prob_down", "prob_flat")
    assert "prob_flat" in flat_rule.condition

    assert none_rule.source_fields == ("prob_up", "prob_down", "prob_flat")
    assert "missing" in none_rule.condition


def test_prediction_payload_mapping_plan_to_dict_is_json_safe() -> None:
    plan = PredictionPayloadMappingPlan()

    payload = plan.to_dict()

    assert payload["name"] == "gate_policy_prediction_payload_mapping"
    assert payload["version"] == "ml19.1"

    assert payload["required_target_fields"] == [
        "direction",
        "confidence",
        "tp_before_sl_probability",
        "regime",
    ]

    assert payload["optional_target_fields"] == [
        "risk_score",
        "expected_move_atr",
        "model_version",
        "symbol",
        "interval",
    ]

    assert "prob_up" in payload["all_source_fields"]
    assert "prob_down" in payload["all_source_fields"]
    assert "prob_flat" in payload["all_source_fields"]
    assert "confidence" in payload["all_source_fields"]
    assert "tp_before_sl_probability" in payload["all_source_fields"]

    assert len(payload["mapping_rules"]) == 9
    assert len(payload["direction_rules"]) == 4

    assert payload["integration_status"]["prediction_service_imported"] is False
    assert payload["integration_status"]["predictor_imported"] is False
    assert payload["integration_status"]["database_connected"] is False
    assert payload["integration_status"]["model_inference_connected"] is False
    assert payload["integration_status"]["traders_core_connected"] is False
    assert payload["integration_status"]["live_trading_connected"] is False
    assert payload["integration_status"]["runtime_adapter_implemented"] is False

    json.dumps(payload, ensure_ascii=False)
