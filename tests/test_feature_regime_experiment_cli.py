import json
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import cli
from app.experiments.feature_regime_result_analyzer import FeatureRegimeResultAnalyzer


def test_feature_regime_experiment_preview_and_run_cli(tmp_path: Path) -> None:
    runner = CliRunner()

    preview = runner.invoke(cli, ["feature-regime-experiment-preview"])
    dry_run = runner.invoke(
        cli,
        [
            "feature-regime-experiment-run",
            "--symbol",
            "BTCUSDT",
            "--interval",
            "15m",
            "--start-date",
            "2025-01-01",
            "--experiment-id",
            "fr_dry_cli",
            "--dry-run",
            "--output-dir",
            str(tmp_path),
        ],
    )
    sample_run = runner.invoke(
        cli,
        [
            "feature-regime-experiment-run",
            "--symbol",
            "BTCUSDT",
            "--interval",
            "15m",
            "--start-date",
            "2025-01-01",
            "--experiment-id",
            "fr_sample_cli",
            "--sample-mode",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert preview.exit_code == 0
    assert dry_run.exit_code == 0
    assert sample_run.exit_code == 0

    preview_payload = json.loads(preview.stdout)
    dry_payload = json.loads(dry_run.stdout)
    sample_payload = json.loads(sample_run.stdout)

    assert "available_base_label_configs" in preview_payload
    assert dry_payload["experiment_status"] == "DRY_RUN_COMPLETED"
    assert sample_payload["experiment_status"] == "SAMPLE_COMPLETED"
    for payload in (dry_payload, sample_payload):
        assert payload["approved_for_live_trading"] is False
        assert payload["approved_for_auto_activation"] is False
        assert payload["orders_enabled"] is False
        assert payload["traders_core_connected"] is False


def test_feature_regime_results_analyze_cli_explicit_and_latest(tmp_path: Path, monkeypatch) -> None:
    experiment_dir = tmp_path / "fr_analysis"
    experiment_dir.mkdir(parents=True)
    (experiment_dir / "feature_regime_experiment_summary.json").write_text(
        json.dumps(
            {
                "experiment_id": "fr_analysis",
                "experiment_status": "SAMPLE_COMPLETED",
                "config_count": 2,
                "candidate_count": 2,
                "accepted_candidate_count": 0,
                "rejected_candidate_count": 2,
                "best_candidate_config_id": "cfg_1",
                "best_candidate_score": -6.1,
                "feature_quality_summary": {"weak_signal_detected": True},
                "regime_feature_summary": {"regime_data_available": True},
                "regime_training_applied": False,
                "feature_leakage_summary": {"leakage_risk_detected": False},
                "failed_gates_summary": {
                    "collapse_gate": 2,
                    "baseline_edge_gate": 1,
                    "walk_forward_gate": 2,
                    "profit_aware_gate": 1,
                },
                "baseline_reference": {
                    "experiment_id": "ml31",
                    "best_candidate_score": -6.372101,
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        FeatureRegimeResultAnalyzer,
        "latest_experiment_dir",
        staticmethod(lambda root_dir=Path("reports/feature_regime_experiments"): experiment_dir),
    )

    runner = CliRunner()
    explicit_result = runner.invoke(
        cli,
        ["feature-regime-results-analyze", "--experiment-dir", str(experiment_dir)],
    )
    latest_result = runner.invoke(cli, ["feature-regime-results-analyze", "--latest"])

    assert explicit_result.exit_code == 0
    assert latest_result.exit_code == 0

    explicit_payload = json.loads(explicit_result.stdout)
    latest_payload = json.loads(latest_result.stdout)
    assert explicit_payload["experiment_id"] == "fr_analysis"
    assert latest_payload["experiment_id"] == "fr_analysis"
    assert explicit_payload["approved_for_live_trading"] is False
    assert explicit_payload["approved_for_auto_activation"] is False
    assert explicit_payload["orders_enabled"] is False
    assert explicit_payload["traders_core_connected"] is False
