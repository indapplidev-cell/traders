from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.engine_orchestrator.orchestrator_models import OnlinePipelineResultRow, OnlinePipelineRun
from app.server_api.app_factory import create_app
from app.server_api.trading_funnel import (
    CANONICAL_DOWNSTREAM_STAGES,
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


def _project_5m(pairs, eligible=None):
    universe = SimpleNamespace(version_id="trading-universe-v2", symbols=SYMBOLS)
    for run, result in pairs:
        run.primary_timeframe = "5m"
        run.trade_profile_id = "trade-5m-v1"
        if result is not None:
            result.primary_timeframe = "5m"
            result.trade_profile_id = "trade-5m-v1"
    return build_projection(
        tuple(pairs), universe, NOW_MS, eligible or {}, "trade-5m-v1"
    )


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


def test_scalping_canonical_downstream_order_risk_distinction_and_detail():
    run = _run("BTCUSDT")
    result = _result(run)
    result.strategy_payload_json.update({
        "strategy_type": "SCALP_BREAKOUT_RESEARCH",
        "strategy_final_score": "88.75",
    })
    result.setup_payload_json["setup_type"] = "SCALP_BREAKOUT"
    result.paper_payload_json["paper_context"] = {
        "production_rr_floor": "1.5",
        "scalping_geometry_diagnostics": {
            "entry": "100.25",
            "final_stop": "99.75",
            "causal_target": "101.30",
            "stop_envelope_pass": True,
            "causal_target_exists": True,
            "economic_gate_pass": True,
            "valid_plan": True,
            "stop_distance_bps": "42.5",
            "target_distance_bps": "90",
            "target_source_type": "LOCAL_5M",
            "spread_bps": "0.8",
            "depth_impact_bps": "1.2",
            "entry_fee_bps": "10",
            "exit_fee_bps": "10",
            "entry_slippage_bps": "2",
            "exit_slippage_bps": "2",
            "safety_margin_bps": "3",
            "total_cost_bps": "27.8",
            "gross_rr": "2.1",
            "net_rr": "1.6",
            "expected_net_edge_bps": "62.2",
            "break_even_win_rate": "0.38461538",
        }
    }
    result.paper_payload_json.update({
        "hypothetical_entry_reference": "100.25",
        "hypothetical_stop_level": "99.75",
        "hypothetical_target_level": "101.30",
        "entry_reference_source": "confirmation_or_reference_closed_candle",
        "stop_source": "causal_invalidation_plus_profile_atr_buffer",
        "target_source": "LOCAL_5M",
        "created_at_ms": BOUNDARY + 100,
        "closed_until_ms": BOUNDARY,
        "quantity_sizing_audit": {
            "paper_equity_at_approval": "100",
            "risk_budget": "1",
            "normalized_quantity": "0.9",
            "applicable_quantity_step": "0.1",
        },
        "approval_validity": {
            "source_candle_close_time_ms": BOUNDARY,
            "valid_until_ms": BOUNDARY + 300_000,
        },
    })
    other = _run("ETHUSDT")
    other_result = _result(
        other, setup="NO_SETUP", strategy="NO_DECISION",
        risk="NO_DECISION", paper="NO_PLAN", approvals=False,
        reasons={"setup": ["NO_STRUCTURAL_SETUP"], "paper": ["PAPER_NO_PLAN_SOURCE_NO_DECISION"]},
    )
    value = _project_5m(((run, result), (other, other_result)))
    item = value["current_cycle"]["items"][0]
    assert tuple(value["downstream_stage_order"]) == CANONICAL_DOWNSTREAM_STAGES
    assert item["downstream_stage_trace"]["RISK_COMPATIBILITY_ADMITTED"] == "PASS"
    assert item["downstream_stage_trace"]["RISK_ADMITTED"] == "PASS"
    assert item["downstream_stage_trace"]["PORTFOLIO_ADMITTED"] == "UNAVAILABLE"
    assert item["downstream_detail"]["strategy_type"] == "SCALP_BREAKOUT_RESEARCH"
    assert item["downstream_detail"]["net_rr"] == "1.6"
    assert item["downstream_detail"]["entry_price"] == "100.25"
    assert item["downstream_detail"]["stop_price"] == "99.75"
    assert item["downstream_detail"]["target_price"] == "101.30"
    assert item["downstream_detail"]["stop_distance_absolute"] == "0.50"
    assert item["downstream_detail"]["target_distance_absolute"] == "1.05"
    assert item["downstream_detail"]["required_rr"] == "1.5"
    assert item["downstream_detail"]["fee_estimate_bps"] == "20"
    assert item["downstream_detail"]["slippage_estimate_bps"] == "4"
    assert item["downstream_detail"]["expected_net_edge_bps"] == "62.2"
    assert item["downstream_detail"]["risk_percent"] == "1.00"
    assert item["downstream_detail"]["planned_quantity"] == "0.9"
    assert item["downstream_detail"]["planned_notional"] == "90.225"
    assert item["downstream_detail"]["ttl_ms"] == 300_000
    assert value["current_cycle"]["downstream_stage_counts"]["RR_PASS"] == 1
    assert value["current_cycle"]["downstream_stage_counts"]["PORTFOLIO_ADMITTED"] is None
    assert value["rolling_1h"]["downstream_stage_counts"]["NET_COST_PASS"] == 1
    assert value["rolling_4h"]["downstream_stage_counts"]["NET_COST_PASS"] == 1
    rejected = value["current_cycle"]["items"][1]
    assert rejected["terminal_reason_code"] == "NO_STRUCTURAL_SETUP"


def test_scalping_geometry_terminal_reason_and_null_are_not_zero():
    run = _run("BTCUSDT")
    result = _result(run, paper="NO_PLAN", approvals=False)
    result.paper_payload_json["paper_context"] = {
        "scalping_geometry_diagnostics": {
            "stop_envelope_pass": False,
            "stop_distance_bps": "254.1",
            "rejection_stage": "STOP_ENVELOPE",
            "rejection_reason": "GEOMETRY_STOP_TOO_WIDE",
            "target_distance_bps": None,
            "spread_bps": None,
        }
    }
    other = _run("ETHUSDT")
    other_result = _result(other, setup="NO_SETUP", approvals=False)
    value = _project_5m(((run, result), (other, other_result)))
    item = value["current_cycle"]["items"][0]
    assert item["downstream_stage_trace"]["GEOMETRY_VALID"] == "REJECTED"
    assert item["terminal_reason_code"] == "GEOMETRY_STOP_TOO_WIDE"
    assert item["downstream_detail"]["target_distance_bps"] is None
    assert item["downstream_detail"]["spread_bps"] is None
    assert value["current_cycle"]["stage_rejected_count"]["GEOMETRY_VALID"] == 1


def test_detail_candidate_prefers_historical_plan_then_latest_rr_reject():
    current = _run("BTCUSDT")
    current_result = _result(current, setup="NO_SETUP", approvals=False)
    other_current = _run("ETHUSDT")
    other_current_result = _result(other_current, setup="NO_SETUP", approvals=False)
    old_boundary = BOUNDARY - 300_000
    plan = _run("BTCUSDT", old_boundary)
    plan_result = _result(plan)
    plan_result.paper_payload_json["paper_context"] = {
        "production_rr_floor": "1.5",
        "scalping_geometry_diagnostics": {
            "stop_envelope_pass": True, "causal_target_exists": True,
            "economic_gate_pass": True, "valid_plan": True,
            "gross_rr": "2", "net_rr": "1.6",
        },
    }
    rr = _run("ETHUSDT", old_boundary)
    rr_result = _result(rr, paper="REJECT", approvals=False)
    rr_result.paper_payload_json["paper_context"] = {
        "production_rr_floor": "1.5",
        "scalping_geometry_diagnostics": {
            "stop_envelope_pass": True, "causal_target_exists": True,
            "economic_gate_pass": True, "valid_plan": False,
            "gross_rr": "1.4", "net_rr": "1.1",
            "rejection_stage": "RR_GATE",
            "rejection_reason": "PAPER_REJECT_LOW_NET_RR",
        },
    }
    value = _project_5m(((current, current_result), (other_current, other_current_result),
                         (plan, plan_result), (rr, rr_result)))
    details = {item["symbol"]: item for item in value["detail_candidates"]}
    assert details["BTCUSDT"]["source_run_id"] == plan.run_id
    assert details["BTCUSDT"]["downstream_stage_trace"]["PAPER_PLAN"] == "PASS"
    assert details["ETHUSDT"]["source_run_id"] == rr.run_id
    assert details["ETHUSDT"]["downstream_stage_trace"]["RR_PASS"] == "REJECTED"


def test_15m_downstream_is_explicitly_not_applicable_and_legacy_is_unchanged():
    run = _run("BTCUSDT")
    other = _run("ETHUSDT")
    value = _project(((run, _result(run)), (other, _result(other))))
    item = value["current_cycle"]["items"][0]
    assert all(
        status == "NOT_APPLICABLE"
        for status in item["downstream_stage_trace"].values()
    )
    assert all(
        count is None
        for count in value["current_cycle"]["downstream_stage_counts"].values()
    )
    assert value["current_cycle"]["stage_counts"]["RISK_APPROVED"] == 2


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
    assert five.json()["data"]["trade_mode"] == "SCALPING"
    assert five.json()["data"]["display_i18n_key"] == "trading.profile.trade_5m.title"
    assert five.json()["data"]["primary_timeframe"] == "5m"
    assert five.json()["data"]["entry_timeframes"] == ["1m", "5m"]
    assert five.json()["data"]["context_timeframes"] == ["15m", "1h"]
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


def test_5m_repository_uses_bounded_cycle_and_historical_plan_queries():
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
        monotonic_clock=lambda: 10.0,
    )
    first = projection.project(NOW_MS, "trade-5m-v1")
    second = projection.project(NOW_MS + 1_000, "trade-5m-v1")

    assert first["trade_profile_id"] == "trade-5m-v1"
    assert second["projection_generated_at_ms"] == NOW_MS + 1_000
    assert len(sessions) == 1
    # One rolling-window query plus one set-based historical PAPER-plan query;
    # neither path issues per-symbol/N+1 reads, and both are cached together.
    assert sessions[0].execute_count == 2


def test_expired_5m_cache_is_released_before_replacement_query():
    run = _run("BTCUSDT")
    run.id = 1
    run.primary_timeframe = "5m"
    run.trade_profile_id = "trade-5m-v1"
    result = _result(run, approvals=False)
    result.id = 1
    result.primary_timeframe = "5m"
    result.trade_profile_id = "trade-5m-v1"
    clock = iter((10.0, 41.0))
    repository = None

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, _statement):
            assert repository is not None
            assert "trade-5m-v1" not in repository._row_cache
            return ((run, result),)

    class Capabilities:
        def snapshot(self):
            return self

        def has(self, _capability):
            return True

    universe = SimpleNamespace(
        version_id="trading-universe-v2",
        symbols=("BTCUSDT",),
    )
    repository = TradingFunnelReadRepository(
        Session,
        lambda: universe,
        schema_capabilities=Capabilities(),
        monotonic_clock=lambda: next(clock),
    )

    repository.project(NOW_MS, "trade-5m-v1")
    first_rows = repository._row_cache["trade-5m-v1"][1]
    repository.project(NOW_MS + 31_000, "trade-5m-v1")

    assert repository._row_cache["trade-5m-v1"][1] is not first_rows
