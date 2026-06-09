from pathlib import Path


def test_stage_ml15_gate_policy_adapter_report_exists_and_documents_scope() -> None:
    report_path = Path("reports/stage_ml15_gate_policy_adapter_report.md")

    assert report_path.exists()

    text = report_path.read_text(encoding="utf-8")

    required_phrases = [
        "Stage ML15",
        "GatePolicy Adapter Layer",
        "GatePolicyEvaluationAdapter",
        "GatePolicyAdapterDiagnosticsService",
        "GatePolicyAdapterReporter",
        "gate-policy-adapter-preview",
        "gate-policy-adapter-export",
        "raw dict payloads",
        "GatePolicyInput",
        "GatePolicyDiagnosticsReport",
        "131 passed",
        "runtime artifact",
        "does not connect GatePolicy to trading execution",
        "Stage ML16.1",
    ]

    for phrase in required_phrases:
        assert phrase in text
