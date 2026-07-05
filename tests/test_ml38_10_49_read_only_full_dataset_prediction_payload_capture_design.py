from app.diagnostics.full_dataset_prediction_payload_capture_design import (
    build_capture_point_options_board,
    build_compact_profile_whitelist_design,
    build_current_prediction_payload_inventory,
    build_full_dataset_guardrail,
    build_implementation_plan,
    build_leakage_and_guardrail_contract,
    build_read_only_full_dataset_prediction_payload_capture_design_audit,
    build_required_full_dataset_prediction_stream_contract,
)


def test_inventory_marks_973_as_test_only_and_zero_full_rows_as_blocker() -> None:
    inventory = build_current_prediction_payload_inventory()
    calibrated = inventory["discovered_prediction_sources"][0]

    assert inventory["test_prediction_rows_found"] == 973
    assert inventory["dataset_prediction_rows_found"] == 0
    assert calibrated["usable_for_test_only"] is True
    assert calibrated["usable_for_full_dataset"] is False
    assert inventory["current_status"] == "BLOCKED_FULL_DATASET_PREDICTION_STREAM_MISSING"


def test_contract_requires_6481_unique_keys_and_separates_target() -> None:
    contract = build_required_full_dataset_prediction_stream_contract()
    rules = " | ".join(contract["validation_rules"])

    assert contract["required_row_count"] == 6481
    assert contract["required_join_key"] == "symbol+interval+candle_open_time"
    assert "exactly 6481 unique join keys" in rules
    assert "ml_labels.direction_label" in contract["forbidden_fields_as_prediction"]
    assert "predicted_label" in contract["required_prediction_fields"]
    assert any("actual_label" in item and "never prediction" in item for item in contract["optional_actual_label_fields"])


def test_capture_options_recommend_sidecar_and_never_allow_db_write_now() -> None:
    options = build_capture_point_options_board()
    sidecar = next(row for row in options if row["option_id"] == "F")
    database = next(row for row in options if row["option_id"] == "E")

    assert "sidecar JSON/JSONL" in sidecar["capture_point"]
    assert sidecar["recommended"] is True
    assert sidecar["requires_db_write"] is False
    assert database["requires_db_write"] is True
    assert database["recommended"] is False


def test_compact_whitelist_keeps_stream_summary_and_schema() -> None:
    design = build_compact_profile_whitelist_design()
    payloads = design["payloads_to_whitelist"]

    assert "full_dataset_prediction_stream.jsonl" in payloads
    assert "full_dataset_prediction_stream_summary.json" in payloads
    assert "prediction_payload_schema.json" in payloads


def test_leakage_guardrail_fails_closed_when_stream_is_missing() -> None:
    contract = build_leakage_and_guardrail_contract()

    assert contract["actual_label_substitution_allowed"] is False
    assert "FAIL_CLOSED_IF_PREDICTED_LABEL_STREAM_MISSING" in contract["decisions"]
    assert "DO_NOT_BUILD_FULL_6481_CASCADE_WITHOUT_FULL_PREDICTIONS" in contract["decisions"]


def test_implementation_plan_requires_separate_approval() -> None:
    plan = build_implementation_plan()

    assert plan["recommended_next_stage_name"].startswith("ML38.10.50")
    assert plan["future_capture_requires_separate_approval"] is True
    assert any("separate user approval" in step for step in plan["implementation_steps"])


def test_full_dataset_guardrail_forbids_cascade_and_outcome_now() -> None:
    guardrail = build_full_dataset_guardrail()

    assert guardrail["full_dataset_cascade_allowed_now"] is False
    assert guardrail["full_dataset_outcome_allowed_now"] is False
    assert guardrail["db_writes_allowed_now"] is False
    assert guardrail["actual_label_substitution_allowed"] is False


def test_audit_contains_required_design_only_decisions() -> None:
    audit = build_read_only_full_dataset_prediction_payload_capture_design_audit()
    decisions = audit["ml38_10_49_payload_capture_design_decision"]

    assert audit["diagnostic_name"] == "read_only_full_dataset_prediction_payload_capture_design_audit"
    assert "DESIGN_ONLY_NO_CAPTURE_EXECUTED" in decisions
    assert "FULL_6481_PREDICTION_STREAM_MISSING" in decisions
    assert "FUTURE_CAPTURE_REQUIRES_SEPARATE_APPROVAL" in decisions


def test_builders_accept_synthetic_denominators_without_database() -> None:
    audit = build_read_only_full_dataset_prediction_payload_capture_design_audit(
        test_prediction_rows_found=2,
        dataset_prediction_rows_found=0,
        full_dataset_feature_rows=5,
        split_total_rows=5,
    )

    assert audit["current_prediction_payload_inventory"]["test_prediction_rows_found"] == 2
    assert audit["required_full_dataset_prediction_stream_contract"]["required_row_count"] == 5
    assert audit["full_dataset_guardrail"]["full_dataset_prediction_rows_found"] == 0
