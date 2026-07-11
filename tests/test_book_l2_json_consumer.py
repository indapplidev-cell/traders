from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import cli
from app.market_interpreter import (
    L2ContextConsumerConfig,
    L2ContextConsumerFormatter,
    L2ContextJsonConsumer,
)


def test_missing_file_returns_fail(tmp_path: Path) -> None:
    result = L2ContextJsonConsumer().run(L2ContextConsumerConfig(input_path=tmp_path / "missing.json"))

    assert result.status == "FAIL"
    assert "L2 context JSON file not found" in result.errors


def test_invalid_json_returns_fail(tmp_path: Path) -> None:
    path = tmp_path / "timeline_context.json"
    path.write_text("{not json", encoding="utf-8")

    result = _run(path)

    assert result.status == "FAIL"
    assert any("invalid JSON" in error for error in result.errors)


def test_missing_required_top_level_key_returns_fail(tmp_path: Path) -> None:
    path = _write_payload(tmp_path, mutate=lambda payload: payload.pop("service"))

    result = _run(path)

    assert result.status == "FAIL"
    assert any("missing top-level key: service" in error for error in result.errors)


def test_wrong_contract_version_returns_fail(tmp_path: Path) -> None:
    path = _write_payload(tmp_path, mutate=lambda payload: payload.update(contract_version="old"))

    result = _run(path)

    assert result.status == "FAIL"
    assert any("contract_version must be book_l2_timeline_context_v1" in error for error in result.errors)


def test_wrong_service_or_layer_returns_fail(tmp_path: Path) -> None:
    path = _write_payload(tmp_path, mutate=lambda payload: payload.update(service="BOOK_L1_MARKET_READER"))

    result = _run(path)

    assert result.status == "FAIL"
    assert any("payload belongs to BOOK-L1" in error for error in result.errors)


def test_source_is_not_l1_timeline_returns_fail(tmp_path: Path) -> None:
    def mutate(payload: dict[str, object]) -> None:
        payload["source_report"] = "reports/book_l1/current_preview.json"
        payload["source"] = {"service": "BOOK_L1_MARKET_READER", "input_path": "reports/book_l1/current_preview.json"}

    result = _run(_write_payload(tmp_path, mutate=mutate))

    assert result.status == "FAIL"
    assert any("source must be reports/book_l1/timeline_preview.json" in error for error in result.errors)


def test_missing_symbols_returns_fail(tmp_path: Path) -> None:
    path = _write_payload(tmp_path, mutate=lambda payload: payload["result"].pop("symbols"))  # type: ignore[index, union-attr]

    result = _run(path)

    assert result.status == "FAIL"
    assert any("missing result key: symbols" in error or "symbols must be a list" in error for error in result.errors)


def test_symbol_missing_bucket_returns_fail(tmp_path: Path) -> None:
    path = _write_payload(tmp_path, mutate=lambda payload: payload["result"]["symbols"][0].pop("bucket"))  # type: ignore[index, union-attr]

    result = _run(path)

    assert result.status == "FAIL"
    assert any("missing bucket" in error for error in result.errors)


def test_symbol_missing_skip_candidate_returns_fail(tmp_path: Path) -> None:
    path = _write_payload(tmp_path, mutate=lambda payload: payload["result"]["symbols"][0].pop("skip_candidate"))  # type: ignore[index, union-attr]

    result = _run(path)

    assert result.status == "FAIL"
    assert any("missing skip_candidate" in error for error in result.errors)


def test_symbol_quality_score_outside_range_returns_fail(tmp_path: Path) -> None:
    path = _write_payload(tmp_path, mutate=lambda payload: payload["result"]["symbols"][0].update(context_quality_score=1.2))  # type: ignore[index, union-attr]

    result = _run(path)

    assert result.status == "FAIL"
    assert any("context_quality_score must be a number from 0.0 to 1.0" in error for error in result.errors)


def test_rank_missing_for_non_skip_symbol_returns_fail(tmp_path: Path) -> None:
    path = _write_payload(tmp_path, mutate=lambda payload: payload["result"]["symbols"][0].update(context_rank=None))  # type: ignore[index, union-attr]

    result = _run(path)

    assert result.status == "FAIL"
    assert any("context_rank must be" in error for error in result.errors)


def test_ranks_with_gaps_or_duplicates_return_fail(tmp_path: Path) -> None:
    def mutate(payload: dict[str, object]) -> None:
        symbols = payload["result"]["symbols"]  # type: ignore[index]
        symbols[1]["skip_candidate"] = False
        symbols[1]["context_quality_grade"] = "MEDIUM"
        symbols[1]["context_rank"] = 3

    result = _run(_write_payload(tmp_path, mutate=mutate))

    assert result.status == "FAIL"
    assert any("1..N without gaps or duplicates" in error for error in result.errors)


def test_valid_symbols_schema_returns_pass(tmp_path: Path) -> None:
    result = _run(_write_payload(tmp_path))

    assert result.status == "PASS"
    assert result.symbol_count == 2


def test_missing_market_brief_returns_fail(tmp_path: Path) -> None:
    path = _write_payload(tmp_path, mutate=lambda payload: payload["result"].pop("market_brief"))  # type: ignore[index, union-attr]

    result = _run(path)

    assert result.status == "FAIL"
    assert any("market_brief" in error for error in result.errors)


def test_market_brief_missing_observation_candidates_returns_fail(tmp_path: Path) -> None:
    path = _write_payload(tmp_path, mutate=lambda payload: payload["result"]["market_brief"].pop("observation_candidates"))  # type: ignore[index, union-attr]

    result = _run(path)

    assert result.status == "FAIL"
    assert any("observation_candidates" in error for error in result.errors)


def test_forbidden_term_in_brief_returns_fail(tmp_path: Path) -> None:
    path = _write_payload(tmp_path, mutate=lambda payload: payload["result"]["market_brief"].update(brief_state="BUY_CONTEXT"))  # type: ignore[index, union-attr]

    result = _run(path)

    assert result.status == "FAIL"
    assert any("forbidden term" in error for error in result.errors)


def test_forbidden_term_in_key_points_returns_fail(tmp_path: Path) -> None:
    path = _write_payload(tmp_path, mutate=lambda payload: payload["result"]["market_brief"].update(key_points=["Place order."]))  # type: ignore[index, union-attr]

    result = _run(path)

    assert result.status == "FAIL"
    assert any("ORDER" in error for error in result.errors)


def test_valid_market_brief_returns_pass(tmp_path: Path) -> None:
    result = _run(_write_payload(tmp_path))

    assert result.status == "PASS"
    assert result.market_brief is not None


def test_safety_safe_for_runtime_true_returns_fail(tmp_path: Path) -> None:
    path = _write_payload(tmp_path, mutate=lambda payload: payload["safety"].update(safe_for_runtime_trading=True))  # type: ignore[union-attr]

    result = _run(path)

    assert result.status == "FAIL"
    assert any("safety.safe_for_runtime_trading must be false" in error for error in result.errors)


def test_safety_orders_enabled_true_returns_fail(tmp_path: Path) -> None:
    path = _write_payload(tmp_path, mutate=lambda payload: payload["safety"].update(orders_enabled=True))  # type: ignore[union-attr]

    result = _run(path)

    assert result.status == "FAIL"
    assert any("safety.orders_enabled must be false" in error for error in result.errors)


def test_safety_trade_signal_not_not_evaluated_returns_fail(tmp_path: Path) -> None:
    path = _write_payload(tmp_path, mutate=lambda payload: payload["safety"].update(trade_signal="LONG"))  # type: ignore[union-attr]

    result = _run(path)

    assert result.status == "FAIL"
    assert any("safety.trade_signal must be NOT_EVALUATED" in error for error in result.errors)


def test_valid_fail_closed_safety_returns_pass(tmp_path: Path) -> None:
    result = _run(_write_payload(tmp_path))

    assert result.status == "PASS"
    assert any(check.name == "fail_closed_safety" and check.status == "PASS" for check in result.checks)


def test_warnings_in_default_mode_return_pass_with_warnings(tmp_path: Path) -> None:
    path = _write_payload(tmp_path, mutate=lambda payload: payload.update(warnings=["diagnostic warning"]))

    result = _run(path)

    assert result.status == "PASS_WITH_WARNINGS"
    assert result.warnings


def test_warnings_in_strict_mode_return_fail(tmp_path: Path) -> None:
    path = _write_payload(tmp_path, mutate=lambda payload: payload.update(warnings=["diagnostic warning"]))

    result = L2ContextJsonConsumer().run(L2ContextConsumerConfig(input_path=path, strict=True))

    assert result.status == "FAIL"


def test_formatter_includes_result_pass(tmp_path: Path) -> None:
    output = L2ContextConsumerFormatter().format(_run(_write_payload(tmp_path)))

    assert "BOOK-L2 JSON Consumer Smoke" in output
    assert "Result: PASS" in output


def test_formatter_details_include_symbols_and_market_brief(tmp_path: Path) -> None:
    output = L2ContextConsumerFormatter().format(_run(_write_payload(tmp_path)), show_details=True)

    assert "Details:" in output
    assert "BTCUSDT: bucket=CLEAN_TREND" in output
    assert "Market brief:" in output
    assert "Observation candidates: BTCUSDT" in output


def test_json_stdout_payload_is_serializable(tmp_path: Path) -> None:
    payload = L2ContextConsumerFormatter().to_json_payload(_run(_write_payload(tmp_path)))

    decoded = json.loads(json.dumps(payload))

    assert decoded["status"] == "PASS"
    assert decoded["checks"]


def test_cli_parser_supports_strict(tmp_path: Path) -> None:
    result = CliRunner().invoke(cli, ["book-l2-json-consumer-smoke", "--input-path", str(_write_payload(tmp_path)), "--strict"])

    assert result.exit_code == 0
    assert "Result: PASS" in result.stdout


def test_cli_parser_supports_show_details(tmp_path: Path) -> None:
    result = CliRunner().invoke(cli, ["book-l2-json-consumer-smoke", "--input-path", str(_write_payload(tmp_path)), "--show-details"])

    assert result.exit_code == 0
    assert "Details:" in result.stdout


def test_cli_parser_supports_json(tmp_path: Path) -> None:
    result = CliRunner().invoke(cli, ["book-l2-json-consumer-smoke", "--input-path", str(_write_payload(tmp_path)), "--json"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["status"] == "PASS"


def _run(path: Path):
    return L2ContextJsonConsumer().run(L2ContextConsumerConfig(input_path=path))


def _write_payload(tmp_path: Path, *, mutate=None) -> Path:
    path = tmp_path / "timeline_context.json"
    payload = _valid_payload()
    if mutate is not None:
        mutate(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _valid_payload() -> dict[str, object]:
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
                _symbol("BTCUSDT", bucket="CLEAN_TREND", skip_candidate=False, score=0.82, grade="HIGH", rank=1),
                _symbol("SOLUSDT", bucket="UNSTABLE", skip_candidate=True, score=0.18, grade="SKIP", rank=None),
            ],
            "summary": {
                "bucket_summary": {"CLEAN_TREND": 1, "UNSTABLE": 1},
                "quality_summary": {"HIGH": 1, "MEDIUM": 0, "LOW": 0, "SKIP": 1, "ERROR": 0},
                "top_ranked_symbols": ["BTCUSDT"],
            },
            "market_context": {
                "overall_state": "MIXED",
                "symbol_count": 2,
                "skip_candidate_count": 1,
                "quality_summary": {"HIGH": 1, "MEDIUM": 0, "LOW": 0, "SKIP": 1, "ERROR": 0},
                "top_ranked_symbols": ["BTCUSDT"],
            },
            "market_brief": {
                "overall_state": "MIXED",
                "brief_state": "CLEAN_CONTEXT_AVAILABLE",
                "observation_candidates": [
                    {
                        "symbol": "BTCUSDT",
                        "bucket": "CLEAN_TREND",
                        "context_quality_score": 0.82,
                        "quality_grade": "HIGH",
                        "context_rank": 1,
                        "skip_candidate": False,
                        "main_reason": "High quality clean context.",
                    }
                ],
                "skip_candidates": [
                    {
                        "symbol": "SOLUSDT",
                        "bucket": "UNSTABLE",
                        "context_quality_score": 0.18,
                        "quality_grade": "SKIP",
                        "context_rank": None,
                        "skip_candidate": True,
                        "main_reason": "Unstable context; skip candidate.",
                    }
                ],
                "key_points": [
                    "Overall context is MIXED.",
                    "Best observation candidates: BTCUSDT.",
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


def _symbol(
    symbol: str,
    *,
    bucket: str,
    skip_candidate: bool,
    score: float,
    grade: str,
    rank: int | None,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "status": "OK",
        "current_regime": "UP",
        "stability": "STABLE",
        "last_transition": "NO_CHANGE",
        "confidence": 0.8,
        "current_confidence": 0.8,
        "current_trend_strength": "MODERATE",
        "bucket": bucket,
        "skip_candidate": skip_candidate,
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
