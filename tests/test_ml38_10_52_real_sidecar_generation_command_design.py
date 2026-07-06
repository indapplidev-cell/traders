from pathlib import Path

from app.diagnostics.real_sidecar_generation_command_design import (
    build_read_only_real_sidecar_generation_command_design,
    read_only_real_sidecar_generation_command_design,
)


def test_design_block_and_readiness_are_design_only() -> None:
    design = read_only_real_sidecar_generation_command_design

    assert design["diagnostic_name"] == "read_only_real_sidecar_generation_command_design"
    assert design["diagnostic_version"] == "ml38.10.52"
    assert design["execution_mode"] == "DESIGN_ONLY_NO_QUICK_QUALITY_NO_TRAINING_NO_DB_WRITES"
    assert design["current_readiness_summary"]["readiness_status"] == "READY_FOR_DESIGN_ONLY_NOT_EXECUTION"
    assert design["current_readiness_summary"]["real_full_dataset_stream_exists"] is False


def test_command_candidates_are_blocked_and_require_approval() -> None:
    board = read_only_real_sidecar_generation_command_design["command_design_board"]

    assert 2 <= len(board) <= 3
    assert all(candidate["run_allowed_now"] is False for candidate in board)
    assert all(candidate["separate_user_approval_required"] is True for candidate in board)
    assert any(
        candidate["command_text"]
        == "python run_fv3_cached_tuning.py --quick-quality --quick-quality-symbol SOLUSDT"
        for candidate in board
    )
    preferred = board[0]
    assert preferred["currently_supported_by_code"] == "partial"
    assert preferred["requires_preflight_probe"] is True


def test_preflight_and_source_consistency_are_fail_closed() -> None:
    design = read_only_real_sidecar_generation_command_design
    checks = {item["check_name"] for item in design["preflight_checklist"]}

    assert {"git status clean", "logs outside repo", "user approval present"} <= checks
    contract = design["source_config_consistency_contract"]
    assert contract["mismatch_policy"] == "FAIL_CLOSED"
    examples = " | ".join(contract["forbidden_mix_examples"])
    assert "lv36 probability payload with lv31 candidate_result" in examples
    assert "test-only 973 predictions treated as full 6481 stream" in examples
    assert "ml_labels.direction_label treated as predicted_label" in examples


def test_artifact_and_post_run_contracts_block_on_failure() -> None:
    design = read_only_real_sidecar_generation_command_design
    required = set(design["expected_artifact_contract"]["required_files"])

    assert {
        "prediction_payloads/full_dataset_prediction_stream.jsonl",
        "prediction_payloads/full_dataset_prediction_stream_summary.json",
        "prediction_payloads/prediction_payload_schema.json",
    } <= required
    steps = design["post_run_validation_plan"]["steps"]
    assert len(steps) == 12
    assert all(step["blocks_next_stage_if_failed"] is True for step in steps)
    assert all("FAIL_CLOSED" in step["failure_action"] for step in steps)


def test_failure_approval_guardrail_and_decisions() -> None:
    design = read_only_real_sidecar_generation_command_design
    failures = design["failure_handling_plan"]
    approval = design["approval_gate_contract"]
    guardrail = design["real_stream_guardrail"]
    decisions = design["ml38_10_52_real_sidecar_generation_command_design_decision"]

    assert failures["default_policy"] == "FAIL_CLOSED"
    assert all(item["fail_closed"] is True for item in failures["scenarios"])
    assert approval["this_stage_allows_real_run"] is False
    assert approval["real_quick_quality_requires_separate_user_approval"] is True
    assert "quick-quality" in approval["disallowed_without_approval"]
    assert guardrail["real_full_dataset_prediction_stream_created"] is False
    assert guardrail["real_stream_row_count"] == 0
    assert "DESIGN_ONLY_NO_QUICK_QUALITY_EXECUTED" in decisions
    assert "REAL_FULL_6481_STREAM_NOT_CREATED" in decisions


def test_builder_is_pure_and_does_not_create_report_sidecars() -> None:
    reports = Path("reports")
    sidecar_names = {
        "full_dataset_prediction_stream.jsonl",
        "full_dataset_prediction_stream_summary.json",
        "prediction_payload_schema.json",
    }
    before = {path.resolve() for path in reports.rglob("*") if path.name in sidecar_names}

    design = build_read_only_real_sidecar_generation_command_design()

    after = {path.resolve() for path in reports.rglob("*") if path.name in sidecar_names}
    assert design["real_stream_guardrail"]["real_stream_row_count"] == 0
    assert after == before

