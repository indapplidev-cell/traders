from app.evaluation.gap_quality_gate_normalizer import normalize_gap_quality_gate


def test_ok_training_safe_dataset_report_passes_gap_gate() -> None:
    failed, passed = normalize_gap_quality_gate(
        gap_severity_for_training="OK",
        gap_training_safe=True,
        failed_gates=["gap_quality_gate", "collapse_gate"],
        passed_gates=[],
    )

    assert "gap_quality_gate" not in failed
    assert "gap_quality_gate" in passed


def test_critical_training_unsafe_dataset_report_fails_gap_gate() -> None:
    failed, passed = normalize_gap_quality_gate(
        gap_severity_for_training="CRITICAL",
        gap_training_safe=False,
        failed_gates=[],
        passed_gates=["gap_quality_gate"],
    )

    assert "gap_quality_gate" in failed
    assert "gap_quality_gate" not in passed
