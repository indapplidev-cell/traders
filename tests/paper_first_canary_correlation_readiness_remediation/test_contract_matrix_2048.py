from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.engine_paper.accounting import PaperAccountBaseline, PaperAccountIdentity
from app.operator_control.schemas import (
    PaperCanaryNormalizedState,
    PaperOperatorCanaryStatus,
    PaperOperatorStartFirstCanaryRequest,
)
from app.operator_control.app import create_paper_operator_control_app
from app.server_api import create_app
from app.server_api.schemas.paper import PaperControlStatus, PaperReadiness
from app.server_api.services.paper_reporting import PaperReadonlyReportingService, PaperRuntimeObservation
from tests.paper_readonly_reporting_api.test_api_contract import FakePaperRepository


@pytest.mark.parametrize("case", range(2048))
def test_2048_exact_contract_cases(case: int) -> None:
    states = tuple(PaperCanaryNormalizedState)
    state = states[case % len(states)]
    symbol = ("BTCUSDT", "ETHUSDT", "SOLUSDT")[case % 3]
    linked = bool(case & 1)
    canary_id = f"00000000-0000-4000-8000-{case:012x}"
    dto = PaperOperatorCanaryStatus(
        canary_id=canary_id,
        state=state,
        availability_code="AVAILABLE",
        deployment_status="ISOLATED",
        allowed_symbols=(symbol,),
        command_count=int(linked),
        command_id=f"command:{case}" if linked else None,
        position_count=int(linked),
        position_id=f"position:{case}" if linked else None,
        live_allowed=False,
        binance_order_calls_allowed=False,
    )
    payload = dto.model_dump(mode="json")
    assert payload["canary_id"] == canary_id
    assert payload["command_count"] <= payload["max_new_commands"] == 1
    assert payload["position_count"] <= payload["max_open_positions"] == 1
    assert payload["allowed_symbols"] == [symbol]
    assert payload["live_allowed"] is payload["binance_order_calls_allowed"] is False


def test_start_contract_requires_both_authoritative_identities() -> None:
    schema = PaperOperatorStartFirstCanaryRequest.model_json_schema()
    assert {"canary_id", "arming_transition_id"} <= set(schema["required"])


def test_readiness_serializes_real_false_and_true_booleans() -> None:
    base = dict(
        environment="isolated", paper_schema_ready=True, status="READY",
        paper_runtime_enabled=True, paper_daemon_enabled=False, paper_scheduler_enabled=False,
        paper_control_state="DISABLED", paper_control_effective_state="DISABLED",
        paper_control_generation=1, paper_control_health="HEALTHY",
        account_baseline_persistence_ready=True, account_baseline_exists=True,
        account_baseline_valid=True, accounting_reconciliation_status="HEALTHY",
        paper_reconciliation_status="HEALTHY", market_data_adapter_ready=True,
        approval_source_adapter_ready=True, wal_ready=True, pitr_ready=True,
        current_approval_availability="AVAILABLE", current_mutation_denial_reasons=[],
    )
    assert PaperReadiness(**base, current_mutation_ready=False).model_dump(mode="json")["current_mutation_ready"] is False
    assert PaperReadiness(**base, current_mutation_ready=True).model_dump(mode="json")["current_mutation_ready"] is True
    prop = PaperReadiness.model_json_schema()["properties"]["current_mutation_ready"]
    assert prop["type"] == "boolean"
    assert "enum" not in prop


def test_future_ready_composition_true_and_current_like_false() -> None:
    baseline = PaperAccountBaseline(
        "baseline-001", PaperAccountIdentity("paper-primary", "session-001"),
        Decimal("100"), datetime(2026, 8, 12, tzinfo=timezone.utc),
    )
    repository = FakePaperRepository(
        baseline, revision="0013_paper_first_canary_correlation", facts=()
    )
    control = PaperControlStatus(
        state="DISABLED", effective_state="DISABLED", generation=3, health="HEALTHY",
        emergency_stop_available=True, audit_health="PASS", state_audit_reconciliation="PASS",
    )
    future = PaperReadonlyReportingService(
        repository,
        runtime=PaperRuntimeObservation(
            environment="isolated", runtime_enabled=True, market_data_adapter_ready=True,
            approval_source_adapter_ready=True, wal_ready=True, pitr_ready=True,
            paper_principal_ready=True, runtime_config_ready=True, kill_switch_ready=True,
            canary_scope_valid=True, live_enabled=False,
        ),
        control_status=lambda: control,
    ).readiness()
    assert future.current_mutation_ready is True
    assert future.current_mutation_denial_reasons == []

    current = PaperReadonlyReportingService(
        FakePaperRepository(baseline, revision="0008_engine_orchestrator_freshness_retry"),
        runtime=PaperRuntimeObservation(environment="production-like"),
        control_status=lambda: control,
    ).readiness()
    assert current.current_mutation_ready is False
    assert "PAPER_SCHEMA_NOT_DEPLOYED" in current.current_mutation_denial_reasons
    assert "PITR_NOT_READY" in current.current_mutation_denial_reasons


def test_openapi_surfaces_are_narrow_and_readiness_is_boolean() -> None:
    control_api = create_paper_operator_control_app().openapi()
    control_methods = {
        (method.upper(), path)
        for path, operations in control_api["paths"].items()
        for method in operations
        if method in {"get", "post", "put", "patch", "delete"}
    }
    assert sum(method == "GET" for method, _ in control_methods) == 3
    assert sum(method == "POST" for method, _ in control_methods) == 5
    assert not any(method in {"PUT", "PATCH", "DELETE"} for method, _ in control_methods)
    assert ("GET", "/control/v1/canaries/{canary_id}") in control_methods

    readonly = create_app().openapi()
    paper_paths = {
        path: operations for path, operations in readonly["paths"].items()
        if path.startswith("/api/v1/paper")
    }
    assert len(paper_paths) == 10
    assert all("get" in operations for operations in paper_paths.values())
    assert not any(
        method in operations
        for operations in paper_paths.values()
        for method in ("post", "put", "patch", "delete")
    )
    readiness = readonly["components"]["schemas"]["PaperReadiness"]
    prop = readiness["properties"]["current_mutation_ready"]
    assert prop["type"] == "boolean"
    assert "enum" not in prop
