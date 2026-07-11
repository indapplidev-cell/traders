from __future__ import annotations

import json

from typer.testing import CliRunner

from app.cli.commands import cli
from app.market_reader.json_consumer import (
    EXPECTED_CONTRACT_VERSION,
    EXPECTED_SERVICE,
    REPORT_TYPE_TO_FILENAME,
    REPORT_TYPE_TO_JSON_REPORT_TYPE,
    RuntimeJsonConsumer,
    RuntimeJsonConsumerConfig,
    RuntimeJsonConsumerFormatter,
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

VALID_ENVELOPE = {
    "status": "ok",
    "service": EXPECTED_SERVICE,
    "report_type": "current_preview",
    "contract_version": EXPECTED_CONTRACT_VERSION,
    "request": {},
    "result": {},
    "summary": {},
    "safety": VALID_SAFETY,
    "warnings": [],
    "errors": [],
}


def test_default_config_uses_reports_book_l1() -> None:
    assert RuntimeJsonConsumerConfig().input_dir.as_posix() == "reports/book_l1"


def test_default_report_types_are_current_multi_history_timeline() -> None:
    assert RuntimeJsonConsumerConfig().report_types == ("current", "multi", "history", "timeline")


def test_report_type_to_filename_mapping_is_stable() -> None:
    assert REPORT_TYPE_TO_FILENAME == {
        "current": "current_preview.json",
        "multi": "multi_preview.json",
        "history": "history_preview.json",
        "timeline": "timeline_preview.json",
    }


def test_valid_current_preview_json_passes(tmp_path) -> None:
    _write_valid_report(tmp_path, "current")

    check = _run_one(tmp_path, "current")

    assert check.status == "OK"
    assert check.api_readable is True


def test_valid_multi_preview_json_passes(tmp_path) -> None:
    _write_valid_report(tmp_path, "multi")

    check = _run_one(tmp_path, "multi")

    assert check.status == "OK"
    assert check.api_readable is True


def test_valid_history_preview_json_passes(tmp_path) -> None:
    _write_valid_report(tmp_path, "history")

    check = _run_one(tmp_path, "history")

    assert check.status == "OK"
    assert check.api_readable is True


def test_valid_timeline_preview_json_passes(tmp_path) -> None:
    _write_valid_report(tmp_path, "timeline")

    check = _run_one(tmp_path, "timeline")

    assert check.status == "OK"
    assert check.api_readable is True


def test_missing_file_returns_missing_and_not_api_readable(tmp_path) -> None:
    check = _run_one(tmp_path, "history")

    assert check.status == "MISSING"
    assert check.api_readable is False


def test_invalid_json_returns_invalid_json(tmp_path) -> None:
    (tmp_path / REPORT_TYPE_TO_FILENAME["current"]).write_text("{", encoding="utf-8")

    check = _run_one(tmp_path, "current")

    assert check.status == "INVALID_JSON"
    assert check.api_readable is False


def test_missing_top_level_required_key_returns_invalid_contract(tmp_path) -> None:
    envelope = _valid_envelope("current")
    del envelope["request"]
    _write_report(tmp_path, "current", envelope)

    check = _run_one(tmp_path, "current")

    assert check.status == "INVALID_CONTRACT"
    assert "missing top-level key: request" in check.validation_errors


def test_wrong_service_returns_invalid_contract(tmp_path) -> None:
    _write_report(tmp_path, "current", _valid_envelope("current", service="OTHER"))

    check = _run_one(tmp_path, "current")

    assert check.status == "INVALID_CONTRACT"


def test_wrong_contract_version_returns_invalid_contract(tmp_path) -> None:
    _write_report(tmp_path, "current", _valid_envelope("current", contract_version="v0"))

    check = _run_one(tmp_path, "current")

    assert check.status == "INVALID_CONTRACT"


def test_wrong_report_type_for_filename_returns_invalid_contract(tmp_path) -> None:
    _write_report(tmp_path, "current", _valid_envelope("timeline"))

    check = _run_one(tmp_path, "current")

    assert check.status == "INVALID_CONTRACT"


def test_warnings_not_list_returns_invalid_contract(tmp_path) -> None:
    envelope = _valid_envelope("current")
    envelope["warnings"] = "warning"
    _write_report(tmp_path, "current", envelope)

    check = _run_one(tmp_path, "current")

    assert check.status == "INVALID_CONTRACT"


def test_errors_not_list_returns_invalid_contract(tmp_path) -> None:
    envelope = _valid_envelope("current")
    envelope["errors"] = "error"
    _write_report(tmp_path, "current", envelope)

    check = _run_one(tmp_path, "current")

    assert check.status == "INVALID_CONTRACT"


def test_missing_safety_returns_invalid_contract(tmp_path) -> None:
    envelope = _valid_envelope("current")
    del envelope["safety"]
    _write_report(tmp_path, "current", envelope)

    check = _run_one(tmp_path, "current")

    assert check.status == "INVALID_CONTRACT"


def test_unsafe_trade_signal_returns_invalid_safety(tmp_path) -> None:
    check = _run_with_safety_override(tmp_path, "trade_signal", "BUY")

    assert check.status == "INVALID_SAFETY"


def test_safe_for_runtime_trading_true_returns_invalid_safety(tmp_path) -> None:
    check = _run_with_safety_override(tmp_path, "safe_for_runtime_trading", True)

    assert check.status == "INVALID_SAFETY"


def test_orders_enabled_true_returns_invalid_safety(tmp_path) -> None:
    check = _run_with_safety_override(tmp_path, "orders_enabled", True)

    assert check.status == "INVALID_SAFETY"


def test_live_trading_connected_true_returns_invalid_safety(tmp_path) -> None:
    check = _run_with_safety_override(tmp_path, "live_trading_connected", True)

    assert check.status == "INVALID_SAFETY"


def test_one_invalid_file_does_not_hide_valid_files(tmp_path) -> None:
    _write_valid_report(tmp_path, "current")
    _write_report(tmp_path, "timeline", _valid_envelope("timeline", service="OTHER"))

    result = RuntimeJsonConsumer().run(
        RuntimeJsonConsumerConfig(input_dir=tmp_path, report_types=("current", "timeline"))
    )

    assert [check.status for check in result.checks] == ["OK", "INVALID_CONTRACT"]
    assert result.summary["api_readable"] == 1


def test_summary_counts_checked_readable_missing_invalid_contract_invalid_safety(tmp_path) -> None:
    _write_valid_report(tmp_path, "current")
    _write_report(tmp_path, "history", _valid_envelope("history", service="OTHER"))
    _write_report(tmp_path, "timeline", _valid_envelope("timeline", safety={**VALID_SAFETY, "orders_enabled": True}))

    result = RuntimeJsonConsumer().run(
        RuntimeJsonConsumerConfig(input_dir=tmp_path, report_types=("current", "multi", "history", "timeline"))
    )

    assert result.summary["reports_checked"] == 4
    assert result.summary["api_readable"] == 1
    assert result.summary["missing"] == 1
    assert result.summary["invalid_contract"] == 1
    assert result.summary["invalid_safety"] == 1


def test_formatter_prints_table_columns(tmp_path) -> None:
    _write_valid_report(tmp_path, "current")
    result = RuntimeJsonConsumer().run(RuntimeJsonConsumerConfig(input_dir=tmp_path, report_types=("current",)))

    output = RuntimeJsonConsumerFormatter().format(result)

    assert "| Type" in output
    assert "| File" in output
    assert "| Contract" in output
    assert "| API OK" in output


def test_formatter_prints_pass_when_all_files_ok(tmp_path) -> None:
    for report_type in REPORT_TYPE_TO_FILENAME:
        _write_valid_report(tmp_path, report_type)

    result = RuntimeJsonConsumer().run(RuntimeJsonConsumerConfig(input_dir=tmp_path))
    output = RuntimeJsonConsumerFormatter().format(result)

    assert "Result: PASS" in output


def test_formatter_prints_fail_when_at_least_one_file_invalid(tmp_path) -> None:
    _write_valid_report(tmp_path, "current")

    result = RuntimeJsonConsumer().run(RuntimeJsonConsumerConfig(input_dir=tmp_path, report_types=("current", "multi")))
    output = RuntimeJsonConsumerFormatter().format(result)

    assert "Result: FAIL" in output


def test_show_details_prints_validation_errors(tmp_path) -> None:
    _write_report(tmp_path, "current", _valid_envelope("current", service="OTHER"))
    result = RuntimeJsonConsumer().run(RuntimeJsonConsumerConfig(input_dir=tmp_path, report_types=("current",)))

    output = RuntimeJsonConsumerFormatter().format(result, show_details=True)

    assert "Details:" in output
    assert "validation messages:" in output
    assert "service must be BOOK_L1_MARKET_READER" in output


def test_cli_help_contains_book_l1_json_consumer_smoke() -> None:
    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "book-l1-json-consumer-smoke" in result.stdout


def test_cli_command_supports_input_dir(tmp_path) -> None:
    _write_valid_report(tmp_path, "current")
    result = CliRunner().invoke(
        cli,
        ["book-l1-json-consumer-smoke", "--input-dir", str(tmp_path), "--report-types", "current"],
    )

    assert result.exit_code == 0
    assert "Input dir:" in result.stdout
    assert "Result: PASS" in result.stdout


def test_cli_command_supports_report_types(tmp_path) -> None:
    _write_valid_report(tmp_path, "current")
    _write_valid_report(tmp_path, "timeline")
    result = CliRunner().invoke(
        cli,
        [
            "book-l1-json-consumer-smoke",
            "--input-dir",
            str(tmp_path),
            "--report-types",
            "current,timeline",
        ],
    )

    assert result.exit_code == 0
    assert "current_preview.json" in result.stdout
    assert "timeline_preview.json" in result.stdout
    assert "multi_preview.json" not in result.stdout


def test_cli_command_supports_strict(tmp_path) -> None:
    result = CliRunner().invoke(
        cli,
        ["book-l1-json-consumer-smoke", "--input-dir", str(tmp_path), "--report-types", "current", "--strict"],
    )

    assert result.exit_code == 1
    assert "Result: FAIL" in result.stdout


def _run_one(tmp_path, report_type: str):
    result = RuntimeJsonConsumer().run(RuntimeJsonConsumerConfig(input_dir=tmp_path, report_types=(report_type,)))
    return result.checks[0]


def _run_with_safety_override(tmp_path, field_name: str, value: object):
    safety = {**VALID_SAFETY, field_name: value}
    _write_report(tmp_path, "current", _valid_envelope("current", safety=safety))
    return _run_one(tmp_path, "current")


def _write_valid_report(tmp_path, report_type: str) -> None:
    _write_report(tmp_path, report_type, _valid_envelope(report_type))


def _write_report(tmp_path, report_type: str, envelope: dict[str, object]) -> None:
    (tmp_path / REPORT_TYPE_TO_FILENAME[report_type]).write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _valid_envelope(
    report_type: str,
    *,
    service: str = EXPECTED_SERVICE,
    contract_version: str = EXPECTED_CONTRACT_VERSION,
    safety: dict[str, object] | None = None,
) -> dict[str, object]:
    envelope = dict(VALID_ENVELOPE)
    envelope["service"] = service
    envelope["contract_version"] = contract_version
    envelope["report_type"] = REPORT_TYPE_TO_JSON_REPORT_TYPE[report_type]
    envelope["safety"] = dict(VALID_SAFETY if safety is None else safety)
    envelope["warnings"] = []
    envelope["errors"] = []
    return envelope
