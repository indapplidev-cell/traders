from pathlib import Path

from app.diagnostics.real_sidecar_generation_preflight_probe import (
    build_read_only_real_sidecar_generation_preflight_probe,
    read_only_real_sidecar_generation_preflight_probe,
)


def test_preflight_block_is_present_and_execution_is_prohibited() -> None:
    probe = read_only_real_sidecar_generation_preflight_probe

    assert probe["diagnostic_name"] == "read_only_real_sidecar_generation_preflight_probe"
    assert probe["diagnostic_version"] == "ml38.10.53"
    assert probe["execution_mode"] == "PREFLIGHT_PROBE_ONLY_NO_QUICK_QUALITY_NO_TRAINING_NO_DB_WRITES"
    assert probe["preferred_command"] == (
        "python run_fv3_cached_tuning.py --quick-quality --quick-quality-symbol SOLUSDT"
    )
    assert probe["preflight_decision_gate"]["quick_quality_run_allowed_now"] is False


def test_entrypoint_flags_are_statically_detected() -> None:
    board = read_only_real_sidecar_generation_preflight_probe["entrypoint_probe_board"]
    by_name = {row["probe_name"]: row for row in board}

    assert by_name["--quick-quality flag supported or detected"]["status"] == "PASS"
    assert by_name["--quick-quality-symbol flag supported or detected"]["status"] == "PASS"
    assert by_name["15m interval is default or traceable"]["status"] == "PASS"
    assert by_name["output root under reports/feature_regime_experiments is traceable"]["status"] == "PASS"


def test_sidecar_wiring_is_nonblank_and_blocks_real_generation() -> None:
    probe = read_only_real_sidecar_generation_preflight_probe
    board = probe["sidecar_wiring_probe_board"]

    assert board
    assert all(row["status"] in {"WIRED", "PARTIAL", "NOT_WIRED", "UNKNOWN"} for row in board)
    runner = next(row for row in board if row["component"] == "run_fv3_cached_tuning.py")
    invocation = next(
        row for row in board if row["component"] == "exporter invocation at candidate artifact boundary"
    )
    assert runner["status"] == "NOT_WIRED"
    assert invocation["status"] == "NOT_WIRED"
    assert probe["preflight_decision_gate"]["preflight_probe_status"] == (
        "NOT_READY_SIDEСAR_WIRING_NOT_CONFIRMED"
    )


def test_full_dataset_boundary_is_not_claimed_proven() -> None:
    boundary = read_only_real_sidecar_generation_preflight_probe["full_dataset_boundary_probe"]

    assert boundary["expected_denominator_scope"] == "FULL_DATASET_6481"
    assert boundary["expected_reference_rows"] == 6481
    assert boundary["test_only_973_boundary_detected"] is True
    assert boundary["can_prove_future_export_will_be_6481"] is False
    assert boundary["status"] == "TEST_ONLY_BOUNDARY_RISK"


def test_compact_whitelist_accepts_only_approved_paths() -> None:
    whitelist = read_only_real_sidecar_generation_preflight_probe["compact_whitelist_probe"]
    checks = {row["path"]: row for row in whitelist["path_checks"]}

    assert whitelist["status"] == "PASS"
    for path in (
        "prediction_payloads/full_dataset_prediction_stream.jsonl",
        "prediction_payloads/full_dataset_prediction_stream_summary.json",
        "prediction_payloads/prediction_payload_schema.json",
        "prediction_payloads/test_prediction_stream.jsonl",
    ):
        assert checks[path]["expected_preserved"] is True
        assert checks[path]["observed_preserved"] is True
        assert checks[path]["status"] == "PASS"
    for path in (
        "prediction_payloads/raw_feature_dump.jsonl",
        "raw_features/features.jsonl",
        "credentials/token.json",
    ):
        assert checks[path]["expected_preserved"] is False
        assert checks[path]["observed_preserved"] is False
        assert checks[path]["status"] == "PASS"


def test_consistency_and_risks_are_fail_closed() -> None:
    probe = read_only_real_sidecar_generation_preflight_probe
    consistency = probe["source_config_consistency_probe"]
    risks = {row["risk"]: row for row in probe["risk_board"]}

    assert consistency["mismatch_policy"] == "FAIL_CLOSED"
    assert consistency["status"] == "CONSISTENCY_VALIDATION_PARTIAL"
    examples = " | ".join(consistency["forbidden_mix_examples"])
    assert "973-row test stream treated as 6481-row full stream" in examples
    assert "ml_labels.direction_label as predicted_label" in examples
    assert "only test rows are exported" in risks
    assert "source/config mismatch" in risks
    assert risks["only test rows are exported"]["blocks_real_generation_now"] is True
    assert risks["source/config mismatch"]["fail_closed_required"] is True


def test_guardrail_and_decisions_record_no_execution_or_stream() -> None:
    probe = read_only_real_sidecar_generation_preflight_probe
    guardrail = probe["real_stream_guardrail"]
    decisions = probe["decision"]

    assert guardrail["real_full_dataset_prediction_stream_created"] is False
    assert guardrail["real_stream_row_count"] == 0
    assert guardrail["sidecars_written_to_reports"] is False
    assert guardrail["quick_quality_executed"] is False
    assert guardrail["training_or_runtime_executed"] is False
    assert "DESIGN_ONLY_NO_QUICK_QUALITY_EXECUTED" in decisions
    assert "REAL_FULL_6481_STREAM_NOT_CREATED" in decisions
    assert "FULL_6481_CASCADE_NOT_ALLOWED_UNTIL_STREAM_EXISTS" in decisions
    assert "NOT_READY_FOR_REAL_GENERATION" in decisions


def test_builder_is_read_only_and_does_not_create_report_sidecars() -> None:
    reports = Path("reports")
    sidecar_names = {
        "full_dataset_prediction_stream.jsonl",
        "full_dataset_prediction_stream_summary.json",
        "prediction_payload_schema.json",
    }
    before = {path.resolve() for path in reports.rglob("*") if path.name in sidecar_names}

    rebuilt = build_read_only_real_sidecar_generation_preflight_probe()

    after = {path.resolve() for path in reports.rglob("*") if path.name in sidecar_names}
    assert rebuilt["real_stream_guardrail"]["real_stream_row_count"] == 0
    assert after == before

