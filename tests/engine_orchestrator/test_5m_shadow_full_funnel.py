from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.engine_orchestrator.orchestrator_models import (
    OnlinePipelineResultRow,
    OnlinePipelineRun,
)
from app.engine_orchestrator.orchestrator_config import OrchestratorConfig
from app.engine_orchestrator.pipeline_result import PipelineResult
from app.engine_orchestrator.pipeline_result_store import PipelineResultStore
from app.engine_orchestrator.pipeline_runner import PipelineRunner
from app.engine_orchestrator.runtime_parameters import resolve_runtime_parameters
from app.engine_paper.accounting import PaperAccountSummary
from app.engine_paper.paper_runner import PaperRunner
from app.engine_paper.shadow_approval_materializer import (
    ShadowFinalApprovalMaterializer,
)
from app.server_api.trading_funnel import build_projection
from app.engine_risk.risk_decision import RiskDecision
from tests.engine_orchestrator_01_helpers import CandleRepo, component, outputs


BOUNDARY = 1_800_000_000_000
NOW_MS = BOUNDARY + 1_000


def _account() -> PaperAccountSummary:
    zero = Decimal("0")
    return PaperAccountSummary(
        "account:shadow", "session:shadow", "USDT", Decimal("100"),
        Decimal("100"), zero, zero, zero, zero, 0, 0, 0, 0, zero,
        zero, zero, None, None, None, None, None, None,
    )


def _result() -> PipelineResult:
    parameter_id = resolve_runtime_parameters("trade-5m-v1").parameter_set_id
    return PipelineResult(
        symbol="BTCUSDT",
        primary_timeframe="5m",
        closed_until_ms=BOUNDARY,
        trade_profile_id="trade-5m-v1",
        profile_mode="SHADOW_SEARCH",
        runtime_parameter_set_id=parameter_id,
        analysis_status="ANALYZED",
        setup_status="SETUP_CANDIDATE",
        strategy_status="ALLOW_RESEARCH_TRADE_PLAN",
        risk_status="RISK_PRE_APPROVED_RESEARCH",
        paper_status="SHADOW_SEARCH",
        setup_payload={
            "setup_id": "setup:shadow:1",
            "status": "SETUP_CANDIDATE",
            "direction_hint": "BULLISH",
        },
        strategy_payload={
            "decision_id": "strategy:shadow:1",
            "decision_status": "ALLOW_RESEARCH_TRADE_PLAN",
            "strategy_score": "82",
        },
        risk_payload={
            "risk_decision_id": "risk:shadow:1",
            "risk_status": "RISK_PRE_APPROVED_RESEARCH",
            "risk_score": "90",
        },
        paper_payload={
            "paper_status": "SHADOW_SEARCH",
            "paper_command_creation_enabled": False,
            "position_opening_enabled": False,
            "validity_policy": {
                "valid_until_ms": BOUNDARY + 300_000,
                "validity_boundaries": 1,
            },
            "shadow_plan": {
                "paper_status": "PAPER_PLAN_READY",
                "symbol": "BTCUSDT",
                "timeframe": "5m",
                "closed_until_ms": BOUNDARY,
                "source_risk_decision_id": "risk:shadow:1",
                "source_strategy_decision_id": "strategy:shadow:1",
                "source_setup_id": "setup:shadow:1",
                "hypothetical_entry_reference": "100",
                "hypothetical_stop_level": "99",
                "hypothetical_target_level": "102",
                "planned_rr": "2",
            },
            "shadow_final_approval_candidate": {
                "candidate_id": "shadow:trade-5m-v1:BTCUSDT:1800000000000",
                "status": "PLAN_READY",
                "execution_eligible": False,
                "persisted_final_approval_created": False,
            },
        },
    )


def test_real_paper_planner_is_reused_as_non_executable_5m_shadow_plan():
    analysis, setup, strategy, _risk, _paper = outputs(
        setup_status="SETUP_CANDIDATE",
        strategy_status="ALLOW_RESEARCH_TRADE_PLAN",
        risk_status="RISK_PRE_APPROVED_RESEARCH",
    )
    risk = RiskDecision(
        risk_decision_id="risk:shadow:typed",
        created_at_ms=BOUNDARY,
        source_strategy_decision_id="strategy:shadow:typed",
        source_setup_id="setup:shadow:typed",
        source_analysis_snapshot_id="analysis:shadow:typed",
        symbol="BTCUSDT",
        timeframe="5m",
        closed_until_ms=BOUNDARY,
        risk_status="RISK_PRE_APPROVED_RESEARCH",
        risk_level="LOW",
        risk_score=90,
        risk_policy_version="shadow-risk-v1",
        source_decision_status="ALLOW_RESEARCH_TRADE_PLAN",
        source_strategy_type="BREAKOUT_CONTINUATION_RESEARCH",
        source_strategy_quality="ACCEPTABLE",
        source_strategy_score=82,
        direction_hint="BULLISH",
        risk_context={
            "reference_close": 100,
            "causal_support_level": 99.5,
            "causal_target_level": 101,
            "volatility_buffer": 0.1,
        },
        risk_pre_approved=True,
        requires_execution_review=True,
    )
    config = OrchestratorConfig(
        symbols=("BTCUSDT",),
        trade_profile_id="trade-5m-v1",
        primary_timeframe="5m",
        required_timeframes=("5m",),
        minimum_windows={"5m": 1},
    )
    result = PipelineRunner(
        config,
        CandleRepo(),
        analysis_runner=component(analysis),
        setup_runner=component(setup),
        strategy_runner=component(strategy),
        risk_runner=component(risk),
        paper_runner=PaperRunner(),
    ).run("BTCUSDT", BOUNDARY)
    assert result.paper_status == "SHADOW_SEARCH"
    assert result.paper_payload["shadow_plan_status"] == "PAPER_PLAN_READY"
    assert result.paper_payload["shadow_plan"]["planned_rr"] > 1.5
    assert result.paper_payload["shadow_final_approval_candidate"]["status"] == "PLAN_READY"
    assert result.safety_counters.has_violation is False


def test_shadow_materializer_completes_all_non_executable_approval_stages():
    materializer = ShadowFinalApprovalMaterializer(
        account_summary_source=lambda _session: _account()
    )
    value = materializer.materialize(
        None,  # type: ignore[arg-type]
        run_id="run:shadow:1",
        result=_result(),
        evaluation_time=datetime.fromtimestamp(NOW_MS / 1000, tz=timezone.utc),
    )
    payload = value.paper_payload
    assert value.final_approval_created is False
    assert value.outcome == "SHADOW_FINAL_APPROVAL_CREATED"
    assert "persisted_final_approvals" not in payload
    assert payload["shadow_final_approval_generation"]["status"] == "PASS"
    assert payload["shadow_final_approval_generation"]["execution_eligible"] is False
    assert set(payload["shadow_approvals"]) == {
        "shadow_plan_approval",
        "shadow_quantity_approval",
        "shadow_validity_approval",
        "shadow_final_approval",
    }
    assert payload["shadow_final_approval_candidate"]["status"] == "ELIGIBLE"
    assert payload["shadow_final_approval_candidate"]["execution_eligible"] is False


def test_shadow_projection_reaches_eligible_and_deterministic_winner_without_execution():
    materialized = ShadowFinalApprovalMaterializer(
        account_summary_source=lambda _session: _account()
    ).materialize(
        None,  # type: ignore[arg-type]
        run_id="run:shadow:1",
        result=_result(),
        evaluation_time=datetime.fromtimestamp(NOW_MS / 1000, tz=timezone.utc),
    )
    stamp = datetime.fromtimestamp(BOUNDARY / 1000, tz=timezone.utc)
    run = OnlinePipelineRun(
        run_id="run:shadow:1",
        trade_profile_id="trade-5m-v1",
        profile_mode="SHADOW_SEARCH",
        symbol="BTCUSDT",
        primary_timeframe="5m",
        closed_until_ms=BOUNDARY,
        closed_until_utc=stamp,
        status="COMPLETED",
        started_at=stamp,
        finished_at=stamp,
        trigger_source="test",
        daemon_instance_id="test",
        analysis_status="ANALYZED",
        setup_status="SETUP_CANDIDATE",
        strategy_status="ALLOW_RESEARCH_TRADE_PLAN",
        risk_status="RISK_PRE_APPROVED_RESEARCH",
        paper_status="SHADOW_SEARCH",
        updated_at=stamp,
    )
    source = _result()
    row = OnlinePipelineResultRow(
        run_id=run.run_id,
        trade_profile_id="trade-5m-v1",
        profile_mode="SHADOW_SEARCH",
        symbol="BTCUSDT",
        primary_timeframe="5m",
        closed_until_ms=BOUNDARY,
        analysis_payload_json={"status": "ANALYZED"},
        setup_payload_json=source.setup_payload,
        strategy_payload_json=source.strategy_payload,
        risk_payload_json=source.risk_payload,
        paper_payload_json=dict(materialized.paper_payload),
        module_reasons_json={},
        module_warnings_json={},
        safety_counters_json={},
        created_at=stamp,
    )
    universe = SimpleNamespace(
        version_id="trading-universe-v2", symbols=("BTCUSDT",)
    )
    projection = build_projection(
        ((run, row),), universe, NOW_MS,
        trade_profile_id="trade-5m-v1",
    )
    cycle = projection["current_cycle"]
    item = cycle["items"][0]
    assert item["stage_trace"] == {
        "ANALYSIS": "PASS",
        "STRUCTURAL_SETUP": "PASS",
        "STRATEGY_ELIGIBLE": "PASS",
        "RISK_APPROVED": "PASS",
        "PAPER_TRADE_PLAN": "PASS",
        "QUANTITY_APPROVED": "PASS",
        "VALIDITY_APPROVED": "PASS",
        "FINAL_APPROVAL": "PASS",
        "ELIGIBLE": "PASS",
        "SELECTOR_WINNER": "PASS",
    }
    assert item["selected_winner"] is True
    assert item["eligible"] is True
    assert item["execution_eligible"] is False
    assert cycle["winner_symbol"] == "BTCUSDT"

    expired = build_projection(
        ((run, row),), universe, BOUNDARY + 300_001,
        trade_profile_id="trade-5m-v1",
    )
    expired_item = expired["current_cycle"]["items"][0]
    assert expired_item["stage_trace"]["VALIDITY_APPROVED"] == "PASS"
    assert expired_item["stage_trace"]["FINAL_APPROVAL"] == "PASS"
    assert expired_item["stage_trace"]["ELIGIBLE"] == "REJECTED"
    assert expired_item["eligible"] is False
    assert expired_item["selected_winner"] is False
    assert expired_item["source_reason_code"] == "SHADOW_APPROVAL_EXPIRED"
    assert expired["rolling_1h"]["stage_counts"]["VALIDITY_APPROVED"] == 1
    assert expired["rolling_1h"]["stage_counts"]["FINAL_APPROVAL"] == 1


def test_shadow_store_persists_full_funnel_but_never_promotes_execution_flags():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    OnlinePipelineRun.__table__.create(engine)
    OnlinePipelineResultRow.__table__.create(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)

    class Owner:
        def assert_active(self, _session):
            return None

    store = PipelineResultStore(
        sessions,
        clock=lambda: datetime.fromtimestamp(NOW_MS / 1000, tz=timezone.utc),
        owner_guard=Owner(),
        shadow_approval_materializer=ShadowFinalApprovalMaterializer(
            account_summary_source=lambda _session: _account()
        ),
    )
    run_id = store.reserve(
        "BTCUSDT", "5m", BOUNDARY,
        daemon_instance_id="shadow-owner", trigger_source="test",
        trade_profile_id="trade-5m-v1",
    )
    assert run_id is not None
    claim = store.get_claim(run_id)
    assert store.mark_running(
        claim, daemon_instance_id="shadow-owner",
        checked_at=datetime.fromtimestamp(NOW_MS / 1000, tz=timezone.utc),
        payload={},
    )
    source = _result()
    assert store.finish(run_id, source, freshness_status="READY")
    with sessions() as session:
        run = session.scalar(select(OnlinePipelineRun).where(
            OnlinePipelineRun.run_id == run_id
        ))
        row = session.scalar(select(OnlinePipelineResultRow).where(
            OnlinePipelineResultRow.run_id == run_id
        ))
    assert run is not None and row is not None
    assert row.paper_payload_json["shadow_final_approval_candidate"]["status"] == "ELIGIBLE"
    assert "persisted_final_approvals" not in row.paper_payload_json
    assert run.is_trade_signal is False
    assert run.is_executable is False
    assert run.order_approved is False
    assert run.execution_approved is False
    assert run.position_size_approved is False
    assert run.position_opened is False
