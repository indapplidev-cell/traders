from __future__ import annotations

import pytest

from app.engine_execution import ExecutionIntentBuilder
from app.engine_execution.approval_policy import ApprovalScope, evaluate_approval_pair


def build(payload, mode="DRY_RUN"):
    return ExecutionIntentBuilder().build(
        payload["strategy_decision"], payload["risk_decision"], payload["setup_context"],
        mode, payload["source_window"],
    )


def test_production_approval_pair_has_production_scope(approved_payload):
    intent = build(approved_payload)
    assert intent.status.value == "READY"
    assert intent.metadata["approval_scope"] == ApprovalScope.PRODUCTION_APPROVED.value


@pytest.mark.parametrize("mode", ["PAPER", "DRY_RUN"])
def test_research_approval_pair_is_safe_mode_only(payload_copy, mode):
    payload = payload_copy()
    payload["strategy_decision"]["decision_status"] = "ALLOW_RESEARCH_TRADE_PLAN"
    payload["risk_decision"]["risk_status"] = "RISK_PRE_APPROVED_RESEARCH"
    intent = build(payload, mode)
    assert intent.status.value == "READY"
    assert intent.metadata["approval_scope"] == ApprovalScope.RESEARCH_ONLY.value


@pytest.mark.parametrize("strategy_status,risk_status", [
    ("APPROVED", "RISK_PRE_APPROVED_RESEARCH"),
    ("ALLOW_RESEARCH_TRADE_PLAN", "RISK_APPROVED"),
])
def test_mixed_approval_pairs_are_contract_mismatch(payload_copy, strategy_status, risk_status):
    payload = payload_copy()
    payload["strategy_decision"]["decision_status"] = strategy_status
    payload["risk_decision"]["risk_status"] = risk_status
    intent = build(payload)
    assert intent.status.value == "REJECTED"
    assert intent.reason_codes[0] == "CONTRACT_MISMATCH"
    assert "approval_scope" not in intent.metadata


def test_approval_policy_uses_exact_values_only():
    result = evaluate_approval_pair("NOT_APPROVED", "RISK_APPROVED_SUFFIX")
    assert result.scope is None
    assert result.reason_codes == ("STRATEGY_NOT_APPROVED", "RISK_NOT_APPROVED")


def test_live_gate_is_first_even_with_other_invalid_input(payload_copy):
    payload = payload_copy()
    payload["strategy_decision"]["decision_status"] = "REJECT"
    payload["setup_context"]["quantity"] = "0"
    intent = build(payload, "LIVE")
    assert intent.status.value == "DISABLED"
    assert intent.reason_codes == ("LIVE_EXECUTION_DISABLED",)


def test_research_statuses_never_authorize_live(payload_copy):
    payload = payload_copy()
    payload["strategy_decision"]["decision_status"] = "ALLOW_RESEARCH_TRADE_PLAN"
    payload["risk_decision"]["risk_status"] = "RISK_PRE_APPROVED_RESEARCH"
    intent = build(payload, "LIVE")
    assert intent.status.value == "DISABLED"
    assert intent.reason_codes == ("LIVE_EXECUTION_DISABLED",)
    assert "approval_scope" not in intent.metadata
