from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.engine_paper.paper_config import PaperConfig
from app.engine_paper.trading_criteria import build_trading_criteria_snapshot
from app.engine_risk.risk_config import RiskConfig
import app.engine_paper.trading_criteria as criteria_module
from app.server_api.routes.paper import build_paper_router
from app.server_api.services.paper_reporting import PaperReadonlyReportingService
from app.trading_universe.domain import PREPARED_NEXT_TRADING_UNIVERSE


def _items(snapshot):
    return {item["key"]: item for values in snapshot["groups"].values() for item in values}


def test_snapshot_reads_authoritative_policy_objects(monkeypatch):
    paper = replace(PaperConfig(), minimum_planned_rr=1.75)
    risk = replace(RiskConfig(), minimum_strategy_score=71.0)
    monkeypatch.setattr(criteria_module, "PaperConfig", lambda: paper)
    monkeypatch.setattr(criteria_module, "RiskConfig", lambda: risk)
    items = _items(build_trading_criteria_snapshot())
    assert items["minimum_planned_risk_reward"]["value"] == 1.75
    assert items["minimum_strategy_score"]["value"] == 71.0


def test_semantic_classifications_and_no_invented_target_return():
    items = _items(build_trading_criteria_snapshot())
    assert items["minimum_planned_risk_reward"]["classification"] == "FIXED_THRESHOLD"
    assert items["stop_loss"]["classification"] == "DYNAMIC_RULE"
    assert items["planned_risk_reward"]["classification"] == "DERIVED_VALUE"
    assert items["minimum_target_return"]["classification"] == "NOT_CONFIGURED_AS_FIXED_THRESHOLD"
    assert items["minimum_target_return"]["value"] is None
    assert items["default_stop_buffer"]["value"] == 0.1
    assert items["fallback_target_default_rr"]["classification"] == "NOT_APPLICABLE"
    assert items["allowed_risk_levels"]["value"] == ["LOW"]
    assert items["intrabar_conflict_policy"]["value"] == ["STOP_FIRST_CONSERVATIVE"]
    assert items["balance_exposure_limit"]["classification"] == "NOT_CONFIGURED_AS_FIXED_THRESHOLD"
    assert items["allowed_symbols"]["classification"] == "ENUM_ALLOWLIST"
    assert items["mode"]["value"] == ["PAPER"]
    assert items["max_new_commands"]["value"] == 1
    assert items["max_open_positions"]["value"] == 1


def test_snapshot_is_bounded_and_contains_no_secrets():
    payload = build_trading_criteria_snapshot()
    rendered = repr(payload).lower()
    assert len(rendered) < 50_000
    for forbidden in ("database_url", "password", "bearer", "protected_binding", "environment variables"):
        assert forbidden not in rendered


def test_readonly_get_contract_and_zero_write_routes():
    app = FastAPI()
    repository = SimpleNamespace(active_trading_universe=lambda: PREPARED_NEXT_TRADING_UNIVERSE)
    service = PaperReadonlyReportingService(repository)
    app.include_router(build_paper_router(service, lambda: "2026-08-14T00:00:00.000Z"))
    response = TestClient(app).get("/api/v1/paper/trading-criteria")
    assert response.status_code == 200
    assert response.json()["data"]["title_key"] == "current_server_trading_criteria"
    paths = {path: operations for path, operations in app.openapi()["paths"].items()
             if path.startswith("/api/v1/paper")}
    assert set(paths["/api/v1/paper/trading-criteria"]) == {"get"}
    assert not any({"post", "put", "patch", "delete"} & set(operations)
                   for operations in paths.values())
