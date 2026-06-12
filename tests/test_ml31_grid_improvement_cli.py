import json
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import cli
from app.experiments.ml31_grid_improvement_analyzer import ML31GridImprovementAnalyzer


def test_ml31_grid_improvement_cli_current_experiment_dir_and_latest(
    tmp_path: Path,
    monkeypatch,
) -> None:
    experiment_dir = tmp_path / "exp_ml31"
    experiment_dir.mkdir(parents=True)
    (experiment_dir / "label_grid_experiment_summary.json").write_text(
        json.dumps(
            {
                "experiment_id": "exp_ml31",
                "config_count": 3,
                "accepted_candidate_count": 0,
                "rejected_candidate_count": 3,
                "best_candidate_config_id": "cfg_best",
                "best_candidate_score": -6.3,
            }
        ),
        encoding="utf-8",
    )
    (experiment_dir / "label_grid_result_analysis.json").write_text(
        json.dumps(
            {
                "experiment_id": "exp_ml31",
                "best_candidate_score": -6.3,
                "gate_failure_counts": {
                    "collapse_gate": 3,
                    "profit_aware_gate": 2,
                    "walk_forward_gate": 2,
                    "gap_quality_gate": 3,
                },
                "baseline_edge_summary": {
                    "above_threshold_count": 0,
                    "best_accuracy_edge": 0.004,
                },
                "top_failed_gate": "collapse_gate",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        ML31GridImprovementAnalyzer,
        "latest_experiment_dir",
        staticmethod(lambda root_dir=Path("reports/label_grid_experiments"): experiment_dir),
    )

    runner = CliRunner()
    explicit_result = runner.invoke(
        cli,
        ["ml31-grid-improvement-analyze", "--current-experiment-dir", str(experiment_dir)],
    )
    latest_result = runner.invoke(cli, ["ml31-grid-improvement-analyze", "--latest"])

    assert explicit_result.exit_code == 0
    assert latest_result.exit_code == 0

    explicit_payload = json.loads(explicit_result.stdout)
    latest_payload = json.loads(latest_result.stdout)

    assert explicit_payload["current_experiment_id"] == "exp_ml31"
    assert latest_payload["current_experiment_id"] == "exp_ml31"
    assert explicit_payload["approved_for_live_trading"] is False
    assert explicit_payload["approved_for_auto_activation"] is False
    assert explicit_payload["orders_enabled"] is False
    assert explicit_payload["traders_core_connected"] is False
