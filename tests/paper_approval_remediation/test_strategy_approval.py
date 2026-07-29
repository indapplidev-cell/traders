from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.engine_paper.paper_approvals import (
    PAPER_APPROVAL_CONTRACT_VERSION,
    PAPER_APPROVAL_IDEMPOTENCY_VERSION,
    PaperApprovalReasonCode,
    approval_serialization,
    finalize_paper_strategy_approval,
)
from app.engine_safety.paper_domain import PaperDomainError, PaperSide
from tests.paper_approval_remediation.conftest import (
    APPROVED_AT,
    CLOSED,
    VALID,
    make_strategy,
    strategy_kwargs,
)


def test_final_strategy_success_contract():
    result = finalize_paper_strategy_approval(make_strategy(), **strategy_kwargs())
    assert result.contract_version == PAPER_APPROVAL_CONTRACT_VERSION
    assert result.paper_execution_approved is True
    assert result.reason_code is PaperApprovalReasonCode.PAPER_STRATEGY_FINAL_APPROVED
    assert result.approval_id.startswith(
        f"paper:strategy-approval:{PAPER_APPROVAL_IDEMPOTENCY_VERSION}:"
    )


def test_research_strategy_semantics_are_preserved():
    research = make_strategy()
    before = research.to_dict()
    finalize_paper_strategy_approval(research, **strategy_kwargs())
    assert research.to_dict() == before
    assert research.is_executable is False
    assert research.risk_approved is False


def test_strategy_approval_is_immutable():
    approval = finalize_paper_strategy_approval(make_strategy(), **strategy_kwargs())
    with pytest.raises((FrozenInstanceError, AttributeError)):
        approval.symbol = "ETHUSDT"


def test_strategy_serialization_is_stable_and_enum_values_are_strings():
    approval = finalize_paper_strategy_approval(make_strategy(), **strategy_kwargs())
    assert approval_serialization(approval) == approval.to_dict()
    assert approval.to_dict()["side"] == "LONG"
    assert approval.to_dict()["input_health_status"] == "CURRENT"


@pytest.mark.parametrize("mode", ["OFF", "LIVE", "UNKNOWN", "", None])
def test_strategy_rejects_every_non_paper_mode(mode):
    with pytest.raises(PaperDomainError):
        finalize_paper_strategy_approval(
            make_strategy(), **strategy_kwargs(mode=mode)
        )


@pytest.mark.parametrize("authorization", [False, None, 0, 1, "true", object()])
def test_strategy_requires_literal_explicit_authorization(authorization):
    with pytest.raises(PaperDomainError):
        finalize_paper_strategy_approval(
            make_strategy(), **strategy_kwargs(paper_authorized=authorization)
        )


@pytest.mark.parametrize(
    "status",
    ["REJECT", "WAIT", "NO_DECISION", "ERROR"],
)
def test_strategy_rejects_non_allow_research_outcomes(status):
    with pytest.raises(PaperDomainError):
        finalize_paper_strategy_approval(
            make_strategy(decision_status=status), **strategy_kwargs()
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("setup_id", "setup:other"),
        ("analysis_result_id", "analysis:other"),
        ("correlation_id", "run:other"),
        ("causation_id", "strategy:other"),
    ],
)
def test_strategy_rejects_causal_graph_mismatch(field, value):
    with pytest.raises(PaperDomainError):
        finalize_paper_strategy_approval(
            make_strategy(), **strategy_kwargs(**{field: value})
        )


@pytest.mark.parametrize(
    "health",
    ["HEALTHY", "WITHIN_GRACE", "STALE", "DEGRADED", "UNKNOWN", None, ""],
)
def test_strategy_rejects_every_non_current_health(health):
    with pytest.raises(PaperDomainError):
        finalize_paper_strategy_approval(
            make_strategy(), **strategy_kwargs(input_health_status=health)
        )


@pytest.mark.parametrize("future", [True, 1, "true", None])
def test_strategy_rejects_non_false_future_input(future):
    with pytest.raises(PaperDomainError):
        finalize_paper_strategy_approval(
            make_strategy(), **strategy_kwargs(future_bars_used=future)
        )


@pytest.mark.parametrize(
    ("side", "direction", "stop", "entry", "target"),
    [
        ("LONG", "BULLISH", "90", "100", "120"),
        ("SHORT", "BEARISH", "120", "100", "90"),
    ],
)
def test_strategy_accepts_long_and_short_geometry(side, direction, stop, entry, target):
    result = finalize_paper_strategy_approval(
        make_strategy(direction_hint=direction),
        **strategy_kwargs(
            side=side,
            stop_price=Decimal(stop),
            entry_reference_price=Decimal(entry),
            target_price=Decimal(target),
        ),
    )
    assert result.side is PaperSide(side)


@pytest.mark.parametrize(
    ("side", "direction", "stop", "entry", "target"),
    [
        ("LONG", "BULLISH", "100", "100", "120"),
        ("LONG", "BULLISH", "110", "100", "120"),
        ("LONG", "BULLISH", "90", "100", "100"),
        ("LONG", "BULLISH", "90", "100", "80"),
        ("SHORT", "BEARISH", "100", "100", "90"),
        ("SHORT", "BEARISH", "90", "100", "80"),
        ("SHORT", "BEARISH", "120", "100", "100"),
        ("SHORT", "BEARISH", "120", "100", "130"),
    ],
)
def test_strategy_rejects_invalid_price_geometry(side, direction, stop, entry, target):
    with pytest.raises(PaperDomainError):
        finalize_paper_strategy_approval(
            make_strategy(direction_hint=direction),
            **strategy_kwargs(
                side=side,
                stop_price=Decimal(stop),
                entry_reference_price=Decimal(entry),
                target_price=Decimal(target),
            ),
        )


INVALID_MONETARY = [
    1.0,
    1,
    "1",
    None,
    True,
    Decimal("NaN"),
    Decimal("Infinity"),
    Decimal("-Infinity"),
    Decimal("0"),
    Decimal("-1"),
]


@pytest.mark.parametrize("field", ["entry_reference_price", "stop_price", "target_price"])
@pytest.mark.parametrize("value", INVALID_MONETARY)
def test_strategy_rejects_non_decimal_nonfinite_or_nonpositive_money(field, value):
    with pytest.raises(PaperDomainError):
        finalize_paper_strategy_approval(
            make_strategy(), **strategy_kwargs(**{field: value})
        )


@pytest.mark.parametrize(
    ("valid_until", "evaluation"),
    [
        (CLOSED - 1, CLOSED - 1),
        (CLOSED, CLOSED + 1),
        (CLOSED + 999, CLOSED + 999),
        (VALID, VALID + 1),
    ],
)
def test_strategy_rejects_invalid_or_expired_validity(valid_until, evaluation):
    with pytest.raises(PaperDomainError):
        finalize_paper_strategy_approval(
            make_strategy(),
            **strategy_kwargs(
                valid_until_ms=valid_until,
                evaluation_time_ms=evaluation,
            ),
        )


@pytest.mark.parametrize(
    "quantity_marker",
    [Decimal(index) / Decimal("100") for index in range(1, 31)],
)
def test_strategy_identity_is_repeated_input_deterministic(quantity_marker):
    # Marker selects 30 distinct valid price tuples; each tuple is replayed twice.
    target = Decimal("120") + quantity_marker
    kwargs = strategy_kwargs(target_price=target)
    first = finalize_paper_strategy_approval(make_strategy(), **kwargs)
    second = finalize_paper_strategy_approval(make_strategy(), **kwargs)
    assert first == second
    assert first.approval_id == second.approval_id


def test_strategy_identity_changes_for_public_causal_change():
    first = finalize_paper_strategy_approval(make_strategy(), **strategy_kwargs())
    second = finalize_paper_strategy_approval(
        make_strategy(), **strategy_kwargs(target_price=Decimal("121"))
    )
    assert first.approval_id != second.approval_id
