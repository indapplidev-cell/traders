from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import cli
from app.data_audit.market_reader_15m_stabilization import (
    CONTRACT_VERSION,
    DEFAULT_OUTPUT_JSON,
    DEFAULT_OUTPUT_MD,
    FAIL,
    PASS,
    PASS_WITH_WARNINGS,
    MarketReader15mStabilizationConfig,
    MarketReader15mStabilizationFormatter,
    MarketReader15mStabilizationResult,
    MarketReader15mStabilizationRunner,
    MarketReader15mStabilizationStep,
    build_json_payload,
    build_markdown,
    parse_stabilization_symbols,
    resolve_stabilization_status,
    validate_interval_policy,
    write_stabilization_json,
    write_stabilization_markdown,
)


def test_default_config_uses_symbols_btc_eth_sol() -> None:
    assert MarketReader15mStabilizationConfig().symbols == ("BTCUSDT", "ETHUSDT", "SOLUSDT")


def test_default_interval_is_15m() -> None:
    assert MarketReader15mStabilizationConfig().interval == "15m"


def test_default_output_json_path() -> None:
    assert MarketReader15mStabilizationConfig().output_json == DEFAULT_OUTPUT_JSON


def test_default_output_md_path() -> None:
    assert MarketReader15mStabilizationConfig().output_md == DEFAULT_OUTPUT_MD


def test_non_15m_interval_returns_fail(tmp_path: Path) -> None:
    result = _run(tmp_path, interval="1h")

    assert result.status == FAIL
    assert _step_status(result, "interval_policy_15m_only") == FAIL


def test_all_steps_pass_gives_result_pass(tmp_path: Path) -> None:
    result = _run(tmp_path)

    assert result.status == PASS


def test_failed_availability_gives_result_fail(tmp_path: Path) -> None:
    result = _run(tmp_path, fail_step="candle_availability_15m")

    assert result.status == FAIL


def test_failed_l1_consumer_gives_result_fail(tmp_path: Path) -> None:
    result = _run(tmp_path, fail_step="l1_json_consumer_strict")

    assert result.status == FAIL


def test_failed_l2_consumer_gives_result_fail(tmp_path: Path) -> None:
    result = _run(tmp_path, fail_step="l2_json_consumer_strict")

    assert result.status == FAIL


def test_failed_l2_readiness_gives_result_fail(tmp_path: Path) -> None:
    result = _run(tmp_path, fail_step="l2_api_readiness_strict")

    assert result.status == FAIL


def test_failed_interval_answer_smoke_gives_result_fail(tmp_path: Path) -> None:
    result = _run(tmp_path, fail_step="l1_l2_interval_answer_15m")

    assert result.status == FAIL


def test_unsafe_safety_gives_result_fail(tmp_path: Path) -> None:
    result = _run(tmp_path, unsafe=True)

    assert result.status == FAIL
    assert _step_status(result, "safety_fail_closed") == FAIL


def test_warnings_with_core_pass_can_return_pass_with_warnings(tmp_path: Path) -> None:
    result = _run(tmp_path, warnings=("stale optional 1h/4h gaps",))

    assert result.status == PASS_WITH_WARNINGS


def test_json_writer_creates_output(tmp_path: Path) -> None:
    config = _config(tmp_path)
    result = _result(config)

    path = write_stabilization_json(config, result)

    assert path == tmp_path / "market_reader_15m_stabilization.json"
    assert path.is_file()


def test_json_contains_contract_version(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = build_json_payload(config, _result(config))

    assert payload["contract_version"] == CONTRACT_VERSION


def test_json_contains_active_interval_15m(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = build_json_payload(config, _result(config))

    assert payload["decision"]["active_interval"] == "15m"


def test_json_contains_safety_safe_for_runtime_false(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = build_json_payload(config, _result(config))

    assert payload["safety"]["safe_for_runtime_trading"] is False


def test_markdown_writer_creates_output(tmp_path: Path) -> None:
    config = _config(tmp_path)
    result = _result(config)

    path = write_stabilization_markdown(config, result)

    assert path == tmp_path / "market_reader_15m_stabilization.md"
    assert path.is_file()


def test_markdown_contains_stabilization_checks(tmp_path: Path) -> None:
    markdown = build_markdown(_config(tmp_path), _result(_config(tmp_path)))

    assert "## Stabilization Checks" in markdown


def test_markdown_contains_actual_l2_answer_on_15m(tmp_path: Path) -> None:
    markdown = build_markdown(_config(tmp_path), _result(_config(tmp_path)))

    assert "## Actual L2 Answer On 15m" in markdown


def test_markdown_contains_safety(tmp_path: Path) -> None:
    markdown = build_markdown(_config(tmp_path), _result(_config(tmp_path)))

    assert "## Safety" in markdown


def test_markdown_contains_conclusion(tmp_path: Path) -> None:
    markdown = build_markdown(_config(tmp_path), _result(_config(tmp_path)))

    assert "## Conclusion" in markdown


def test_formatter_prints_result(tmp_path: Path) -> None:
    config = _config(tmp_path)
    output = MarketReader15mStabilizationFormatter().format(_result(config), config=config)

    assert "Result: PASS" in output


def test_formatter_prints_actual_l2_answer(tmp_path: Path) -> None:
    config = _config(tmp_path)
    output = MarketReader15mStabilizationFormatter().format(_result(config), config=config)

    assert "Actual L2 answer on 15m:" in output


def test_cli_parser_supports_symbols() -> None:
    assert _help_contains("--symbols")


def test_cli_parser_supports_symbol() -> None:
    assert _help_contains("--symbol")


def test_cli_parser_supports_interval() -> None:
    assert _help_contains("--interval")


def test_cli_parser_supports_output_json() -> None:
    assert _help_contains("--output-json")


def test_cli_parser_supports_output_md() -> None:
    assert _help_contains("--output-md")


def test_cli_parser_supports_strict() -> None:
    assert _help_contains("--strict")


def test_cli_parser_supports_show_details() -> None:
    assert _help_contains("--show-details")


def test_parse_symbols_supports_symbols_csv() -> None:
    assert parse_stabilization_symbols("btcusdt, ethusdt") == ("BTCUSDT", "ETHUSDT")


def test_parse_symbols_supports_symbol_option() -> None:
    assert parse_stabilization_symbols(None, ("solusdt",)) == ("SOLUSDT",)


def test_interval_policy_accepts_only_15m() -> None:
    assert validate_interval_policy("15m").status == PASS
    assert validate_interval_policy("4h").status == FAIL


def test_status_resolver_returns_fail_on_failed_step() -> None:
    assert resolve_stabilization_status((_step("x", FAIL),)) == FAIL


class _FakeServices:
    def __init__(
        self,
        *,
        fail_step: str | None = None,
        warnings: tuple[str, ...] = (),
        unsafe: bool = False,
    ) -> None:
        self.fail_step = fail_step
        self.warnings = warnings
        self.unsafe = unsafe

    def run_candle_availability(self, config: MarketReader15mStabilizationConfig):
        return self._step("candle_availability_15m", config.candle_audit_json)

    def check_interval_decision(self, config: MarketReader15mStabilizationConfig):
        step, warnings, errors = self._step("interval_preparation_decision", config.decision_json)
        return step, _decision_payload(), warnings, errors

    def run_l1_timeline_export(self, config: MarketReader15mStabilizationConfig):
        return self._step("l1_timeline_export_15m", config.l1_json_path)

    def run_l1_json_consumer(self, config: MarketReader15mStabilizationConfig):
        return self._step("l1_json_consumer_strict", None)

    def run_l2_context_export(self, config: MarketReader15mStabilizationConfig):
        _write_json(config.l2_json_path, _l2_payload(unsafe=self.unsafe))
        return self._step("l2_context_export_15m", config.l2_json_path)

    def run_l2_json_consumer(self, config: MarketReader15mStabilizationConfig):
        return self._step("l2_json_consumer_strict", config.l2_json_path)

    def run_l2_api_readiness(self, config: MarketReader15mStabilizationConfig):
        return self._step("l2_api_readiness_strict", None)

    def run_l1_l2_answer(self, config: MarketReader15mStabilizationConfig):
        return self._step("l1_l2_interval_answer_15m", config.l2_answer_md)

    def _step(self, name: str, path: Path | None):
        if self.fail_step == name:
            return _step(name, FAIL, path), (), (f"{name} failed",)
        return _step(name, PASS, path), self.warnings, ()


def _run(
    tmp_path: Path,
    *,
    interval: str = "15m",
    fail_step: str | None = None,
    warnings: tuple[str, ...] = (),
    unsafe: bool = False,
) -> MarketReader15mStabilizationResult:
    config = _config(tmp_path, interval=interval)
    services = _FakeServices(fail_step=fail_step, warnings=warnings, unsafe=unsafe)
    return MarketReader15mStabilizationRunner(services).run(config)


def _config(tmp_path: Path, *, interval: str = "15m") -> MarketReader15mStabilizationConfig:
    return MarketReader15mStabilizationConfig(
        interval=interval,
        output_json=tmp_path / "market_reader_15m_stabilization.json",
        output_md=tmp_path / "market_reader_15m_stabilization.md",
        stage_report=tmp_path / "book_data_03c_15m_only_market_reader_stabilization_report.md",
        candle_audit_json=tmp_path / "candle_availability_audit.json",
        candle_audit_md=tmp_path / "candle_availability_audit.md",
        decision_json=tmp_path / "interval_data_preparation_decision.json",
        l1_json_path=tmp_path / "timeline_preview.json",
        l2_json_path=tmp_path / "timeline_context.json",
        l2_answer_md=tmp_path / "l1_l2_interval_answer.md",
    )


def _result(config: MarketReader15mStabilizationConfig) -> MarketReader15mStabilizationResult:
    return MarketReader15mStabilizationResult(
        status=PASS,
        symbols=config.symbols,
        steps=(
            _step("interval_policy_15m_only", PASS),
            _step("candle_availability_15m", PASS, config.candle_audit_json),
            _step("evidence_written", PASS, config.output_json),
        ),
        output_json=config.output_json.as_posix(),
        output_md=config.output_md.as_posix(),
        l2_overall_state="UNKNOWN",
        observation_candidates=(),
        skip_candidates=("SOLUSDT",),
        decision={
            "active_interval": "15m",
            "decision_id": "ACTIVE_INTERVAL_15M_ONLY_WITH_1H_4H_MISSING",
            "recommended_option": "OPTION_D_HYBRID_LATER",
            "optional_missing_intervals": ["1h", "4h"],
            "source": config.decision_json.as_posix(),
        },
        l2_answer={
            "overall_state": "UNKNOWN",
            "brief": "NO_CLEAN_CONTEXT",
            "observation_candidates": [],
            "skip_candidates": ["SOLUSDT"],
            "evidence_path": config.l2_answer_md.as_posix(),
        },
        safety={
            "read_only": True,
            "download_executed": False,
            "db_write_executed": False,
            "aggregation_executed": False,
            "trading_signal": "NOT_EVALUATED",
            "safe_for_runtime_trading": False,
            "live_trading_connected": False,
        },
    )


def _step(name: str, status: str, path: Path | None = None) -> MarketReader15mStabilizationStep:
    return MarketReader15mStabilizationStep(
        name=name,
        status=status,
        message=f"{name} {status}",
        evidence_path=path.as_posix() if path else None,
    )


def _step_status(result: MarketReader15mStabilizationResult, name: str) -> str | None:
    for step in result.steps:
        if step.name == name:
            return step.status
    return None


def _help_contains(option: str) -> bool:
    result = CliRunner().invoke(cli, ["book-data-15m-stabilization", "--help"])
    return result.exit_code == 0 and option in result.stdout


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _decision_payload() -> dict[str, object]:
    return {
        "decision": {
            "decision_id": "ACTIVE_INTERVAL_15M_ONLY_WITH_1H_4H_MISSING",
            "recommended_option": "OPTION_D_HYBRID_LATER",
            "active_intervals": ["15m"],
            "missing_intervals": ["1h", "4h"],
            "optional_intervals": ["1h", "4h"],
            "required_intervals_for_current_market_reader": ["15m"],
        }
    }


def _l2_payload(*, unsafe: bool = False) -> dict[str, object]:
    return {
        "result": {
            "overall_state": "UNKNOWN",
            "market_brief": {
                "brief_state": "NO_CLEAN_CONTEXT",
                "observation_candidates": [],
                "skip_candidates": [{"symbol": "SOLUSDT"}],
                "key_points": ["Overall context is UNKNOWN."],
            },
            "symbols": [
                {
                    "symbol": "SOLUSDT",
                    "bucket": "UNKNOWN",
                    "context_quality_score": 0.1,
                    "context_quality_grade": "SKIP",
                    "context_rank": None,
                    "skip_candidate": True,
                }
            ],
        },
        "safety": {
            "trade_signal": "NOT_EVALUATED",
            "safe_for_runtime_trading": unsafe,
            "live_trading_connected": False,
            "orders_enabled": False,
            "traders_core_connected": False,
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
        },
    }
