from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.engine_orchestrator.orchestrator_models import OnlinePipelineResultRow, OnlinePipelineRun
from app.server_api.app_factory import create_app
from app.server_api.trading_funnel import (
    MAX_HORIZON_MS,
    TradingFunnelReadRepository,
    build_projection,
)
from app.trading_universe.domain import runtime_universe
from tests.server_api.fakes import FakeReadRepository


NOW_MS = 1_900_000_800_000
BOUNDARY = 1_900_000_200_000
SYMBOLS = ("BTCUSDT", "ETHUSDT")


def _run(symbol: str, boundary: int = BOUNDARY, *, status: str = "COMPLETED", run_id: str | None = None):
    stamp = datetime.fromtimestamp(boundary / 1000, tz=timezone.utc)
    return OnlinePipelineRun(
        run_id=run_id or f"run:{symbol}:{boundary}", symbol=symbol, primary_timeframe="15m",
        closed_until_ms=boundary, closed_until_utc=stamp, status=status, started_at=stamp,
        finished_at=stamp, trigger_source="test", daemon_instance_id="test", updated_at=stamp,
    )


def _result(run: OnlinePipelineRun, *, setup="SETUP_CANDIDATE", strategy="ALLOW_RESEARCH_TRADE_PLAN",
            risk="RISK_PRE_APPROVED_RESEARCH", paper="PAPER_PLAN_READY", approvals=True,
            valid_until=NOW_MS + 60_000, reasons=None, generation=None):
    approval = {
        "approval_id": f"approval:{run.symbol}", "valid_until_ms": valid_until,
        "final_paper_approval": True, "order_approved": True,
        "execution_approved": True, "position_size_approved": True,
    }
    payload = {"paper_status": paper, "planned_risk_reward": "2"}
    if approvals:
        payload["persisted_final_approvals"] = {
            "paper_strategy_approval": dict(approval),
            "paper_quantity_approval": {**approval, "quantity_approval_id": f"quantity:{run.symbol}"},
            "paper_risk_approval": dict(approval),
        }
        payload["final_approval_generation"] = {
            "final_approval_id": f"approval:{run.symbol}", "candidate_id": f"setup:{run.symbol}"
        }
    elif generation is not None:
        payload["final_approval_generation"] = generation
    return OnlinePipelineResultRow(
        run_id=run.run_id, symbol=run.symbol, primary_timeframe="15m", closed_until_ms=run.closed_until_ms,
        analysis_payload_json={"status": "ANALYZED"},
        setup_payload_json={"status": setup, "setup_id": f"setup:{run.symbol}", "direction_hint": "BULLISH"},
        strategy_payload_json={"decision_status": strategy, "strategy_score": "80"},
        risk_payload_json={"risk_status": risk, "risk_score": "70"}, paper_payload_json=payload,
        module_reasons_json=reasons or {}, module_warnings_json={}, safety_counters_json={},
        created_at=datetime.fromtimestamp(run.closed_until_ms / 1000, tz=timezone.utc),
    )


def _candidate(run: OnlinePipelineRun):
    ranking = SimpleNamespace(risk_score=Decimal("70"), planned_risk_reward=Decimal("2"),
                              strategy_score=Decimal("80"), closed_until_ms=run.closed_until_ms,
                              source_run_id=run.run_id, final_approval_id=f"approval:{run.symbol}")
    lineage = SimpleNamespace(source_run_id=run.run_id, final_approval_id=f"approval:{run.symbol}")
    return SimpleNamespace(candidate_id=f"candidate:{run.symbol}", symbol=run.symbol, ranking=ranking, lineage=lineage)


def _project(pairs, eligible=None):
    universe = SimpleNamespace(version_id="trading-universe-v2", symbols=SYMBOLS)
    return build_projection(tuple(pairs), universe, NOW_MS, eligible or {})


def test_current_cycle_empty_or_startup():
    value = _project([])
    assert value["current_cycle"] is None
    assert value["last_completed_cycle"] is None
    assert value["freshness_state"] == "NOT_AVAILABLE"


def test_current_partial_complete_and_last_completed_are_distinct():
    old = BOUNDARY - 900_000
    pairs = []
    for symbol in SYMBOLS:
        run = _run(symbol, old)
        pairs.append((run, _result(run, setup="NO_SETUP", strategy="NO_DECISION", risk="NO_DECISION", paper="NO_PLAN", approvals=False)))
    current = _run("BTCUSDT")
    pairs.append((current, _result(current)))
    value = _project(pairs)
    assert value["current_cycle"]["symbols_processed"] == 1
    assert value["current_cycle"]["cycle_complete"] is False
    assert value["last_completed_cycle"]["boundary_close_ms"] == old
    assert value["current_cycle"]["boundary_close_ms"] != value["last_completed_cycle"]["boundary_close_ms"]


def test_complete_boundary_requires_each_expected_symbol_terminal_after_natural_unique_identity():
    pairs = []
    for symbol in SYMBOLS:
        run = _run(symbol)
        pairs.append((run, _result(run)))
    newer = _run("BTCUSDT", BOUNDARY + 900_000, status="RUNNING")
    pairs.append((newer, None))
    value = _project(pairs)
    assert value["current_cycle"]["symbols_seen"] == 1
    assert value["current_cycle"]["symbols_processed"] == 0
    assert value["last_completed_cycle"]["cycle_complete"] is True


def test_stage_reason_not_reached_error_and_expiry_semantics():
    rejected = _run("BTCUSDT")
    error = _run("ETHUSDT", status="MODULE_ERROR")
    pairs = [
        (rejected, _result(rejected, strategy="REJECT", risk="NO_DECISION", paper="NO_PLAN", approvals=False,
                           reasons={"strategy": ["STRATEGY_SCORE_TOO_LOW"]})),
        (error, _result(error, setup="ERROR", strategy="NO_DECISION", risk="NO_DECISION", paper="NO_PLAN", approvals=False)),
    ]
    value = _project(pairs)
    first, second = value["current_cycle"]["items"]
    assert first["stage_trace"]["STRATEGY_ELIGIBLE"] == "REJECTED"
    assert first["stage_trace"]["RISK_APPROVED"] == "NOT_REACHED"
    assert first["source_reason_code"] == "STRATEGY_SCORE_TOO_LOW"
    assert second["stage_trace"]["STRUCTURAL_SETUP"] == "ERROR"


def test_expired_final_approval_preserves_historical_funnel_but_is_not_eligible():
    run = _run("BTCUSDT")
    other = _run("ETHUSDT")
    value = _project(
        [(run, _result(run, valid_until=NOW_MS - 1)),
         (other, _result(other, setup="NO_SETUP", approvals=False))],
        {run.run_id: _candidate(run)},
    )
    item = value["current_cycle"]["items"][0]
    assert item["stage_trace"]["FINAL_APPROVAL"] == "PASS"
    assert item["stage_trace"]["VALIDITY_APPROVED"] == "PASS"
    assert item["eligible"] is False
    assert item["source_reason_code"] == "APPROVAL_EXPIRED"
    assert value["rolling_1h"]["stage_counts"]["VALIDITY_APPROVED"] == 1
    assert value["rolling_1h"]["stage_counts"]["FINAL_APPROVAL"] == 1
    assert value["rolling_4h"]["stage_counts"]["VALIDITY_APPROVED"] == 1
    assert value["rolling_4h"]["stage_counts"]["FINAL_APPROVAL"] == 1


def test_identity_failure_uses_authoritative_reason_and_quantity_not_reached():
    run = _run("BTCUSDT")
    result = _result(
        run,
        approvals=False,
        reasons={"paper": ["PAPER_PLAN_READY_LOW_RISK"]},
        generation={
            "outcome": "PAPER_INPUT_IDENTITY_INVALID",
            "reason_code": "PAPER_INPUT_IDENTITY_INVALID",
            "stage": "FINAL_APPROVAL",
            "status": "REJECTED",
            "safe_reason_detail": "invalid public identity (causation_id)",
            "source_component": "NaturalFinalApprovalMaterializer",
            "quantity_authority_status": "NOT_REACHED",
        },
    )
    item = _project([(run, result)])["current_cycle"]["items"][0]
    assert item["source_reason_code"] == "PAPER_INPUT_IDENTITY_INVALID"
    assert item["source_reason_detail_safe"] == "invalid public identity (causation_id)"
    assert item["current_stage"] == "FINAL_APPROVAL"
    assert item["stage_status"] == "REJECTED"
    assert item["stage_trace"]["QUANTITY_APPROVED"] == "NOT_REACHED"
    assert item["stage_trace"]["FINAL_APPROVAL"] == "REJECTED"


def test_actual_quantity_reject_is_quantity_rejected_with_authority_reason():
    run = _run("BTCUSDT")
    result = _result(
        run,
        approvals=False,
        reasons={"paper": ["PAPER_PLAN_READY_LOW_RISK"]},
        generation={
            "outcome": "PAPER_INPUT_NOTIONAL_INVALID",
            "reason_code": "PAPER_INPUT_NOTIONAL_INVALID",
            "stage": "QUANTITY_APPROVED",
            "status": "REJECTED",
            "safe_reason_detail": "minimum notional is not met (approved_quantity)",
            "source_component": "NaturalFinalApprovalMaterializer",
            "quantity_authority_status": "REJECTED",
        },
    )
    item = _project([(run, result)])["current_cycle"]["items"][0]
    assert item["source_reason_code"] == "PAPER_INPUT_NOTIONAL_INVALID"
    assert item["current_stage"] == "QUANTITY_APPROVED"
    assert item["stage_status"] == "REJECTED"
    assert item["stage_trace"]["FINAL_APPROVAL"] == "NOT_REACHED"


def test_plan_ready_without_materializer_attempt_stays_at_plan_ready():
    run = _run("BTCUSDT")
    result = _result(
        run, approvals=False, reasons={"paper": ["PAPER_PLAN_READY_LOW_RISK"]}
    )
    item = _project([(run, result)])["current_cycle"]["items"][0]
    assert item["current_stage"] == "PAPER_TRADE_PLAN"
    assert item["stage_status"] == "PASS"
    assert item["stage_trace"]["QUANTITY_APPROVED"] == "NOT_REACHED"
    assert item["source_reason_code"] == "PAPER_PLAN_READY_LOW_RISK"


def test_zero_one_multiple_eligible_ranking_and_winner():
    runs = [_run(symbol) for symbol in SYMBOLS]
    pairs = [(run, _result(run)) for run in runs]
    zero = _project(pairs)
    assert zero["current_cycle"]["winner_symbol"] is None
    one = _project(pairs, {runs[0].run_id: _candidate(runs[0])})
    assert one["current_cycle"]["winner_symbol"] == "BTCUSDT"
    high = _candidate(runs[1])
    high.ranking.risk_score = Decimal("90")
    multiple = _project(pairs, {runs[0].run_id: _candidate(runs[0]), runs[1].run_id: high})
    assert multiple["current_cycle"]["winner_symbol"] == "ETHUSDT"
    assert multiple["current_cycle"]["eligible_competitors"][0]["rank"] == 1


def test_rolling_inclusion_boundaries_and_query_contract():
    pairs = []
    for delta in (0, 3_600_000, 3_600_001, 4 * 3_600_000):
        run = _run("BTCUSDT", NOW_MS - delta)
        pairs.append((run, _result(run, setup="NO_SETUP", approvals=False)))
    value = _project(pairs)
    assert value["rolling_1h"]["stage_counts"]["ANALYSIS"] == 2
    assert value["rolling_4h"]["stage_counts"]["ANALYSIS"] == 4
    assert value["query_time_horizon_ms"] == MAX_HORIZON_MS


class _Funnel:
    def project(self, now_ms):
        return _project([])


def test_get_route_healthy_empty_and_write_methods_absent():
    repositories = replace(FakeReadRepository().api_repositories(), funnel=_Funnel())
    client = TestClient(create_app(repositories=repositories, clock=lambda: datetime.fromtimestamp(NOW_MS / 1000, tz=timezone.utc)))
    response = client.get("/api/v1/trading/funnel")
    assert response.status_code == 200
    assert response.json()["data"]["current_cycle"] is None
    assert client.post("/api/v1/trading/funnel").status_code == 405


def test_get_route_explicit_profiles_are_isolated_and_invalid_is_4xx():
    class Profiles:
        def project(self, now_ms, trade_profile_id="trade-15m-v1"):
            universe = SimpleNamespace(version_id="trading-universe-v2", symbols=SYMBOLS)
            return build_projection((), universe, now_ms, {}, trade_profile_id)

    repositories = replace(FakeReadRepository().api_repositories(), funnel=Profiles())
    client = TestClient(create_app(
        repositories=repositories,
        clock=lambda: datetime.fromtimestamp(NOW_MS / 1000, tz=timezone.utc),
    ))
    fifteen = client.get("/api/v1/trading/funnel?trade_profile=trade-15m-v1")
    five = client.get("/api/v1/trading/funnel?trade_profile=trade-5m-v1")
    invalid = client.get("/api/v1/trading/funnel?trade_profile=unknown")
    assert fifteen.status_code == five.status_code == 200
    assert fifteen.json()["data"]["trade_profile_id"] == "trade-15m-v1"
    assert fifteen.json()["data"]["expected_1h_cycle_count"] == 4
    assert five.json()["data"]["trade_profile_id"] == "trade-5m-v1"
    assert five.json()["data"]["profile_mode"] == "PRODUCTION_SEARCH"
    assert five.json()["data"]["expected_1h_cycle_count"] == 12
    assert five.json()["data"]["expected_4h_cycle_count"] == 48
    assert five.json()["data"]["paper_command_creation_enabled"] is True
    assert five.json()["data"]["position_opening_enabled"] is True
    assert invalid.status_code == 422


def test_get_route_db_error_is_not_empty_success():
    class Broken:
        def project(self, now_ms):
            raise RuntimeError("database unavailable")
    repositories = replace(FakeReadRepository().api_repositories(), funnel=Broken())
    response = TestClient(create_app(repositories=repositories), raise_server_exceptions=False).get("/api/v1/trading/funnel")
    assert response.status_code == 500


def test_5m_repository_reuses_bounded_rows_for_approval_classification():
    run = _run("BTCUSDT")
    run.id = 1
    run.primary_timeframe = "5m"
    run.trade_profile_id = "trade-5m-v1"
    result = _result(run, approvals=False)
    result.id = 1
    result.primary_timeframe = "5m"
    result.trade_profile_id = "trade-5m-v1"

    class Session:
        execute_count = 0

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, _statement):
            self.execute_count += 1
            return ((run, result),)

    sessions = []

    def session_factory():
        session = Session()
        sessions.append(session)
        return session

    class Capabilities:
        def snapshot(self):
            return self

        def has(self, _capability):
            return True

    universe = SimpleNamespace(
        version_id="trading-universe-v2",
        symbols=("BTCUSDT",),
    )
    projection = TradingFunnelReadRepository(
        session_factory,
        lambda: universe,
        schema_capabilities=Capabilities(),
    ).project(NOW_MS, "trade-5m-v1")

    assert projection["trade_profile_id"] == "trade-5m-v1"
    assert len(sessions) == 1
    assert sessions[0].execute_count == 1
