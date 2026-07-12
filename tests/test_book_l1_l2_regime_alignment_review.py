from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import cli
from app.market_reader.regime_alignment_review import (
    CONTRACT_ALIGNMENT_NEEDS_REVIEW,
    CONTRACT_VERSION,
    DEFAULT_OUTPUT_JSON,
    DEFAULT_OUTPUT_MD,
    FAIL,
    L1_FLAT_HIGH_CONFIDENCE_BUT_L2_UNKNOWN_SKIP,
    L1_TO_L2_REGIME_FIELD_MISSING,
    L1_UNKNOWN_PROPAGATED_TO_L2_SKIP,
    L2_CONTEXT_REASON_CODES_MISSING,
    L2_MAIN_REASON_MISSING,
    L2_OVERALL_UNKNOWN_DESPITE_L1_FLAT_SYMBOLS,
    L2_SKIPS_FLAT_CONTEXT,
    PASS,
    PASS_WITH_ALIGNMENT_WARNINGS,
    RegimeAlignmentReviewConfig,
    RegimeAlignmentReviewFormatter,
    RegimeAlignmentReviewRunner,
    build_json_payload,
    build_markdown,
    parse_regime_alignment_symbols,
    write_regime_alignment_review_json,
    write_regime_alignment_review_markdown,
)


def test_default_config_uses_btc_eth_sol() -> None:
    assert RegimeAlignmentReviewConfig().symbols == ("BTCUSDT", "ETHUSDT", "SOLUSDT")


def test_default_interval_is_15m() -> None:
    assert RegimeAlignmentReviewConfig().interval == "15m"


def test_default_output_json_path() -> None:
    assert RegimeAlignmentReviewConfig().output_json == DEFAULT_OUTPUT_JSON


def test_default_output_md_path() -> None:
    assert RegimeAlignmentReviewConfig().output_md == DEFAULT_OUTPUT_MD


def test_non_15m_interval_returns_fail(tmp_path: Path) -> None:
    result = RegimeAlignmentReviewRunner().run(_write_fixture(tmp_path, interval="1h"))

    assert result.status == FAIL
    assert "reviews only 15m" in result.errors[0]


def test_missing_quality_review_json_returns_fail(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    config.quality_review_json.unlink()

    result = RegimeAlignmentReviewRunner().run(config)

    assert result.status == FAIL
    assert "market_reader_15m_quality_review.json" in result.errors[0]


def test_missing_l1_timeline_json_returns_fail(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    config.l1_timeline_json.unlink()

    result = RegimeAlignmentReviewRunner().run(config)

    assert result.status == FAIL
    assert "timeline_preview.json" in result.errors[0]


def test_missing_l2_context_json_returns_fail(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    config.l2_context_json.unlink()

    result = RegimeAlignmentReviewRunner().run(config)

    assert result.status == FAIL
    assert "timeline_context.json" in result.errors[0]


def test_l1_flat_high_confidence_with_l2_unknown_skip_produces_finding(tmp_path: Path) -> None:
    result = RegimeAlignmentReviewRunner().run(_write_fixture(tmp_path, weak=True))

    assert L1_FLAT_HIGH_CONFIDENCE_BUT_L2_UNKNOWN_SKIP in result.alignments[0].findings


def test_l1_unknown_with_l2_skip_produces_finding(tmp_path: Path) -> None:
    result = RegimeAlignmentReviewRunner().run(_write_fixture(tmp_path, weak=True))

    assert L1_UNKNOWN_PROPAGATED_TO_L2_SKIP in result.alignments[2].findings


def test_l2_overall_unknown_despite_l1_flat_symbols_produces_global_finding(tmp_path: Path) -> None:
    result = RegimeAlignmentReviewRunner().run(_write_fixture(tmp_path, weak=True))

    assert L2_OVERALL_UNKNOWN_DESPITE_L1_FLAT_SYMBOLS in result.global_findings


def test_l2_skip_for_flat_produces_finding(tmp_path: Path) -> None:
    result = RegimeAlignmentReviewRunner().run(_write_fixture(tmp_path, weak=True))

    assert L2_SKIPS_FLAT_CONTEXT in result.alignments[0].findings


def test_missing_l1_regime_field_produces_regime_missing_or_fail(tmp_path: Path) -> None:
    config = _write_fixture(
        tmp_path,
        mutate_quality=lambda payload: payload["symbols"][0].pop("market_regime"),  # type: ignore[index, union-attr]
        mutate_l1=lambda payload: (
            payload["result"]["rows"][0].pop("regimes"),  # type: ignore[index, union-attr]
            payload["result"]["rows"][0]["windows"][-1].pop("market_regime"),  # type: ignore[index, union-attr]
        ),
    )

    result = RegimeAlignmentReviewRunner().run(config)

    assert result.status == FAIL
    assert L1_TO_L2_REGIME_FIELD_MISSING in result.alignments[0].findings


def test_missing_l2_main_reason_produces_finding(tmp_path: Path) -> None:
    config = _write_fixture(
        tmp_path,
        mutate_l2=lambda payload: (
            payload["result"]["market_brief"]["skip_candidates"][0].pop("main_reason"),  # type: ignore[index, union-attr]
            payload["result"]["symbols"][0].pop("observe_reason"),  # type: ignore[index, union-attr]
        ),
    )

    result = RegimeAlignmentReviewRunner().run(config)

    assert L2_MAIN_REASON_MISSING in result.alignments[0].findings


def test_missing_l2_context_reason_codes_produces_finding(tmp_path: Path) -> None:
    config = _write_fixture(
        tmp_path,
        mutate_l2=lambda payload: payload["result"]["symbols"][0].pop("context_reason_codes"),  # type: ignore[index, union-attr]
    )

    result = RegimeAlignmentReviewRunner().run(config)

    assert L2_CONTEXT_REASON_CODES_MISSING in result.alignments[0].findings


def test_alignment_warnings_return_pass_with_alignment_warnings(tmp_path: Path) -> None:
    result = RegimeAlignmentReviewRunner().run(_write_fixture(tmp_path, weak=True))

    assert result.status == PASS_WITH_ALIGNMENT_WARNINGS


def test_clean_alignment_can_return_pass(tmp_path: Path) -> None:
    result = RegimeAlignmentReviewRunner().run(_write_fixture(tmp_path, weak=False))

    assert result.status == PASS


def test_safety_violation_returns_fail(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path, mutate_l2=lambda payload: payload["safety"].update(safe_for_runtime_trading=True))  # type: ignore[union-attr]

    result = RegimeAlignmentReviewRunner().run(config)

    assert result.status == FAIL


def test_json_writer_creates_output(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = RegimeAlignmentReviewRunner().run(config)

    path = write_regime_alignment_review_json(config, result)

    assert path.is_file()


def test_json_contains_contract_version(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = RegimeAlignmentReviewRunner().run(config)

    assert build_json_payload(config, result)["contract_version"] == CONTRACT_VERSION


def test_json_contains_source_artifacts(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = RegimeAlignmentReviewRunner().run(config)

    assert "source_artifacts" in build_json_payload(config, result)


def test_json_contains_global_findings(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = RegimeAlignmentReviewRunner().run(config)

    assert "global_findings" in build_json_payload(config, result)["overall"]


def test_markdown_writer_creates_output(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = RegimeAlignmentReviewRunner().run(config)

    path = write_regime_alignment_review_markdown(config, result)

    assert path.is_file()


def test_markdown_contains_main_finding(tmp_path: Path) -> None:
    assert "## Main Finding" in _markdown(tmp_path)


def test_markdown_contains_per_symbol_alignment(tmp_path: Path) -> None:
    assert "## Per-Symbol Alignment" in _markdown(tmp_path)


def test_markdown_contains_symbol_details(tmp_path: Path) -> None:
    assert "## Symbol Details" in _markdown(tmp_path)


def test_markdown_contains_recommended_next_stage(tmp_path: Path) -> None:
    assert "## Recommended Next Stage" in _markdown(tmp_path)


def test_formatter_prints_result(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = RegimeAlignmentReviewRunner().run(config)

    output = RegimeAlignmentReviewFormatter().format(result, config=config)

    assert "Result:" in output


def test_formatter_prints_global_findings(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = RegimeAlignmentReviewRunner().run(config)

    output = RegimeAlignmentReviewFormatter().format(result, config=config)

    assert L2_OVERALL_UNKNOWN_DESPITE_L1_FLAT_SYMBOLS in output
    assert CONTRACT_ALIGNMENT_NEEDS_REVIEW in output


def test_formatter_prints_symbol_table(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = RegimeAlignmentReviewRunner().run(config)

    output = RegimeAlignmentReviewFormatter().format(result, config=config)

    assert "| Symbol" in output
    assert "BTCUSDT" in output


def test_cli_parser_supports_symbols() -> None:
    assert _help_contains("--symbols")


def test_cli_parser_supports_symbol() -> None:
    assert _help_contains("--symbol")


def test_cli_parser_supports_interval() -> None:
    assert _help_contains("--interval")


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
    assert parse_regime_alignment_symbols("btcusdt, ethusdt") == ("BTCUSDT", "ETHUSDT")


def test_parse_symbols_supports_symbol() -> None:
    assert parse_regime_alignment_symbols(None, ("solusdt",)) == ("SOLUSDT",)


def _markdown(tmp_path: Path) -> str:
    config = _write_fixture(tmp_path)
    result = RegimeAlignmentReviewRunner().run(config)
    return build_markdown(config, result)


def _write_fixture(
    tmp_path: Path,
    *,
    interval: str = "15m",
    weak: bool = True,
    mutate_quality=None,
    mutate_l1=None,
    mutate_l2=None,
) -> RegimeAlignmentReviewConfig:
    quality_path = tmp_path / "reports/book_l1/market_reader_15m_quality_review.json"
    l1_path = tmp_path / "reports/book_l1/timeline_preview.json"
    l2_path = tmp_path / "reports/book_l2/timeline_context.json"
    output_json = tmp_path / "reports/book_l1/l1_l2_regime_alignment_review.json"
    output_md = tmp_path / "reports/book_l1/l1_l2_regime_alignment_review.md"
    quality_payload = _quality_payload(interval=interval, weak=weak)
    l1_payload = _l1_payload(interval=interval, weak=weak)
    l2_payload = _l2_payload(weak=weak)
    if mutate_quality is not None:
        mutate_quality(quality_payload)
    if mutate_l1 is not None:
        mutate_l1(l1_payload)
    if mutate_l2 is not None:
        mutate_l2(l2_payload)
    _write_json(quality_path, quality_payload)
    _write_json(l1_path, l1_payload)
    _write_json(l2_path, l2_payload)
    return RegimeAlignmentReviewConfig(
        symbols=("BTCUSDT", "ETHUSDT", "SOLUSDT"),
        interval=interval,
        quality_review_json=quality_path,
        l1_timeline_json=l1_path,
        l2_context_json=l2_path,
        output_json=output_json,
        output_md=output_md,
    )


def _quality_payload(*, interval: str, weak: bool) -> dict[str, object]:
    return {
        "status": "PASS_WITH_QUALITY_WARNINGS" if weak else "PASS",
        "service": "BOOK_L1_MARKET_READER",
        "report_type": "market_reader_15m_quality_review",
        "contract_version": "book_l1_15m_quality_review_v1",
        "request": {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"], "interval": interval},
        "source_artifacts": {},
        "overall": {"l2_overall_state": "UNKNOWN" if weak else "RANGING", "global_findings": []},
        "symbols": [
            _quality_symbol("BTCUSDT", "FLAT", 0.94, weak=weak),
            _quality_symbol("ETHUSDT", "FLAT", 0.87, weak=weak),
            _quality_symbol("SOLUSDT", "UNKNOWN" if weak else "FLAT", 0.0 if weak else 0.81, weak=weak),
        ],
        "safety": _safety(),
        "warnings": [],
        "errors": [],
    }


def _quality_symbol(symbol: str, regime: str, confidence: float, *, weak: bool) -> dict[str, object]:
    bucket = "UNKNOWN" if weak else "STABLE_FLAT"
    skip = weak
    return {
        "symbol": symbol,
        "market_regime": regime,
        "confidence": confidence,
        "directional_bias": "NEUTRAL" if regime == "FLAT" else "UNKNOWN",
        "trend_strength": "NONE" if regime == "FLAT" else "UNKNOWN",
        "stability": "CHANGING" if weak and regime == "FLAT" else "STABLE",
        "last_transition": "NO_CHANGE",
        "l1_reason_codes": ["MARKET_READER_ORCHESTRATED", "COMPOSER_FLAT_RANGE_DOMINANT"],
        "l2_bucket": bucket,
        "l2_skip_candidate": skip,
        "l2_quality_score": 0.2 if weak else 0.7,
        "l2_quality_grade": "SKIP" if weak else "MEDIUM",
        "l2_main_reason": "Unknown current regime." if weak else "Stable flat context; observe only.",
        "l2_context_reason_codes": ["CONTEXT_RULE_UNMATCHED"] if weak else ["STABLE_FLAT_CONTEXT"],
    }


def _l1_payload(*, interval: str, weak: bool) -> dict[str, object]:
    regimes = ("FLAT", "FLAT", "UNKNOWN") if weak else ("FLAT", "FLAT", "FLAT")
    confidences = (0.94, 0.87, 0.0) if weak else (0.94, 0.87, 0.81)
    return {
        "status": "ok",
        "service": "BOOK_L1_MARKET_READER",
        "report_type": "timeline_preview",
        "contract_version": "book_l1_json_export_v1",
        "request": {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"], "interval": interval},
        "result": {
            "rows": [
                _l1_row("BTCUSDT", regimes[0], confidences[0], weak=weak),
                _l1_row("ETHUSDT", regimes[1], confidences[1], weak=weak),
                _l1_row("SOLUSDT", regimes[2], confidences[2], weak=weak),
            ]
        },
        "safety": _safety(),
        "warnings": [],
        "errors": [],
    }


def _l1_row(symbol: str, regime: str, confidence: float, *, weak: bool) -> dict[str, object]:
    return {
        "symbol": symbol,
        "status": "OK",
        "regimes": [regime, regime, regime, regime],
        "last_transition": "NO_CHANGE",
        "stability": "CHANGING" if weak and regime == "FLAT" else "STABLE",
        "current_confidence": confidence,
        "current_trend_strength": "NONE" if regime == "FLAT" else "UNKNOWN",
        "trade_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": False,
        "windows": [
            {
                "symbol": symbol,
                "label": "Current",
                "market_regime": regime,
                "directional_bias": "NEUTRAL" if regime == "FLAT" else "UNKNOWN",
                "confidence": confidence,
                "trend_strength": "NONE" if regime == "FLAT" else "UNKNOWN",
                "reason_codes": ["MARKET_READER_ORCHESTRATED", "COMPOSER_FLAT_RANGE_DOMINANT"],
            }
        ],
    }


def _l2_payload(*, weak: bool) -> dict[str, object]:
    if weak:
        symbols = [
            _l2_symbol("BTCUSDT", "FLAT", "UNKNOWN", True, 0.2, "SKIP", ["CONTEXT_RULE_UNMATCHED"]),
            _l2_symbol("ETHUSDT", "FLAT", "UNKNOWN", True, 0.2, "SKIP", ["CONTEXT_RULE_UNMATCHED"]),
            _l2_symbol("SOLUSDT", "UNKNOWN", "UNKNOWN", True, 0.0, "SKIP", ["CURRENT_REGIME_UNKNOWN"]),
        ]
        observation_candidates: list[dict[str, object]] = []
        skip_candidates = [
            _candidate("BTCUSDT", "UNKNOWN", 0.2, "SKIP", True, "Unknown current regime."),
            _candidate("ETHUSDT", "UNKNOWN", 0.2, "SKIP", True, "Unknown current regime."),
            _candidate("SOLUSDT", "UNKNOWN", 0.0, "SKIP", True, "Unknown current regime."),
        ]
        overall_state = "UNKNOWN"
    else:
        symbols = [
            _l2_symbol("BTCUSDT", "FLAT", "STABLE_FLAT", False, 0.7, "MEDIUM", ["STABLE_FLAT_CONTEXT"]),
            _l2_symbol("ETHUSDT", "FLAT", "STABLE_FLAT", False, 0.68, "MEDIUM", ["STABLE_FLAT_CONTEXT"]),
            _l2_symbol("SOLUSDT", "FLAT", "STABLE_FLAT", False, 0.66, "MEDIUM", ["STABLE_FLAT_CONTEXT"]),
        ]
        observation_candidates = [
            _candidate("BTCUSDT", "STABLE_FLAT", 0.7, "MEDIUM", False, "Stable flat context; observe only."),
            _candidate("ETHUSDT", "STABLE_FLAT", 0.68, "MEDIUM", False, "Stable flat context; observe only."),
        ]
        skip_candidates = []
        overall_state = "RANGING"
    return {
        "status": "ok",
        "service": "BOOK_L2_MARKET_INTERPRETER",
        "report_type": "timeline_context",
        "contract_version": "book_l2_timeline_context_v1",
        "source_report": "reports/book_l1/timeline_preview.json",
        "source": {"input_path": "reports/book_l1/timeline_preview.json"},
        "result": {
            "overall_state": overall_state,
            "symbols": symbols,
            "market_brief": {
                "overall_state": overall_state,
                "brief_state": "UNKNOWN_CONTEXT" if weak else "FLAT_HEAVY_CONTEXT",
                "observation_candidates": observation_candidates,
                "skip_candidates": skip_candidates,
                "key_points": ["No clean observation candidates found." if weak else "Market context is flat-heavy."],
                "warnings": [],
            },
        },
        "safety": _safety(),
        "warnings": [],
        "errors": [],
    }


def _l2_symbol(
    symbol: str,
    regime: str,
    bucket: str,
    skip: bool,
    score: float,
    grade: str,
    reason_codes: list[str],
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "status": "OK",
        "current_regime": regime,
        "stability": "CHANGING" if skip and regime == "FLAT" else "STABLE",
        "last_transition": "NO_CHANGE",
        "confidence": score,
        "current_confidence": score,
        "current_trend_strength": "NONE",
        "bucket": bucket,
        "skip_candidate": skip,
        "context_quality_score": score,
        "context_quality_grade": grade,
        "context_rank": None if skip else 1,
        "context_quality_reason_codes": ["CONTEXT_QUALITY_SCORED"],
        "context_reason_codes": [*reason_codes, "SKIP_CANDIDATE_CONTEXT"] if skip else reason_codes,
        "trade_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": False,
        "context_label": bucket,
        "observe_reason": "Unknown current regime." if skip else "Stable flat context; observe only.",
        "warnings": [],
    }


def _candidate(
    symbol: str,
    bucket: str,
    score: float,
    grade: str,
    skip: bool,
    reason: str,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "bucket": bucket,
        "context_quality_score": score,
        "quality_grade": grade,
        "context_rank": None,
        "skip_candidate": skip,
        "main_reason": reason,
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
    result = CliRunner().invoke(cli, ["book-l1-l2-regime-alignment-review", "--help"])
    return result.exit_code == 0 and option in result.stdout
