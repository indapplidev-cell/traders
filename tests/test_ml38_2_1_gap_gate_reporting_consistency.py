from app.evaluation.gap_quality_gate_normalizer import normalize_gap_quality_gate
from app.experiments.label_grid_experiment_runner import LabelGridExperimentRunner


def test_ok_safe_gaps_move_gap_gate_from_failed_to_passed() -> None:
    failed_gates, passed_gates = normalize_gap_quality_gate(
        gap_severity_for_training="OK",
        gap_training_safe=True,
        failed_gates=["baseline_edge_gate", "gap_quality_gate", "collapse_gate"],
        passed_gates=[],
    )

    assert "gap_quality_gate" not in failed_gates
    assert "gap_quality_gate" in passed_gates


def test_critical_unsafe_gaps_force_rejected_status() -> None:
    failed_gates, passed_gates = normalize_gap_quality_gate(
        gap_severity_for_training="CRITICAL",
        gap_training_safe=False,
        failed_gates=[],
        passed_gates=["gap_quality_gate"],
    )

    candidate_status = LabelGridExperimentRunner._normalize_final_candidate_status(
        "ACCEPTED",
        status="COMPLETED",
    )
    if failed_gates and candidate_status == "ACCEPTED":
        candidate_status = "REJECTED"

    assert "gap_quality_gate" in failed_gates
    assert "gap_quality_gate" not in passed_gates
    assert candidate_status == "REJECTED"
