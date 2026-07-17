from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from app.engine_execution import DryRunExecutionGateway, ExecutionAcknowledgement, ExecutionIntent, ExecutionIntentBuilder


def ready_intent(payload_copy):
    payload = payload_copy()
    payload["setup_context"]["metadata"] = {"nested": {"items": [1, 2]}, "sequence": ["a", "b"]}
    payload["setup_context"]["warnings"] = ["warning"]
    return ExecutionIntentBuilder().build(
        payload["strategy_decision"], payload["risk_decision"], payload["setup_context"],
        "DRY_RUN", payload["source_window"],
    )


def test_execution_intent_is_deeply_immutable(payload_copy):
    intent = ready_intent(payload_copy)
    with pytest.raises(FrozenInstanceError):
        intent.symbol = "ETHUSDT"
    with pytest.raises(TypeError):
        intent.metadata["new"] = 1
    with pytest.raises(TypeError):
        intent.metadata["nested"]["new"] = 1
    with pytest.raises(TypeError):
        intent.metadata["nested"]["items"][0] = 9
    with pytest.raises(FrozenInstanceError):
        intent.reason_codes += ("OTHER",)
    with pytest.raises(FrozenInstanceError):
        intent.warnings += ("OTHER",)


def test_acknowledgement_is_deeply_immutable(payload_copy):
    intent = ready_intent(payload_copy)
    acknowledgement = DryRunExecutionGateway().submit(intent)
    with pytest.raises(FrozenInstanceError):
        acknowledgement.status = "REJECTED"
    with pytest.raises(TypeError):
        acknowledgement.metadata["new"] = 1
    with pytest.raises(FrozenInstanceError):
        acknowledgement.reason_codes += ("OTHER",)
    with pytest.raises(FrozenInstanceError):
        acknowledgement.warnings += ("OTHER",)


def test_round_trip_restores_equivalent_immutable_nested_data(payload_copy):
    intent = ready_intent(payload_copy)
    restored = ExecutionIntent.from_dict(intent.to_dict())
    assert restored == intent
    with pytest.raises(TypeError):
        restored.metadata["nested"]["items"][0] = 10
    acknowledgement = DryRunExecutionGateway().submit(restored)
    restored_ack = ExecutionAcknowledgement.from_dict(acknowledgement.to_dict())
    assert restored_ack == acknowledgement
    with pytest.raises(TypeError):
        restored_ack.metadata["new"] = True
