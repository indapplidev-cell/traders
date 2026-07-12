from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import cli
from app.market_reader.quality_review import (
    ALL_SYMBOLS_SKIPPED,
    CONTRACT_FIELD_MISSING,
    CONTRACT_VERSION,
    DEFAULT_OUTPUT_JSON,
    DEFAULT_OUTPUT_MD,
    FAIL,
    LOW_CONFIDENCE,
    MIXED_TREND_STRUCTURE,
    NO_ACTIVE_BREAKOUT,
    NO_OBSERVATION_CANDIDATES,
    PASS,
    PASS_WITH_QUALITY_WARNINGS,
    UNKNOWN_REGIME_DOMINANT,
    MarketReader15mQualityReviewConfig,
    MarketReader15mQualityReviewFormatter,
    MarketReader15mQualityReviewRunner,
    build_json_payload,
    build_markdown,
    parse_quality_review_symbols,
    write_quality_review_json,
    write_quality_review_markdown,
)


def test_default_config_uses_btc_eth_sol() -> None:
    assert MarketReader15mQualityReviewConfig().symbols == ("BTCUSDT", "ETHUSDT", "SOLUSDT")


def test_default_interval_is_15m() -> None:
    assert MarketReader15mQualityReviewConfig().interval == "15m"


def test_default_output_json_path() -> None:
    assert MarketReader15mQualityReviewConfig().output_json == DEFAULT_OUTPUT_JSON


def test_default_output_md_path() -> None:
    assert MarketReader15mQualityReviewConfig().output_md == DEFAULT_OUTPUT_MD


def test_non_15m_interval_returns_fail(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path, interval="1h")

    result = MarketReader15mQualityReviewRunner().run(config)

    assert result.status == FAIL
    assert "reviews only 15m" in result.errors[0]


def test_missing_l1_timeline_json_returns_fail(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    config.l1_timeline_json.unlink()

    result = MarketReader15mQualityReviewRunner().run(config)

    assert result.status == FAIL
    assert "timeline_preview.json" in result.errors[0]


def test_missing_l2_context_json_returns_fail(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    config.l2_context_json.unlink()

    result = MarketReader15mQualityReviewRunner().run(config)

    assert result.status == FAIL
    assert "timeline_context.json" in result.errors[0]


def test_all_symbols_skipped_produces_finding(tmp_path: Path) -> None:
    result = MarketReader15mQualityReviewRunner().run(_write_fixture(tmp_path, weak=True))

    assert ALL_SYMBOLS_SKIPPED in result.global_findings


def test_no_observation_candidates_produces_finding(tmp_path: Path) -> None:
    result = MarketReader15mQualityReviewRunner().run(_write_fixture(tmp_path, weak=True))

    assert NO_OBSERVATION_CANDIDATES in result.global_findings


def test_unknown_regimes_produce_unknown_regime_dominant(tmp_path: Path) -> None:
    result = MarketReader15mQualityReviewRunner().run(_write_fixture(tmp_path, weak=True))

    assert UNKNOWN_REGIME_DOMINANT in result.symbols[0].findings


def test_low_confidence_produces_low_confidence_finding(tmp_path: Path) -> None:
    result = MarketReader15mQualityReviewRunner().run(_write_fixture(tmp_path, confidence=0.2))

    assert LOW_CONFIDENCE in result.symbols[0].findings


def test_mixed_trend_reason_code_produces_finding(tmp_path: Path) -> None:
    result = MarketReader15mQualityReviewRunner().run(
        _write_fixture(tmp_path, reason_codes=("MIXED_SWING_STRUCTURE",))
    )

    assert MIXED_TREND_STRUCTURE in result.symbols[0].findings


def test_no_active_breakout_reason_code_produces_finding(tmp_path: Path) -> None:
    result = MarketReader15mQualityReviewRunner().run(
        _write_fixture(tmp_path, reason_codes=("NO_ACTIVE_BREAKOUT",))
    )

    assert NO_ACTIVE_BREAKOUT in result.symbols[0].findings


def test_missing_contract_field_produces_contract_missing_or_fail(tmp_path: Path) -> None:
    config = _write_fixture(
        tmp_path,
        mutate_l1=lambda payload: payload["result"]["rows"][0]["windows"][-1].pop("reason_codes"),  # type: ignore[index, union-attr]
    )

    result = MarketReader15mQualityReviewRunner().run(config)

    assert result.status == FAIL
    assert CONTRACT_FIELD_MISSING in result.symbols[0].findings


def test_all_contracts_readable_with_weak_context_returns_quality_warnings(tmp_path: Path) -> None:
    result = MarketReader15mQualityReviewRunner().run(_write_fixture(tmp_path, weak=True))

    assert result.status == PASS_WITH_QUALITY_WARNINGS


def test_useful_non_unknown_context_can_return_pass(tmp_path: Path) -> None:
    result = MarketReader15mQualityReviewRunner().run(_write_fixture(tmp_path, weak=False))

    assert result.status == PASS


def test_safety_violation_returns_fail(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path, mutate_l2=lambda payload: payload["safety"].update(safe_for_runtime_trading=True))  # type: ignore[union-attr]

    result = MarketReader15mQualityReviewRunner().run(config)

    assert result.status == FAIL


def test_json_writer_creates_output(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = MarketReader15mQualityReviewRunner().run(config)

    path = write_quality_review_json(config, result)

    assert path.is_file()


def test_json_contains_contract_version(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = MarketReader15mQualityReviewRunner().run(config)

    assert build_json_payload(config, result)["contract_version"] == CONTRACT_VERSION


def test_json_contains_source_artifacts(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = MarketReader15mQualityReviewRunner().run(config)

    assert "source_artifacts" in build_json_payload(config, result)


def test_json_contains_global_findings(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = MarketReader15mQualityReviewRunner().run(config)

    assert "global_findings" in build_json_payload(config, result)["overall"]


def test_markdown_writer_creates_output(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = MarketReader15mQualityReviewRunner().run(config)

    path = write_quality_review_markdown(config, result)

    assert path.is_file()


def test_markdown_contains_current_15m_answer(tmp_path: Path) -> None:
    assert "## Current 15m Answer" in _markdown(tmp_path)


def test_markdown_contains_global_findings(tmp_path: Path) -> None:
    assert "## Global Findings" in _markdown(tmp_path)


def test_markdown_contains_per_symbol_review(tmp_path: Path) -> None:
    assert "## Per-Symbol Review" in _markdown(tmp_path)


def test_markdown_contains_safety(tmp_path: Path) -> None:
    assert "## Safety" in _markdown(tmp_path)


def test_formatter_prints_result(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = MarketReader15mQualityReviewRunner().run(config)

    output = MarketReader15mQualityReviewFormatter().format(result, config=config)

    assert "Result:" in output


def test_formatter_prints_global_findings(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path, weak=True)
    result = MarketReader15mQualityReviewRunner().run(config)

    output = MarketReader15mQualityReviewFormatter().format(result, config=config)

    assert ALL_SYMBOLS_SKIPPED in output


def test_formatter_prints_symbol_table(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = MarketReader15mQualityReviewRunner().run(config)

    output = MarketReader15mQualityReviewFormatter().format(result, config=config)

    assert "| Symbol" in output
    assert "BTCUSDT" in output


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


def test_parse_symbols_supports_symbols() -> None:
    assert parse_quality_review_symbols("btcusdt, ethusdt") == ("BTCUSDT", "ETHUSDT")


def test_parse_symbols_supports_symbol() -> None:
    assert parse_quality_review_symbols(None, ("solusdt",)) == ("SOLUSDT",)


def _markdown(tmp_path: Path) -> str:
    config = _write_fixture(tmp_path)
    result = MarketReader15mQualityReviewRunner().run(config)
    return build_markdown(config, result)


def _write_fixture(
    tmp_path: Path,
    *,
    interval: str = "15m",
    weak: bool = True,
    confidence: float = 0.2,
    reason_codes: tuple[str, ...] = ("COMPOSER_MIXED_OR_WEAK_CONTEXT", "MIXED_SWING_STRUCTURE", "NO_CLOSE_BREAKOUT"),
    mutate_l1=None,
    mutate_l2=None,
) -> MarketReader15mQualityReviewConfig:
    l1_path = tmp_path / "reports/book_l1/timeline_preview.json"
    l2_path = tmp_path / "reports/book_l2/timeline_context.json"
    output_json = tmp_path / "reports/book_l1/market_reader_15m_quality_review.json"
    output_md = tmp_path / "reports/book_l1/market_reader_15m_quality_review.md"
    l1_payload = _l1_payload(interval=interval, confidence=confidence, reason_codes=reason_codes, weak=weak)
    l2_payload = _l2_payload(weak=weak, confidence=confidence)
    if mutate_l1 is not None:
        mutate_l1(l1_payload)
    if mutate_l2 is not None:
        mutate_l2(l2_payload)
    _write_json(l1_path, l1_payload)
    _write_json(l2_path, l2_payload)
    return MarketReader15mQualityReviewConfig(
        symbols=("BTCUSDT", "ETHUSDT", "SOLUSDT"),
        interval=interval,
        l1_timeline_json=l1_path,
        l2_context_json=l2_path,
        output_json=output_json,
        output_md=output_md,
    )


def _l1_payload(*, interval: str, confidence: float, reason_codes: tuple[str, ...], weak: bool) -> dict[str, object]:
    regimes = ("UNKNOWN", "UNKNOWN", "UNKNOWN") if weak else ("UP", "FLAT", "UNKNOWN")
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
                _l1_row("BTCUSDT", regimes[0], confidence, reason_codes),
                _l1_row("ETHUSDT", regimes[1], confidence, reason_codes),
                _l1_row("SOLUSDT", regimes[2], confidence, reason_codes),
            ]
        },
        "summary": {},
        "safety": _safety(),
        "warnings": [],
        "errors": [],
    }


def _l1_row(symbol: str, regime: str, confidence: float, reason_codes: tuple[str, ...]) -> dict[str, object]:
    return {
        "symbol": symbol,
        "status": "OK",
        "regimes": [regime, regime, regime, regime],
        "transitions": ["NO_CHANGE", "NO_CHANGE", "NO_CHANGE"],
        "last_transition": "NO_CHANGE",
        "stability": "STABLE" if regime != "UNKNOWN" else "UNSTABLE",
        "current_confidence": confidence,
        "current_trend_strength": "MODERATE" if regime != "UNKNOWN" else "UNKNOWN",
        "trade_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": False,
        "windows": [
            {
                "symbol": symbol,
                "label": "Current",
                "market_regime": regime,
                "directional_bias": "UP" if regime == "UP" else "UNKNOWN",
                "confidence": confidence,
                "trend_strength": "MODERATE" if regime != "UNKNOWN" else "UNKNOWN",
                "trade_signal": "NOT_EVALUATED",
                "safe_for_runtime_trading": False,
                "candle_count": 300,
                "reason_codes": list(reason_codes),
            }
        ],
        "warning": None,
    }


def _l2_payload(*, weak: bool, confidence: float) -> dict[str, object]:
    if weak:
        symbols = [
            _l2_symbol("BTCUSDT", "UNKNOWN", "SKIP", 0.1, None, True, "UNKNOWN"),
            _l2_symbol("ETHUSDT", "UNKNOWN", "SKIP", 0.1, None, True, "UNKNOWN"),
            _l2_symbol("SOLUSDT", "UNKNOWN", "SKIP", 0.1, None, True, "UNKNOWN"),
        ]
        observation_candidates: list[dict[str, object]] = []
        skip_candidates = [
            _candidate("BTCUSDT", "UNKNOWN", "SKIP", 0.1, None, True, "Unknown current regime."),
            _candidate("ETHUSDT", "UNKNOWN", "SKIP", 0.1, None, True, "Unknown current regime."),
            _candidate("SOLUSDT", "UNKNOWN", "SKIP", 0.1, None, True, "Unknown current regime."),
        ]
        overall_state = "UNKNOWN"
    else:
        symbols = [
            _l2_symbol("BTCUSDT", "CLEAN_TREND", "HIGH", 0.82, 1, False, "UP"),
            _l2_symbol("ETHUSDT", "STABLE_FLAT", "MEDIUM", 0.61, 2, False, "FLAT"),
            _l2_symbol("SOLUSDT", "UNKNOWN", "SKIP", 0.12, None, True, "UNKNOWN"),
        ]
        observation_candidates = [
            _candidate("BTCUSDT", "CLEAN_TREND", "HIGH", 0.82, 1, False, "High quality clean context."),
            _candidate("ETHUSDT", "STABLE_FLAT", "MEDIUM", 0.61, 2, False, "Stable flat context; observe only."),
        ]
        skip_candidates = [_candidate("SOLUSDT", "UNKNOWN", "SKIP", 0.12, None, True, "Unknown current regime.")]
        overall_state = "MIXED"
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
                "brief_state": "UNKNOWN_CONTEXT" if weak else "CLEAN_CONTEXT_AVAILABLE",
                "observation_candidates": observation_candidates,
                "skip_candidates": skip_candidates,
                "key_points": ["No clean observation candidates found." if weak else "Readable context exists."],
                "warnings": [],
            },
        },
        "safety": _safety(),
        "warnings": [],
        "errors": [],
    }


def _l2_symbol(
    symbol: str,
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
        "confidence": score,
        "current_confidence": score,
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


def _safety() -> dict[str, object]:
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


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _help_contains(option: str) -> bool:
    result = CliRunner().invoke(cli, ["book-l1-15m-quality-review", "--help"])
    return result.exit_code == 0 and option in result.stdout
