from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import cli
from app.market_interpreter.flat_context_integration_review import (
    CONTRACT_VERSION,
    DEFAULT_OUTPUT_JSON,
    DEFAULT_OUTPUT_MD,
    FAIL,
    PASS,
    PASS_WITH_INTEGRATION_WARNINGS,
    FlatContextIntegrationReviewConfig,
    FlatContextIntegrationReviewFormatter,
    FlatContextIntegrationReviewRunner,
    build_json_payload,
    build_markdown,
    parse_flat_context_integration_symbols,
    write_flat_context_integration_review_json,
    write_flat_context_integration_review_markdown,
)


def test_default_config_uses_btc_eth_sol() -> None:
    assert FlatContextIntegrationReviewConfig().symbols == ("BTCUSDT", "ETHUSDT", "SOLUSDT")


def test_default_interval_is_15m() -> None:
    assert FlatContextIntegrationReviewConfig().interval == "15m"


def test_default_high_confidence_threshold_is_080() -> None:
    assert FlatContextIntegrationReviewConfig().high_confidence_threshold == 0.80


def test_default_output_json_is_flat_context_integration_review_json() -> None:
    assert FlatContextIntegrationReviewConfig().output_json == DEFAULT_OUTPUT_JSON


def test_default_output_md_is_flat_context_integration_review_md() -> None:
    assert FlatContextIntegrationReviewConfig().output_md == DEFAULT_OUTPUT_MD


def test_non_15m_interval_returns_fail(tmp_path: Path) -> None:
    result = FlatContextIntegrationReviewRunner().run(_write_fixture(tmp_path, interval="1h"))

    assert result.status == FAIL
    assert "stabilized 15m workflow" in result.errors[0]


def test_missing_l1_timeline_json_returns_fail(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    config.l1_timeline_json.unlink()

    result = FlatContextIntegrationReviewRunner().run(config)

    assert result.status == FAIL
    assert "timeline_preview.json" in result.errors[0]


def test_missing_l2_context_json_returns_fail(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    config.l2_context_json.unlink()

    result = FlatContextIntegrationReviewRunner().run(config)

    assert result.status == FAIL
    assert "timeline_context.json" in result.errors[0]


def test_missing_implementation_json_returns_fail(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    config.implementation_json.unlink()

    result = FlatContextIntegrationReviewRunner().run(config)

    assert result.status == FAIL
    assert "flat_context_handling_implementation.json" in result.errors[0]


def test_high_confidence_flat_with_flat_context_passes(tmp_path: Path) -> None:
    result = FlatContextIntegrationReviewRunner().run(_write_fixture(tmp_path))

    assert result.symbols[0].passed is True
    assert result.symbols[0].l2_bucket == "FLAT_CONTEXT"


def test_high_confidence_flat_with_unknown_fails(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path, mutate_l2=lambda payload: payload["result"]["symbols"][0].update(bucket="UNKNOWN"))  # type: ignore[index, union-attr]

    result = FlatContextIntegrationReviewRunner().run(config)

    assert result.status == FAIL
    assert "FAIL_HIGH_CONFIDENCE_FLAT_NOT_FLAT_CONTEXT" in result.symbols[0].findings


def test_unknown_remains_unknown_passes(tmp_path: Path) -> None:
    result = FlatContextIntegrationReviewRunner().run(_write_fixture(tmp_path))

    assert result.symbols[2].l1_market_regime == "UNKNOWN"
    assert result.symbols[2].l2_bucket == "UNKNOWN"
    assert result.symbols[2].passed is True


def test_unknown_mapped_to_flat_context_fails(tmp_path: Path) -> None:
    def mutate(payload: dict[str, object]) -> None:
        payload["result"]["symbols"][2].update(bucket="FLAT_CONTEXT")  # type: ignore[index, union-attr]

    result = FlatContextIntegrationReviewRunner().run(_write_fixture(tmp_path, mutate_l2=mutate))

    assert result.status == FAIL
    assert "FAIL_UNKNOWN_BECAME_FLAT_CONTEXT" in result.symbols[2].findings


def test_flat_context_observation_candidate_true_fails(tmp_path: Path) -> None:
    def mutate(payload: dict[str, object]) -> None:
        payload["result"]["market_brief"]["observation_candidates"] = [{"symbol": "BTCUSDT"}]  # type: ignore[index]

    result = FlatContextIntegrationReviewRunner().run(_write_fixture(tmp_path, mutate_l2=mutate))

    assert result.status == FAIL
    assert "FAIL_FLAT_CONTEXT_OBSERVATION_CANDIDATE" in result.symbols[0].findings


def test_flat_context_skip_candidate_false_fails_unless_explicitly_allowed(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path, mutate_l2=lambda payload: payload["result"]["symbols"][0].update(skip_candidate=False))  # type: ignore[index, union-attr]

    result = FlatContextIntegrationReviewRunner().run(config)

    assert result.status == FAIL
    assert "FAIL_FLAT_CONTEXT_NOT_SKIP_CANDIDATE" in result.symbols[0].findings


def test_flat_context_safe_for_runtime_trading_true_fails(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path, mutate_l2=lambda payload: payload["result"]["symbols"][0].update(safe_for_runtime_trading=True))  # type: ignore[index, union-attr]

    result = FlatContextIntegrationReviewRunner().run(config)

    assert result.status == FAIL
    assert "FAIL_FLAT_CONTEXT_RUNTIME_SAFETY_TRUE" in result.symbols[0].findings


def test_trade_signal_other_than_not_evaluated_fails(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path, mutate_l2=lambda payload: payload["result"]["symbols"][0].update(trade_signal="BUY"))  # type: ignore[index, union-attr]

    result = FlatContextIntegrationReviewRunner().run(config)

    assert result.status == FAIL
    assert "FAIL_TRADE_SIGNAL_CHANGED" in result.symbols[0].findings


def test_missing_interval_answer_evidence_can_be_warning_or_fail_in_strict_mode(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    config.interval_answer_md.unlink()

    warning_result = FlatContextIntegrationReviewRunner().run(config)
    strict_result = FlatContextIntegrationReviewRunner().run(FlatContextIntegrationReviewConfig(**{**config.__dict__, "strict": True}))

    assert warning_result.status == PASS_WITH_INTEGRATION_WARNINGS
    assert strict_result.status == FAIL


def test_missing_multi_interval_evidence_can_be_warning_or_fail_in_strict_mode(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    config.multi_interval_answer_md.unlink()

    warning_result = FlatContextIntegrationReviewRunner().run(config)
    strict_result = FlatContextIntegrationReviewRunner().run(FlatContextIntegrationReviewConfig(**{**config.__dict__, "strict": True}))

    assert warning_result.status == PASS_WITH_INTEGRATION_WARNINGS
    assert strict_result.status == FAIL


def test_multi_interval_1h_4h_missing_data_is_accepted_as_documented_condition(tmp_path: Path) -> None:
    result = FlatContextIntegrationReviewRunner().run(_write_fixture(tmp_path))

    check = _check(result, "multi_interval_1h_4h_missing_data_documented")
    assert check.status == PASS


def test_all_checks_pass_returns_pass(tmp_path: Path) -> None:
    assert FlatContextIntegrationReviewRunner().run(_write_fixture(tmp_path)).status == PASS


def test_non_critical_missing_optional_evidence_returns_pass_with_warnings(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    config.multi_interval_answer_md.unlink()

    result = FlatContextIntegrationReviewRunner().run(config)

    assert result.status == PASS_WITH_INTEGRATION_WARNINGS


def test_json_writer_creates_output(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = FlatContextIntegrationReviewRunner().run(config)

    assert write_flat_context_integration_review_json(config, result).is_file()


def test_json_contains_contract_version(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = FlatContextIntegrationReviewRunner().run(config)

    assert build_json_payload(config, result)["contract_version"] == CONTRACT_VERSION


def test_json_contains_checks(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = FlatContextIntegrationReviewRunner().run(config)

    assert build_json_payload(config, result)["checks"]


def test_json_contains_downstream_section(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = FlatContextIntegrationReviewRunner().run(config)

    assert "downstream" in build_json_payload(config, result)


def test_markdown_writer_creates_output(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = FlatContextIntegrationReviewRunner().run(config)

    assert write_flat_context_integration_review_markdown(config, result).is_file()


def test_markdown_contains_integration_checks(tmp_path: Path) -> None:
    assert "## Integration Checks" in _markdown(tmp_path)


def test_markdown_contains_symbol_review(tmp_path: Path) -> None:
    assert "## Symbol Review" in _markdown(tmp_path)


def test_markdown_contains_downstream_review(tmp_path: Path) -> None:
    assert "## Downstream Review" in _markdown(tmp_path)


def test_markdown_contains_safety(tmp_path: Path) -> None:
    assert "## Safety" in _markdown(tmp_path)


def test_formatter_prints_result(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = FlatContextIntegrationReviewRunner().run(config)

    assert "Result:" in FlatContextIntegrationReviewFormatter().format(result, config=config)


def test_formatter_prints_integration_checks(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = FlatContextIntegrationReviewRunner().run(config)

    assert "Integration checks:" in FlatContextIntegrationReviewFormatter().format(result, config=config)


def test_formatter_prints_symbol_table(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = FlatContextIntegrationReviewRunner().run(config)

    assert "Symbols:" in FlatContextIntegrationReviewFormatter().format(result, config=config)


def test_cli_parser_supports_symbols() -> None:
    assert _help_contains("--symbols")


def test_cli_parser_supports_symbol() -> None:
    assert _help_contains("--symbol")


def test_cli_parser_supports_interval() -> None:
    assert _help_contains("--interval")


def test_cli_parser_supports_high_confidence_threshold() -> None:
    assert _help_contains("--high-confidence-threshold")


def test_cli_parser_supports_l1_timeline_json() -> None:
    assert _help_contains("--l1-timeline-json")


def test_cli_parser_supports_l2_context_json() -> None:
    assert _help_contains("--l2-context-json")


def test_cli_parser_supports_implementation_json() -> None:
    assert _help_contains("--implementation-json")


def test_cli_parser_supports_interval_answer_md() -> None:
    assert _help_contains("--interval-answer-md")


def test_cli_parser_supports_multi_interval_answer_md() -> None:
    assert _help_contains("--multi-interval-answer-md")


def test_cli_parser_supports_output_json() -> None:
    assert _help_contains("--output-json")


def test_cli_parser_supports_output_md() -> None:
    assert _help_contains("--output-md")


def test_cli_parser_supports_strict() -> None:
    assert _help_contains("--strict")


def test_cli_parser_supports_show_details() -> None:
    assert _help_contains("--show-details")


def test_parse_symbols_supports_symbols() -> None:
    assert parse_flat_context_integration_symbols("btcusdt, ethusdt") == ("BTCUSDT", "ETHUSDT")


def test_parse_symbols_supports_symbol() -> None:
    assert parse_flat_context_integration_symbols(None, ("solusdt",)) == ("SOLUSDT",)


def _write_fixture(
    tmp_path: Path,
    *,
    interval: str = "15m",
    mutate_l2=None,
    mutate_interval_answer=None,
    mutate_multi_interval_answer=None,
) -> FlatContextIntegrationReviewConfig:
    l1_path = tmp_path / "reports/book_l1/timeline_preview.json"
    l2_path = tmp_path / "reports/book_l2/timeline_context.json"
    implementation_path = tmp_path / "reports/book_l2/flat_context_handling_implementation.json"
    interval_md = tmp_path / "reports/book_l2/l1_l2_interval_answer.md"
    multi_md = tmp_path / "reports/book_l2/l1_l2_multi_interval_answer.md"
    output_json = tmp_path / "reports/book_l2/flat_context_integration_review.json"
    output_md = tmp_path / "reports/book_l2/flat_context_integration_review.md"

    _write_json(l1_path, _l1_payload(interval=interval))
    l2_payload = _l2_payload()
    if mutate_l2 is not None:
        mutate_l2(l2_payload)
    _write_json(l2_path, l2_payload)
    _write_json(implementation_path, _implementation_payload(interval=interval))
    interval_text = _interval_answer_text()
    multi_text = _multi_interval_answer_text()
    if mutate_interval_answer is not None:
        interval_text = mutate_interval_answer(interval_text)
    if mutate_multi_interval_answer is not None:
        multi_text = mutate_multi_interval_answer(multi_text)
    interval_md.parent.mkdir(parents=True, exist_ok=True)
    interval_md.write_text(interval_text, encoding="utf-8")
    multi_md.write_text(multi_text, encoding="utf-8")

    return FlatContextIntegrationReviewConfig(
        symbols=("BTCUSDT", "ETHUSDT", "SOLUSDT"),
        interval=interval,
        l1_timeline_json=l1_path,
        l2_context_json=l2_path,
        implementation_json=implementation_path,
        interval_answer_md=interval_md,
        multi_interval_answer_md=multi_md,
        output_json=output_json,
        output_md=output_md,
    )


def _l1_payload(*, interval: str = "15m") -> dict[str, object]:
    return {
        "status": "ok",
        "service": "BOOK_L1_MARKET_READER",
        "report_type": "timeline_preview",
        "contract_version": "book_l1_json_export_v1",
        "request": {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"], "interval": interval},
        "result": {
            "rows": [
                _l1_row("BTCUSDT", "FLAT", 0.94),
                _l1_row("ETHUSDT", "FLAT", 0.87),
                _l1_row("SOLUSDT", "UNKNOWN", 0.0),
            ]
        },
        "safety": _safety(),
        "warnings": [],
        "errors": [],
    }


def _l1_row(symbol: str, regime: str, confidence: float) -> dict[str, object]:
    return {
        "symbol": symbol,
        "status": "OK",
        "regimes": [regime],
        "current_confidence": confidence,
        "windows": [{"label": "Current", "market_regime": regime, "confidence": confidence}],
    }


def _l2_payload() -> dict[str, object]:
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
            "overall_state": "RANGING",
            "symbols": [
                _l2_symbol("BTCUSDT", "FLAT", 0.94, "FLAT_CONTEXT"),
                _l2_symbol("ETHUSDT", "FLAT", 0.87, "FLAT_CONTEXT"),
                _l2_symbol("SOLUSDT", "UNKNOWN", 0.0, "UNKNOWN", reason_codes=["CURRENT_REGIME_UNKNOWN", "SKIP_CANDIDATE_CONTEXT"]),
            ],
            "summary": {"bucket_summary": {"FLAT_CONTEXT": 2, "UNKNOWN": 1}, "quality_summary": {}, "top_ranked_symbols": []},
            "market_context": {"overall_state": "RANGING", "symbol_count": 3},
            "market_brief": {
                "overall_state": "RANGING",
                "brief_state": "FLAT_HEAVY_CONTEXT",
                "observation_candidates": [],
                "skip_candidates": [
                    _brief("SOLUSDT", "UNKNOWN", "Unknown current regime."),
                    _brief("BTCUSDT", "FLAT_CONTEXT", "High-confidence L1 FLAT preserved as non-directional observe-only context."),
                    _brief("ETHUSDT", "FLAT_CONTEXT", "High-confidence L1 FLAT preserved as non-directional observe-only context."),
                ],
                "key_points": [
                    "Overall context is RANGING.",
                    "No clean observation candidates found.",
                    "High-confidence L1 FLAT is preserved as FLAT_CONTEXT.",
                ],
                "warnings": [],
                "safety_note": "Observe-only context. Runtime action is not approved.",
            },
        },
        "safety": _safety(),
        "warnings": [],
        "errors": [],
    }


def _l2_symbol(
    symbol: str,
    regime: str,
    confidence: float,
    bucket: str,
    *,
    reason_codes: list[str] | None = None,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "status": "OK",
        "current_regime": regime,
        "stability": "CHANGING" if regime == "FLAT" else "UNSTABLE",
        "last_transition": "NO_CHANGE" if regime == "FLAT" else "TO_UNKNOWN",
        "confidence": confidence,
        "current_confidence": confidence,
        "current_trend_strength": "NONE" if regime == "FLAT" else "UNKNOWN",
        "bucket": bucket,
        "skip_candidate": True,
        "context_quality_score": 0.5 if bucket == "FLAT_CONTEXT" else 0.0,
        "context_quality_grade": "MEDIUM" if bucket == "FLAT_CONTEXT" else "SKIP",
        "context_rank": None,
        "context_quality_reason_codes": ["CONTEXT_QUALITY_SCORED"],
        "context_reason_codes": reason_codes
        or [
            "L1_FLAT_HIGH_CONFIDENCE",
            "FLAT_CONTEXT_PRESERVED",
            "NON_DIRECTIONAL_CONTEXT",
            "NOT_TRADING_SIGNAL",
            "SKIP_CANDIDATE_CONTEXT",
        ],
        "trade_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": False,
        "context_label": bucket,
        "observe_reason": "observe only",
        "warnings": [],
    }


def _brief(symbol: str, bucket: str, reason: str) -> dict[str, object]:
    return {
        "symbol": symbol,
        "bucket": bucket,
        "context_quality_score": 0.5 if bucket == "FLAT_CONTEXT" else 0.0,
        "quality_grade": "MEDIUM" if bucket == "FLAT_CONTEXT" else "SKIP",
        "context_rank": None,
        "skip_candidate": True,
        "main_reason": reason,
    }


def _implementation_payload(*, interval: str = "15m") -> dict[str, object]:
    return {
        "status": "PASS",
        "service": "BOOK_L2_MARKET_INTERPRETER",
        "report_type": "flat_context_handling_implementation",
        "contract_version": "book_l2_flat_context_handling_implementation_v1",
        "request": {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"], "interval": interval, "high_confidence_threshold": 0.8},
        "safety": {
            "runtime_behavior_changed": True,
            "l1_logic_changed": False,
            "l2_flat_context_rule_changed": True,
            "trading_signal": "NOT_EVALUATED",
            "safe_for_runtime_trading": False,
            "live_trading_connected": False,
        },
        "warnings": [],
        "errors": [],
    }


def _safety() -> dict[str, object]:
    return {
        "trade_signal": "NOT_EVALUATED",
        "trading_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": False,
        "orders_enabled": False,
        "live_trading_connected": False,
        "traders_core_connected": False,
        "approved_for_live_trading": False,
        "approved_for_auto_activation": False,
        "model_training_executed": False,
    }


def _interval_answer_text() -> str:
    return """
# L1-L2 Interval Answer Smoke

## Status

`PASS`

| Field | Value |
|---|---|
| Interval | `15m` |

| Rank | Symbol | Bucket | Quality | Score | Skip | Current regime |
|---:|---|---|---|---:|---|---|
|  | BTCUSDT | FLAT_CONTEXT | MEDIUM | 0.50 | true | FLAT |
|  | ETHUSDT | FLAT_CONTEXT | MEDIUM | 0.50 | true | FLAT |
|  | SOLUSDT | UNKNOWN | SKIP | 0.00 | true | UNKNOWN |
"""


def _multi_interval_answer_text() -> str:
    return """
# L1-L2 Multi-Interval Answer Smoke

## Status

`FAIL`

| Interval | Status | Overall State | Observation Candidates | Skip Candidates | Safety |
|---|---|---|---|---|---|
| 15m | PASS | RANGING | none | SOLUSDT, BTCUSDT, ETHUSDT | LOCKED |
| 1h | FAIL | UNKNOWN | none | BTCUSDT, ETHUSDT, SOLUSDT | LOCKED |
| 4h | FAIL | UNKNOWN | none | BTCUSDT, ETHUSDT, SOLUSDT | LOCKED |

BTCUSDT | FLAT_CONTEXT | MEDIUM | 0.50 | true | FLAT
ETHUSDT | FLAT_CONTEXT | MEDIUM | 0.50 | true | FLAT
SOLUSDT | UNKNOWN | SKIP | 0.00 | true | UNKNOWN

Interval 1h: warnings are present; L2 warnings: BTCUSDT: required 1200 candles, found 0.
Interval 4h: warnings are present; L2 warnings: BTCUSDT: required 1200 candles, found 0.
"""


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _markdown(tmp_path: Path) -> str:
    config = _write_fixture(tmp_path)
    result = FlatContextIntegrationReviewRunner().run(config)
    return build_markdown(config, result)


def _check(result, name: str):
    return next(check for check in result.checks if check.name == name)


def _help_contains(option: str) -> bool:
    result = CliRunner().invoke(cli, ["book-l2-flat-context-integration-review", "--help"])
    return result.exit_code == 0 and option in result.stdout
