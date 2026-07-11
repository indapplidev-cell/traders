from __future__ import annotations

from pathlib import Path

from typer.main import get_command
from typer.testing import CliRunner

from app.cli.commands import cli
from app.integration.l1_l2_interval_answer_smoke import (
    DEFAULT_SYMBOLS,
    L1L2IntervalAnswerSmokeConfig,
    L1L2IntervalAnswerSmokeResult,
)
from app.integration.l1_l2_multi_interval_answer_smoke import (
    DEFAULT_INTERVALS,
    L1L2IntervalAnswerSummary,
    L1L2MultiIntervalAnswerSmokeConfig,
    L1L2MultiIntervalAnswerSmokeFormatter,
    L1L2MultiIntervalAnswerSmokeRunner,
    aggregate_interval_summaries,
    build_multi_interval_markdown,
)


def test_default_config_uses_symbols_btc_eth_sol() -> None:
    assert L1L2MultiIntervalAnswerSmokeConfig().symbols == DEFAULT_SYMBOLS


def test_default_intervals_are_15m_1h_4h() -> None:
    assert L1L2MultiIntervalAnswerSmokeConfig().intervals == DEFAULT_INTERVALS


def test_output_md_default_path() -> None:
    assert L1L2MultiIntervalAnswerSmokeConfig().output_md == Path(
        "reports/book_l2/l1_l2_multi_interval_answer.md"
    )


def test_formatter_prints_result() -> None:
    result = _multi_result((_summary("15m", "PASS"),), status="PASS")

    output = L1L2MultiIntervalAnswerSmokeFormatter().format(
        result,
        config=L1L2MultiIntervalAnswerSmokeConfig(intervals=("15m",)),
    )

    assert "Result: PASS" in output


def test_formatter_prints_interval_summary() -> None:
    result = _multi_result((_summary("15m", "PASS", overall_state="UNKNOWN"),), status="PASS")

    output = L1L2MultiIntervalAnswerSmokeFormatter().format(
        result,
        config=L1L2MultiIntervalAnswerSmokeConfig(intervals=("15m",)),
    )

    assert "Intervals:" in output
    assert "UNKNOWN" in output


def test_markdown_writer_creates_file(tmp_path: Path) -> None:
    config = L1L2MultiIntervalAnswerSmokeConfig(output_md=tmp_path / "answer.md", intervals=("15m", "1h"))

    result = L1L2MultiIntervalAnswerSmokeRunner(interval_runner=_FakeIntervalRunner()).run(config)

    assert result.passed
    assert config.output_md.is_file()


def test_markdown_contains_interval_summary() -> None:
    markdown = _markdown_for((_summary("15m", "PASS"),))

    assert "## Interval Summary" in markdown


def test_markdown_contains_actual_answers_by_interval() -> None:
    markdown = _markdown_for((_summary("15m", "PASS"),))

    assert "## Actual Answers By Interval" in markdown


def test_markdown_contains_cross_interval_observations() -> None:
    markdown = _markdown_for((_summary("15m", "PASS"),))

    assert "## Cross-Interval Observations" in markdown


def test_aggregation_counts_pass_fail_intervals() -> None:
    aggregation = aggregate_interval_summaries((_summary("15m", "PASS"), _summary("1h", "FAIL")))

    assert aggregation.pass_count == 1
    assert aggregation.fail_count == 1


def test_aggregation_detects_intervals_with_observation_candidates() -> None:
    aggregation = aggregate_interval_summaries(
        (_summary("15m", "PASS", observation=("BTCUSDT",)), _summary("1h", "PASS"))
    )

    assert aggregation.intervals_with_observation_candidates == ("15m",)


def test_aggregation_detects_intervals_with_all_symbols_skipped() -> None:
    aggregation = aggregate_interval_summaries(
        (_summary("15m", "PASS", skip=("BTCUSDT", "ETHUSDT"), symbol_count=2), _summary("1h", "PASS"))
    )

    assert aggregation.intervals_with_all_symbols_skipped == ("15m",)


def test_repeated_skip_candidates_calculated_correctly() -> None:
    aggregation = aggregate_interval_summaries(
        (
            _summary("15m", "PASS", skip=("BTCUSDT", "ETHUSDT")),
            _summary("1h", "PASS", skip=("BTCUSDT",)),
        )
    )

    assert aggregation.repeated_skip_candidates == ("BTCUSDT",)


def test_repeated_observation_candidates_calculated_correctly() -> None:
    aggregation = aggregate_interval_summaries(
        (
            _summary("15m", "PASS", observation=("SOLUSDT",)),
            _summary("1h", "PASS", observation=("SOLUSDT", "BTCUSDT")),
        )
    )

    assert aggregation.repeated_observation_candidates == ("SOLUSDT",)


def test_one_failed_interval_does_not_prevent_markdown_creation(tmp_path: Path) -> None:
    config = L1L2MultiIntervalAnswerSmokeConfig(output_md=tmp_path / "answer.md", intervals=("15m", "1h"))

    result = L1L2MultiIntervalAnswerSmokeRunner(
        interval_runner=_FakeIntervalRunner(fail_intervals={"1h"})
    ).run(config)

    assert result.status == "PASS_WITH_WARNINGS"
    assert len(result.intervals) == 2
    assert config.output_md.is_file()


def test_strict_mode_returns_fail_if_any_interval_fails(tmp_path: Path) -> None:
    config = L1L2MultiIntervalAnswerSmokeConfig(
        output_md=tmp_path / "answer.md",
        intervals=("15m", "1h"),
        strict=True,
    )

    result = L1L2MultiIntervalAnswerSmokeRunner(
        interval_runner=_FakeIntervalRunner(fail_intervals={"1h"})
    ).run(config)

    assert result.status == "FAIL"


def test_non_strict_mode_can_return_pass_with_warnings_if_some_interval_fails(tmp_path: Path) -> None:
    config = L1L2MultiIntervalAnswerSmokeConfig(output_md=tmp_path / "answer.md", intervals=("15m", "1h"))

    result = L1L2MultiIntervalAnswerSmokeRunner(
        interval_runner=_FakeIntervalRunner(fail_intervals={"1h"})
    ).run(config)

    assert result.status == "PASS_WITH_WARNINGS"


def test_forbidden_term_in_human_brief_makes_result_fail(tmp_path: Path) -> None:
    config = L1L2MultiIntervalAnswerSmokeConfig(output_md=tmp_path / "answer.md", intervals=("15m",))

    result = L1L2MultiIntervalAnswerSmokeRunner(
        interval_runner=_FakeIntervalRunner(brief_by_interval={"15m": "BUY_CONTEXT"})
    ).run(config)

    assert result.status == "FAIL"
    assert any("forbidden term" in error for error in result.errors)


def test_safety_unsafe_makes_result_fail(tmp_path: Path) -> None:
    config = L1L2MultiIntervalAnswerSmokeConfig(output_md=tmp_path / "answer.md", intervals=("15m",))

    result = L1L2MultiIntervalAnswerSmokeRunner(
        interval_runner=_FakeIntervalRunner(unsafe_intervals={"15m"})
    ).run(config)

    assert result.status == "FAIL"
    assert any("safety is not fail-closed" in error for error in result.errors)


def test_cli_parser_supports_intervals() -> None:
    result = CliRunner().invoke(cli, ["book-l1-l2-multi-interval-answer-smoke", "--help"])

    assert result.exit_code == 0
    assert "--intervals" in result.stdout


def test_cli_parser_supports_symbols() -> None:
    result = CliRunner().invoke(cli, ["book-l1-l2-multi-interval-answer-smoke", "--help"])

    assert result.exit_code == 0
    assert "--symbols" in result.stdout


def test_cli_parser_supports_symbol() -> None:
    result = CliRunner().invoke(cli, ["book-l1-l2-multi-interval-answer-smoke", "--help"])

    assert result.exit_code == 0
    assert "--symbol" in result.stdout


def test_cli_parser_supports_output_md() -> None:
    result = CliRunner().invoke(cli, ["book-l1-l2-multi-interval-answer-smoke", "--help"])

    assert result.exit_code == 0
    assert "--output-md" in result.stdout


def test_cli_parser_supports_continue_on_fail() -> None:
    command = get_command(cli).commands["book-l1-l2-multi-interval-answer-smoke"]

    assert any("--continue-on-fail" in parameter.opts for parameter in command.params)


class _FakeIntervalRunner:
    def __init__(
        self,
        *,
        fail_intervals: set[str] | None = None,
        unsafe_intervals: set[str] | None = None,
        brief_by_interval: dict[str, str] | None = None,
    ) -> None:
        self.fail_intervals = fail_intervals or set()
        self.unsafe_intervals = unsafe_intervals or set()
        self.brief_by_interval = brief_by_interval or {}

    def run(self, config: L1L2IntervalAnswerSmokeConfig) -> L1L2IntervalAnswerSmokeResult:
        status = "FAIL" if config.interval in self.fail_intervals else "PASS"
        errors = (f"Insufficient data for {config.interval}.",) if status == "FAIL" else ()
        payload = _l2_payload(
            brief=self.brief_by_interval.get(config.interval, "CLEAN_CONTEXT_AVAILABLE"),
            unsafe=config.interval in self.unsafe_intervals,
        )
        config.output_md.parent.mkdir(parents=True, exist_ok=True)
        config.output_md.write_text(f"# Interval {config.interval}\n", encoding="utf-8")
        return L1L2IntervalAnswerSmokeResult(
            status=status,
            output_md=config.output_md.as_posix(),
            errors=errors,
            l2_payload=payload,
        )


def _multi_result(
    summaries: tuple[L1L2IntervalAnswerSummary, ...],
    *,
    status: str,
):
    from app.integration.l1_l2_multi_interval_answer_smoke import L1L2MultiIntervalAnswerSmokeResult

    return L1L2MultiIntervalAnswerSmokeResult(
        status=status,
        output_md="reports/book_l2/l1_l2_multi_interval_answer.md",
        intervals=summaries,
        aggregation=aggregate_interval_summaries(summaries),
    )


def _markdown_for(summaries: tuple[L1L2IntervalAnswerSummary, ...]) -> str:
    result = _multi_result(summaries, status="PASS")
    return build_multi_interval_markdown(config=L1L2MultiIntervalAnswerSmokeConfig(), result=result)


def _summary(
    interval: str,
    status: str,
    *,
    overall_state: str = "UNKNOWN",
    observation: tuple[str, ...] = (),
    skip: tuple[str, ...] = (),
    symbol_count: int = 3,
) -> L1L2IntervalAnswerSummary:
    return L1L2IntervalAnswerSummary(
        interval=interval,
        status=status,
        overall_state=overall_state,
        brief="Observe-only context.",
        observation_candidates=observation,
        skip_candidates=skip,
        symbol_count=symbol_count,
        safety_status="LOCKED",
        safety=_safe_safety(),
    )


def _l2_payload(*, brief: str, unsafe: bool = False) -> dict[str, object]:
    safety = _safe_safety()
    if unsafe:
        safety["orders_enabled"] = True
    return {
        "status": "ok",
        "result": {
            "overall_state": "UNKNOWN",
            "symbols": [
                _symbol("BTCUSDT", rank=1, skip=False),
                _symbol("ETHUSDT", rank=None, skip=True),
                _symbol("SOLUSDT", rank=None, skip=True),
            ],
            "market_brief": {
                "brief_state": brief,
                "observation_candidates": [
                    _candidate("BTCUSDT", rank=1, skip=False, reason="Clean context."),
                ],
                "skip_candidates": [
                    _candidate("ETHUSDT", rank=None, skip=True, reason="Unknown context."),
                    _candidate("SOLUSDT", rank=None, skip=True, reason="Unknown context."),
                ],
                "key_points": ["Safety remains fail-closed."],
            },
        },
        "safety": safety,
    }


def _symbol(symbol: str, *, rank: int | None, skip: bool) -> dict[str, object]:
    return {
        "symbol": symbol,
        "current_regime": "UNKNOWN",
        "stability": "UNSTABLE" if skip else "STABLE",
        "last_transition": "NO_CHANGE",
        "bucket": "UNKNOWN" if skip else "CLEAN_TREND",
        "skip_candidate": skip,
        "context_quality_score": 0.2 if skip else 0.8,
        "context_quality_grade": "SKIP" if skip else "HIGH",
        "context_rank": rank,
    }


def _candidate(symbol: str, *, rank: int | None, skip: bool, reason: str) -> dict[str, object]:
    return {
        "symbol": symbol,
        "bucket": "UNKNOWN" if skip else "CLEAN_TREND",
        "context_quality_score": 0.2 if skip else 0.8,
        "quality_grade": "SKIP" if skip else "HIGH",
        "context_rank": rank,
        "skip_candidate": skip,
        "main_reason": reason,
    }


def _safe_safety() -> dict[str, object]:
    return {
        "trade_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": False,
        "orders_enabled": False,
        "live_trading_connected": False,
        "traders_core_connected": False,
        "approved_for_live_trading": False,
        "approved_for_auto_activation": False,
        "model_training_executed": False,
        "binance_download_executed": False,
        "observe_only": True,
    }
