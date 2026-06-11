from pathlib import Path


def test_stage_ml23_gate_policy_replay_evaluation_report_exists_and_documents_scope() -> None:
    report_path = Path("reports/stage_ml23_gate_policy_replay_evaluation_report.md")

    assert report_path.exists()

    text = report_path.read_text(encoding="utf-8")

    required_phrases = [
        "Stage ML23",
        "GatePolicy replay/evaluation layer",
        "app/evaluation/gate_policy_replay_evaluator.py",
        "app/evaluation/gate_policy_replay_reporter.py",
        "gate-policy-replay-evaluate-preview",
        "gate-policy-replay-evaluate-export",
        "invalid payloads",
        "direction NONE",
        "does not open trades",
        "orders",
        "live trading",
        "traders-core",
        "database was not changed",
        "Alembic was not touched",
        "ML24",
        "Final standalone traders-ml readiness audit",
    ]

    for phrase in required_phrases:
        assert phrase in text
