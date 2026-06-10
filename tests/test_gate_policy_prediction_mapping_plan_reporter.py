import json

from app.gates.gate_policy_prediction_mapping_plan import (
    PredictionMappingRule,
    PredictionPayloadMappingPlan,
)
from app.gates.gate_policy_prediction_mapping_plan_reporter import (
    GatePolicyPredictionMappingPlanReporter,
)


def test_mapping_plan_reporter_builds_full_plan_dict() -> None:
    reporter = GatePolicyPredictionMappingPlanReporter()

    payload = reporter.plan_to_dict()

    assert payload["name"] == "gate_policy_prediction_payload_mapping"
    assert payload["version"] == "ml19.1"

    assert payload["required_target_count"] == 4
    assert payload["optional_target_count"] == 5
    assert payload["all_target_count"] == 9
    assert payload["all_source_count"] == 13
    assert payload["mapping_rule_count"] == 9
    assert payload["direction_rule_count"] == 4

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

    assert payload["mapping_rules"][0]["target_field"] == "direction"
    assert payload["mapping_rules"][0]["mapping_type"] == "probability_argmax"

    assert payload["direction_rules"][0]["output_direction"] == "LONG"
    assert payload["direction_rules"][1]["output_direction"] == "SHORT"
    assert payload["direction_rules"][2]["output_direction"] == "FLAT"
    assert payload["direction_rules"][3]["output_direction"] == "NONE"

    assert payload["integration_status"]["prediction_service_imported"] is False
    assert payload["integration_status"]["predictor_imported"] is False
    assert payload["integration_status"]["database_connected"] is False
    assert payload["integration_status"]["model_inference_connected"] is False
    assert payload["integration_status"]["traders_core_connected"] is False
    assert payload["integration_status"]["live_trading_connected"] is False
    assert payload["integration_status"]["runtime_adapter_implemented"] is False


def test_mapping_plan_reporter_builds_summary_dict() -> None:
    reporter = GatePolicyPredictionMappingPlanReporter()

    payload = reporter.summary_to_dict()

    assert payload["name"] == "gate_policy_prediction_payload_mapping"
    assert payload["version"] == "ml19.1"

    assert payload["required_target_count"] == 4
    assert payload["optional_target_count"] == 5
    assert payload["all_target_count"] == 9
    assert payload["all_source_count"] == 13
    assert payload["mapping_rule_count"] == 9
    assert payload["direction_rule_count"] == 4

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

    assert payload["direction_outputs"] == [
        "LONG",
        "SHORT",
        "FLAT",
        "NONE",
    ]

    assert "mapping_rules" not in payload
    assert "direction_rules" not in payload
    assert "all_target_fields" not in payload

    assert payload["integration_status"]["runtime_adapter_implemented"] is False


def test_mapping_plan_reporter_supports_custom_plan() -> None:
    reporter = GatePolicyPredictionMappingPlanReporter()

    plan = PredictionPayloadMappingPlan(
        mapping_rules=(
            PredictionMappingRule(
                target_field="confidence",
                source_fields=("confidence",),
                mapping_type="direct_float",
                required=True,
                description="Custom confidence mapping.",
                fallback="0.0",
            ),
            PredictionMappingRule(
                target_field="model_version",
                source_fields=("model_version",),
                mapping_type="metadata_traceability",
                required=False,
                description="Custom model_version mapping.",
                fallback=None,
            ),
        ),
    )

    payload = reporter.plan_to_dict(plan)

    assert payload["required_target_count"] == 1
    assert payload["optional_target_count"] == 1
    assert payload["all_target_count"] == 2
    assert payload["all_source_count"] == 2
    assert payload["mapping_rule_count"] == 2
    assert payload["direction_rule_count"] == 4

    assert payload["required_target_fields"] == ["confidence"]
    assert payload["optional_target_fields"] == ["model_version"]
    assert payload["all_source_fields"] == ["confidence", "model_version"]


def test_mapping_plan_reporter_converts_full_plan_to_json() -> None:
    reporter = GatePolicyPredictionMappingPlanReporter()

    json_payload = reporter.plan_to_json()
    payload = json.loads(json_payload)

    assert payload["name"] == "gate_policy_prediction_payload_mapping"
    assert payload["version"] == "ml19.1"
    assert payload["required_target_count"] == 4
    assert payload["optional_target_count"] == 5
    assert payload["mapping_rule_count"] == 9
    assert payload["direction_rule_count"] == 4
    assert payload["mapping_rules"][0]["target_field"] == "direction"
    assert payload["direction_rules"][0]["output_direction"] == "LONG"


def test_mapping_plan_reporter_converts_summary_to_json() -> None:
    reporter = GatePolicyPredictionMappingPlanReporter()

    json_payload = reporter.summary_to_json()
    payload = json.loads(json_payload)

    assert payload["name"] == "gate_policy_prediction_payload_mapping"
    assert payload["version"] == "ml19.1"
    assert payload["direction_outputs"] == ["LONG", "SHORT", "FLAT", "NONE"]
    assert payload["integration_status"]["runtime_adapter_implemented"] is False
    assert "mapping_rules" not in payload


def test_mapping_plan_reporter_supports_compact_full_json() -> None:
    reporter = GatePolicyPredictionMappingPlanReporter()

    json_payload = reporter.plan_to_json(indent=None)

    assert "\n" not in json_payload

    payload = json.loads(json_payload)

    assert payload["name"] == "gate_policy_prediction_payload_mapping"
    assert payload["mapping_rule_count"] == 9


def test_mapping_plan_reporter_supports_compact_summary_json() -> None:
    reporter = GatePolicyPredictionMappingPlanReporter()

    json_payload = reporter.summary_to_json(indent=None)

    assert "\n" not in json_payload

    payload = json.loads(json_payload)

    assert payload["name"] == "gate_policy_prediction_payload_mapping"
    assert payload["direction_outputs"] == ["LONG", "SHORT", "FLAT", "NONE"]

