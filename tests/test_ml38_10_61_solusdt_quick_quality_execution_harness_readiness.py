from pathlib import Path

import run_solusdt_quick_quality_once as wrapper
from app.diagnostics.solusdt_quick_quality_execution_harness_readiness import (
    ALLOWED_COMMAND,
    EXECUTION_MODE,
    solusdt_quick_quality_execution_harness_readiness,
)


EXPECTED_COMMAND = (
    "python run_fv3_cached_tuning.py --quick-quality --quick-quality-symbol SOLUSDT"
)


def test_wrapper_and_diagnostic_identity() -> None:
    assert Path("run_solusdt_quick_quality_once.py").is_file()
    diagnostic = solusdt_quick_quality_execution_harness_readiness
    assert diagnostic["diagnostic_name"] == (
        "solusdt_quick_quality_execution_harness_readiness"
    )
    assert diagnostic["execution_mode"] == EXECUTION_MODE
    assert EXECUTION_MODE == (
        "NO_RUN_EXECUTION_HARNESS_DRY_RUN_NO_QUICK_QUALITY_NO_TRAINING_NO_DB_WRITES"
    )


def test_default_dry_run_prints_plan_without_subprocess(monkeypatch, capsys) -> None:
    def forbidden(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("dry-run must not use subprocess")

    monkeypatch.setattr(wrapper.subprocess, "run", forbidden)
    monkeypatch.setattr(wrapper.subprocess, "Popen", forbidden)
    assert wrapper.main([]) == 0
    output = capsys.readouterr().out
    assert EXPECTED_COMMAND in output
    assert "External log path template:" in output
    assert "Completion marker path template:" in output
    assert "Safety constraints:" in output
    assert "REAL QUICK-QUALITY WAS NOT RUN" in output


def test_execute_requires_both_explicit_flags(monkeypatch) -> None:
    calls = 0

    def fake_execute() -> int:
        nonlocal calls
        calls += 1
        return 37

    monkeypatch.setattr(wrapper, "execute_once", fake_execute)
    assert wrapper.main(["--execute"]) == 2
    assert calls == 0
    assert wrapper.main([wrapper.ACKNOWLEDGEMENT_FLAG]) == 0
    assert calls == 0
    assert wrapper.main(["--execute", wrapper.ACKNOWLEDGEMENT_FLAG]) == 37
    assert calls == 1


def test_exact_command_and_scope_guardrails() -> None:
    diagnostic = solusdt_quick_quality_execution_harness_readiness
    contract = diagnostic["wrapper_contract"]
    guardrail = diagnostic["command_scope_guardrail"]
    assert contract["default_mode"] == "dry-run"
    assert contract["execute_requires_explicit_flags"] is True
    assert ALLOWED_COMMAND == EXPECTED_COMMAND == wrapper.DISPLAY_COMMAND
    assert contract["allowed_symbol"] == "SOLUSDT"
    assert contract["allowed_interval"] == "15m"
    for key in (
        "btc_allowed",
        "eth_allowed",
        "multisymbol_allowed",
        "clean_allowed",
        "fast_allowed",
        "sequence_allowed",
        "cascade_outcome_allowed",
    ):
        assert contract[key] is False
    assert guardrail["only_solusdt_quick_quality_command_allowed"] is True
    assert guardrail["command_injection_disallowed"] is True
    assert guardrail["user_custom_symbols_disallowed"] is True


def test_external_logging_progress_and_exit_code_contract() -> None:
    diagnostic = solusdt_quick_quality_execution_harness_readiness
    logging = diagnostic["external_logging_contract"]
    safety = diagnostic["execute_mode_safety"]
    exit_code = diagnostic["exit_code_contract"]
    external_dir = logging["external_log_dir"].lower().replace("/", "\\")
    assert "\\reports\\" not in external_dir
    assert not external_dir.endswith("\\reports")
    assert logging["log_inside_repo_reports_allowed"] is False
    assert logging["completion_marker_json_required"] is True
    assert safety["progress_interval_minutes"] == 20
    assert safety["no_short_parent_timeout"] is True
    assert safety["fake_exit_code_forbidden"] is True
    assert exit_code["child_process_exit_code_captured"] is True
    assert exit_code["wrapper_returns_child_exit_code_on_execute"] is True
    assert exit_code["unknown_exit_code_policy"] == "fail-closed"


def test_no_run_real_artifact_guardrails_and_decision() -> None:
    diagnostic = solusdt_quick_quality_execution_harness_readiness
    artifact = diagnostic["real_artifact_guardrail"]
    assert artifact["quick_quality_executed_during_stage"] is False
    assert artifact["training_or_runtime_executed_during_stage"] is False
    assert artifact["db_writes_during_stage"] is False
    assert artifact["existing_real_artifacts_mutated"] is False
    assert artifact["new_real_sidecars_created"] is False
    assert artifact["new_zip_created"] is False
    gate = diagnostic["decision_gate"]
    assert gate["dry_run_validated"] is True
    assert gate["separate_user_approval_required_for_execute"] is True
    assert gate["decision"] == (
        "SOLUSDT_QUICK_QUALITY_EXECUTION_HARNESS_READY_NO_RUN"
    )
    assert gate["next_allowed_stage"].startswith("ML38.10.62")
