from __future__ import annotations

import builtins
import json

import pytest
from typer.testing import CliRunner

import app.cli.commands as commands_module
from app.cli.commands import cli
from app.market_reader import api_readiness_review as review_module
from app.market_reader.api_readiness_review import (
    ApiReadinessCheck,
    ApiReadinessReviewFormatter,
    ApiReadinessReviewResult,
    ApiReadinessReviewer,
)


VALID_SAFETY = {
    "trade_signal": "NOT_EVALUATED",
    "safe_for_runtime_trading": False,
    "orders_enabled": False,
    "live_trading_connected": False,
    "traders_core_connected": False,
    "approved_for_live_trading": False,
    "approved_for_auto_activation": False,
    "model_training_executed": False,
    "binance_download_executed": False,
}


def test_api_readiness_check_created() -> None:
    check = ApiReadinessCheck(name="modules", status="PASS", message="ok")

    assert check.name == "modules"
    assert check.status == "PASS"
    assert check.message == "ok"
    assert check.severity == "INFO"


def test_review_result_freeze_candidate_true_when_no_fail() -> None:
    result = ApiReadinessReviewResult.from_checks(
        (
            ApiReadinessCheck(name="a", status="PASS", message="ok"),
            ApiReadinessCheck(name="b", status="WARN", severity="WARN", message="warning"),
        )
    )

    assert result.status == "WARN"
    assert result.freeze_candidate is True


def test_review_result_freeze_candidate_false_when_fail() -> None:
    result = ApiReadinessReviewResult.from_checks(
        (ApiReadinessCheck(name="a", status="FAIL", severity="ERROR", message="broken"),)
    )

    assert result.status == "FAIL"
    assert result.freeze_candidate is False


def test_reviewer_passes_with_required_files_and_valid_json(tmp_path) -> None:
    _create_project(tmp_path)

    result = ApiReadinessReviewer(project_root=tmp_path).run()

    assert result.status == "PASS"
    assert result.freeze_candidate is True


def test_missing_required_module_fails(tmp_path) -> None:
    _create_project(tmp_path)
    (tmp_path / "app/market_reader/json_export.py").unlink()

    result = ApiReadinessReviewer(project_root=tmp_path).run()

    assert _check(result, "market_reader_modules").status == "FAIL"
    assert result.freeze_candidate is False


def test_missing_required_test_fails(tmp_path) -> None:
    _create_project(tmp_path)
    (tmp_path / "tests/test_book_l1_json_consumer.py").unlink()

    result = ApiReadinessReviewer(project_root=tmp_path).run()

    assert _check(result, "book_l1_tests").status == "FAIL"
    assert result.freeze_candidate is False


def test_missing_planning_file_fails(tmp_path) -> None:
    _create_project(tmp_path)
    (tmp_path / "planning/02_CURRENT_TASK.md").unlink()

    result = ApiReadinessReviewer(project_root=tmp_path).run()

    assert _check(result, "planning_files").status == "FAIL"
    assert result.freeze_candidate is False


def test_missing_runtime_json_warns_not_fails(tmp_path) -> None:
    _create_project(tmp_path, write_json=False)

    result = ApiReadinessReviewer(project_root=tmp_path).run()

    assert result.status == "WARN"
    assert _check(result, "json_export_files").status == "WARN"
    assert result.freeze_candidate is True


def test_invalid_runtime_json_fails(tmp_path) -> None:
    _create_project(tmp_path)
    _write_text(tmp_path / "reports/book_l1/current_preview.json", "{")

    result = ApiReadinessReviewer(project_root=tmp_path).run()

    assert _check(result, "json_export_files").status == "FAIL"
    assert result.freeze_candidate is False


def test_wrong_contract_version_fails(tmp_path) -> None:
    _create_project(tmp_path)
    _write_report(tmp_path, "current_preview", contract_version="v0")

    result = ApiReadinessReviewer(project_root=tmp_path).run()

    assert _check(result, "json_contract").status == "FAIL"
    assert result.freeze_candidate is False


def test_wrong_service_fails(tmp_path) -> None:
    _create_project(tmp_path)
    _write_report(tmp_path, "current_preview", service="OTHER")

    result = ApiReadinessReviewer(project_root=tmp_path).run()

    assert _check(result, "json_contract").status == "FAIL"
    assert result.freeze_candidate is False


def test_missing_safety_fails(tmp_path) -> None:
    _create_project(tmp_path)
    envelope = _valid_envelope("current_preview")
    del envelope["safety"]
    _write_report_payload(tmp_path, "current_preview", envelope)

    result = ApiReadinessReviewer(project_root=tmp_path).run()

    assert _check(result, "json_contract").status == "FAIL"
    assert _check(result, "safety_contract").status == "FAIL"


def test_safe_for_runtime_trading_true_fails(tmp_path) -> None:
    _create_project(tmp_path)
    _write_report(tmp_path, "current_preview", safety={**VALID_SAFETY, "safe_for_runtime_trading": True})

    result = ApiReadinessReviewer(project_root=tmp_path).run()

    assert _check(result, "safety_contract").status == "FAIL"


def test_trade_signal_not_not_evaluated_fails(tmp_path) -> None:
    _create_project(tmp_path)
    _write_report(tmp_path, "current_preview", safety={**VALID_SAFETY, "trade_signal": "BUY"})

    result = ApiReadinessReviewer(project_root=tmp_path).run()

    assert _check(result, "safety_contract").status == "FAIL"


def test_formatter_shows_result() -> None:
    result = ApiReadinessReviewResult.from_checks((ApiReadinessCheck("modules", "PASS", "ok"),))

    output = ApiReadinessReviewFormatter().format(result)

    assert "Result: PASS" in output


def test_formatter_shows_freeze_candidate() -> None:
    result = ApiReadinessReviewResult.from_checks((ApiReadinessCheck("modules", "PASS", "ok"),))

    output = ApiReadinessReviewFormatter().format(result)

    assert "Freeze candidate: YES" in output


def test_formatter_shows_pass_warn_fail_checks() -> None:
    result = ApiReadinessReviewResult.from_checks(
        (
            ApiReadinessCheck("pass_check", "PASS", "ok"),
            ApiReadinessCheck("warn_check", "WARN", "warn", severity="WARN"),
            ApiReadinessCheck("fail_check", "FAIL", "fail", severity="ERROR"),
        )
    )

    output = ApiReadinessReviewFormatter().format(result)

    assert "PASS" in output
    assert "WARN" in output
    assert "FAIL" in output


def test_cli_help_contains_book_l1_api_readiness_review() -> None:
    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "book-l1-api-readiness-review" in result.stdout


def test_cli_command_smoke_does_not_run_market_analysis(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _create_project(tmp_path)

    def fail_get_session() -> object:
        raise AssertionError("api readiness review must not open a database session")

    def fail_input(prompt: str = "") -> str:
        raise AssertionError("api readiness review must not call input()")

    monkeypatch.setattr(commands_module, "get_session", fail_get_session)
    monkeypatch.setattr(builtins, "input", fail_input)

    result = CliRunner().invoke(cli, ["book-l1-api-readiness-review", "--project-root", str(tmp_path)])

    assert result.exit_code == 0
    assert "BOOK-L1 API Readiness Final Review" in result.stdout
    assert "Result: PASS" in result.stdout


def test_cli_strict_turns_warn_into_fail(tmp_path) -> None:
    _create_project(tmp_path, write_json=False)

    result = CliRunner().invoke(
        cli,
        ["book-l1-api-readiness-review", "--project-root", str(tmp_path), "--strict"],
    )

    assert result.exit_code == 1
    assert "Result: FAIL" in result.stdout
    assert "Freeze candidate: YES" in result.stdout


def test_cli_show_details_adds_details_section(tmp_path) -> None:
    _create_project(tmp_path)

    result = CliRunner().invoke(
        cli,
        ["book-l1-api-readiness-review", "--project-root", str(tmp_path), "--show-details"],
    )

    assert result.exit_code == 0
    assert "Details:" in result.stdout
    assert "Warnings:" in result.stdout
    assert "Errors:" in result.stdout


def _create_project(tmp_path, *, write_json: bool = True) -> None:
    for relative_path in (
        *review_module.REQUIRED_MARKET_READER_MODULES,
        *review_module.REQUIRED_BOOK_L1_TESTS,
        *review_module.REQUIRED_PLANNING_FILES,
    ):
        _write_text(tmp_path / relative_path, "# placeholder\n")

    commands = "\n".join(f'@cli.command("{command}")' for command in review_module.REQUIRED_CLI_COMMANDS)
    _write_text(tmp_path / "app/cli/commands.py", commands)

    if write_json:
        for report_type in review_module.STABLE_JSON_FILES:
            _write_report(tmp_path, report_type)


def _write_report(
    tmp_path,
    report_type: str,
    *,
    service: str = review_module.SERVICE_NAME,
    contract_version: str = review_module.CONTRACT_VERSION,
    safety: dict[str, object] | None = None,
) -> None:
    _write_report_payload(
        tmp_path,
        report_type,
        _valid_envelope(
            report_type,
            service=service,
            contract_version=contract_version,
            safety=safety,
        ),
    )


def _write_report_payload(tmp_path, report_type: str, payload: dict[str, object]) -> None:
    _write_text(
        tmp_path / review_module.STABLE_JSON_FILES[report_type],
        json.dumps(payload, ensure_ascii=False, indent=2),
    )


def _valid_envelope(
    report_type: str,
    *,
    service: str = review_module.SERVICE_NAME,
    contract_version: str = review_module.CONTRACT_VERSION,
    safety: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "status": "ok",
        "service": service,
        "report_type": report_type,
        "contract_version": contract_version,
        "request": {},
        "result": {},
        "summary": {},
        "safety": dict(VALID_SAFETY if safety is None else safety),
        "warnings": [],
        "errors": [],
    }


def _write_text(path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _check(result: ApiReadinessReviewResult, name: str) -> ApiReadinessCheck:
    return next(check for check in result.checks if check.name == name)
