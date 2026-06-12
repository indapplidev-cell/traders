import json
from pathlib import Path

from app.experiments.label_grid_experiment_reporter import LabelGridExperimentReporter
from app.experiments.label_grid_experiment_runner import (
    LabelGridExperimentConfig,
    LabelGridExperimentRunner,
)


def test_label_grid_experiment_reporter_includes_ranking_and_safety(tmp_path: Path) -> None:
    runner = LabelGridExperimentRunner()
    reporter = LabelGridExperimentReporter()
    result = runner.run(
        LabelGridExperimentConfig(
            symbol="BTCUSDT",
            interval="15m",
            start_date="2025-01-01",
            max_configs=2,
            sample_mode=True,
            output_dir=tmp_path,
        )
    )

    payload = reporter.result_to_dict(result)
    compact = reporter.compact_summary_to_dict(result)

    assert payload["candidate_ranking"]
    assert compact["experiment_status"] == "SAMPLE_COMPLETED"

    markdown_path = reporter.write_markdown_summary(result)
    text = markdown_path.read_text(encoding="utf-8")
    assert "Candidate Ranking" in text
    assert "| Rank | Config | Candidate | Quality | Score | Failed Gates |" in text
    assert "no traders-core integration" in text
    assert "no live trading" in text


def test_label_grid_experiment_reporter_writes_candidate_json_and_markdown(
    tmp_path: Path,
) -> None:
    runner = LabelGridExperimentRunner()
    reporter = LabelGridExperimentReporter()
    result = runner.run(
        LabelGridExperimentConfig(
            symbol="BTCUSDT",
            interval="15m",
            start_date="2025-01-01",
            max_configs=1,
            sample_mode=True,
            output_dir=tmp_path,
        )
    )
    candidate = result.candidate_results[0]

    json_path = reporter.write_candidate_json(candidate, tmp_path / "candidate.json")
    markdown_path = reporter.write_candidate_markdown(candidate, tmp_path / "candidate.md")

    assert json.loads(json_path.read_text(encoding="utf-8"))["config_id"] == candidate.config_id
    assert "approved_for_live_trading" in markdown_path.read_text(encoding="utf-8")
