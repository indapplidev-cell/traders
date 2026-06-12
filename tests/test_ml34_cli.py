import json

from typer.testing import CliRunner

from app.cli import commands
from app.cli.commands import cli


def test_ml34_cli_commands_return_json_and_keep_safety_flags_disabled(monkeypatch) -> None:
    monkeypatch.setattr(
        commands,
        "build_gap_quality_preview_payload",
        lambda: {
            "gap_count": 1,
            "real_gap_count": 0,
            "trailing_incomplete_count": 1,
            "trailing_incomplete_range_detected": True,
            "effective_gap_count_for_training": 0,
            "gap_severity_for_training": "OK",
            "dataset_safe_for_training": True,
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "orders_enabled": False,
            "traders_core_connected": False,
        },
    )
    monkeypatch.setattr(
        commands,
        "build_real_feature_diagnostics_preview_payload",
        lambda: {
            "sample_mode": False,
            "degraded_mode": False,
            "row_count": 12,
            "feature_count": 20,
            "feature_version": "fv2",
            "feature_group_quality": {},
            "leakage_guard": {},
            "regime_feature_diagnostics": {},
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "orders_enabled": False,
            "traders_core_connected": False,
        },
    )
    monkeypatch.setattr(
        commands,
        "build_feature_regime_integration_preview_payload",
        lambda: {
            "feature_version_available": True,
            "feature_version_used": "fv2",
            "regime_features_attached": True,
            "regime_feature_count": 6,
            "regime_specific_labeling_available": True,
            "regime_specific_training_applied": False,
            "missing_requirements": ["regime_specific_label_builder_not_wired_into_training_pipeline"],
            "next_steps": ["Wire regime-specific label selection into the real training pipeline before claiming applied training."],
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "orders_enabled": False,
            "traders_core_connected": False,
        },
    )

    runner = CliRunner()
    outputs = [
        runner.invoke(cli, ["gap-quality-preview"]),
        runner.invoke(cli, ["real-feature-diagnostics-preview"]),
        runner.invoke(cli, ["feature-regime-integration-preview"]),
    ]

    for result in outputs:
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["approved_for_live_trading"] is False
        assert payload["approved_for_auto_activation"] is False
        assert payload["orders_enabled"] is False
        assert payload["traders_core_connected"] is False
