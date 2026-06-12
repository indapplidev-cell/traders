import json
from pathlib import Path

from app.experiments.ml31_grid_improvement_reporter import ML31GridImprovementReporter


def test_ml31_grid_improvement_reporter_writes_json_and_markdown(tmp_path: Path) -> None:
    reporter = ML31GridImprovementReporter()
    payload = {
        "current_experiment_id": "ml31_current",
        "previous_experiment_id": "ml29_previous",
        "current_best_candidate_config_id": "cfg_best",
        "current_best_candidate_score": -2.0,
        "previous_best_candidate_score": -3.7,
        "current_accepted_candidate_count": 1,
        "current_rejected_candidate_count": 2,
        "overall_improvement_status": "PARTIAL_IMPROVEMENT",
        "accepted_candidate_improved": True,
        "baseline_edge_improved": True,
        "collapse_improved": True,
        "profit_aware_improved": False,
        "walk_forward_improved": False,
        "gap_quality_improved": False,
        "recommendations": ["Keep research mode only."],
    }
    json_path = tmp_path / "ml31_grid_improvement_analysis.json"
    markdown_path = tmp_path / "ml31_grid_improvement_analysis.md"

    reporter.write_analysis_json(payload, json_path)
    reporter.write_analysis_markdown(payload, markdown_path)

    assert json.loads(json_path.read_text(encoding="utf-8"))["overall_improvement_status"] == "PARTIAL_IMPROVEMENT"
    text = markdown_path.read_text(encoding="utf-8")
    assert "PARTIAL_IMPROVEMENT" in text
    assert "## Safety" in text

