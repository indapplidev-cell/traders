from __future__ import annotations

from app.engine_execution import ExecutionAcknowledgement, ExecutionIntent, ExecutionIntentBuilder


def test_canonical_json_is_stable_and_round_trip_preserves_intent(approved_payload):
    intent = ExecutionIntentBuilder().build(
        approved_payload["strategy_decision"], approved_payload["risk_decision"],
        approved_payload["setup_context"], "DRY_RUN", approved_payload["source_window"],
    )
    encoded = intent.canonical_json()
    restored = ExecutionIntent.from_dict(intent.to_dict())
    assert restored == intent
    assert restored.canonical_json() == encoded
    assert encoded == intent.canonical_json()
    assert '"quantity":"0.25"' in encoded
    assert '"execution_schema_version":1' in encoded


def test_acknowledgement_round_trip(approved_payload):
    from app.engine_execution import DryRunExecutionGateway
    intent = ExecutionIntentBuilder().build(
        approved_payload["strategy_decision"], approved_payload["risk_decision"],
        approved_payload["setup_context"], "DRY_RUN", approved_payload["source_window"],
    )
    acknowledgement = DryRunExecutionGateway().submit(intent)
    assert ExecutionAcknowledgement.from_dict(acknowledgement.to_dict()) == acknowledgement
    assert acknowledgement.external_order_id is None
