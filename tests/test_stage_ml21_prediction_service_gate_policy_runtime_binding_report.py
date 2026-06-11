from pathlib import Path


def test_stage_ml21_prediction_service_gate_policy_runtime_binding_report_exists_and_documents_scope() -> None:
    report_path = Path(
        "reports/stage_ml21_prediction_service_gate_policy_runtime_binding_report.md"
    )

    assert report_path.exists()

    text = report_path.read_text(encoding="utf-8")

    required_phrases = [
        "Stage ML21",
        "PredictionService to GatePolicy Runtime Binding",
        "app/gates/gate_policy_prediction_runtime_binding.py",
        "app/gates/gate_policy_prediction_runtime_binding_reporter.py",
        "app/gates/gate_policy_prediction_runtime_adapter.py",
        "gate-policy-runtime-binding-preview",
        "gate-policy-runtime-binding-export",
        "reports/gate_policy_runtime_binding_summary.json",
        "payload mode",
        "service-result mode",
        "PredictionService",
        "runtime adapter",
        "GatePolicy service",
        "API response is not changed yet",
        "ML22",
        "API response with GatePolicy block",
        "database_connected: false",
        "traders_core_connected: false",
        "live_trading_connected: false",
        "orders_enabled: false",
        "traders-core",
        "does not open trades",
    ]

    for phrase in required_phrases:
        assert phrase in text
