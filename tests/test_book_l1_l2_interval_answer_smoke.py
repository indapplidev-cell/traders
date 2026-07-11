from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import cli
from app.integration.l1_l2_interval_answer_smoke import (
    DEFAULT_SYMBOLS,
    L1L2IntervalAnswerSmokeConfig,
    L1L2IntervalAnswerSmokeFormatter,
    L1L2IntervalAnswerSmokeResult,
    L1L2IntervalAnswerSmokeRunner,
    L1L2IntervalAnswerSmokeStep,
    parse_smoke_symbols,
)


def test_default_config_uses_requested_defaults() -> None:
    config = L1L2IntervalAnswerSmokeConfig()

    assert config.symbols == DEFAULT_SYMBOLS
    assert config.interval == "15m"
    assert config.window_size == 300
    assert config.window_count == 4
    assert config.min_candles == 50


def test_output_md_default_path() -> None:
    assert L1L2IntervalAnswerSmokeConfig().output_md == Path("reports/book_l2/l1_l2_interval_answer.md")


def test_formatter_prints_result_pass() -> None:
    result = L1L2IntervalAnswerSmokeResult(
        status="PASS",
        output_md="reports/book_l2/l1_l2_interval_answer.md",
        steps=(L1L2IntervalAnswerSmokeStep("L1 timeline export", "PASS", "ok"),),
    )

    output = L1L2IntervalAnswerSmokeFormatter().format(result, config=L1L2IntervalAnswerSmokeConfig())

    assert "Result: PASS" in output


def test_markdown_writer_creates_file(tmp_path: Path) -> None:
    config = _write_smoke_fixture(tmp_path)

    result = L1L2IntervalAnswerSmokeRunner().run(config, execute_pipeline=False)

    assert result.passed
    assert config.output_md.is_file()


def test_markdown_contains_request_interval(tmp_path: Path) -> None:
    config = _write_smoke_fixture(tmp_path, interval="1h")

    L1L2IntervalAnswerSmokeRunner().run(config, execute_pipeline=False)

    assert "| Interval | `1h` |" in config.output_md.read_text(encoding="utf-8")


def test_markdown_contains_actual_book_l2_answer_section(tmp_path: Path) -> None:
    config = _write_smoke_fixture(tmp_path)

    L1L2IntervalAnswerSmokeRunner().run(config, execute_pipeline=False)

    assert "## Actual BOOK-L2 Answer" in config.output_md.read_text(encoding="utf-8")


def test_markdown_contains_overall_state_from_l2_json(tmp_path: Path) -> None:
    config = _write_smoke_fixture(tmp_path)

    L1L2IntervalAnswerSmokeRunner().run(config, execute_pipeline=False)

    assert "Overall state: `MIXED`" in config.output_md.read_text(encoding="utf-8")


def test_markdown_contains_observation_candidates_from_l2_json(tmp_path: Path) -> None:
    config = _write_smoke_fixture(tmp_path)

    L1L2IntervalAnswerSmokeRunner().run(config, execute_pipeline=False)

    text = config.output_md.read_text(encoding="utf-8")
    assert "### Observation candidates" in text
    assert "- BTCUSDT" in text


def test_markdown_contains_skip_candidates_from_l2_json(tmp_path: Path) -> None:
    config = _write_smoke_fixture(tmp_path)

    L1L2IntervalAnswerSmokeRunner().run(config, execute_pipeline=False)

    text = config.output_md.read_text(encoding="utf-8")
    assert "### Skip candidates" in text
    assert "- SOLUSDT" in text


def test_markdown_contains_per_symbol_table(tmp_path: Path) -> None:
    config = _write_smoke_fixture(tmp_path)

    L1L2IntervalAnswerSmokeRunner().run(config, execute_pipeline=False)

    text = config.output_md.read_text(encoding="utf-8")
    assert "## Per-symbol Context" in text
    assert "| 1 | BTCUSDT | CLEAN_TREND | HIGH | 0.82 | false | UP | STABLE | NO_CHANGE | High quality clean context. |" in text


def test_markdown_contains_safety_section(tmp_path: Path) -> None:
    config = _write_smoke_fixture(tmp_path)

    L1L2IntervalAnswerSmokeRunner().run(config, execute_pipeline=False)

    text = config.output_md.read_text(encoding="utf-8")
    assert "## Safety" in text
    assert "safe_for_runtime_trading: `false`" in text


def test_missing_l1_json_makes_result_fail(tmp_path: Path) -> None:
    config = _write_smoke_fixture(tmp_path)
    config.l1_json_path.unlink()

    result = L1L2IntervalAnswerSmokeRunner().run(config, execute_pipeline=False)

    assert result.status == "FAIL"
    assert any(step.name == "L1 timeline export" and step.status == "FAIL" for step in result.steps)


def test_missing_l2_json_makes_result_fail(tmp_path: Path) -> None:
    config = _write_smoke_fixture(tmp_path)
    config.l2_json_path.unlink()

    result = L1L2IntervalAnswerSmokeRunner().run(config, execute_pipeline=False)

    assert result.status == "FAIL"
    assert any(step.name == "L2 context export" and step.status == "FAIL" for step in result.steps)


def test_symbol_propagation_mismatch_makes_result_fail(tmp_path: Path) -> None:
    config = _write_smoke_fixture(tmp_path, mutate_l2=lambda payload: payload["result"]["symbols"].pop())  # type: ignore[index]

    result = L1L2IntervalAnswerSmokeRunner().run(config, execute_pipeline=False)

    assert result.status == "FAIL"
    assert any(step.name == "Symbol propagation" and step.status == "FAIL" for step in result.steps)


def test_source_lineage_missing_makes_result_fail(tmp_path: Path) -> None:
    def mutate(payload: dict[str, object]) -> None:
        payload["source_report"] = "reports/book_l1/current_preview.json"
        payload["source"] = {"service": "BOOK_L1_MARKET_READER", "report_type": "current_preview"}

    config = _write_smoke_fixture(tmp_path, mutate_l2=mutate)

    result = L1L2IntervalAnswerSmokeRunner().run(config, execute_pipeline=False)

    assert result.status == "FAIL"
    assert any(step.name == "Source lineage" and step.status == "FAIL" for step in result.steps)


def test_unsafe_safety_makes_result_fail(tmp_path: Path) -> None:
    config = _write_smoke_fixture(tmp_path, mutate_l2=lambda payload: payload["safety"].update(orders_enabled=True))  # type: ignore[union-attr]

    result = L1L2IntervalAnswerSmokeRunner().run(config, execute_pipeline=False)

    assert result.status == "FAIL"
    assert any(step.name == "Fail-closed safety" and step.status == "FAIL" for step in result.steps)


def test_forbidden_term_in_brief_makes_result_fail(tmp_path: Path) -> None:
    config = _write_smoke_fixture(
        tmp_path,
        mutate_l2=lambda payload: payload["result"]["market_brief"].update(brief_state="BUY_CONTEXT"),  # type: ignore[index, union-attr]
    )

    result = L1L2IntervalAnswerSmokeRunner().run(config, execute_pipeline=False)

    assert result.status == "FAIL"
    assert any(step.name == "Forbidden terms" and step.status == "FAIL" for step in result.steps)


def test_fail_result_still_writes_markdown_with_failure_reason(tmp_path: Path) -> None:
    config = _write_smoke_fixture(tmp_path)
    config.l1_json_path.unlink()

    result = L1L2IntervalAnswerSmokeRunner().run(config, execute_pipeline=False)

    assert result.status == "FAIL"
    text = config.output_md.read_text(encoding="utf-8")
    assert "## Failure" in text
    assert "missing file" in text


def test_show_details_output_includes_brief_and_candidates(tmp_path: Path) -> None:
    config = _write_smoke_fixture(tmp_path, show_details=True)
    result = L1L2IntervalAnswerSmokeRunner().run(config, execute_pipeline=False)

    output = L1L2IntervalAnswerSmokeFormatter().format(result, config=config)

    assert "Brief: CLEAN_CONTEXT_AVAILABLE" in output
    assert "Observation candidates: BTCUSDT, ETHUSDT" in output
    assert "Skip candidates: SOLUSDT" in output


def test_cli_help_contains_symbols_option() -> None:
    result = CliRunner().invoke(cli, ["book-l1-l2-interval-answer-smoke", "--help"])

    assert result.exit_code == 0
    assert "--symbols" in result.stdout


def test_parse_symbols_supports_symbols() -> None:
    assert parse_smoke_symbols("btcusdt, ethusdt") == ("BTCUSDT", "ETHUSDT")


def test_parse_symbols_supports_symbol() -> None:
    assert parse_smoke_symbols(None, ("solusdt",)) == ("SOLUSDT",)


def test_cli_help_contains_interval_and_output_md_options() -> None:
    result = CliRunner().invoke(cli, ["book-l1-l2-interval-answer-smoke", "--help"])

    assert result.exit_code == 0
    assert "--interval" in result.stdout
    assert "--output-md" in result.stdout


def _write_smoke_fixture(
    tmp_path: Path,
    *,
    interval: str = "15m",
    show_details: bool = False,
    mutate_l2=None,
) -> L1L2IntervalAnswerSmokeConfig:
    l1_path = tmp_path / "reports/book_l1/timeline_preview.json"
    l2_path = tmp_path / "reports/book_l2/timeline_context.json"
    output_md = tmp_path / "reports/book_l2/l1_l2_interval_answer.md"
    _write_json(l1_path, _valid_l1_payload(interval=interval))
    l2_payload = _valid_l2_payload()
    if mutate_l2 is not None:
        mutate_l2(l2_payload)
    _write_json(l2_path, l2_payload)
    return L1L2IntervalAnswerSmokeConfig(
        interval=interval,
        output_md=output_md,
        l1_json_path=l1_path,
        l2_json_path=l2_path,
        show_details=show_details,
        run_api_readiness=False,
    )


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _valid_l1_payload(*, interval: str) -> dict[str, object]:
    return {
        "status": "ok",
        "service": "BOOK_L1_MARKET_READER",
        "report_type": "timeline_preview",
        "contract_version": "book_l1_json_export_v1",
        "request": {
            "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            "interval": interval,
            "window_size": 300,
            "window_count": 4,
            "min_candles": 50,
        },
        "result": {
            "rows": [
                _l1_row("BTCUSDT", "UP", "STABLE", "NO_CHANGE"),
                _l1_row("ETHUSDT", "FLAT", "STABLE", "NO_CHANGE"),
                _l1_row("SOLUSDT", "UNKNOWN", "UNSTABLE", "TO_UNKNOWN"),
            ]
        },
        "summary": {},
        "safety": _l1_safety(),
        "warnings": [],
        "errors": [],
    }


def _valid_l2_payload() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "BOOK_L2_MARKET_INTERPRETER",
        "report_type": "timeline_context",
        "contract_version": "book_l2_timeline_context_v1",
        "source_report": "reports/book_l1/timeline_preview.json",
        "source": {
            "service": "BOOK_L1_MARKET_READER",
            "report_type": "timeline_preview",
            "contract_version": "book_l1_json_export_v1",
            "input_path": "reports/book_l1/timeline_preview.json",
        },
        "result": {
            "overall_state": "MIXED",
            "symbols": [
                _l2_symbol("BTCUSDT", bucket="CLEAN_TREND", grade="HIGH", score=0.82, rank=1, skip=False, regime="UP"),
                _l2_symbol("ETHUSDT", bucket="STABLE_FLAT", grade="MEDIUM", score=0.61, rank=2, skip=False, regime="FLAT"),
                _l2_symbol("SOLUSDT", bucket="UNKNOWN", grade="SKIP", score=0.12, rank=None, skip=True, regime="UNKNOWN"),
            ],
            "summary": {
                "bucket_summary": {"CLEAN_TREND": 1, "STABLE_FLAT": 1, "UNKNOWN": 1},
                "quality_summary": {"HIGH": 1, "MEDIUM": 1, "LOW": 0, "SKIP": 1, "ERROR": 0},
                "top_ranked_symbols": ["BTCUSDT", "ETHUSDT"],
            },
            "market_context": {"overall_state": "MIXED", "symbol_count": 3},
            "market_brief": {
                "overall_state": "MIXED",
                "brief_state": "CLEAN_CONTEXT_AVAILABLE",
                "observation_candidates": [
                    _candidate("BTCUSDT", "CLEAN_TREND", "HIGH", 0.82, 1, False, "High quality clean context."),
                    _candidate("ETHUSDT", "STABLE_FLAT", "MEDIUM", 0.61, 2, False, "Stable flat context; observe only."),
                ],
                "skip_candidates": [
                    _candidate("SOLUSDT", "UNKNOWN", "SKIP", 0.12, None, True, "Unknown current regime."),
                ],
                "key_points": [
                    "Overall context is MIXED.",
                    "Best observation candidates: BTCUSDT, ETHUSDT.",
                    "Skip candidates: SOLUSDT.",
                    "Safety remains fail-closed: runtime action is not approved.",
                ],
                "warnings": [],
                "safety_note": "Observe-only context. Runtime action is not approved.",
            },
        },
        "safety": {
            "trade_signal": "NOT_EVALUATED",
            "safe_for_runtime_trading": False,
            "orders_enabled": False,
            "live_trading_connected": False,
            "traders_core_connected": False,
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "model_training_executed": False,
        },
        "warnings": [],
        "errors": [],
    }


def _l1_row(symbol: str, regime: str, stability: str, last_transition: str) -> dict[str, object]:
    return {
        "symbol": symbol,
        "status": "OK",
        "regimes": [regime, regime, regime, regime],
        "transitions": ["NO_CHANGE", "NO_CHANGE", last_transition],
        "last_transition": last_transition,
        "stability": stability,
        "current_confidence": 0.8,
        "current_trend_strength": "MODERATE",
        "trade_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": False,
        "windows": [],
        "warning": None,
    }


def _l2_symbol(
    symbol: str,
    *,
    bucket: str,
    grade: str,
    score: float,
    rank: int | None,
    skip: bool,
    regime: str,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "status": "OK",
        "current_regime": regime,
        "stability": "STABLE" if not skip else "UNSTABLE",
        "last_transition": "NO_CHANGE",
        "confidence": 0.8,
        "current_confidence": 0.8,
        "current_trend_strength": "MODERATE",
        "bucket": bucket,
        "skip_candidate": skip,
        "context_quality_score": score,
        "context_quality_grade": grade,
        "context_rank": rank,
        "context_quality_reason_codes": ["CONTEXT_QUALITY_SCORED"],
        "context_reason_codes": ["CONTEXT_RULE_MATCHED"],
        "trade_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": False,
        "context_label": bucket,
        "observe_reason": "observe only",
        "warnings": [],
    }


def _candidate(
    symbol: str,
    bucket: str,
    grade: str,
    score: float,
    rank: int | None,
    skip: bool,
    reason: str,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "bucket": bucket,
        "context_quality_score": score,
        "quality_grade": grade,
        "context_rank": rank,
        "skip_candidate": skip,
        "main_reason": reason,
    }


def _l1_safety() -> dict[str, object]:
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
    }
