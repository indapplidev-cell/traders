import json
from pathlib import Path

from app.experiments.label_grid_result_analyzer import LabelGridResultAnalyzer
from app.experiments.label_grid_result_reporter import LabelGridResultReporter


def test_label_grid_result_reporter_creates_markdown_table(tmp_path: Path) -> None:
    reporter = LabelGridResultReporter()
    analysis = LabelGridResultAnalyzer().analyze(_sample_summary())

    markdown_path = reporter.write_analysis_markdown(analysis, tmp_path / "analysis.md")
    text = markdown_path.read_text(encoding="utf-8")

    assert "| Rank | Config | Score | Candidate | Quality | Accuracy Edge | Collapse | Profit Factor | Walk-Forward PF | Failed Gates | Recommendation |" in text
    assert "no traders-core integration" in text


def test_label_grid_result_reporter_writes_json_and_plan(tmp_path: Path) -> None:
    reporter = LabelGridResultReporter()
    analysis = LabelGridResultAnalyzer().analyze(_sample_summary())
    plan = {
        "planner_name": analysis["planner_name"],
        "planner_version": analysis["planner_version"],
        "experiment_id": analysis["experiment_id"],
        "recommendations": analysis["recommendations"],
        "next_experiment_plan": analysis["next_experiment_plan"],
    }

    analysis_json = reporter.write_analysis_json(analysis, tmp_path / "analysis.json")
    plan_json = reporter.write_plan_json(plan, tmp_path / "plan.json")

    assert json.loads(analysis_json.read_text(encoding="utf-8"))["experiment_id"] == "exp_report"
    assert json.loads(plan_json.read_text(encoding="utf-8"))["planner_name"]


def _sample_summary() -> dict:
    return {
        "experiment_id": "exp_report",
        "experiment_status": "COMPLETED_NO_ACCEPTED_CANDIDATE",
        "config_count": 1,
        "accepted_candidate_count": 0,
        "rejected_candidate_count": 1,
        "best_candidate_config_id": "cfg_1",
        "best_candidate_status": "CANDIDATE_REJECTED",
        "best_candidate_score": -1.0,
        "candidate_ranking": [
            {
                "rank": 1,
                "config_id": "cfg_1",
                "score": -1.0,
                "candidate_status": "CANDIDATE_REJECTED",
                "quality_status": "QUALITY_REJECTED",
                "failed_gates": ["collapse_gate"],
            }
        ],
        "candidate_results": [
            {
                "config_id": "cfg_1",
                "candidate_status": "CANDIDATE_REJECTED",
                "quality_status": "QUALITY_REJECTED",
                "accuracy_edge": 0.001,
                "collapse_detected": True,
                "collapse_type": "MIXED_COLLAPSE",
                "profit_factor": 0.9,
                "profit_total_r": -2.0,
                "walk_forward_global_total_r": -1.0,
                "walk_forward_profit_factor": 0.95,
                "failed_gates": ["collapse_gate"],
                "recommendations": ["review labels"],
            }
        ],
        "recommendations": ["base"],
    }
