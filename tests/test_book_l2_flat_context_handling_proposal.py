from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import cli
from app.market_interpreter.flat_context_proposal import (
    BOOK_L2_09_IMPLEMENTATION_RECOMMENDED,
    CONTRACT_VERSION,
    CURRENT_L2_CONFLATES_FLAT_WITH_UNKNOWN,
    DEFAULT_OUTPUT_JSON,
    DEFAULT_OUTPUT_MD,
    FAIL,
    FLAT_CONTEXT_SHOULD_BE_PRESERVED,
    PASS,
    PASS_WITH_PROPOSAL_WARNINGS,
    RECOMMENDED_NEXT_STAGE,
    RECOMMENDED_OPTION,
    FlatContextHandlingProposalConfig,
    FlatContextHandlingProposalFormatter,
    FlatContextHandlingProposalRunner,
    build_json_payload,
    build_markdown,
    parse_flat_context_proposal_symbols,
    write_flat_context_handling_proposal_json,
    write_flat_context_handling_proposal_markdown,
)


def test_default_config_uses_btcusdt_ethusdt_solusdt() -> None:
    assert FlatContextHandlingProposalConfig().symbols == ("BTCUSDT", "ETHUSDT", "SOLUSDT")


def test_default_interval_is_15m() -> None:
    assert FlatContextHandlingProposalConfig().interval == "15m"


def test_default_high_confidence_threshold_is_080() -> None:
    assert FlatContextHandlingProposalConfig().high_confidence_threshold == 0.80


def test_default_output_json_is_flat_context_handling_proposal_json() -> None:
    assert FlatContextHandlingProposalConfig().output_json == DEFAULT_OUTPUT_JSON


def test_default_output_md_is_flat_context_handling_proposal_md() -> None:
    assert FlatContextHandlingProposalConfig().output_md == DEFAULT_OUTPUT_MD


def test_non_15m_interval_returns_fail(tmp_path: Path) -> None:
    result = FlatContextHandlingProposalRunner().run(_write_fixture(tmp_path, interval="1h"))

    assert result.status == FAIL
    assert "stabilized 15m workflow" in result.errors[0]


def test_missing_flat_diagnostic_json_returns_fail(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    config.flat_diagnostic_json.unlink()

    result = FlatContextHandlingProposalRunner().run(config)

    assert result.status == FAIL
    assert "flat_context_alignment_diagnostic.json" in result.errors[0]


def test_missing_alignment_review_json_returns_fail(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    config.alignment_review_json.unlink()

    result = FlatContextHandlingProposalRunner().run(config)

    assert result.status == FAIL
    assert "l1_l2_regime_alignment_review.json" in result.errors[0]


def test_missing_l1_timeline_json_returns_fail(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    config.l1_timeline_json.unlink()

    result = FlatContextHandlingProposalRunner().run(config)

    assert result.status == FAIL
    assert "timeline_preview.json" in result.errors[0]


def test_missing_l2_context_json_returns_fail(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    config.l2_context_json.unlink()

    result = FlatContextHandlingProposalRunner().run(config)

    assert result.status == FAIL
    assert "timeline_context.json" in result.errors[0]


def test_high_confidence_flat_case_produces_proposed_flat_context(tmp_path: Path) -> None:
    result = FlatContextHandlingProposalRunner().run(_write_fixture(tmp_path))

    assert result.cases[0].proposed_l2_bucket == "FLAT_CONTEXT"


def test_high_confidence_flat_proposed_observation_candidate_false(tmp_path: Path) -> None:
    result = FlatContextHandlingProposalRunner().run(_write_fixture(tmp_path))

    assert result.cases[0].proposed_observation_candidate is False


def test_high_confidence_flat_proposed_skip_candidate_true(tmp_path: Path) -> None:
    result = FlatContextHandlingProposalRunner().run(_write_fixture(tmp_path))

    assert result.cases[0].proposed_skip_candidate is True


def test_high_confidence_flat_proposed_reason_code_flat_context_preserved(tmp_path: Path) -> None:
    result = FlatContextHandlingProposalRunner().run(_write_fixture(tmp_path))

    assert "FLAT_CONTEXT_PRESERVED" in result.cases[0].proposed_reason_codes


def test_unknown_case_remains_unknown_proposal(tmp_path: Path) -> None:
    result = FlatContextHandlingProposalRunner().run(_write_fixture(tmp_path))

    assert result.cases[2].l1_market_regime == "UNKNOWN"
    assert result.cases[2].proposed_l2_bucket == "UNKNOWN"


def test_current_flat_to_unknown_behavior_produces_conflation_finding(tmp_path: Path) -> None:
    result = FlatContextHandlingProposalRunner().run(_write_fixture(tmp_path, weak=True))

    assert CURRENT_L2_CONFLATES_FLAT_WITH_UNKNOWN in result.global_findings


def test_recommended_option_is_option_c(tmp_path: Path) -> None:
    result = FlatContextHandlingProposalRunner().run(_write_fixture(tmp_path))

    assert result.recommended_option == RECOMMENDED_OPTION


def test_recommended_next_stage_is_book_l2_09(tmp_path: Path) -> None:
    result = FlatContextHandlingProposalRunner().run(_write_fixture(tmp_path))

    assert result.recommended_next_stage == RECOMMENDED_NEXT_STAGE


def test_proposal_status_returns_pass_with_warnings_when_runtime_implementation_pending(tmp_path: Path) -> None:
    result = FlatContextHandlingProposalRunner().run(_write_fixture(tmp_path, weak=True))

    assert result.status == PASS_WITH_PROPOSAL_WARNINGS


def test_clean_proposal_can_return_pass(tmp_path: Path) -> None:
    result = FlatContextHandlingProposalRunner().run(_write_fixture(tmp_path, weak=False))

    assert result.status == PASS


def test_safety_violation_returns_fail(tmp_path: Path) -> None:
    config = _write_fixture(
        tmp_path,
        mutate_l2=lambda payload: payload["safety"].update(safe_for_runtime_trading=True),  # type: ignore[union-attr]
    )

    result = FlatContextHandlingProposalRunner().run(config)

    assert result.status == FAIL


def test_json_writer_creates_output(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = FlatContextHandlingProposalRunner().run(config)

    assert write_flat_context_handling_proposal_json(config, result).is_file()


def test_json_contains_contract_version(tmp_path: Path) -> None:
    payload = _json_payload(tmp_path)

    assert payload["contract_version"] == CONTRACT_VERSION


def test_json_contains_current_behavior(tmp_path: Path) -> None:
    assert "current_behavior" in _json_payload(tmp_path)


def test_json_contains_proposed_behavior(tmp_path: Path) -> None:
    assert "proposed_behavior" in _json_payload(tmp_path)


def test_json_contains_semantic_options(tmp_path: Path) -> None:
    assert _json_payload(tmp_path)["semantic_options"]


def test_json_contains_implementation_plan(tmp_path: Path) -> None:
    assert _json_payload(tmp_path)["implementation_plan"]["recommended_next_stage"] == RECOMMENDED_NEXT_STAGE


def test_markdown_writer_creates_output(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = FlatContextHandlingProposalRunner().run(config)

    assert write_flat_context_handling_proposal_markdown(config, result).is_file()


def test_markdown_contains_current_problem(tmp_path: Path) -> None:
    assert "## Current Problem" in _markdown(tmp_path)


def test_markdown_contains_proposed_interpretation(tmp_path: Path) -> None:
    assert "## Proposed Interpretation" in _markdown(tmp_path)


def test_markdown_contains_case_proposals(tmp_path: Path) -> None:
    assert "## Case Proposals" in _markdown(tmp_path)


def test_markdown_contains_semantic_options_considered(tmp_path: Path) -> None:
    assert "## Semantic Options Considered" in _markdown(tmp_path)


def test_markdown_contains_implementation_not_approved_yet(tmp_path: Path) -> None:
    assert "## Implementation Not Approved Yet" in _markdown(tmp_path)


def test_markdown_contains_proposed_book_l2_09_scope(tmp_path: Path) -> None:
    assert "## Proposed BOOK-L2-09 Scope" in _markdown(tmp_path)


def test_markdown_contains_safety(tmp_path: Path) -> None:
    assert "## Safety" in _markdown(tmp_path)


def test_formatter_prints_result(tmp_path: Path) -> None:
    output = _formatter_output(tmp_path)

    assert "Result:" in output


def test_formatter_prints_proposed_behavior(tmp_path: Path) -> None:
    output = _formatter_output(tmp_path)

    assert "Proposed behavior:" in output
    assert "FLAT_CONTEXT" in output


def test_formatter_prints_recommended_next_stage(tmp_path: Path) -> None:
    output = _formatter_output(tmp_path)

    assert RECOMMENDED_NEXT_STAGE in output


def test_cli_parser_supports_symbols() -> None:
    assert _help_contains("--symbols")


def test_cli_parser_supports_symbol() -> None:
    assert _help_contains("--symbol")


def test_cli_parser_supports_interval() -> None:
    assert _help_contains("--interval")


def test_cli_parser_supports_high_confidence_threshold() -> None:
    assert _help_contains("--high-confidence-threshold")


def test_cli_parser_supports_flat_diagnostic_json() -> None:
    assert _help_contains("--flat-diagnostic-json")


def test_cli_parser_supports_alignment_review_json() -> None:
    assert _help_contains("--alignment-review-json")


def test_cli_parser_supports_l1_timeline_json() -> None:
    assert _help_contains("--l1-timeline-json")


def test_cli_parser_supports_l2_context_json() -> None:
    assert _help_contains("--l2-context-json")


def test_cli_parser_supports_output_json() -> None:
    assert _help_contains("--output-json")


def test_cli_parser_supports_output_md() -> None:
    assert _help_contains("--output-md")


def test_cli_parser_supports_strict() -> None:
    assert _help_contains("--strict")


def test_cli_parser_supports_show_details() -> None:
    assert _help_contains("--show-details")


def test_parse_symbols_supports_symbols() -> None:
    assert parse_flat_context_proposal_symbols("btcusdt, ethusdt") == ("BTCUSDT", "ETHUSDT")


def test_parse_symbols_supports_symbol() -> None:
    assert parse_flat_context_proposal_symbols(None, ("solusdt",)) == ("SOLUSDT",)


def test_proposal_global_findings_include_context_preservation(tmp_path: Path) -> None:
    result = FlatContextHandlingProposalRunner().run(_write_fixture(tmp_path))

    assert FLAT_CONTEXT_SHOULD_BE_PRESERVED in result.global_findings
    assert BOOK_L2_09_IMPLEMENTATION_RECOMMENDED in result.global_findings


def _json_payload(tmp_path: Path) -> dict[str, object]:
    config = _write_fixture(tmp_path)
    result = FlatContextHandlingProposalRunner().run(config)
    return build_json_payload(config, result)


def _markdown(tmp_path: Path) -> str:
    config = _write_fixture(tmp_path)
    result = FlatContextHandlingProposalRunner().run(config)
    return build_markdown(config, result)


def _formatter_output(tmp_path: Path) -> str:
    config = _write_fixture(tmp_path)
    result = FlatContextHandlingProposalRunner().run(config)
    return FlatContextHandlingProposalFormatter().format(result, config=config)


def _write_fixture(
    tmp_path: Path,
    *,
    interval: str = "15m",
    weak: bool = True,
    btc_confidence: float = 0.94,
    mutate_flat=None,
    mutate_alignment=None,
    mutate_l1=None,
    mutate_l2=None,
) -> FlatContextHandlingProposalConfig:
    flat_path = tmp_path / "reports/book_l1/flat_context_alignment_diagnostic.json"
    alignment_path = tmp_path / "reports/book_l1/l1_l2_regime_alignment_review.json"
    l1_path = tmp_path / "reports/book_l1/timeline_preview.json"
    l2_path = tmp_path / "reports/book_l2/timeline_context.json"
    output_json = tmp_path / "reports/book_l2/flat_context_handling_proposal.json"
    output_md = tmp_path / "reports/book_l2/flat_context_handling_proposal.md"
    flat_payload = _flat_payload(interval=interval, weak=weak, btc_confidence=btc_confidence)
    alignment_payload = _alignment_payload(interval=interval, weak=weak, btc_confidence=btc_confidence)
    l1_payload = _l1_payload(interval=interval, weak=weak, btc_confidence=btc_confidence)
    l2_payload = _l2_payload(weak=weak, btc_confidence=btc_confidence)
    if mutate_flat is not None:
        mutate_flat(flat_payload)
    if mutate_alignment is not None:
        mutate_alignment(alignment_payload)
    if mutate_l1 is not None:
        mutate_l1(l1_payload)
    if mutate_l2 is not None:
        mutate_l2(l2_payload)
    _write_json(flat_path, flat_payload)
    _write_json(alignment_path, alignment_payload)
    _write_json(l1_path, l1_payload)
    _write_json(l2_path, l2_payload)
    return FlatContextHandlingProposalConfig(
        symbols=("BTCUSDT", "ETHUSDT", "SOLUSDT"),
        interval=interval,
        flat_diagnostic_json=flat_path,
        alignment_review_json=alignment_path,
        l1_timeline_json=l1_path,
        l2_context_json=l2_path,
        output_json=output_json,
        output_md=output_md,
    )


def _flat_payload(*, interval: str, weak: bool, btc_confidence: float) -> dict[str, object]:
    return {
        "status": "PASS_WITH_FLAT_ALIGNMENT_WARNINGS" if weak else "PASS",
        "service": "BOOK_L1_MARKET_READER",
        "report_type": "flat_context_alignment_diagnostic",
        "contract_version": "book_l1_flat_context_alignment_diagnostic_v1",
        "request": {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"], "interval": interval, "high_confidence_threshold": 0.80},
        "source_artifacts": {},
        "cases": [
            _flat_case("BTCUSDT", "FLAT", btc_confidence, weak=weak),
            _flat_case("ETHUSDT", "FLAT", 0.87, weak=weak),
            _flat_case("SOLUSDT", "UNKNOWN" if weak else "FLAT", 0.0 if weak else 0.81, weak=weak),
        ],
        "global_findings": [],
        "safety": _safety(),
        "warnings": [],
        "errors": [],
    }


def _flat_case(symbol: str, regime: str, confidence: float, *, weak: bool) -> dict[str, object]:
    bucket = "UNKNOWN" if weak else "FLAT_CONTEXT"
    return {
        "symbol": symbol,
        "l1_regime": regime,
        "l1_confidence": confidence,
        "l2_received_regime": regime,
        "l2_bucket": bucket,
        "l2_skip_candidate": weak,
        "findings": ["HIGH_CONFIDENCE_FLAT_PRESENT"] if regime == "FLAT" else [],
    }


def _alignment_payload(*, interval: str, weak: bool, btc_confidence: float) -> dict[str, object]:
    return {
        "status": "PASS_WITH_ALIGNMENT_WARNINGS" if weak else "PASS",
        "service": "BOOK_L1_MARKET_READER",
        "report_type": "l1_l2_regime_alignment_review",
        "contract_version": "book_l1_l2_regime_alignment_review_v1",
        "request": {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"], "interval": interval},
        "source_artifacts": {},
        "overall": {"global_findings": [], "l2_overall_state": "UNKNOWN" if weak else "FLAT_CONTEXT"},
        "symbols": [
            _alignment_symbol("BTCUSDT", "FLAT", btc_confidence, weak=weak),
            _alignment_symbol("ETHUSDT", "FLAT", 0.87, weak=weak),
            _alignment_symbol("SOLUSDT", "UNKNOWN" if weak else "FLAT", 0.0 if weak else 0.81, weak=weak),
        ],
        "safety": _safety(),
        "warnings": [],
        "errors": [],
    }


def _alignment_symbol(symbol: str, regime: str, confidence: float, *, weak: bool) -> dict[str, object]:
    return {
        "symbol": symbol,
        "l1_regime": regime,
        "l1_confidence": confidence,
        "l2_received_regime": regime,
        "l2_received_confidence": confidence,
        "l2_bucket": "UNKNOWN" if weak else "FLAT_CONTEXT",
        "l2_skip_candidate": weak,
        "l2_quality_grade": "SKIP" if weak else "MEDIUM",
        "l2_context_reason_codes": ["CONTEXT_RULE_UNMATCHED"] if weak else ["FLAT_CONTEXT_PRESERVED"],
    }


def _l1_payload(*, interval: str, weak: bool, btc_confidence: float) -> dict[str, object]:
    regimes = ("FLAT", "FLAT", "UNKNOWN") if weak else ("FLAT", "FLAT", "FLAT")
    confidences = (btc_confidence, 0.87, 0.0) if weak else (btc_confidence, 0.87, 0.81)
    return {
        "status": "ok",
        "service": "BOOK_L1_MARKET_READER",
        "report_type": "timeline_preview",
        "contract_version": "book_l1_json_export_v1",
        "request": {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"], "interval": interval},
        "result": {
            "rows": [
                _l1_row("BTCUSDT", regimes[0], confidences[0]),
                _l1_row("ETHUSDT", regimes[1], confidences[1]),
                _l1_row("SOLUSDT", regimes[2], confidences[2]),
            ]
        },
        "safety": _safety(),
        "warnings": [],
        "errors": [],
    }


def _l1_row(symbol: str, regime: str, confidence: float) -> dict[str, object]:
    return {
        "symbol": symbol,
        "regimes": [regime],
        "current_confidence": confidence,
        "windows": [
            {
                "symbol": symbol,
                "label": "Current",
                "market_regime": regime,
                "confidence": confidence,
            }
        ],
    }


def _l2_payload(*, weak: bool, btc_confidence: float) -> dict[str, object]:
    symbols = [
        _l2_symbol("BTCUSDT", "FLAT", btc_confidence, weak=weak),
        _l2_symbol("ETHUSDT", "FLAT", 0.87, weak=weak),
        _l2_symbol("SOLUSDT", "UNKNOWN" if weak else "FLAT", 0.0 if weak else 0.81, weak=weak),
    ]
    return {
        "status": "ok",
        "service": "BOOK_L2_MARKET_INTERPRETER",
        "report_type": "timeline_context",
        "contract_version": "book_l2_timeline_context_v1",
        "result": {
            "overall_state": "UNKNOWN" if weak else "FLAT_CONTEXT",
            "symbols": symbols,
            "market_brief": {
                "overall_state": "UNKNOWN" if weak else "FLAT_CONTEXT",
                "observation_candidates": [],
                "skip_candidates": [],
            },
        },
        "safety": _safety(),
        "warnings": [],
        "errors": [],
    }


def _l2_symbol(symbol: str, regime: str, confidence: float, *, weak: bool) -> dict[str, object]:
    return {
        "symbol": symbol,
        "current_regime": regime,
        "current_confidence": confidence,
        "bucket": "UNKNOWN" if weak else "FLAT_CONTEXT",
        "skip_candidate": weak,
        "context_quality_score": 0.2 if weak else 0.7,
        "context_quality_grade": "SKIP" if weak else "MEDIUM",
        "context_reason_codes": ["CONTEXT_RULE_UNMATCHED"] if weak else ["FLAT_CONTEXT_PRESERVED"],
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
        "binance_download_executed": False,
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _help_contains(option: str) -> bool:
    result = CliRunner().invoke(cli, ["book-l2-flat-context-handling-proposal", "--help"])
    return result.exit_code == 0 and option in result.stdout
