import json
from pathlib import Path

from app.experiments.label_grid_experiment_runner import (
    LabelGridExperimentConfig,
    LabelGridExperimentRunner,
)


def test_label_grid_experiment_runner_dry_run_creates_runtime_outputs(tmp_path: Path) -> None:
    runner = LabelGridExperimentRunner()

    result = runner.run(
        LabelGridExperimentConfig(
            symbol="BTCUSDT",
            interval="15m",
            start_date="2025-01-01",
            max_configs=2,
            dry_run=True,
            output_dir=tmp_path,
        )
    )

    payload = result.to_dict()

    assert result.experiment_status == "DRY_RUN_COMPLETED"
    assert result.config_count == 2
    assert len(result.candidate_results) == 2
    assert result.completed_candidate_count == 0
    assert Path(result.log_path).exists()
    assert Path(result.events_path).exists()
    assert Path(result.summary_json_path).exists()
    assert Path(result.summary_markdown_path).exists()
    assert result.approved_for_live_trading is False
    assert result.approved_for_auto_activation is False
    assert result.orders_enabled is False
    assert result.traders_core_connected is False
    json.dumps(payload, ensure_ascii=False, sort_keys=True)


def test_label_grid_experiment_runner_sample_mode_creates_candidate_results(tmp_path: Path) -> None:
    runner = LabelGridExperimentRunner()

    result = runner.run(
        LabelGridExperimentConfig(
            symbol="BTCUSDT",
            interval="15m",
            start_date="2025-01-01",
            max_configs=3,
            sample_mode=True,
            output_dir=tmp_path,
        )
    )

    assert result.experiment_status == "SAMPLE_COMPLETED"
    assert len(result.candidate_results) == 3
    assert result.completed_candidate_count == 3
    assert Path(result.candidate_results_dir).exists()
    for candidate in result.candidate_results:
        assert candidate.status == "COMPLETED"
        assert candidate.approved_for_live_trading is False
        assert candidate.approved_for_auto_activation is False
        assert candidate.orders_enabled is False
        assert candidate.traders_core_connected is False
        assert (Path(result.candidate_results_dir) / f"{candidate.config_id}.json").exists()
        assert (Path(result.candidate_results_dir) / f"{candidate.config_id}.md").exists()

    events = Path(result.events_path).read_text(encoding="utf-8")
    assert "candidate_completed" in events
    assert "experiment_completed" in events
