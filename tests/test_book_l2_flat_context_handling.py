from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import cli
from app.market_interpreter.context_quality import ContextQualityScorer
from app.market_interpreter.context_rules import SymbolBucket, classify_symbol_bucket
from app.market_interpreter.context_summary import build_market_brief, build_market_brief_lines
from app.market_interpreter.flat_context_handling import (
    CONTRACT_VERSION,
    FAIL,
    PASS,
    FlatContextHandlingImplementationConfig,
    FlatContextHandlingImplementationRunner,
    build_json_payload,
    build_markdown,
    parse_flat_context_implementation_symbols,
    write_flat_context_handling_implementation_json,
    write_flat_context_handling_implementation_markdown,
)
from app.market_interpreter.json_consumer import L2ContextConsumerConfig, L2ContextJsonConsumer
from app.market_interpreter.api_readiness_review import L2ApiReadinessConfig, L2ApiReadinessReviewer


def test_high_confidence_l1_flat_maps_to_flat_context() -> None:
    decision = classify_symbol_bucket(_row(current_regime="FLAT", confidence=0.94))

    assert decision.bucket == SymbolBucket.FLAT_CONTEXT


def test_flat_confidence_below_threshold_does_not_force_flat_context() -> None:
    decision = classify_symbol_bucket(_row(current_regime="FLAT", confidence=0.79, stability="STABLE"))

    assert decision.bucket == SymbolBucket.STABLE_FLAT


def test_l1_unknown_remains_unknown() -> None:
    decision = classify_symbol_bucket(_row(current_regime="UNKNOWN", confidence=0.0))

    assert decision.bucket == SymbolBucket.UNKNOWN


def test_flat_context_observation_candidate_false_by_default(tmp_path: Path) -> None:
    result = FlatContextHandlingImplementationRunner().run(_write_fixture(tmp_path))

    assert result.cases[0].actual_observation_candidate is False


def test_flat_context_skip_candidate_true_by_default() -> None:
    decision = classify_symbol_bucket(_row(current_regime="FLAT", confidence=0.94))

    assert decision.skip_candidate is True


def test_flat_context_safe_for_runtime_trading_false() -> None:
    decision = classify_symbol_bucket(_row(current_regime="FLAT", confidence=0.94))

    assert decision.safe_for_runtime_trading is False


def test_flat_context_trading_signal_not_evaluated() -> None:
    decision = classify_symbol_bucket(_row(current_regime="FLAT", confidence=0.94))

    assert decision.trade_signal == "NOT_EVALUATED"


def test_flat_context_reason_codes() -> None:
    decision = classify_symbol_bucket(_row(current_regime="FLAT", confidence=0.94))

    assert "L1_FLAT_HIGH_CONFIDENCE" in decision.reason_codes
    assert "FLAT_CONTEXT_PRESERVED" in decision.reason_codes
    assert "NON_DIRECTIONAL_CONTEXT" in decision.reason_codes
    assert "NOT_TRADING_SIGNAL" in decision.reason_codes


def test_current_l2_context_rules_preserve_up_behavior() -> None:
    assert classify_symbol_bucket(_row(current_regime="UP", confidence=0.74)).bucket == SymbolBucket.CLEAN_TREND


def test_current_l2_context_rules_preserve_down_behavior() -> None:
    assert classify_symbol_bucket(_row(current_regime="DOWN", confidence=0.74)).bucket == SymbolBucket.CLEAN_TREND


def test_current_l2_context_rules_preserve_unknown_behavior() -> None:
    assert classify_symbol_bucket(_row(current_regime="UNKNOWN")).bucket == SymbolBucket.UNKNOWN


def test_context_quality_handles_flat_context() -> None:
    score = ContextQualityScorer().score(
        {
            "symbol": "BTCUSDT",
            "status": "OK",
            "bucket": "FLAT_CONTEXT",
            "skip_candidate": True,
            "stability": "CHANGING",
            "current_regime": "FLAT",
            "last_transition": "NO_CHANGE",
            "current_confidence": 0.94,
        }
    )

    assert "QUALITY_FLAT_CONTEXT_PRESERVED" in score.reason_codes
    assert score.rank is None


def test_context_summary_mentions_flat_context_without_decision_terms() -> None:
    brief = build_market_brief(
        (
            _brief("BTCUSDT", "FLAT_CONTEXT"),
            _brief("ETHUSDT", "FLAT_CONTEXT"),
            _brief("SOLUSDT", "UNKNOWN"),
        ),
        overall_state="RANGING",
    )
    text = "\n".join(build_market_brief_lines(brief)).upper()

    assert "FLAT_CONTEXT" in text
    assert "UNKNOWN CURRENT REGIME" not in text.split("BTCUSDT", maxsplit=1)[-1].split("ETHUSDT", maxsplit=1)[0]
    assert "BUY" not in text
    assert "SELL" not in text


def test_json_consumer_accepts_flat_context(tmp_path: Path) -> None:
    path = tmp_path / "timeline_context.json"
    _write_json(path, _l2_payload())

    result = L2ContextJsonConsumer().run(L2ContextConsumerConfig(input_path=path, strict=True))

    assert result.status == "PASS"


def test_api_readiness_accepts_flat_context(tmp_path: Path) -> None:
    project = _write_valid_project(tmp_path)

    result = L2ApiReadinessReviewer().run(L2ApiReadinessConfig(project_root=project, strict=True))

    assert result.status == "PASS"


def test_l2_timeline_context_export_includes_flat_context_for_high_confidence_flat(tmp_path: Path) -> None:
    result = FlatContextHandlingImplementationRunner().run(_write_fixture(tmp_path))

    assert result.status == PASS
    assert result.cases[0].actual_l2_bucket == "FLAT_CONTEXT"


def test_implementation_smoke_returns_pass_when_expected_mapping_exists(tmp_path: Path) -> None:
    result = FlatContextHandlingImplementationRunner().run(_write_fixture(tmp_path))

    assert result.status == PASS


def test_implementation_smoke_returns_fail_when_flat_still_maps_to_unknown(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path, mutate_l2=lambda payload: payload["result"]["symbols"][0].update(bucket="UNKNOWN", context_reason_codes=["CONTEXT_RULE_UNMATCHED"]))  # type: ignore[index, union-attr]

    result = FlatContextHandlingImplementationRunner().run(config)

    assert result.status == FAIL


def test_implementation_smoke_returns_fail_when_flat_context_becomes_observation_candidate(tmp_path: Path) -> None:
    def mutate(payload: dict[str, object]) -> None:
        payload["result"]["market_brief"]["observation_candidates"] = [payload["result"]["symbols"][0]]  # type: ignore[index]

    result = FlatContextHandlingImplementationRunner().run(_write_fixture(tmp_path, mutate_l2=mutate))

    assert result.status == FAIL


def test_implementation_smoke_returns_fail_when_safety_is_true(tmp_path: Path) -> None:
    config = _write_fixture(
        tmp_path,
        mutate_l2=lambda payload: payload["result"]["symbols"][0].update(safe_for_runtime_trading=True),  # type: ignore[index, union-attr]
    )

    result = FlatContextHandlingImplementationRunner().run(config)

    assert result.status == FAIL


def test_json_writer_creates_implementation_output(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = FlatContextHandlingImplementationRunner().run(config)

    assert write_flat_context_handling_implementation_json(config, result).is_file()


def test_markdown_writer_creates_implementation_output(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = FlatContextHandlingImplementationRunner().run(config)

    assert write_flat_context_handling_implementation_markdown(config, result).is_file()


def test_json_payload_contains_contract_version(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = FlatContextHandlingImplementationRunner().run(config)

    assert build_json_payload(config, result)["contract_version"] == CONTRACT_VERSION


def test_markdown_contains_case_results(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    result = FlatContextHandlingImplementationRunner().run(config)

    assert "## Case Results" in build_markdown(config, result)


def test_cli_parser_supports_symbols() -> None:
    assert _help_contains("--symbols")


def test_cli_parser_supports_symbol() -> None:
    assert _help_contains("--symbol")


def test_cli_parser_supports_interval() -> None:
    assert _help_contains("--interval")


def test_cli_parser_supports_high_confidence_threshold() -> None:
    assert _help_contains("--high-confidence-threshold")


def test_cli_parser_supports_proposal_json() -> None:
    assert _help_contains("--proposal-json")


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
    assert parse_flat_context_implementation_symbols("btcusdt, ethusdt") == ("BTCUSDT", "ETHUSDT")


def test_parse_symbols_supports_symbol() -> None:
    assert parse_flat_context_implementation_symbols(None, ("solusdt",)) == ("SOLUSDT",)


def test_non_15m_interval_returns_fail(tmp_path: Path) -> None:
    result = FlatContextHandlingImplementationRunner().run(_write_fixture(tmp_path, interval="1h"))

    assert result.status == FAIL
    assert "stabilized 15m workflow" in result.errors[0]


def test_missing_proposal_returns_required_message(tmp_path: Path) -> None:
    config = _write_fixture(tmp_path)
    config.proposal_json.unlink()

    result = FlatContextHandlingImplementationRunner().run(config)

    assert result.status == FAIL
    assert "Required proposal artifact is missing" in result.errors[0]


def _row(
    *,
    symbol: str = "BTCUSDT",
    status: str = "OK",
    current_regime: str = "FLAT",
    stability: str = "CHANGING",
    last_transition: str = "NO_CHANGE",
    confidence: float = 0.94,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "status": status,
        "current_regime": current_regime,
        "stability": stability,
        "last_transition": last_transition,
        "confidence": confidence,
        "current_confidence": confidence,
        "regimes": (current_regime,),
    }


def _brief(symbol: str, bucket: str) -> dict[str, object]:
    return {
        "symbol": symbol,
        "bucket": bucket,
        "skip_candidate": True,
        "context_quality_score": 0.35,
        "context_quality_grade": "LOW" if bucket == "FLAT_CONTEXT" else "SKIP",
        "context_rank": None,
    }


def _write_fixture(
    tmp_path: Path,
    *,
    interval: str = "15m",
    mutate_l2=None,
) -> FlatContextHandlingImplementationConfig:
    proposal_path = tmp_path / "reports/book_l2/flat_context_handling_proposal.json"
    l1_path = tmp_path / "reports/book_l1/timeline_preview.json"
    l2_path = tmp_path / "reports/book_l2/timeline_context.json"
    output_json = tmp_path / "reports/book_l2/flat_context_handling_implementation.json"
    output_md = tmp_path / "reports/book_l2/flat_context_handling_implementation.md"
    _write_json(proposal_path, _proposal_payload(interval=interval))
    _write_json(l1_path, _l1_payload(interval=interval))
    l2_payload = _l2_payload()
    if mutate_l2 is not None:
        mutate_l2(l2_payload)
    _write_json(l2_path, l2_payload)
    return FlatContextHandlingImplementationConfig(
        symbols=("BTCUSDT", "ETHUSDT", "SOLUSDT"),
        interval=interval,
        proposal_json=proposal_path,
        l1_timeline_json=l1_path,
        l2_context_json=l2_path,
        output_json=output_json,
        output_md=output_md,
    )


def _proposal_payload(*, interval: str) -> dict[str, object]:
    return {
        "status": "PASS_WITH_PROPOSAL_WARNINGS",
        "service": "BOOK_L2_MARKET_INTERPRETER",
        "report_type": "flat_context_handling_proposal",
        "contract_version": "book_l2_flat_context_handling_proposal_v1",
        "request": {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"], "interval": interval},
        "safety": _safety(),
        "warnings": [],
        "errors": [],
    }


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
        "summary": {},
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
    symbols = [
        _l2_symbol("BTCUSDT", "FLAT", 0.94, "FLAT_CONTEXT", True, None),
        _l2_symbol("ETHUSDT", "FLAT", 0.87, "FLAT_CONTEXT", True, None),
        _l2_symbol("SOLUSDT", "UNKNOWN", 0.0, "UNKNOWN", True, None, reason_codes=["CURRENT_REGIME_UNKNOWN", "SKIP_CANDIDATE_CONTEXT"]),
    ]
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
            "symbols": symbols,
            "summary": {"bucket_summary": {"FLAT_CONTEXT": 2, "UNKNOWN": 1}, "quality_summary": {}, "top_ranked_symbols": []},
            "market_context": {"overall_state": "RANGING", "symbol_count": 3},
            "market_brief": {
                "overall_state": "RANGING",
                "brief_state": "FLAT_HEAVY_CONTEXT",
                "observation_candidates": [],
                "skip_candidates": [
                    _brief("BTCUSDT", "FLAT_CONTEXT"),
                    _brief("ETHUSDT", "FLAT_CONTEXT"),
                    _brief("SOLUSDT", "UNKNOWN"),
                ],
                "key_points": [
                    "Overall context is RANGING.",
                    "No clean observation candidates found.",
                    "High-confidence L1 FLAT is preserved as FLAT_CONTEXT.",
                    "Safety remains fail-closed: runtime action is not approved.",
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
    skip_candidate: bool,
    rank: int | None,
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
        "skip_candidate": skip_candidate,
        "context_quality_score": 0.35 if bucket == "FLAT_CONTEXT" else 0.0,
        "context_quality_grade": "LOW" if bucket == "FLAT_CONTEXT" else "SKIP",
        "context_rank": rank,
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


def _write_valid_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    for relative_path in (
        "app/market_interpreter/__init__.py",
        "app/market_interpreter/context_rules.py",
        "app/market_interpreter/context_quality.py",
        "app/market_interpreter/context_summary.py",
        "app/market_interpreter/flat_context_handling.py",
        "app/market_interpreter/json_consumer.py",
        "app/market_interpreter/l1_timeline_consumer.py",
        "tests/test_book_l2_timeline_context.py",
        "tests/test_book_l2_context_rules.py",
        "tests/test_book_l2_context_quality.py",
        "tests/test_book_l2_context_summary.py",
        "tests/test_book_l2_flat_context_handling.py",
        "tests/test_book_l2_json_consumer.py",
        "tests/test_book_l2_api_readiness_review.py",
    ):
        path = project / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# fixture\n", encoding="utf-8")
    (project / "app/cli").mkdir(parents=True, exist_ok=True)
    (project / "app/cli/commands.py").write_text(
        "\n".join(
            f'@cli.command("{command}")'
            for command in (
                "book-l2-timeline-context",
                "book-l2-flat-context-handling-implementation",
                "book-l2-json-consumer-smoke",
                "book-l2-api-readiness-review",
            )
        ),
        encoding="utf-8",
    )
    guide_path = project / "app/market_reader/terminal_guide.py"
    guide_path.parent.mkdir(parents=True, exist_ok=True)
    guide_path.write_text(
        "\n".join(
            (
                "BOOK-L2 freeze candidate review",
                "book-l2-timeline-context",
                "book-l2-flat-context-handling-implementation",
                "book-l2-json-consumer-smoke",
                "book-l2-api-readiness-review",
            )
        ),
        encoding="utf-8",
    )
    planning_text = "\n".join(
        (
            "BOOK-L2-05 completed API readiness final review.",
            "BOOK-L2 is now Layer 2 Freeze Candidate.",
            "BOOK-L2 remains consume-only / observe-only / fail-closed.",
        )
    )
    for relative_path in (
        "planning/01_CURRENT_STATE.md",
        "planning/02_CURRENT_TASK.md",
        "planning/03_REMAINING_WORK.md",
        "planning/07_BOOK_L2_MARKET_INTERPRETER_PLAN.md",
    ):
        path = project / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(planning_text, encoding="utf-8")
    for index in range(5):
        report = project / f"reports/book_l2/book_l2_0{index}_fixture_report.md"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text("PASS\n", encoding="utf-8")
    (project / "reports/book_l2/book_l2_05_api_readiness_review_report.md").write_text("PASS\n", encoding="utf-8")
    _write_json(project / "reports/book_l1/timeline_preview.json", {"status": "ok"})
    _write_json(project / "reports/book_l2/timeline_context.json", _l2_payload())
    return project


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _help_contains(option: str) -> bool:
    result = CliRunner().invoke(cli, ["book-l2-flat-context-handling-implementation", "--help"])
    return result.exit_code == 0 and option in result.stdout
