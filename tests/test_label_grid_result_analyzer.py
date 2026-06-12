import json
from pathlib import Path

from app.experiments.label_grid_result_analyzer import LabelGridResultAnalyzer


def test_label_grid_result_analyzer_counts_gate_failures_and_best_candidate() -> None:
    analyzer = LabelGridResultAnalyzer()

    payload = analyzer.analyze(_sample_summary())

    assert payload["best_candidate_config_id"] == "cfg_b"
    assert payload["best_candidate_status"] == "CANDIDATE_REJECTED"
    assert payload["gate_failure_counts"]["collapse_gate"] == 2
    assert payload["gate_failure_counts"]["profit_aware_gate"] == 1
    assert payload["top_failed_gate"] == "collapse_gate"


def test_label_grid_result_analyzer_can_load_latest_experiment_dir(tmp_path: Path) -> None:
    root = tmp_path / "reports" / "label_grid_experiments"
    older = root / "older"
    newer = root / "newer"
    older.mkdir(parents=True)
    newer.mkdir(parents=True)
    (older / "label_grid_experiment_summary.json").write_text(
        json.dumps(_sample_summary()),
        encoding="utf-8",
    )
    (newer / "label_grid_experiment_summary.json").write_text(
        json.dumps(_sample_summary(experiment_id="newer")),
        encoding="utf-8",
    )

    latest = LabelGridResultAnalyzer.latest_experiment_dir(root)
    loaded = LabelGridResultAnalyzer.load_summary(latest)

    assert latest.name == "newer"
    assert loaded["experiment_id"] == "newer"


def _sample_summary(*, experiment_id: str = "exp_1") -> dict:
    return {
        "experiment_id": experiment_id,
        "experiment_status": "COMPLETED_NO_ACCEPTED_CANDIDATE",
        "config_count": 2,
        "accepted_candidate_count": 0,
        "rejected_candidate_count": 2,
        "best_candidate_config_id": "cfg_b",
        "best_candidate_status": "CANDIDATE_REJECTED",
        "best_candidate_score": -1.25,
        "candidate_ranking": [
            {
                "rank": 1,
                "config_id": "cfg_b",
                "score": -1.25,
                "candidate_status": "CANDIDATE_REJECTED",
                "quality_status": "QUALITY_REJECTED",
                "failed_gates": ["collapse_gate", "gap_quality_gate"],
            },
            {
                "rank": 2,
                "config_id": "cfg_a",
                "score": -2.0,
                "candidate_status": "CANDIDATE_REJECTED",
                "quality_status": "QUALITY_REJECTED",
                "failed_gates": ["collapse_gate", "profit_aware_gate", "walk_forward_gate"],
            },
        ],
        "candidate_results": [
            {
                "config_id": "cfg_a",
                "candidate_status": "CANDIDATE_REJECTED",
                "quality_status": "QUALITY_REJECTED",
                "accuracy_edge": 0.001,
                "collapse_detected": True,
                "collapse_type": "MIXED_COLLAPSE",
                "profit_factor": 0.92,
                "profit_total_r": -4.0,
                "walk_forward_global_total_r": -2.0,
                "walk_forward_profit_factor": 0.96,
                "failed_gates": ["collapse_gate", "profit_aware_gate", "walk_forward_gate"],
                "recommendations": ["fix_profit"],
            },
            {
                "config_id": "cfg_b",
                "candidate_status": "CANDIDATE_REJECTED",
                "quality_status": "QUALITY_REJECTED",
                "accuracy_edge": 0.003,
                "collapse_detected": True,
                "collapse_type": "MIXED_COLLAPSE",
                "profit_factor": 1.05,
                "profit_total_r": 1.2,
                "walk_forward_global_total_r": -0.5,
                "walk_forward_profit_factor": 0.99,
                "failed_gates": ["collapse_gate", "gap_quality_gate"],
                "recommendations": ["fix_gaps"],
            },
        ],
        "recommendations": ["base_recommendation"],
    }
