import json

from app.evaluation.gate_policy_replay_evaluator import GatePolicyReplayEvaluator
from app.evaluation.gate_policy_replay_reporter import GatePolicyReplayReporter


def test_gate_policy_replay_reporter_full_and_compact_shapes() -> None:
    evaluator = GatePolicyReplayEvaluator()
    reporter = GatePolicyReplayReporter()

    summary = evaluator.evaluate(_sample_payloads())

    full_payload = reporter.summary_to_dict(summary)
    compact_payload = reporter.compact_summary_to_dict(summary)

    assert full_payload["records"]
    assert "records" not in compact_payload
    assert compact_payload["integration_status"]["orders_enabled"] is False
    assert compact_payload["integration_status"]["live_trading_connected"] is False
    assert compact_payload["integration_status"]["traders_core_connected"] is False


def test_gate_policy_replay_reporter_json_serialization() -> None:
    evaluator = GatePolicyReplayEvaluator()
    reporter = GatePolicyReplayReporter()

    summary = evaluator.evaluate(_sample_payloads())

    json.loads(reporter.summary_to_json(summary))
    json.loads(reporter.compact_summary_to_json(summary))


def _sample_payloads() -> list[dict[str, object]]:
    return [
        {
            "prob_up": 0.61,
            "prob_down": 0.21,
            "prob_flat": 0.18,
            "confidence": 0.72,
            "tp_before_sl_probability": 0.64,
            "risk_score": 0.31,
            "expected_move_atr": 1.45,
            "regime": "trend_up",
        }
    ]
