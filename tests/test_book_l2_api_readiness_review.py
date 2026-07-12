from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import cli
from app.market_interpreter import (
    L2ApiReadinessConfig,
    L2ApiReadinessFormatter,
    L2ApiReadinessReviewer,
)


def test_config_defaults_point_to_stable_l1_and_l2_paths() -> None:
    config = L2ApiReadinessConfig()

    assert config.l1_timeline_path == Path("reports/book_l1/timeline_preview.json")
    assert config.l2_context_path == Path("reports/book_l2/timeline_context.json")
    assert config.strict is False
    assert config.show_details is False


def test_missing_l1_timeline_input_returns_fail(tmp_path: Path) -> None:
    project = _write_valid_project(tmp_path)
    (project / "reports/book_l1/timeline_preview.json").unlink()

    result = _run(project)

    assert result.status == "FAIL"
    assert _check_status(result, "l1_timeline_input_exists") == "FAIL"


def test_missing_l2_context_output_returns_fail(tmp_path: Path) -> None:
    project = _write_valid_project(tmp_path)
    (project / "reports/book_l2/timeline_context.json").unlink()

    result = _run(project)

    assert result.status == "FAIL"
    assert _check_status(result, "l2_context_export_exists") == "FAIL"


def test_missing_required_l2_module_returns_fail(tmp_path: Path) -> None:
    project = _write_valid_project(tmp_path)
    (project / "app/market_interpreter/context_rules.py").unlink()

    result = _run(project)

    assert result.status == "FAIL"
    assert _check_status(result, "l2_modules_exist") == "FAIL"


def test_missing_required_l2_test_file_warns_by_default(tmp_path: Path) -> None:
    project = _write_valid_project(tmp_path)
    (project / "tests/test_book_l2_context_rules.py").unlink()

    result = _run(project)

    assert result.status == "PASS_WITH_WARNINGS"
    assert _check_status(result, "l2_tests_exist") == "WARN"


def test_valid_minimal_project_structure_returns_pass(tmp_path: Path) -> None:
    result = _run(_write_valid_project(tmp_path))

    assert result.status == "PASS"
    assert result.freeze_candidate is True


def test_l2_json_consumer_pass_contributes_pass(tmp_path: Path) -> None:
    result = _run(_write_valid_project(tmp_path))

    assert _check_status(result, "l2_json_consumer_strict") == "PASS"


def test_l2_json_consumer_fail_makes_readiness_fail(tmp_path: Path) -> None:
    project = _write_valid_project(tmp_path)
    payload = _valid_l2_payload()
    payload["contract_version"] = "old"
    _write_json(project / "reports/book_l2/timeline_context.json", payload)

    result = _run(project)

    assert result.status == "FAIL"
    assert _check_status(result, "l2_json_consumer_strict") == "FAIL"


def test_safety_violation_makes_readiness_fail(tmp_path: Path) -> None:
    project = _write_valid_project(tmp_path)
    payload = _valid_l2_payload()
    payload["safety"]["safe_for_runtime_trading"] = True  # type: ignore[index]
    _write_json(project / "reports/book_l2/timeline_context.json", payload)

    result = _run(project)

    assert result.status == "FAIL"
    assert _check_status(result, "fail_closed_safety") == "FAIL"


def test_observe_only_forbidden_term_in_market_brief_makes_readiness_fail(tmp_path: Path) -> None:
    project = _write_valid_project(tmp_path)
    payload = _valid_l2_payload()
    payload["result"]["market_brief"]["key_points"] = ["BUY context is present."]  # type: ignore[index]
    _write_json(project / "reports/book_l2/timeline_context.json", payload)

    result = _run(project)

    assert result.status == "FAIL"
    assert _check_status(result, "observe_only_constraints") == "FAIL"


def test_forbidden_import_match_makes_readiness_fail(tmp_path: Path) -> None:
    project = _write_valid_project(tmp_path)
    (project / "app/market_interpreter/context_rules.py").write_text("from x import CandleRepository\n", encoding="utf-8")

    result = _run(project)

    assert result.status == "FAIL"
    assert _check_status(result, "forbidden_imports") == "FAIL"


def test_stable_output_policy_rejects_timestamped_runtime_output(tmp_path: Path) -> None:
    project = _write_valid_project(tmp_path)
    _write_json(project / "reports/book_l2/timeline_context_2026_07_11.json", _valid_l2_payload())

    result = _run(project)

    assert result.status == "FAIL"
    assert _check_status(result, "stable_output_file_policy") == "FAIL"


def test_stage_report_missing_warns_by_default(tmp_path: Path) -> None:
    project = _write_valid_project(tmp_path)
    (project / "reports/book_l2/book_l2_05_api_readiness_review_report.md").unlink()

    result = _run(project)

    assert result.status == "PASS_WITH_WARNINGS"
    assert _check_status(result, "stage_reports_exist") == "WARN"


def test_planning_missing_l2_freeze_text_warns_by_default(tmp_path: Path) -> None:
    project = _write_valid_project(tmp_path)
    (project / "planning/02_CURRENT_TASK.md").write_text("BOOK-L2-04 done\n", encoding="utf-8")
    for path in (
        "planning/01_CURRENT_STATE.md",
        "planning/03_REMAINING_WORK.md",
        "planning/07_BOOK_L2_MARKET_INTERPRETER_PLAN.md",
    ):
        (project / path).write_text("BOOK-L2 older state\n", encoding="utf-8")

    result = _run(project)

    assert result.status == "PASS_WITH_WARNINGS"
    assert _check_status(result, "planning_updated") == "WARN"


def test_strict_mode_converts_warnings_to_fail(tmp_path: Path) -> None:
    project = _write_valid_project(tmp_path)
    (project / "reports/book_l2/book_l2_05_api_readiness_review_report.md").unlink()

    result = _run(project, strict=True)

    assert result.status == "FAIL"
    assert result.freeze_candidate is False


def test_freeze_candidate_true_only_when_result_pass(tmp_path: Path) -> None:
    assert _run(_write_valid_project(tmp_path)).freeze_candidate is True


def test_freeze_candidate_false_when_any_safety_check_fails(tmp_path: Path) -> None:
    project = _write_valid_project(tmp_path)
    payload = _valid_l2_payload()
    payload["safety"]["orders_enabled"] = True  # type: ignore[index]
    _write_json(project / "reports/book_l2/timeline_context.json", payload)

    result = _run(project)

    assert result.freeze_candidate is False


def test_formatter_includes_result_pass(tmp_path: Path) -> None:
    output = L2ApiReadinessFormatter().format(_run(_write_valid_project(tmp_path)))

    assert "BOOK-L2 API Readiness Review" in output
    assert "Result: PASS" in output


def test_formatter_includes_freeze_candidate_yes(tmp_path: Path) -> None:
    output = L2ApiReadinessFormatter().format(_run(_write_valid_project(tmp_path)))

    assert "Freeze candidate: YES" in output


def test_details_output_includes_modules_json_and_safety(tmp_path: Path) -> None:
    output = L2ApiReadinessFormatter().format(_run(_write_valid_project(tmp_path)), show_details=True)

    assert "Details:" in output
    assert "Modules:" in output
    assert "JSON:" in output
    assert "Safety:" in output
    assert "Forbidden imports:" in output


def test_json_output_is_serializable(tmp_path: Path) -> None:
    payload = L2ApiReadinessFormatter().to_json_payload(_run(_write_valid_project(tmp_path)))

    decoded = json.loads(json.dumps(payload))

    assert decoded["status"] == "PASS"
    assert decoded["freeze_candidate"] is True
    assert decoded["checks"]


def test_cli_parser_supports_json_stdout(tmp_path: Path) -> None:
    project = _write_valid_project(tmp_path)

    result = CliRunner().invoke(cli, ["book-l2-api-readiness-review", "--project-root", str(project), "--json"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["status"] == "PASS"


def test_cli_parser_supports_show_details(tmp_path: Path) -> None:
    project = _write_valid_project(tmp_path)

    result = CliRunner().invoke(cli, ["book-l2-api-readiness-review", "--project-root", str(project), "--show-details"])

    assert result.exit_code == 0
    assert "Details:" in result.stdout


def _run(project_root: Path, *, strict: bool = False):
    return L2ApiReadinessReviewer().run(L2ApiReadinessConfig(project_root=project_root, strict=strict))


def _check_status(result, name: str) -> str | None:
    for check in result.checks:
        if check.name == name:
            return check.status
    return None


def _write_valid_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    required_files = (
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
    )
    for relative_path in required_files:
        path = project / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# fixture\n", encoding="utf-8")

    cli_path = project / "app/cli/commands.py"
    cli_path.parent.mkdir(parents=True, exist_ok=True)
    cli_path.write_text(
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

    l1_path = project / "reports/book_l1/timeline_preview.json"
    l1_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(l1_path, {"status": "ok"})
    _write_json(project / "reports/book_l2/timeline_context.json", _valid_l2_payload())
    return project


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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
                {
                    "symbol": "BTCUSDT",
                    "status": "OK",
                    "current_regime": "UP",
                    "stability": "STABLE",
                    "last_transition": "NO_CHANGE",
                    "confidence": 0.8,
                    "current_confidence": 0.8,
                    "current_trend_strength": "MODERATE",
                    "bucket": "CLEAN_TREND",
                    "skip_candidate": False,
                    "context_quality_score": 0.82,
                    "context_quality_grade": "HIGH",
                    "context_rank": 1,
                    "context_quality_reason_codes": ["CONTEXT_QUALITY_SCORED"],
                    "context_reason_codes": ["CONTEXT_RULE_MATCHED"],
                    "trade_signal": "NOT_EVALUATED",
                    "safe_for_runtime_trading": False,
                    "context_label": "CLEAN_TREND",
                    "observe_reason": "observe only",
                    "warnings": [],
                }
            ],
            "summary": {
                "bucket_summary": {"CLEAN_TREND": 1},
                "quality_summary": {"HIGH": 1},
                "top_ranked_symbols": ["BTCUSDT"],
            },
            "market_context": {"overall_state": "MIXED", "symbol_count": 1},
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
                "skip_candidates": [],
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
