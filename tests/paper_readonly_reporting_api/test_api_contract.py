from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.engine_paper.accounting import PaperAccountBaseline, PaperAccountIdentity
from app.engine_safety.paper_domain import PaperPositionState, PaperSide
from app.server_api import create_app
from app.server_api.repositories.records import (
    PaperPositionRecordView, RecordPage, PaperOrderRecordView, PaperFillRecordView,
    PaperJournalRecordView,
)
from app.server_api.schemas.paper import PaperControlStatus
from app.server_api.services import PaperRuntimeObservation
from app.server_api.schema_compatibility import PaperSchemaContractResult
from tests.paper_account_balance_trade_reporting.conftest import make_trade
from tests.server_api.fakes import FakeReadRepository, NOW


ROOT = Path(__file__).resolve().parents[2]
PAPER_PATHS = (
    "/api/v1/paper/readiness", "/api/v1/paper/account", "/api/v1/paper/positions",
    "/api/v1/paper/positions/{position_id}", "/api/v1/paper/trades",
    "/api/v1/paper/trades/{position_id}/report", "/api/v1/paper/reconciliation",
    "/api/v1/paper/runtime/status", "/api/v1/paper/control/status",
    "/api/v1/paper/trading-criteria",
    "/api/v1/paper/orders", "/api/v1/paper/fills", "/api/v1/paper/journal",
)
OPENAPI = create_app().openapi()


@pytest.fixture
def baseline():
    return PaperAccountBaseline("baseline-001", PaperAccountIdentity("paper-primary", "session-001"),
        Decimal("100.000000000000000000"), datetime(2026, 8, 11, tzinfo=timezone.utc))


class FakePaperRepository:
    def __init__(self, baseline: PaperAccountBaseline, *, revision="0016_control_mobile_device_security", facts=(), contract=True):
        self.revision = revision
        self.baselines = (baseline,)
        self.facts = tuple(facts)
        self.paper_calls = 0
        self.schema_calls = 0
        self.contract = contract
        self.extra_positions = ()
        self.orders = ()
        self.fills = ()
        self.journal = ()

    def schema_revision(self):
        self.schema_calls += 1
        return self.revision

    def schema_revisions(self):
        self.schema_calls += 1
        if isinstance(self.revision, tuple):
            return self.revision
        return () if self.revision is None else (self.revision,)

    def paper_schema_contract(self):
        return PaperSchemaContractResult(bool(self.contract))

    def list_account_baselines(self, limit=2):
        self.paper_calls += 1
        return self.baselines[:limit]

    def list_closed_trade_facts(self, limit):
        self.paper_calls += 1
        return self.facts[:limit]

    @staticmethod
    def view(facts):
        position = facts.position
        return PaperPositionRecordView(position=position, entry_time=position.opened_at,
            updated_at=position.closed_at or position.opened_at, exit_reason=facts.exit_reason,
            entry_order_id=position.entry_order_id, entry_fill_id=position.entry_fill_id,
            close_order_id="exit-order", close_fill_id=position.exit_fill_id,
            exit_cursor_status="VERSION_1", exit_decision=facts.exit_reason,
            lifecycle_events=({"event_type": "PAPER_POSITION_OPENED", "occurred_at": "2026-08-11T00:00:00.000Z", "reason_code": "PAPER_POSITION_OPENED"},))

    def _views(self):
        return tuple(self.view(item) for item in self.facts) + tuple(self.extra_positions)

    def list_paper_positions(self, query):
        self.paper_calls += 1
        values = list(self._views())
        if query.state: values = [v for v in values if v.position.state.value == query.state]
        if query.symbol: values = [v for v in values if v.position.symbol == query.symbol]
        values.sort(key=lambda v: (v.updated_at, v.position.position_id), reverse=True)
        if query.cursor:
            anchor = (query.cursor.updated_at, query.cursor.identifier)
            values = [v for v in values if (v.updated_at, v.position.position_id) < anchor]
        return RecordPage(tuple(values[:query.limit]), len(values) > query.limit)

    def get_paper_position(self, position_id):
        self.paper_calls += 1
        return next((item for item in self._views() if item.position.position_id == position_id), None)

    def list_paper_trades(self, query):
        self.paper_calls += 1
        values = list(self.facts)
        if query.symbol: values = [v for v in values if v.position.symbol == query.symbol]
        if query.side: values = [v for v in values if v.position.side.value == query.side]
        if query.exit_reason: values = [v for v in values if v.exit_reason == query.exit_reason]
        if query.from_at: values = [v for v in values if v.position.closed_at >= query.from_at]
        if query.to_at: values = [v for v in values if v.position.closed_at < query.to_at]
        values.sort(key=lambda v: (v.position.closed_at, v.position.position_id), reverse=True)
        if query.cursor:
            anchor = (query.cursor.updated_at, query.cursor.identifier)
            values = [v for v in values if (v.position.closed_at, v.position.position_id) < anchor]
        return RecordPage(tuple(values[:query.limit]), len(values) > query.limit)

    def list_paper_orders(self, query): return RecordPage(self.orders[:query.limit], len(self.orders) > query.limit)
    def list_paper_fills(self, query): return RecordPage(self.fills[:query.limit], len(self.fills) > query.limit)
    def list_paper_journal(self, query): return RecordPage(self.journal[:query.limit], len(self.journal) > query.limit)
    def count_open_paper_positions(self):
        return sum(item.position.state.value in {"OPEN", "CLOSING"} for item in self._views())
    def total_unrealized_pnl(self):
        return sum((item.position.unrealized_pnl for item in self._views()
                    if item.position.state.value in {"OPEN", "CLOSING"}), Decimal("0"))


def control(state="DISABLED", generation=3):
    return PaperControlStatus(state=state, effective_state=state, generation=generation, health="HEALTHY",
        emergency_stop_available=True, audit_health="HEALTHY", state_audit_reconciliation="HEALTHY")


def client_for(baseline, *, revision="0016_control_mobile_device_security", facts=()):
    paper = FakePaperRepository(baseline, revision=revision, facts=facts)
    common = FakeReadRepository().api_repositories()
    app = create_app(repositories=replace(common, paper=paper), clock=lambda: NOW,
        paper_runtime=PaperRuntimeObservation(environment="isolated"), paper_control_status=control)
    return TestClient(app), paper


@pytest.mark.parametrize("case", range(1800))
def test_1800_readonly_openapi_contract_matrix(case):
    path = PAPER_PATHS[case % len(PAPER_PATHS)]
    operations = OPENAPI["paths"][path]
    assert "get" in operations
    assert not ({"post", "put", "patch", "delete"} & set(operations))
    assert OPENAPI["openapi"].startswith("3.1")


def test_0008_readiness_and_zero_paper_relation_reads(baseline):
    client, repo = client_for(baseline, revision="0008_engine_orchestrator_freshness_retry")
    response = client.get("/api/v1/paper/readiness")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "PAPER_SCHEMA_NOT_DEPLOYED"
    assert repo.paper_calls == 0
    for path in ("account", "positions", "trades", "reconciliation"):
        response = client.get(f"/api/v1/paper/{path}")
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PAPER_SCHEMA_NOT_DEPLOYED"
    assert repo.paper_calls == 0


@pytest.mark.parametrize(
    ("revision", "contract"),
    (
        ("0015_trading_universe_activation", True),
        ("0016_control_mobile_device_security", True),
        ("0017_parallel_trade_profiles", True),
        ("0018_promote_5m_production_search", True),
        ("0016_control_mobile_device_security", False),
        (("0015_trading_universe_activation", "0016_control_mobile_device_security"), True),
        ("corrupt", True),
    ),
)
def test_schema_revision_and_required_object_contract_fail_closed(
    baseline, revision, contract
):
    paper = FakePaperRepository(baseline, revision=revision, contract=contract)
    app = create_app(
        repositories=replace(FakeReadRepository().api_repositories(), paper=paper),
        clock=lambda: NOW,
    )
    data = TestClient(app).get("/api/v1/paper/readiness").json()["data"]
    expected = revision in {
        "0015_trading_universe_activation",
        "0016_control_mobile_device_security",
        "0017_parallel_trade_profiles",
        "0018_promote_5m_production_search",
    } and contract
    assert data["paper_schema_ready"] is expected
    assert (data["status"] == "PAPER_SCHEMA_NOT_DEPLOYED") is (not expected)
    if not expected:
        assert paper.paper_calls == 0


def test_0012_empty_missing_baseline_is_precise(baseline):
    client, repo = client_for(baseline)
    repo.baselines = ()
    assert client.get("/api/v1/paper/account").json()["error"]["code"] == "BASELINE_MISSING"
    assert client.get("/api/v1/paper/positions").json()["data"]["items"] == []
    assert client.get("/api/v1/paper/trades").json()["data"]["items"] == []
    reconciliation = client.get("/api/v1/paper/reconciliation").json()["data"]
    assert reconciliation["overall_status"] == "UNHEALTHY"
    assert reconciliation["accounting_reconciliation"]["findings"] == ["BASELINE_MISSING"]


def test_baseline_no_trades_account_exact_decimal_and_utc(baseline):
    client, _ = client_for(baseline)
    account = client.get("/api/v1/paper/account").json()["data"]
    assert account["initial_balance"] == account["current_balance"] == "100"
    assert account["closed_trade_count"] == 0
    assert account["initialized_at"].endswith("Z")
    assert client.get("/api/v1/paper/trades").json()["data"]["items"] == []


def test_full_trade_report_is_authoritative_projection(baseline):
    profitable = make_trade(1)
    losing = make_trade(2, side=PaperSide.SHORT, entry_price=profitable.position.average_entry_price, exit_price=profitable.position.average_entry_price + 1)
    client, _ = client_for(baseline, facts=(losing, profitable))
    account = client.get("/api/v1/paper/account").json()["data"]
    history = client.get("/api/v1/paper/trades").json()["data"]
    report = client.get(f"/api/v1/paper/trades/{profitable.position.position_id}/report").json()["data"]
    assert account["closed_trade_count"] == 2
    assert len(history["items"]) == 2
    assert report["net_pnl"] == str(profitable.position.realized_pnl.normalize())
    assert report["total_fees"] == str((profitable.entry_fill.fee_amount + profitable.exit_fill.fee_amount).normalize())
    assert report["balance_after"] != report["balance_before"]
    assert isinstance(report["entry_price"], str) and isinstance(report["roi_percent"], str)


def test_open_position_visible_and_final_report_unavailable(baseline):
    facts = make_trade(3)
    open_position = replace(facts.position, state=PaperPositionState.OPEN,
        remaining_quantity=facts.position.entry_quantity, average_exit_price=None, closed_at=None,
        exit_fill_id=None, exit_fees=Decimal("0"), realized_pnl=Decimal("0"))
    view = PaperPositionRecordView(position=open_position, entry_time=open_position.opened_at,
        updated_at=open_position.opened_at, entry_order_id=open_position.entry_order_id,
        entry_fill_id=open_position.entry_fill_id)
    client, repo = client_for(baseline)
    repo.extra_positions = (view,)
    item = client.get("/api/v1/paper/positions?state=OPEN").json()["data"]["items"][0]
    assert item["state"] == "OPEN" and item["realized_pnl"] is None
    response = client.get(f"/api/v1/paper/trades/{open_position.position_id}/report")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "FINAL_REPORT_NOT_AVAILABLE"


def test_runtime_and_control_are_read_only_fail_closed(baseline):
    client, _ = client_for(baseline)
    runtime = client.get("/api/v1/paper/runtime/status").json()["data"]
    status = client.get("/api/v1/paper/control/status").json()["data"]
    assert runtime["mutation_enabled"] is False and runtime["live_allowed"] is False
    assert status["state"] == "DISABLED" and status["generation"] == 3


def test_no_eligible_approval_is_healthy_no_trade_semantic(baseline):
    paper = FakePaperRepository(baseline)
    app = create_app(repositories=replace(FakeReadRepository().api_repositories(), paper=paper), clock=lambda: NOW,
        paper_runtime=PaperRuntimeObservation(environment="isolated", market_data_adapter_ready=True,
            approval_source_adapter_ready=True, wal_ready=True, pitr_ready=False,
            current_approval_availability="NO_ELIGIBLE_APPROVAL"), paper_control_status=control)
    data = TestClient(app).get("/api/v1/paper/readiness").json()["data"]
    assert data["status"] == "READY"
    assert data["current_approval_availability"] == "NO_ELIGIBLE_APPROVAL"
    assert data["current_mutation_ready"] is False


def test_callable_authoritative_runtime_can_make_first_arm_truthfully_ready(baseline):
    paper = FakePaperRepository(baseline)
    calls = []
    runtime = PaperRuntimeObservation(
        environment="production", runtime_enabled=True,
        market_data_adapter_ready=True, approval_source_adapter_ready=True,
        wal_ready=True, pitr_ready=True, current_approval_availability="NO_TRADE_SIGNAL",
        paper_principal_ready=True, production_identity_binding_ready=True,
        runtime_config_ready=True, kill_switch_ready=True, canary_scope_valid=True,
        live_enabled=False,
    )
    app = create_app(
        repositories=replace(FakeReadRepository().api_repositories(), paper=paper),
        clock=lambda: NOW,
        paper_runtime=lambda: calls.append("observed") or runtime,
        paper_control_status=lambda: PaperControlStatus(
            state="DISABLED", effective_state="DISABLED", generation=3,
            health="HEALTHY", emergency_stop_available=True,
            audit_health="PASS", state_audit_reconciliation="PASS",
        ),
    )
    data = TestClient(app).get("/api/v1/paper/readiness").json()["data"]
    assert calls == ["observed"]
    assert data["paper_control_state"] == "DISABLED"
    assert data["paper_control_generation"] == 3
    assert data["market_data_adapter_ready"] is True
    assert data["approval_source_adapter_ready"] is True
    assert data["current_mutation_ready"] is True
    assert data["current_mutation_denial_reasons"] == []
    assert data["live_allowed"] is False


def test_armed_control_projects_exact_generation_canary_and_start_specific_readiness(baseline):
    paper = FakePaperRepository(baseline)
    runtime = PaperRuntimeObservation(
        environment="production", runtime_enabled=True,
        market_data_adapter_ready=True, approval_source_adapter_ready=True,
        wal_ready=True, pitr_ready=True, current_approval_availability="NO_TRADE_SIGNAL",
        paper_principal_ready=True, production_identity_binding_ready=True,
        runtime_config_ready=True, kill_switch_ready=False, canary_scope_valid=True,
        live_enabled=False,
    )
    canary_id = "8c52768d-2a3a-47cb-acdc-3d1cb1b6ce9d"
    app = create_app(
        repositories=replace(FakeReadRepository().api_repositories(), paper=paper),
        clock=lambda: NOW,
        paper_runtime=runtime,
        paper_control_status=lambda: PaperControlStatus(
            state="ARMED", effective_state="ARMED", generation=4,
            health="HEALTHY", emergency_stop_available=True,
            audit_health="PASS", state_audit_reconciliation="PASS",
            canary_id=canary_id,
        ),
    )
    client = TestClient(app)
    readiness = client.get("/api/v1/paper/readiness").json()["data"]
    status = client.get("/api/v1/paper/control/status").json()["data"]

    assert readiness["paper_control_state"] == "ARMED"
    assert readiness["paper_control_effective_state"] == "ARMED"
    assert readiness["paper_control_generation"] == 4
    assert readiness["paper_control_health"] == "HEALTHY"
    assert readiness["paper_canary_id"] == canary_id
    assert readiness["current_mutation_ready"] is False
    assert readiness["current_mutation_denial_reasons"] == ["KILL_SWITCH_NOT_READY"]
    assert status == {
        "state": "ARMED", "effective_state": "ARMED", "generation": 4,
        "health": "HEALTHY", "emergency_stop_available": True,
        "audit_health": "PASS", "state_audit_reconciliation": "PASS",
        "canary_id": canary_id,
        "canary_status": None,
        "canary_command_limit": None, "canary_command_count": None,
        "canary_command_remaining": None, "canary_command_budget_exhausted": None,
        "canary_open_position_limit": None, "canary_open_position_count": None,
        "canary_open_position_remaining": None, "canary_open_position_budget_exhausted": None,
        "canary_closed_trade_count": None,
    }


def test_trade_pagination_100_plus_one_has_no_duplicate_or_missing_rows(baseline):
    facts = tuple(make_trade(index + 100) for index in range(101))
    client, _ = client_for(baseline, facts=facts)
    first = client.get("/api/v1/paper/trades?limit=100").json()["data"]
    assert len(first["items"]) == 100 and first["has_more"] is True
    second = client.get("/api/v1/paper/trades", params={"limit": 100, "cursor": first["next_cursor"]}).json()["data"]
    assert len(second["items"]) == 1 and second["has_more"] is False
    ids = [item["position_id"] for item in first["items"] + second["items"]]
    assert len(ids) == len(set(ids)) == 101


@pytest.mark.parametrize("state", ("DISABLED", "ARMED", "EMERGENCY_STOP"))
def test_control_status_stable_states_without_transition(baseline, state):
    paper = FakePaperRepository(baseline)
    app = create_app(repositories=replace(FakeReadRepository().api_repositories(), paper=paper),
        clock=lambda: NOW, paper_control_status=lambda: control(state, 7))
    client = TestClient(app)
    first = client.get("/api/v1/paper/control/status").json()["data"]
    second = client.get("/api/v1/paper/control/status").json()["data"]
    assert first == second and first["state"] == state and first["generation"] == 7


def test_control_corrupt_or_missing_fails_closed_without_detail(baseline):
    paper = FakePaperRepository(baseline)
    def unavailable():
        raise ValueError("internal audit payload must not escape")
    app = create_app(repositories=replace(FakeReadRepository().api_repositories(), paper=paper),
        clock=lambda: NOW, paper_control_status=unavailable)
    data = TestClient(app).get("/api/v1/paper/control/status").json()["data"]
    assert data["effective_state"] == "FAIL_CLOSED" and data["generation"] is None
    assert "payload" not in str(data).lower()


def test_limits_filters_errors_and_schema_inventory(baseline):
    client, _ = client_for(baseline)
    assert client.get("/api/v1/paper/positions?limit=101").json()["error"]["code"] == "LIMIT_EXCEEDED"
    assert client.get("/api/v1/paper/trades?side=INVALID").json()["error"]["code"] == "INVALID_FILTER"
    assert client.get("/api/v1/paper/trades?from=2025-01-01T00:00:00Z&to=2026-08-01T00:00:00Z").json()["error"]["code"] == "DATE_RANGE_EXCEEDED"
    document = create_app().openapi()
    methods = [method for operations in document["paths"].values() for method in operations if method in {"get", "post", "put", "patch", "delete"}]
    assert methods.count("get") == 28
    assert set(methods) == {"get"}


def test_authoritative_canary_budgets_and_counts_are_additive(baseline):
    paper = FakePaperRepository(baseline)
    app = create_app(
        repositories=replace(FakeReadRepository().api_repositories(), paper=paper), clock=lambda: NOW,
        paper_runtime=PaperRuntimeObservation(environment="isolated"),
        paper_control_status=lambda: PaperControlStatus(
            state="ARMED", effective_state="ARMED", generation=6, health="HEALTHY",
            emergency_stop_available=True, audit_health="PASS", state_audit_reconciliation="PASS",
            canary_id="8c52768d-2a3a-47cb-acdc-3d1cb1b6ce9d", canary_status="WAITING_FOR_ELIGIBLE_APPROVAL",
            canary_command_limit=1, canary_command_count=0, canary_command_remaining=1,
            canary_command_budget_exhausted=False, canary_open_position_limit=1,
            canary_open_position_count=0, canary_open_position_remaining=1,
            canary_open_position_budget_exhausted=False, canary_closed_trade_count=0,
        ),
    )
    data = TestClient(app).get("/api/v1/paper/readiness").json()["data"]
    assert data["paper_control_generation"] == 6
    assert (data["canary_command_limit"], data["canary_command_count"], data["canary_command_remaining"]) == (1, 0, 1)
    assert (data["canary_open_position_limit"], data["canary_open_position_count"], data["canary_open_position_remaining"]) == (1, 0, 1)
    assert data["canary_command_budget_exhausted"] is data["canary_open_position_budget_exhausted"] is False


def test_bounded_orders_fills_and_journal_contracts(baseline):
    paper = FakePaperRepository(baseline)
    paper.orders = (PaperOrderRecordView(
        "order-1", "command-1", "BTCUSDT", "LONG", "ENTRY", "MARKET", "FILLED",
        Decimal("1.25"), Decimal("1.25"), Decimal("100"), "PAPER_ORDER_FILLED", NOW, NOW,
    ),)
    paper.fills = (PaperFillRecordView(
        "fill-1", "order-1", "BTCUSDT", "LONG", "ENTRY", Decimal("1.25"),
        Decimal("100"), Decimal("0.1"), "USDT", NOW,
    ),)
    paper.journal = (PaperJournalRecordView(
        "event-1", "ORDER", "order-1", "PAPER_ORDER_FILLED", 1,
        "PAPER_ORDER_FILLED", "cause-1", "correlation-1", NOW,
    ),)
    client = TestClient(create_app(
        repositories=replace(FakeReadRepository().api_repositories(), paper=paper), clock=lambda: NOW,
    ))
    order = client.get("/api/v1/paper/orders?limit=50").json()["data"]["items"][0]
    fill = client.get("/api/v1/paper/fills?limit=50").json()["data"]["items"][0]
    event = client.get("/api/v1/paper/journal?limit=50").json()["data"]["items"][0]
    assert order["quantity"] == "1.25" and order["state"] == "FILLED"
    assert fill["price"] == "100" and fill["fee"] == "0.1"
    assert event["entity_id"] == "order-1" and event["correlation_id"] == "correlation-1"


def test_server_reporting_source_contains_no_mutation_or_financial_formula_duplication():
    paths = tuple((ROOT / "app/server_api").rglob("*.py"))
    source = "\n".join(path.read_text(encoding="utf-8") for path in paths).lower()
    forbidden = (".commit(", ".flush(", ".add(", ".delete(", "with_for_update", "select for update",
                 "gross_realized_pnl", "quote_fee_amount", "binance")
    assert [token for token in forbidden if token in source] == []


def test_future_readonly_capability_plan_is_select_only():
    plan = (ROOT / "docs/paper_readonly_role_capability_matrix.md").read_text(encoding="utf-8")
    for table in ("paper_account_baselines", "paper_positions", "paper_orders", "paper_fills",
                  "paper_exit_evaluation_cursors", "paper_exit_decisions", "paper_journal_entries", "alembic_version"):
        assert table in plan
    for forbidden in ("INSERT", "UPDATE", "DELETE", "TRUNCATE", "CREATE", "ALTER"):
        assert forbidden not in plan
