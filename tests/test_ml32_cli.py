import json

from typer.testing import CliRunner

from app.cli.commands import (
    build_feature_group_quality_preview_payload,
    build_feature_leakage_guard_preview_payload,
    build_regime_experiment_plan_preview_payload,
    build_regime_feature_diagnostics_preview_payload,
    build_regime_label_config_preview_payload,
    cli,
)


def test_build_ml32_preview_payloads() -> None:
    payloads = [
        build_regime_feature_diagnostics_preview_payload(),
        build_feature_group_quality_preview_payload(),
        build_regime_label_config_preview_payload(),
        build_regime_experiment_plan_preview_payload(),
        build_feature_leakage_guard_preview_payload(),
    ]

    for payload in payloads:
        assert payload["approved_for_live_trading"] is False
        assert payload["approved_for_auto_activation"] is False
        assert payload["orders_enabled"] is False
        assert payload["traders_core_connected"] is False


def test_ml32_preview_cli_commands_output_json() -> None:
    runner = CliRunner()

    for command_name, key in [
        ("regime-feature-diagnostics-preview", "diagnostic_name"),
        ("feature-group-quality-preview", "group_name"),
        ("regime-label-config-preview", "planner_name"),
        ("regime-experiment-plan-preview", "planner_name"),
        ("feature-leakage-guard-preview", "guard_name"),
    ]:
        result = runner.invoke(cli, [command_name])

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert key in payload
        assert payload["approved_for_live_trading"] is False
        assert payload["approved_for_auto_activation"] is False
        assert payload["orders_enabled"] is False
        assert payload["traders_core_connected"] is False
