from pathlib import Path


REPORT_PATH = Path(
    "reports/stage_ml38_10_37_flat_majority_directional_recoverability_audit_report.md"
)


def test_stage_report_documents_scope_tests_and_prohibitions() -> None:
    assert REPORT_PATH.is_file()
    text = REPORT_PATH.read_text(encoding="utf-8")

    required = (
        "ML38.10.37",
        "FLAT ≈ 92%",
        "diagnostic-only",
        "flat_majority_directional_recoverability_audit",
        "baseline_edge_gate_explanation",
        "top_candidate_gate_blocker_board",
        "directional_recoverability_decision",
        "test_ml38_10_37_flat_majority_directional_recoverability_audit.py",
        "test_stage_ml38_10_37_report.py",
        "python -m py_compile",
        "python -m pytest",
        "runtime training was not run",
        "clean/fast/quick/sequence/full were not run",
        "labels, label builder behavior, gates, and model logic were not changed",
        "live trading and auto-activation were not changed",
    )
    for item in required:
        assert item in text
