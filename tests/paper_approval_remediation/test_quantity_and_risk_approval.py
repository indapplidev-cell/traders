from __future__ import annotations

from copy import copy
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal

import pytest

from app.engine_paper.paper_approvals import (
    PaperApprovalReasonCode,
    PaperCommandApprovalCompatibility,
    PaperQuantityApproval,
    PaperQuantityApprovalSource,
    approval_serialization,
    finalize_paper_risk_approval,
    finalize_paper_strategy_approval,
    issue_paper_quantity_approval,
    map_final_approvals_to_command_compatibility,
)
from app.engine_safety.paper_domain import ExecutionMode, PaperDomainError
from tests.paper_approval_remediation.conftest import (
    APPROVED_AT,
    CLOSED,
    VALID,
    make_risk,
    make_strategy,
    strategy_kwargs,
)


def _strategy():
    return finalize_paper_strategy_approval(make_strategy(), **strategy_kwargs())


def _quantity(strategy=None, risk=None, **changes):
    strategy = strategy or _strategy()
    risk = risk or make_risk()
    values = {
        "mode": ExecutionMode.PAPER,
        "paper_authorized": True,
        "requested_quantity": Decimal("2"),
        "approval_source": PaperQuantityApprovalSource.CONTROLLED_PAPER_AUTHORITY,
        "approved_at": APPROVED_AT,
        "valid_until_ms": VALID,
        "evaluation_time_ms": CLOSED + 2_000,
        "correlation_id": "run:1",
        "causation_id": strategy.approval_id,
    }
    values.update(changes)
    return issue_paper_quantity_approval(strategy, risk, **values)


def test_quantity_success_is_explicit_controlled_authority():
    approval = _quantity()
    assert approval.approval_source is PaperQuantityApprovalSource.CONTROLLED_PAPER_AUTHORITY
    assert approval.position_size_approved is True
    assert approval.reason_code is PaperApprovalReasonCode.PAPER_QUANTITY_CONTROLLED_APPROVED


def test_quantity_is_immutable_and_serializable():
    approval = _quantity()
    with pytest.raises((FrozenInstanceError, AttributeError)):
        approval.approved_quantity = Decimal("3")
    assert approval_serialization(approval)["approved_quantity"] == Decimal("2")


@pytest.mark.parametrize(
    "quantity",
    [
        1,
        1.0,
        "1",
        None,
        True,
        Decimal("0"),
        Decimal("-1"),
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
    ],
)
def test_quantity_rejects_bare_invalid_or_nonfinite_values(quantity):
    with pytest.raises(PaperDomainError):
        _quantity(requested_quantity=quantity)


@pytest.mark.parametrize("source", [None, "", "DETERMINISTIC_RISK_POLICY", "MANUAL", 1])
def test_quantity_requires_declared_controlled_source(source):
    with pytest.raises(PaperDomainError):
        _quantity(approval_source=source)


@pytest.mark.parametrize("mode", ["OFF", "LIVE", "UNKNOWN", None])
def test_quantity_rejects_non_paper_mode(mode):
    with pytest.raises(PaperDomainError):
        _quantity(mode=mode)


@pytest.mark.parametrize("authorization", [False, None, 0, 1, "yes"])
def test_quantity_requires_literal_explicit_authorization(authorization):
    with pytest.raises(PaperDomainError):
        _quantity(paper_authorized=authorization)


@pytest.mark.parametrize(
    "risk_changes",
    [
        {"source_strategy_decision_id": "strategy:other"},
        {"source_setup_id": "setup:other"},
        {"source_analysis_snapshot_id": "analysis:other"},
        {"symbol": "ETHUSDT"},
        {"closed_until_ms": CLOSED + 1},
        {"direction_hint": "BEARISH"},
    ],
)
def test_quantity_rejects_research_risk_graph_mismatch(risk_changes):
    with pytest.raises(PaperDomainError):
        _quantity(risk=make_risk(**risk_changes))


@pytest.mark.parametrize("status", ["REJECT", "WAIT", "NO_DECISION", "ERROR"])
def test_quantity_rejects_non_preapproved_research_risk(status):
    with pytest.raises(PaperDomainError):
        _quantity(risk=make_risk(risk_status=status, risk_level="BLOCKED"))


@pytest.mark.parametrize("value", [Decimal(index) / Decimal("10") for index in range(1, 31)])
def test_quantity_identity_and_output_are_deterministic_for_controlled_values(value):
    first = _quantity(requested_quantity=value)
    second = _quantity(requested_quantity=value)
    assert first == second
    assert first.quantity_approval_id == second.quantity_approval_id
    assert first.approved_quantity == value


def test_final_risk_success_sets_all_flags_atomically(approval_chain):
    _, research_risk, strategy, quantity, risk = approval_chain
    assert (
        risk.order_approved,
        risk.execution_approved,
        risk.position_size_approved,
        risk.final_paper_approval,
    ) == (True, True, True, True)
    assert risk.reason_code is PaperApprovalReasonCode.PAPER_RISK_FINAL_APPROVED
    assert risk.research_risk_decision_id == research_risk.risk_decision_id
    assert risk.paper_strategy_approval_id == strategy.approval_id
    assert risk.quantity_approval_id == quantity.quantity_approval_id


def test_research_risk_semantics_remain_false_after_final_approval(approval_chain):
    _, research_risk, _, _, _ = approval_chain
    assert research_risk.order_approved is False
    assert research_risk.execution_approved is False
    assert research_risk.position_size_approved is False
    assert research_risk.is_executable is False


def test_final_risk_is_immutable_and_serializable(approval_chain):
    *_, risk = approval_chain
    with pytest.raises((FrozenInstanceError, AttributeError)):
        risk.final_paper_approval = False
    assert approval_serialization(risk)["final_paper_approval"] is True


@pytest.mark.parametrize("mode", ["OFF", "LIVE", "UNKNOWN", None])
def test_final_risk_rejects_non_paper_mode(mode, approval_chain):
    _, research_risk, strategy, quantity, _ = approval_chain
    with pytest.raises(PaperDomainError):
        finalize_paper_risk_approval(
            strategy,
            research_risk,
            quantity,
            mode=mode,
            paper_authorized=True,
            approved_at=APPROVED_AT,
            evaluation_time_ms=CLOSED + 2_000,
            correlation_id="run:1",
            causation_id=quantity.quantity_approval_id,
        )


@pytest.mark.parametrize("authorization", [False, None, 0, 1, "yes"])
def test_final_risk_requires_literal_explicit_authorization(authorization, approval_chain):
    _, research_risk, strategy, quantity, _ = approval_chain
    with pytest.raises(PaperDomainError):
        finalize_paper_risk_approval(
            strategy,
            research_risk,
            quantity,
            mode=ExecutionMode.PAPER,
            paper_authorized=authorization,
            approved_at=APPROVED_AT,
            evaluation_time_ms=CLOSED + 2_000,
            correlation_id="run:1",
            causation_id=quantity.quantity_approval_id,
        )


@pytest.mark.parametrize(
    "mutation",
    [
        {"paper_strategy_approval_id": "paper:strategy:other"},
        {"research_risk_decision_id": "risk:other"},
        {"symbol": "ETHUSDT"},
        {"side": "SHORT"},
        {"configuration_fingerprint": "config:other"},
        {"symbol_constraints_id": "constraints:other"},
        {"position_size_approved": False},
    ],
)
def test_final_risk_rejects_quantity_chain_mismatch(mutation, approval_chain):
    _, research_risk, strategy, quantity, _ = approval_chain
    with pytest.raises(PaperDomainError):
        replace(quantity, **mutation)
    corrupted = copy(quantity)
    for field, value in mutation.items():
        object.__setattr__(corrupted, field, value)
    with pytest.raises(PaperDomainError):
        finalize_paper_risk_approval(
            strategy,
            research_risk,
            corrupted,
            mode=ExecutionMode.PAPER,
            paper_authorized=True,
            approved_at=APPROVED_AT,
            evaluation_time_ms=CLOSED + 2_000,
            correlation_id="run:1",
            causation_id=corrupted.quantity_approval_id,
        )


def test_final_risk_rejects_bare_decimal_as_authority(approval_chain):
    _, research_risk, strategy, _, _ = approval_chain
    with pytest.raises(PaperDomainError):
        finalize_paper_risk_approval(
            strategy,
            research_risk,
            Decimal("2"),
            mode=ExecutionMode.PAPER,
            paper_authorized=True,
            approved_at=APPROVED_AT,
            evaluation_time_ms=CLOSED + 2_000,
            correlation_id="run:1",
            causation_id="quantity:missing",
        )


@pytest.mark.parametrize("offset", range(1, 21))
def test_final_risk_identity_is_deterministic_for_each_valid_quantity(offset):
    strategy = _strategy()
    research_risk = make_risk()
    quantity = _quantity(
        strategy,
        research_risk,
        requested_quantity=Decimal(offset) / Decimal("10"),
    )
    kwargs = {
        "mode": ExecutionMode.PAPER,
        "paper_authorized": True,
        "approved_at": APPROVED_AT,
        "evaluation_time_ms": CLOSED + 2_000,
        "correlation_id": "run:1",
        "causation_id": quantity.quantity_approval_id,
    }
    first = finalize_paper_risk_approval(strategy, research_risk, quantity, **kwargs)
    second = finalize_paper_risk_approval(strategy, research_risk, quantity, **kwargs)
    assert first == second
    assert first.approval_id == second.approval_id


def test_command_compatibility_mapping_has_every_required_field(approval_chain):
    _, _, strategy, quantity, risk = approval_chain
    mapped = map_final_approvals_to_command_compatibility(strategy, quantity, risk)
    assert isinstance(mapped, PaperCommandApprovalCompatibility)
    assert mapped.strategy_decision_id == "strategy:1"
    assert mapped.risk_decision_id == "risk:1"
    assert mapped.setup_id == "setup:1"
    assert mapped.pipeline_run_id == "run:1"
    assert mapped.analysis_result_id == "analysis:1"
    assert mapped.approved_quantity == Decimal("2")
    assert (
        mapped.paper_execution_approved,
        mapped.order_approved,
        mapped.execution_approved,
        mapped.position_size_approved,
        mapped.final_paper_approval,
    ) == (True, True, True, True, True)


@pytest.mark.parametrize(
    "risk_mutation",
    [
        {"paper_strategy_approval_id": "other:strategy"},
        {"quantity_approval_id": "other:quantity"},
        {"research_risk_decision_id": "other:risk"},
        {"approved_quantity": Decimal("3")},
        {"order_approved": False},
        {"execution_approved": False},
        {"position_size_approved": False},
        {"final_paper_approval": False},
    ],
)
def test_command_compatibility_rejects_incomplete_or_mismatched_chain(
    risk_mutation, approval_chain
):
    _, _, strategy, quantity, risk = approval_chain
    with pytest.raises(PaperDomainError):
        map_final_approvals_to_command_compatibility(
            strategy, quantity, replace(risk, **risk_mutation)
        )
