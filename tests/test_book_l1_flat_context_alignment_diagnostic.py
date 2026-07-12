from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import cli
from app.market_reader.flat_context_alignment import (
    CONTRACT_VERSION,
    DEFAULT_OUTPUT_JSON,
    DEFAULT_OUTPUT_MD,
    FAIL,
    FLAT_CONTEXT_SEMANTIC_GAP,
    FLAT_MAPPED_TO_UNKNOWN_BUCKET,
    FLAT_SKIPPED_WITHOUT_FLAT_CONTEXT,
    HIGH_CONFIDENCE_FLAT_PRESENT,
    PASS,
    PASS_WITH_FLAT_ALIGNMENT_WARNINGS,
    RECOMMENDED_NEXT_STAGE,
    RECOMMENDED_OPTION,
    UNKNOWN_AND_FLAT_ARE_CONFLATED,
    FlatContextAlignmentConfig,
    FlatContextAlignmentFormatter,
    FlatContextAlignmentRunner,
    build_json_payload,
    build_markdown,
    parse_flat_context_alignment_symbols,
    write_flat_context_alignment_json,
    write_flat_context_alignment_markdown,
)


def test_default_config_uses_btc_eth_sol() -> None:
    assert FlatContextAlignmentConfig().symbols == ("BTCUSDT", "ETHUSDT", "SOLUSDT")


def test_default_interval_is_15m() -> None:
    assert FlatContextAlignmentConfig().interval == "15m"


def test_default_high_confidence_threshold_is_080() -> None:
    assert FlatContextAlignmentConfig().high_confidence_threshold == 0.80


def test_default_output_json_path() -> None:
    assert FlatContextAlignmentConfig().output_json == DEFAULT_OUTPUT_JSON


def test_default_output_md_path() -> None:
    assert FlatContextAlignmentConfig().output_md == DEFAULT_OUTPUT_MD


def test_non_15m_interval_returns_fail(tmp_path: Path) -> None:
    result = FlatContextAlignmentRunner().run(_write_fixture(tmp_path, interval="1h"))

    assert result.status == FAIL
    assert "reviews only 15m FLAT context alignment" in result.errors[0]


def test_missing_alignment_review_json_returns_fail(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    config.alignment_review_json.unlink()

    result = FlatContextAlignmentRunner().run(config)

    assert result.status == FAIL
    assert "l1_l2_regime_alignment_review.json" in result.errors[0]


def test_missing_quality_review_json_returns_fail(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    config.quality_review_json.unlink()

    result = FlatContextAlignmentRunner().run(config)

    assert result.status == FAIL
    assert "market_reader_15m_quality_review.json" in result.errors[0]


def test_missing_l1_timeline_json_returns_fail(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    config.l1_timeline_json.unlink()

    result = FlatContextAlignmentRunner().run(config)

    assert result.status == FAIL
    assert "timeline_preview.json" in result.errors[0]


def test_missing_l2_context_json_returns_fail(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    config.l2_context_json.unlink()

    result = FlatContextAlignmentRunner().run(config)

    assert result.status == FAIL
    assert "timeline_context.json" in result.errors[0]


def test_l1_flat_confidence_at_threshold_marks_high_confidence_flat(tmp_path: Path) -> None:
    result = FlatContextAlignmentRunner().run(_write_fixture(tmp_path, btc_confidence=0.80))

    assert result.cases[0].is_high_confidence_flat is True


def test_l1_flat_confidence_below_threshold_does_not_mark_high_confidence_flat(tmp_path: Path) -> None:
    result = FlatContextAlignmentRunner().run(_write_fixture(tmp_path, btc_confidence=0.79))

    assert result.cases[0].is_high_confidence_flat is False


def test_flat_received_by_l2_but_unknown_bucket_produces_finding(tmp_path: Path) -> None:
    result = FlatContextAlignmentRunner().run(_write_fixture(tmp_path, weak=True))

    assert FLAT_MAPPED_TO_UNKNOWN_BUCKET in result.cases[0].findings


def test_flat_skip_without_flat_context_produces_finding(tmp_path: Path) -> None:
    result = FlatContextAlignmentRunner().run(_write_fixture(tmp_path, weak=True))

    assert FLAT_SKIPPED_WITHOUT_FLAT_CONTEXT in result.cases[0].findings


def test_high_confidence_flat_cases_produce_global_finding(tmp_path: Path) -> None:
    result = FlatContextAlignmentRunner().run(_write_fixture(tmp_path, weak=True))

    assert HIGH_CONFIDENCE_FLAT_PRESENT in result.global_findings


def test_flat_unknown_conflation_produces_global_finding(tmp_path: Path) -> None:
    result = FlatContextAlignmentRunner().run(_write_fixture(tmp_path, weak=True))

    assert UNKNOWN_AND_FLAT_ARE_CONFLATED in result.global_findings


def test_semantic_gap_produces_global_finding(tmp_path: Path) -> None:
    result = FlatContextAlignmentRunner().run(_write_fixture(tmp_path, weak=True))

    assert FLAT_CONTEXT_SEMANTIC_GAP in result.global_findings


def test_recommended_option_is_option_c(tmp_path: Path) -> None:
    result = FlatContextAlignmentRunner().run(_write_fixture(tmp_path))

    assert result.recommended_option == RECOMMENDED_OPTION


def test_recommended_next_stage_is_book_l2_08(tmp_path: Path) -> None:
    result = FlatContextAlignmentRunner().run(_write_fixture(tmp_path))

    assert result.recommended_next_stage == RECOMMENDED_NEXT_STAGE


def test_diagnostic_warnings_return_pass_with_flat_alignment_warnings(tmp_path: Path) -> None:
    result = FlatContextAlignmentRunner().run(_write_fixture(tmp_path, weak=True))

    assert result.status == PASS_WITH_FLAT_ALIGNMENT_WARNINGS


def test_clean_flat_handling_can_return_pass(tmp_path: Path) -> None:
    result = FlatContextAlignmentRunner().run(_write_fixture(tmp_path, weak=False))

    assert result.status == PASS


def test_safety_violation_returns_fail(tmp_path: Path) -> None:
    config = _write_fixture(
        tmp_path,
        mutate_l2=lambda payload: payload["safety"].update(safe_for_runtime_trading=True),  # type: ignore[union-attr]
    )

    result = FlatContextAlignmentRunner().run(config)

    assert result.status == FAIL


def test_json_writer_creates_output(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = FlatContextAlignmentRunner().run(config)

    path = write_flat_context_alignment_json(config, result)

    assert path.is_file()


def test_json_contains_contract_version(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = FlatContextAlignmentRunner().run(config)

    assert build_json_payload(config, result)["contract_version"] == CONTRACT_VERSION


def test_json_contains_semantic_options(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = FlatContextAlignmentRunner().run(config)

    assert build_json_payload(config, result)["semantic_options"]


def test_json_contains_recommended_option(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = FlatContextAlignmentRunner().run(config)

    assert build_json_payload(config, result)["recommended_option"] == RECOMMENDED_OPTION


def test_markdown_writer_creates_output(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = FlatContextAlignmentRunner().run(config)

    path = write_flat_context_alignment_markdown(config, result)

    assert path.is_file()


def test_markdown_contains_main_finding(tmp_path: Path) -> None:
    assert "## Main Finding" in _markdown(tmp_path)


def test_markdown_contains_flat_cases(tmp_path: Path) -> None:
    assert "## FLAT Cases" in _markdown(tmp_path)


def test_markdown_contains_semantic_options_considered(tmp_path: Path) -> None:
    assert "## Semantic Options Considered" in _markdown(tmp_path)


def test_markdown_contains_recommended_interpretation(tmp_path: Path) -> None:
    assert "## Recommended Interpretation" in _markdown(tmp_path)


def test_markdown_contains_not_approved_in_this_stage(tmp_path: Path) -> None:
    assert "## Not Approved In This Stage" in _markdown(tmp_path)


def test_markdown_contains_safety(tmp_path: Path) -> None:
    assert "## Safety" in _markdown(tmp_path)


def test_formatter_prints_result(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = FlatContextAlignmentRunner().run(config)
    output = FlatContextAlignmentFormatter().format(result, config=config)

    assert "Result:" in output


def test_formatter_prints_global_findings(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = FlatContextAlignmentRunner().run(config)
    output = FlatContextAlignmentFormatter().format(result, config=config)

    assert HIGH_CONFIDENCE_FLAT_PRESENT in output


def test_formatter_prints_recommended_option(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = FlatContextAlignmentRunner().run(config)
    output = FlatContextAlignmentFormatter().format(result, config=config)

    assert RECOMMENDED_OPTION in output


def test_cli_parser_supports_symbols() -> None:
    assert _help_contains("--symbols")


def test_cli_parser_supports_symbol() -> None:
    assert _help_contains("--symbol")


def test_cli_parser_supports_interval() -> None:
    assert _help_contains("--interval")


def test_cli_parser_supports_high_confidence_threshold() -> None:
    assert _help_contains("--high-confidence-threshold")


def test_cli_parser_supports_alignment_review_json() -> None:
    assert _help_contains("--alignment-review-json")


def test_cli_parser_supports_quality_review_json() -> None:
    assert _help_contains("--quality-review-json")


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
    assert parse_flat_context_alignment_symbols("btcusdt, ethusdt") == ("BTCUSDT", "ETHUSDT")


def test_parse_symbols_supports_symbol() -> None:
    assert parse_flat_context_alignment_symbols(None, ("solusdt",)) == ("SOLUSDT",)


def _markdown(tmp_path: Path) -> str:
    config = _write_fixture(tmp_path)
    result = FlatContextAlignmentRunner().run(config)
    return build_markdown(config, result)


def _write_fixture(
    tmp_path: Path,
    *,
    interval: str = "15m",
    weak: bool = True,
    btc_confidence: float = 0.94,
    mutate_alignment=None,
    mutate_quality=None,
    mutate_l1=None,
    mutate_l2=None,
) -> FlatContextAlignmentConfig:
    alignment_path = tmp_path / "reports/book_l1/l1_l2_regime_alignment_review.json"
    quality_path = tmp_path / "reports/book_l1/market_reader_15m_quality_review.json"
    l1_path = tmp_path / "reports/book_l1/timeline_preview.json"
    l2_path = tmp_path / "reports/book_l2/timeline_context.json"
    output_json = tmp_path / "reports/book_l1/flat_context_alignment_diagnostic.json"
    output_md = tmp_path / "reports/book_l1/flat_context_alignment_diagnostic.md"
    alignment_payload = _alignment_payload(interval=interval, weak=weak, btc_confidence=btc_confidence)
    quality_payload = _quality_payload(interval=interval, weak=weak, btc_confidence=btc_confidence)
    l1_payload = _l1_payload(interval=interval, weak=weak, btc_confidence=btc_confidence)
    l2_payload = _l2_payload(weak=weak, btc_confidence=btc_confidence)
    if mutate_alignment is not None:
        mutate_alignment(alignment_payload)
    if mutate_quality is not None:
        mutate_quality(quality_payload)
    if mutate_l1 is not None:
        mutate_l1(l1_payload)
    if mutate_l2 is not None:
        mutate_l2(l2_payload)
    _write_json(alignment_path, alignment_payload)
    _write_json(quality_path, quality_payload)
    _write_json(l1_path, l1_payload)
    _write_json(l2_path, l2_payload)
    return FlatContextAlignmentConfig(
        symbols=("BTCUSDT", "ETHUSDT", "SOLUSDT"),
        interval=interval,
        alignment_review_json=alignment_path,
        quality_review_json=quality_path,
        l1_timeline_json=l1_path,
        l2_context_json=l2_path,
        output_json=output_json,
        output_md=output_md,
    )


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
    bucket = "UNKNOWN" if weak else "FLAT_CONTEXT"
    skip = weak
    reason = "Unknown current regime." if weak else "FLAT context preserved as observe-only."
    received = regime
    return {
        "symbol": symbol,
        "l1_regime": regime,
        "l1_confidence": confidence,
        "l2_received_regime": received,
        "l2_received_confidence": confidence,
        "l2_bucket": bucket,
        "l2_skip_candidate": skip,
        "l2_quality_grade": "SKIP" if weak else "MEDIUM",
        "l2_main_reason": reason,
        "l2_context_reason_codes": ["CONTEXT_RULE_UNMATCHED"] if weak else ["FLAT_CONTEXT_PRESERVED"],
        "l2_context_quality_reason_codes": ["QUALITY_BUCKET_UNKNOWN"] if weak else ["QUALITY_FLAT_CONTEXT"],
    }


def _quality_payload(*, interval: str, weak: bool, btc_confidence: float) -> dict[str, object]:
    return {
        "status": "PASS_WITH_QUALITY_WARNINGS" if weak else "PASS",
        "service": "BOOK_L1_MARKET_READER",
        "report_type": "market_reader_15m_quality_review",
        "contract_version": "book_l1_15m_quality_review_v1",
        "request": {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"], "interval": interval},
        "source_artifacts": {},
        "overall": {"l2_overall_state": "UNKNOWN" if weak else "FLAT_CONTEXT", "global_findings": []},
        "symbols": [
            _quality_symbol("BTCUSDT", "FLAT", btc_confidence, weak=weak),
            _quality_symbol("ETHUSDT", "FLAT", 0.87, weak=weak),
            _quality_symbol("SOLUSDT", "UNKNOWN" if weak else "FLAT", 0.0 if weak else 0.81, weak=weak),
        ],
        "safety": _safety(),
        "warnings": [],
        "errors": [],
    }


def _quality_symbol(symbol: str, regime: str, confidence: float, *, weak: bool) -> dict[str, object]:
    return {
        "symbol": symbol,
        "market_regime": regime,
        "confidence": confidence,
        "l1_reason_codes": ["COMPOSER_FLAT_RANGE_DOMINANT"] if regime == "FLAT" else ["COMPOSER_MIXED_OR_WEAK_CONTEXT"],
        "l2_bucket": "UNKNOWN" if weak else "FLAT_CONTEXT",
        "l2_skip_candidate": weak,
        "l2_quality_grade": "SKIP" if weak else "MEDIUM",
        "l2_main_reason": "Unknown current regime." if weak else "FLAT context preserved as observe-only.",
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
                "reason_codes": ["COMPOSER_FLAT_RANGE_DOMINANT"] if regime == "FLAT" else ["COMPOSER_MIXED_OR_WEAK_CONTEXT"],
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
                "observation_candidates": [] if weak else [{"symbol": "BTCUSDT"}],
                "skip_candidates": [
                    _candidate("BTCUSDT", weak=weak),
                    _candidate("ETHUSDT", weak=weak),
                    _candidate("SOLUSDT", weak=weak),
                ]
                if weak
                else [],
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
        "context_reason_codes": ["CONTEXT_RULE_UNMATCHED", "SKIP_CANDIDATE_CONTEXT"] if weak else ["FLAT_CONTEXT_PRESERVED"],
        "context_quality_reason_codes": ["QUALITY_BUCKET_UNKNOWN"] if weak else ["QUALITY_FLAT_CONTEXT"],
        "observe_reason": "Unknown current regime." if weak else "FLAT context preserved as observe-only.",
    }


def _candidate(symbol: str, *, weak: bool) -> dict[str, object]:
    return {
        "symbol": symbol,
        "bucket": "UNKNOWN" if weak else "FLAT_CONTEXT",
        "skip_candidate": weak,
        "main_reason": "Unknown current regime." if weak else "FLAT context preserved as observe-only.",
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
    result = CliRunner().invoke(cli, ["book-l1-flat-context-alignment-diagnostic", "--help"])
    return result.exit_code == 0 and option in result.stdout
