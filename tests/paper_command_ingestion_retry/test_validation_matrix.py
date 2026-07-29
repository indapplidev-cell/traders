from __future__ import annotations

import ast
from datetime import timedelta
from pathlib import Path

import pytest

from app.engine_paper.command_ingestion_service import (
    PaperCommandIngestionOutcome,
    PaperCommandIngestionReasonCode,
    PaperCommandIngestionService,
)
from app.engine_execution.paper_idempotency import command_idempotency_key
from app.engine_paper.paper_approvals import PaperQuantityApprovalSource
from app.engine_safety.paper_domain import (
    ExecutionMode,
    PaperInputHealthStatus,
    PaperOrderType,
)
from tests.paper_command_ingestion_retry.conftest import (
    CREATED_AT,
    make_request,
)


class NoMutationFactory:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self):
        self.calls += 1
        raise AssertionError("validation failure must not open a UoW")


def run_without_mutation(request):
    factory = NoMutationFactory()
    result = PaperCommandIngestionService(factory, factory).ingest_and_create_entry_order(
        request
    )
    assert factory.calls == 0
    assert result.successful is False
    return result


@pytest.mark.parametrize(
    ("mode", "authorized", "outcome"),
    [
        (ExecutionMode.OFF, True, PaperCommandIngestionOutcome.MODE_OFF),
        ("OFF", True, PaperCommandIngestionOutcome.MODE_OFF),
        (ExecutionMode.LIVE, True, PaperCommandIngestionOutcome.MODE_LIVE_FORBIDDEN),
        ("LIVE", True, PaperCommandIngestionOutcome.MODE_LIVE_FORBIDDEN),
        ("UNKNOWN", True, PaperCommandIngestionOutcome.MODE_UNKNOWN),
        ("", True, PaperCommandIngestionOutcome.MODE_UNKNOWN),
        (None, True, PaperCommandIngestionOutcome.MODE_UNKNOWN),
        (1, True, PaperCommandIngestionOutcome.MODE_UNKNOWN),
        (object(), True, PaperCommandIngestionOutcome.MODE_UNKNOWN),
        (ExecutionMode.PAPER, False, PaperCommandIngestionOutcome.PAPER_AUTHORIZATION_MISSING),
        ("PAPER", False, PaperCommandIngestionOutcome.PAPER_AUTHORIZATION_MISSING),
        (ExecutionMode.PAPER, None, PaperCommandIngestionOutcome.PAPER_AUTHORIZATION_MISSING),
        (ExecutionMode.PAPER, 1, PaperCommandIngestionOutcome.PAPER_AUTHORIZATION_MISSING),
        (ExecutionMode.PAPER, "true", PaperCommandIngestionOutcome.PAPER_AUTHORIZATION_MISSING),
    ],
)
def test_mode_and_authorization_fail_closed(mode, authorized, outcome):
    result = run_without_mutation(
        make_request(execution_mode=mode, explicit_paper_authorization=authorized)
    )
    assert result.outcome is outcome


_CHAIN_MUTATIONS = [
    ("quantity", "paper_strategy_approval_id", "strategy:other"),
    ("risk", "paper_strategy_approval_id", "strategy:other"),
    ("risk", "quantity_approval_id", "quantity:other"),
    ("risk", "research_risk_decision_id", "risk:other"),
    ("risk", "setup_id", "setup:other"),
    ("risk", "pipeline_run_id", "run:other"),
    ("risk", "analysis_result_id", "analysis:other"),
    ("quantity", "symbol", "ETHUSDT"),
    ("risk", "symbol", "ETHUSDT"),
    ("quantity", "side", "SHORT"),
    ("risk", "side", "SHORT"),
    ("risk", "approved_quantity", 3),
    ("quantity", "configuration_fingerprint", "config:other"),
    ("risk", "configuration_fingerprint", "config:other"),
    ("quantity", "symbol_constraints_id", "constraints:other"),
    ("risk", "symbol_constraints_id", "constraints:other"),
]


@pytest.mark.parametrize(
    ("target", "field", "value", "variant"),
    [
        (target, field, value, variant)
        for target, field, value in _CHAIN_MUTATIONS
        for variant in range(6)
    ],
)
def test_all_approval_chain_links_fail_closed(target, field, value, variant):
    request = make_request()
    approval = (
        request.paper_quantity_approval
        if target == "quantity"
        else request.paper_risk_approval
    )
    selected = value
    if isinstance(value, str) and variant:
        selected = f"{value}:{variant}"
    object.__setattr__(approval, field, selected)
    result = run_without_mutation(request)
    assert result.outcome is PaperCommandIngestionOutcome.FINAL_APPROVAL_CHAIN_INCONSISTENT


@pytest.mark.parametrize(
    ("target", "field", "value", "outcome"),
    [
        ("strategy", "paper_execution_approved", False,
         PaperCommandIngestionOutcome.STRATEGY_APPROVAL_INVALID),
        ("strategy", "paper_execution_approved", None,
         PaperCommandIngestionOutcome.STRATEGY_APPROVAL_INVALID),
        ("quantity", "position_size_approved", False,
         PaperCommandIngestionOutcome.QUANTITY_APPROVAL_INVALID),
        ("quantity", "position_size_approved", None,
         PaperCommandIngestionOutcome.QUANTITY_APPROVAL_INVALID),
        ("quantity", "approval_source", "OTHER",
         PaperCommandIngestionOutcome.QUANTITY_APPROVAL_INVALID),
        ("risk", "order_approved", False,
         PaperCommandIngestionOutcome.RISK_APPROVAL_INVALID),
        ("risk", "execution_approved", False,
         PaperCommandIngestionOutcome.RISK_APPROVAL_INVALID),
        ("risk", "position_size_approved", False,
         PaperCommandIngestionOutcome.RISK_APPROVAL_INVALID),
        ("risk", "final_paper_approval", False,
         PaperCommandIngestionOutcome.RISK_APPROVAL_INVALID),
        ("risk", "order_approved", None,
         PaperCommandIngestionOutcome.RISK_APPROVAL_INVALID),
        ("risk", "execution_approved", None,
         PaperCommandIngestionOutcome.RISK_APPROVAL_INVALID),
        ("risk", "position_size_approved", None,
         PaperCommandIngestionOutcome.RISK_APPROVAL_INVALID),
        ("risk", "final_paper_approval", None,
         PaperCommandIngestionOutcome.RISK_APPROVAL_INVALID),
    ],
)
def test_every_final_authority_flag_is_required(target, field, value, outcome):
    request = make_request()
    approval = {
        "strategy": request.paper_strategy_approval,
        "quantity": request.paper_quantity_approval,
        "risk": request.paper_risk_approval,
    }[target]
    object.__setattr__(approval, field, value)
    result = run_without_mutation(request)
    assert result.outcome is outcome


@pytest.mark.parametrize("delta_ms", range(1, 25))
def test_expired_final_chain_has_zero_mutation(delta_ms):
    request = make_request(created_at=CREATED_AT + timedelta(minutes=2, milliseconds=delta_ms))
    result = run_without_mutation(request)
    assert result.outcome is PaperCommandIngestionOutcome.FINAL_APPROVAL_EXPIRED


@pytest.mark.parametrize(
    ("health", "outcome"),
    [
        (PaperInputHealthStatus.HEALTHY, PaperCommandIngestionOutcome.INPUT_DEGRADED),
        (PaperInputHealthStatus.WITHIN_GRACE, PaperCommandIngestionOutcome.INPUT_DEGRADED),
        ("STALE", PaperCommandIngestionOutcome.INPUT_STALE),
        ("SOURCE_STALE", PaperCommandIngestionOutcome.INPUT_STALE),
        ("DEGRADED", PaperCommandIngestionOutcome.INPUT_DEGRADED),
        ("UNKNOWN", PaperCommandIngestionOutcome.INPUT_DEGRADED),
    ],
)
def test_non_current_health_is_rejected(health, outcome):
    request = make_request()
    object.__setattr__(request.paper_strategy_approval, "input_health_status", health)
    result = run_without_mutation(request)
    assert result.outcome is outcome


@pytest.mark.parametrize("future_value", [True, 1, "true", object()])
def test_future_data_is_rejected(future_value):
    request = make_request()
    object.__setattr__(request.paper_strategy_approval, "future_bars_used", future_value)
    result = run_without_mutation(request)
    assert result.outcome is PaperCommandIngestionOutcome.FUTURE_DATA_REJECTED


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("command_id", "paper:wrong"),
        ("correlation_id", "run:wrong"),
        ("causation_id", "risk-approval:wrong"),
    ],
)
def test_caller_cannot_override_causal_identity(field, value):
    result = run_without_mutation(make_request(**{field: value}))
    assert result.outcome is PaperCommandIngestionOutcome.FINAL_APPROVAL_CHAIN_INCONSISTENT


@pytest.mark.parametrize("index", range(4))
def test_journal_identity_must_match_corresponding_event(index):
    request = make_request()
    identities = list(request.journal_entry_ids)
    identities[index] = f"journal:separate:{index}"
    object.__setattr__(request, "journal_entry_ids", tuple(identities))
    result = run_without_mutation(request)
    assert result.outcome is PaperCommandIngestionOutcome.INVALID_COMMAND_COMPATIBILITY


@pytest.mark.parametrize("outcome", tuple(PaperCommandIngestionOutcome))
def test_every_outcome_has_a_bounded_public_identity(outcome):
    assert outcome.value.isascii()
    assert len(outcome.value) <= 64


@pytest.mark.parametrize("reason", tuple(PaperCommandIngestionReasonCode))
def test_every_reason_code_is_bounded_and_secret_free(reason):
    assert reason.value.isascii()
    assert len(reason.value) <= 96
    assert "PASSWORD" not in reason.value
    assert "TOKEN" not in reason.value


def test_static_service_has_no_forbidden_dependencies_or_entropy():
    path = Path("app/engine_paper/command_ingestion_service.py")
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any(
        forbidden in name
        for name in imported
        for forbidden in ("fastapi", "binance", "market_data", "fill_simulator")
    )
    assert "datetime.now" not in source
    assert "time.time" not in source
    assert "uuid4" not in source
    assert "random" not in source
    assert ".commit(" not in source.replace("uow.commit(", "")


def test_controlled_quantity_source_is_the_only_supported_source():
    assert tuple(PaperQuantityApprovalSource) == (
        PaperQuantityApprovalSource.CONTROLLED_PAPER_AUTHORITY,
    )


@pytest.mark.parametrize(
    "field",
    [
        "command_id",
        "idempotency_key",
        "mode",
        "symbol",
        "side",
        "order_type",
        "requested_quantity",
        "requested_notional",
        "entry_reference_price",
        "stop_price",
        "target_price",
        "strategy_decision_id",
        "risk_decision_id",
        "setup_id",
        "pipeline_run_id",
        "analysis_result_id",
        "closed_until_ms",
        "created_at",
        "valid_until_ms",
        "configuration_fingerprint",
        "simulation_policy_id",
        "fee_policy_id",
        "slippage_policy_id",
        "latency_policy_id",
        "final_paper_approval",
        "input_health_status",
        "future_bars_used",
    ],
)
def test_every_command_field_maps_from_authoritative_inputs(field):
    request = make_request()
    strategy = request.paper_strategy_approval
    quantity = request.paper_quantity_approval
    risk = request.paper_risk_approval
    policy = request.simulation_policy
    expected = {
        "command_id": request.command_id,
        "idempotency_key": command_idempotency_key(
            pipeline_run_id=strategy.pipeline_run_id,
            analysis_result_id=strategy.analysis_result_id,
            setup_id=strategy.setup_id,
            strategy_decision_id=strategy.research_strategy_decision_id,
            risk_decision_id=risk.research_risk_decision_id,
            symbol=strategy.symbol,
            side=strategy.side,
            closed_until_ms=strategy.closed_until_ms,
            configuration_fingerprint=strategy.configuration_fingerprint,
        ),
        "mode": ExecutionMode.PAPER,
        "symbol": strategy.symbol,
        "side": strategy.side,
        "order_type": PaperOrderType.MARKET_SIMULATED,
        "requested_quantity": quantity.approved_quantity,
        "requested_notional": None,
        "entry_reference_price": strategy.entry_reference_price,
        "stop_price": strategy.stop_price,
        "target_price": strategy.target_price,
        "strategy_decision_id": strategy.research_strategy_decision_id,
        "risk_decision_id": risk.research_risk_decision_id,
        "setup_id": strategy.setup_id,
        "pipeline_run_id": strategy.pipeline_run_id,
        "analysis_result_id": strategy.analysis_result_id,
        "closed_until_ms": strategy.closed_until_ms,
        "created_at": request.created_at,
        "valid_until_ms": risk.valid_until_ms,
        "configuration_fingerprint": strategy.configuration_fingerprint,
        "simulation_policy_id": policy.simulation_policy_id,
        "fee_policy_id": policy.fee_policy_id,
        "slippage_policy_id": policy.slippage_policy_id,
        "latency_policy_id": policy.latency_policy_id,
        "final_paper_approval": True,
        "input_health_status": PaperInputHealthStatus.CURRENT,
        "future_bars_used": False,
    }
    built = PaperCommandIngestionService(
        NoMutationFactory(), NoMutationFactory()
    )._build_expected(request).command
    assert getattr(built, field) == expected[field]
