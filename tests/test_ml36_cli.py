import json

from typer.testing import CliRunner

from app.cli import commands
from app.cli.commands import cli


def test_ml36_cli_commands_return_json_and_keep_safety_flags_disabled(monkeypatch) -> None:
    monkeypatch.setattr(
        commands,
        "build_collapse_diagnostics_preview_payload",
        lambda: {
            "collapse_detected": True,
            "collapse_type": "MIXED_COLLAPSE",
            "dominant_class": "UP",
            "flat_prediction_rate": 0.02,
            "flat_underprediction_detected": True,
            "low_margin_detected": True,
            "recommendations": ["Increase flat-aware labeling/calibration or add flat threshold diagnostics."],
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "orders_enabled": False,
            "traders_core_connected": False,
        },
    )
    monkeypatch.setattr(
        commands,
        "build_regime_label_builder_preview_payload",
        lambda: {
            "regime_label_builder_available": True,
            "regime_label_builder_used_in_training": True,
            "regime_specific_labeling_available": True,
            "regime_specific_training_applied": True,
            "label_distribution_by_regime": {"trend_up": {"UP": 5, "DOWN": 0, "FLAT": 2}},
            "missing_requirements": [],
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "orders_enabled": False,
            "traders_core_connected": False,
        },
    )
    monkeypatch.setattr(
        commands,
        "build_walk_forward_profit_diagnostics_preview_payload",
        lambda: {
            "walk_forward_profit_factor": 0.96,
            "walk_forward_total_r": -2.4,
            "fold_count": 4,
            "profitable_fold_count": 1,
            "unprofitable_fold_count": 3,
            "worst_fold": {"fold_index": 3},
            "recommendations": ["Audit temporal stability because walk-forward profit factor is not yet above 1.0."],
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "orders_enabled": False,
            "traders_core_connected": False,
        },
    )

    runner = CliRunner()
    outputs = [
        runner.invoke(cli, ["collapse-diagnostics-preview"]),
        runner.invoke(cli, ["regime-label-builder-preview"]),
        runner.invoke(cli, ["walk-forward-profit-diagnostics-preview"]),
    ]

    for result in outputs:
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["approved_for_live_trading"] is False
        assert payload["approved_for_auto_activation"] is False
        assert payload["orders_enabled"] is False
        assert payload["traders_core_connected"] is False
