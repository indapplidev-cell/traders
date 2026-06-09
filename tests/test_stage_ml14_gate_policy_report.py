from pathlib import Path


def test_stage_ml14_gate_policy_report_exists_and_documents_scope() -> None:
    report_path = Path("reports/stage_ml14_gate_policy_report.md")

    assert report_path.exists()

    text = report_path.read_text(encoding="utf-8")

    required_phrases = [
        "Stage ML14",
        "GatePolicy",
        "GatePolicyService",
        "GatePolicyDiagnosticsService",
        "GatePolicyReporter",
        "gate-policy-smoke",
        "gate-policy-export",
        "111 passed",
        "does not trade",
        "does not connect to traders-core",
        "runtime artifact",
    ]

    for phrase in required_phrases:
        assert phrase in text
