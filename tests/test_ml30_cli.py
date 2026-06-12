import json

from typer.testing import CliRunner

from app.cli.commands import (
    build_anti_collapse_training_plan_preview_payload,
    build_candidate_thresholds_preview_payload,
    build_feature_quality_preview_payload,
    build_gap_aware_filter_preview_payload,
    cli,
)


def test_build_ml30_preview_payloads() -> None:
    gap_payload = build_gap_aware_filter_preview_payload()
    feature_payload = build_feature_quality_preview_payload()
    anti_payload = build_anti_collapse_training_plan_preview_payload()
    threshold_payload = build_candidate_thresholds_preview_payload()

    assert gap_payload["filter_version"] == "ml30"
    assert gap_payload["excluded_rows"] == 3
    assert feature_payload["diagnostic_version"] == "ml30"
    assert anti_payload["plan_version"] == "ml30"
    assert threshold_payload["threshold_version"] == "ml30"
    assert threshold_payload["gap_examples"]["HIGH_allowed"] is False


def test_ml30_preview_cli_commands_output_json() -> None:
    runner = CliRunner()

    for command_name, key in [
        ("gap-aware-filter-preview", "filter_name"),
        ("feature-quality-preview", "diagnostic_name"),
        ("anti-collapse-training-plan-preview", "plan_name"),
        ("candidate-thresholds-preview", "threshold_name"),
    ]:
        result = runner.invoke(cli, [command_name])

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert key in payload
