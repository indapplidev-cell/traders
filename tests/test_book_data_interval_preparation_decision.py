from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import cli
from app.data_audit.interval_preparation_decision import (
    CONTRACT_VERSION,
    DECISION_15M_ONLY,
    FAIL,
    PASS,
    PASS_WITH_DATA_GAPS,
    RECOMMENDED_OPTION,
    IntervalPreparationDecisionBuilder,
    IntervalPreparationDecisionConfig,
    IntervalPreparationDecisionFormatter,
    build_json_payload,
    build_markdown,
    write_interval_preparation_decision_json,
    write_interval_preparation_decision_markdown,
)


def test_default_config_points_to_candle_availability_audit_json() -> None:
    assert IntervalPreparationDecisionConfig().audit_json_path == Path(
        "reports/book_data/candle_availability_audit.json"
    )


def test_default_output_json_points_to_interval_decision_json() -> None:
    assert IntervalPreparationDecisionConfig().output_json == Path(
        "reports/book_data/interval_data_preparation_decision.json"
    )


def test_default_output_md_points_to_interval_decision_md() -> None:
    assert IntervalPreparationDecisionConfig().output_md == Path(
        "reports/book_data/interval_data_preparation_decision.md"
    )


def test_missing_audit_json_makes_result_fail(tmp_path: Path) -> None:
    config = _config(tmp_path, audit_json_path=tmp_path / "missing.json")

    result = IntervalPreparationDecisionBuilder().run(config)

    assert result.status == FAIL
    assert "BOOK-DATA-01 audit artifact is missing" in result.errors[0]


def test_15m_ready_and_1h_4h_missing_gives_expected_decision(tmp_path: Path) -> None:
    result = _run_with_audit(tmp_path, _audit_payload())

    assert result.decision_id == DECISION_15M_ONLY


def test_active_intervals_contains_15m(tmp_path: Path) -> None:
    result = _run_with_audit(tmp_path, _audit_payload())

    assert "15m" in result.active_intervals


def test_missing_intervals_contains_1h_and_4h(tmp_path: Path) -> None:
    result = _run_with_audit(tmp_path, _audit_payload())

    assert result.missing_intervals == ("1h", "4h")


def test_optional_intervals_contains_1h_and_4h(tmp_path: Path) -> None:
    result = _run_with_audit(tmp_path, _audit_payload())

    assert result.optional_intervals == ("1h", "4h")


def test_recommended_option_is_hybrid_later(tmp_path: Path) -> None:
    result = _run_with_audit(tmp_path, _audit_payload())

    assert result.recommended_option == RECOMMENDED_OPTION


def test_not_approved_list_includes_forbidden_work(tmp_path: Path) -> None:
    result = _run_with_audit(tmp_path, _audit_payload())

    assert "binance_download" in result.not_approved
    assert "db_write" in result.not_approved
    assert "interval_aggregation" in result.not_approved
    assert "trading_logic" in result.not_approved


def test_json_writer_creates_output(tmp_path: Path) -> None:
    result = _run_with_audit(tmp_path, _audit_payload())
    output = tmp_path / "manual.json"

    path = write_interval_preparation_decision_json(
        IntervalPreparationDecisionConfig(output_json=output),
        result,
    )

    assert path == output
    assert output.is_file()


def test_json_contains_contract_version(tmp_path: Path) -> None:
    result = _run_with_audit(tmp_path, _audit_payload())
    payload = build_json_payload(result)

    assert payload["contract_version"] == CONTRACT_VERSION


def test_json_contains_safety_read_only_true(tmp_path: Path) -> None:
    result = _run_with_audit(tmp_path, _audit_payload())
    payload = build_json_payload(result)

    assert payload["safety"]["read_only"] is True


def test_json_contains_aggregation_approved_false(tmp_path: Path) -> None:
    result = _run_with_audit(tmp_path, _audit_payload())
    payload = build_json_payload(result)

    assert payload["safety"]["aggregation_approved"] is False


def test_markdown_writer_creates_output(tmp_path: Path) -> None:
    result = _run_with_audit(tmp_path, _audit_payload())
    output = tmp_path / "manual.md"

    path = write_interval_preparation_decision_markdown(
        IntervalPreparationDecisionConfig(output_md=output),
        result,
    )

    assert path == output
    assert output.is_file()


def test_markdown_contains_decision_section(tmp_path: Path) -> None:
    markdown = build_markdown(_run_with_audit(tmp_path, _audit_payload()))

    assert "## Decision" in markdown


def test_markdown_contains_options_considered_section(tmp_path: Path) -> None:
    markdown = build_markdown(_run_with_audit(tmp_path, _audit_payload()))

    assert "## Options Considered" in markdown


def test_markdown_contains_not_approved_section(tmp_path: Path) -> None:
    markdown = build_markdown(_run_with_audit(tmp_path, _audit_payload()))

    assert "## Not Approved In This Stage" in markdown


def test_markdown_contains_next_stage_section(tmp_path: Path) -> None:
    markdown = build_markdown(_run_with_audit(tmp_path, _audit_payload()))

    assert "## Next Stage" in markdown


def test_formatter_prints_recommended_option(tmp_path: Path) -> None:
    config = _config(tmp_path, show_details=True)
    result = _run_with_audit(tmp_path, _audit_payload(), config=config)

    output = IntervalPreparationDecisionFormatter().format(result, config=config)

    assert "Recommended option:" in output
    assert RECOMMENDED_OPTION in output


def test_formatter_prints_result(tmp_path: Path) -> None:
    config = _config(tmp_path)
    result = _run_with_audit(tmp_path, _audit_payload(), config=config)

    output = IntervalPreparationDecisionFormatter().format(result, config=config)

    assert "Result: PASS_WITH_DATA_GAPS" in output


def test_strict_mode_fail_when_requested_intervals_missing(tmp_path: Path) -> None:
    result = _run_with_audit(tmp_path, _audit_payload(), strict=True)

    assert result.status == FAIL


def test_default_mode_pass_with_data_gaps_when_requested_intervals_missing(tmp_path: Path) -> None:
    result = _run_with_audit(tmp_path, _audit_payload())

    assert result.status == PASS_WITH_DATA_GAPS


def test_all_intervals_ready_can_produce_pass(tmp_path: Path) -> None:
    result = _run_with_audit(tmp_path, _audit_payload(missing_intervals=()))

    assert result.status == PASS


def test_cli_parser_supports_audit_json() -> None:
    result = CliRunner().invoke(cli, ["book-data-interval-preparation-decision", "--help"])

    assert result.exit_code == 0
    assert "--audit-json" in result.stdout


def test_cli_parser_supports_output_json() -> None:
    result = CliRunner().invoke(cli, ["book-data-interval-preparation-decision", "--help"])

    assert result.exit_code == 0
    assert "--output-json" in result.stdout


def test_cli_parser_supports_output_md() -> None:
    result = CliRunner().invoke(cli, ["book-data-interval-preparation-decision", "--help"])

    assert result.exit_code == 0
    assert "--output-md" in result.stdout


def test_cli_parser_supports_strict() -> None:
    result = CliRunner().invoke(cli, ["book-data-interval-preparation-decision", "--help"])

    assert result.exit_code == 0
    assert "--strict" in result.stdout


def test_cli_parser_supports_show_details() -> None:
    result = CliRunner().invoke(cli, ["book-data-interval-preparation-decision", "--help"])

    assert result.exit_code == 0
    assert "--show-details" in result.stdout


def _run_with_audit(
    tmp_path: Path,
    payload: dict[str, object],
    *,
    config: IntervalPreparationDecisionConfig | None = None,
    strict: bool = False,
):
    active_config = config or _config(tmp_path, strict=strict)
    active_config.audit_json_path.write_text(json.dumps(payload), encoding="utf-8")
    return IntervalPreparationDecisionBuilder().run(active_config)


def _config(
    tmp_path: Path,
    *,
    audit_json_path: Path | None = None,
    strict: bool = False,
    show_details: bool = False,
) -> IntervalPreparationDecisionConfig:
    return IntervalPreparationDecisionConfig(
        audit_json_path=audit_json_path or tmp_path / "candle_availability_audit.json",
        output_json=tmp_path / "interval_data_preparation_decision.json",
        output_md=tmp_path / "interval_data_preparation_decision.md",
        strict=strict,
        show_details=show_details,
    )


def _audit_payload(*, missing_intervals: tuple[str, ...] = ("1h", "4h")) -> dict[str, object]:
    intervals = ("15m", "1h", "4h")
    rows = []
    for symbol in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
        for interval in intervals:
            status = "MISSING" if interval in missing_intervals else "READY"
            rows.append(
                {
                    "symbol": symbol,
                    "interval": interval,
                    "available_candles": 0 if status == "MISSING" else 1200,
                    "required_candles": 1200,
                    "status": status,
                }
            )
    return {
        "status": "PASS_WITH_DATA_GAPS" if missing_intervals else "PASS",
        "service": "BOOK_DATA_AUDIT",
        "report_type": "candle_availability_audit",
        "contract_version": "book_data_candle_availability_v1",
        "request": {
            "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            "intervals": list(intervals),
            "window_size": 300,
            "window_count": 4,
            "required_candles": 1200,
        },
        "rows": rows,
        "warnings": [],
        "errors": [],
    }
