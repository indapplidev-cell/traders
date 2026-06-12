import json
from pathlib import Path

from typer.testing import CliRunner

from app.cli import commands
from app.cli.commands import cli
from app.experiments.label_grid_result_analyzer import LabelGridResultAnalyzer


def test_label_grid_results_analyze_cli_latest_and_explicit_dir(
    tmp_path: Path,
    monkeypatch,
) -> None:
    experiment_dir = tmp_path / "exp_cli"
    experiment_dir.mkdir(parents=True)
    (experiment_dir / "label_grid_experiment_summary.json").write_text(
        json.dumps(_sample_summary()),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        LabelGridResultAnalyzer,
        "latest_experiment_dir",
        staticmethod(lambda root_dir=Path("reports/label_grid_experiments"): experiment_dir),
    )

    runner = CliRunner()
    latest_result = runner.invoke(cli, ["label-grid-results-analyze", "--latest"])
    explicit_result = runner.invoke(
        cli,
        ["label-grid-results-analyze", "--experiment-dir", str(experiment_dir)],
    )

    assert latest_result.exit_code == 0
    assert explicit_result.exit_code == 0

    latest_payload = json.loads(latest_result.stdout)
    explicit_payload = json.loads(explicit_result.stdout)

    assert latest_payload["experiment_id"] == "exp_cli"
    assert explicit_payload["experiment_id"] == "exp_cli"
    assert latest_payload["approved_for_live_trading"] is False
    assert explicit_payload["traders_core_connected"] is False
    assert (experiment_dir / "label_grid_result_analysis.json").exists()
    assert (experiment_dir / "label_grid_result_analysis.md").exists()


def _sample_summary() -> dict:
    return {
        "experiment_id": "exp_cli",
        "experiment_status": "COMPLETED_NO_ACCEPTED_CANDIDATE",
        "config_count": 1,
        "accepted_candidate_count": 0,
        "rejected_candidate_count": 1,
        "best_candidate_config_id": "cfg_cli",
        "best_candidate_status": "CANDIDATE_REJECTED",
        "best_candidate_score": -0.9,
        "candidate_ranking": [
            {
                "rank": 1,
                "config_id": "cfg_cli",
                "score": -0.9,
                "candidate_status": "CANDIDATE_REJECTED",
                "quality_status": "QUALITY_REJECTED",
                "failed_gates": ["collapse_gate", "gap_quality_gate"],
            }
        ],
        "candidate_results": [
            {
                "config_id": "cfg_cli",
                "candidate_status": "CANDIDATE_REJECTED",
                "quality_status": "QUALITY_REJECTED",
                "accuracy_edge": 0.002,
                "collapse_detected": True,
                "collapse_type": "MIXED_COLLAPSE",
                "profit_factor": 1.02,
                "profit_total_r": 0.8,
                "walk_forward_global_total_r": -0.2,
                "walk_forward_profit_factor": 0.99,
                "failed_gates": ["collapse_gate", "gap_quality_gate"],
                "recommendations": ["review labels"],
            }
        ],
        "recommendations": ["base"],
    }
