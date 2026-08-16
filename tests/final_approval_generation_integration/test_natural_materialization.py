from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.paper_models import PaperAccountBaselineRecord
from app.engine_orchestrator.orchestrator_models import OnlinePipelineResultRow, OnlinePipelineRun
from app.engine_orchestrator.pipeline_result import PipelineResult
from app.engine_orchestrator.pipeline_result_store import PipelineResultStore
from app.engine_paper import production_approval as approval_adapter
from app.engine_paper.accounting import PaperAccountSummary
from app.engine_paper.controlled_quantity_validity import (
    DECISION_TIMEFRAME_MS,
    QUANTITY_POLICY_VERSION,
    VALIDITY_POLICY_VERSION,
    derive_approval_valid_until_ms,
)
from app.engine_paper.eligible_approval_ranking import (
    MULTI_SYMBOL_SELECTION_POLICY_VERSION,
    ProductionEligibleApprovalSelector,
)
from app.engine_paper.final_approval_materializer import NaturalFinalApprovalMaterializer
from app.engine_paper import final_approval_materializer as materializer_module
from app.engine_paper.paper_trade_plan import PaperTradePlan
from app.engine_risk.risk_decision import RiskDecision, risk_decision_id
from app.engine_strategy.lineage_identity import BOUNDED_LINEAGE_IDENTITY_ALGORITHM_VERSION
from app.engine_strategy.strategy_decision import (
    StrategyDecision,
    canonical_strategy_decision_identity,
    strategy_decision_id,
)
from app.instrument_constraints.registry import REGISTRY_VERSION


BOUNDARY = 1_800_000_000_000
SOURCE_CLOSE = BOUNDARY - 1
EVALUATION_MS = BOUNDARY + 5_000
EVALUATION = datetime.fromtimestamp(EVALUATION_MS / 1000, tz=timezone.utc)


def account(equity: Decimal = Decimal("100")) -> PaperAccountSummary:
    zero = Decimal("0")
    return PaperAccountSummary(
        "account:production", "session:production", "USDT", equity, equity,
        zero, zero, zero, zero, 0, 0, 0, 0, zero, zero, zero,
        None, None, None, None, None, None,
    )


def strategy() -> StrategyDecision:
    return StrategyDecision(
        decision_id="strategy:natural:1", created_at_ms=BOUNDARY + 300,
        source_setup_id="setup:natural:1", source_analysis_snapshot_id="analysis:natural:1",
        symbol="BTCUSDT", timeframe="15m", closed_until_ms=BOUNDARY,
        decision_status="ALLOW_RESEARCH_TRADE_PLAN",
        strategy_type="BREAKOUT_CONTINUATION_RESEARCH", direction_hint="BULLISH",
        setup_status="SETUP_CANDIDATE", setup_type="BREAKOUT_CONTINUATION",
        setup_quality="GOOD", setup_quality_score=90.0, strategy_score=82.0,
        strategy_quality="ACCEPTABLE", required_next_layer="engine_risk",
        requires_risk_review=True,
    )


def risk() -> RiskDecision:
    return RiskDecision(
        risk_decision_id="risk:natural:1", created_at_ms=BOUNDARY + 400,
        source_strategy_decision_id="strategy:natural:1",
        source_setup_id="setup:natural:1", source_analysis_snapshot_id="analysis:natural:1",
        symbol="BTCUSDT", timeframe="15m", closed_until_ms=BOUNDARY,
        risk_status="RISK_PRE_APPROVED_RESEARCH", risk_level="LOW", risk_score=90.0,
        risk_policy_version="risk-policy-v1",
        source_decision_status="ALLOW_RESEARCH_TRADE_PLAN",
        source_strategy_type="BREAKOUT_CONTINUATION_RESEARCH",
        source_strategy_quality="ACCEPTABLE", source_strategy_score=82.0,
        direction_hint="BULLISH", risk_pre_approved=True,
        requires_execution_review=True,
    )


def plan(**changes) -> PaperTradePlan:
    values = dict(
        paper_plan_id="paper:natural:1", created_at_ms=BOUNDARY + 500,
        source_risk_decision_id="risk:natural:1",
        source_strategy_decision_id="strategy:natural:1",
        source_setup_id="setup:natural:1", source_analysis_snapshot_id="analysis:natural:1",
        symbol="BTCUSDT", timeframe="15m", closed_until_ms=BOUNDARY,
        paper_status="PAPER_PLAN_READY", paper_plan_type="BREAKOUT_CONTINUATION_PAPER_PLAN",
        paper_direction="BULLISH", source_risk_status="RISK_PRE_APPROVED_RESEARCH",
        source_risk_level="LOW", source_risk_score=90.0,
        source_strategy_type="BREAKOUT_CONTINUATION_RESEARCH",
        source_strategy_quality="ACCEPTABLE", source_direction_hint="BULLISH",
        hypothetical_entry_reference=Decimal("100"),
        hypothetical_invalidation_level=Decimal("99"),
        hypothetical_stop_level=Decimal("99"), hypothetical_target_level=Decimal("102"),
        planned_rr=Decimal("2"), entry_reference_source="CAUSAL",
        invalidation_source="CAUSAL", stop_source="CAUSAL", target_source="CAUSAL",
        plan_quality="ACCEPTABLE", plan_score=90.0,
        paper_context={"plan_policy_version": "paper-plan-policy-v1"},
    )
    values.update(changes)
    return PaperTradePlan(**values)


def natural_result(**changes) -> PipelineResult:
    value = PipelineResult(
        symbol="BTCUSDT", primary_timeframe="15m", closed_until_ms=BOUNDARY,
        status="COMPLETED", final_result="PAPER_PLAN_READY",
        market_data_payload={
            "15m": {
                "last_close_time_ms": SOURCE_CLOSE,
                "closed_until_ms": BOUNDARY,
            }
        },
        analysis_payload={
            "snapshot_id": "analysis:natural:1",
            "source_market_data_snapshot_id": "market:natural:1",
            "symbol": "BTCUSDT", "timeframe": "15m", "closed_until_ms": BOUNDARY,
            "created_at_ms": BOUNDARY + 100, "future_bars_used": False,
        },
        setup_payload={
            "setup_id": "setup:natural:1", "source_analysis_snapshot_id": "analysis:natural:1",
            "symbol": "BTCUSDT", "timeframe": "15m", "closed_until_ms": BOUNDARY,
            "created_at_ms": BOUNDARY + 200, "status": "SETUP_CANDIDATE",
        },
        strategy_payload=strategy().to_dict(), risk_payload=risk().to_dict(),
        paper_payload=plan().to_dict(), analysis_status="ANALYZED",
        setup_status="SETUP_CANDIDATE", strategy_status="ALLOW_RESEARCH_TRADE_PLAN",
        risk_status="RISK_PRE_APPROVED_RESEARCH", paper_status="PAPER_PLAN_READY",
    )
    for name, replacement in changes.items():
        setattr(value, name, replacement)
    return value


def materializer(equity: Decimal = Decimal("100")) -> NaturalFinalApprovalMaterializer:
    return NaturalFinalApprovalMaterializer(
        account_summary_source=lambda _: account(equity),
        configuration_fingerprint_source=lambda _session, _result: "paper:approval-config:test:v1",
    )


def materialize(result: PipelineResult | None = None, *, equity: Decimal = Decimal("100")):
    return materializer(equity).materialize(
        SimpleNamespace(), run_id="orchestrator:natural:1",
        result=result or natural_result(), evaluation_time=EVALUATION,
    )


def long_production_shape_result() -> PipelineResult:
    value = deepcopy(natural_result())
    symbol = "AVAXUSDT"
    setup_id = (
        "setup:AVAXUSDT:15m:1800000000000:BREAKOUT_CONTINUATION:"
        "SETUP_CANDIDATE:09b38de71b8e518d"
    )
    canonical = canonical_strategy_decision_identity(
        symbol, "15m", BOUNDARY, setup_id
    )
    decision_id = strategy_decision_id(symbol, "15m", BOUNDARY, setup_id)
    risk_id = risk_decision_id(symbol, "15m", BOUNDARY, decision_id)
    strategy_value = replace(
        strategy(), decision_id=decision_id, source_setup_id=setup_id,
        symbol=symbol,
        context={
            "canonical_strategy_decision_identity": canonical,
            "bounded_identity_algorithm_version":
                BOUNDED_LINEAGE_IDENTITY_ALGORITHM_VERSION,
        },
    )
    risk_value = replace(
        risk(), risk_decision_id=risk_id,
        source_strategy_decision_id=decision_id,
        source_setup_id=setup_id, symbol=symbol,
    )
    plan_value = replace(
        plan(), paper_plan_id="paper:production-shape:1",
        source_risk_decision_id=risk_id,
        source_strategy_decision_id=decision_id,
        source_setup_id=setup_id, symbol=symbol,
        hypothetical_entry_reference=Decimal("6.411"),
        hypothetical_invalidation_level=Decimal("6.361571428571429"),
        hypothetical_stop_level=Decimal("6.361571428571429"),
        hypothetical_target_level=Decimal("6.51"),
    )
    value.symbol = symbol
    value.analysis_payload["symbol"] = symbol
    value.setup_payload.update({"setup_id": setup_id, "symbol": symbol})
    value.strategy_payload = strategy_value.to_dict()
    value.risk_payload = risk_value.to_dict()
    value.paper_payload = plan_value.to_dict()
    return value


def test_long_natural_identity_finalizes_and_reaches_quantity_authority(monkeypatch):
    calls = []
    authority = materializer_module.issue_controlled_paper_quantity_approval

    def observed(*args, **kwargs):
        calls.append((args, kwargs))
        return authority(*args, **kwargs)

    monkeypatch.setattr(
        materializer_module, "issue_controlled_paper_quantity_approval", observed
    )
    value = materialize(long_production_shape_result())
    assert value.final_approval_created
    assert len(calls) == 1
    generation = value.paper_payload["final_approval_generation"]
    assert generation["quantity_authority_status"] == "PASS"
    approvals = value.paper_payload["persisted_final_approvals"]
    assert len(approvals["paper_strategy_approval"]["causation_id"]) == 76
    assert value.paper_payload["controlled_quantity_approval"]["approved_quantity"]
    assert value.paper_payload["paper_context"]["plan_policy_version"] == "paper-plan-policy-v1"


def test_long_natural_identity_actual_quantity_reject_is_not_bypassed(monkeypatch):
    calls = []
    authority = materializer_module.issue_controlled_paper_quantity_approval

    def observed(*args, **kwargs):
        calls.append((args, kwargs))
        return authority(*args, **kwargs)

    monkeypatch.setattr(
        materializer_module, "issue_controlled_paper_quantity_approval", observed
    )
    value = materialize(long_production_shape_result(), equity=Decimal("0.01"))
    assert not value.final_approval_created
    assert len(calls) == 1
    generation = value.paper_payload["final_approval_generation"]
    assert generation["stage"] == "QUANTITY_APPROVED"
    assert generation["quantity_authority_status"] == "REJECTED"
    assert generation["reason_code"] == value.outcome
    assert "persisted_final_approvals" not in value.paper_payload


def test_long_natural_identity_full_typed_lineage_is_preserved():
    source = long_production_shape_result()
    value = materialize(source)
    generation = value.paper_payload["final_approval_generation"]
    strategy_payload = source.strategy_payload
    assert generation["source_run_id"] == "orchestrator:natural:1"
    assert generation["candidate_id"] == source.setup_payload["setup_id"]
    assert strategy_payload["source_setup_id"] == source.setup_payload["setup_id"]
    assert strategy_payload["context"]["canonical_strategy_decision_identity"]
    assert source.risk_payload["source_strategy_decision_id"] == strategy_payload["decision_id"]
    assert source.paper_payload["source_risk_decision_id"] == source.risk_payload["risk_decision_id"]
    assert source.paper_payload["symbol"] == source.symbol
    assert source.paper_payload["paper_direction"] == "BULLISH"
    assert source.closed_until_ms == BOUNDARY


def test_valid_triplet_persists_final_approval_test():
    value = materialize()
    assert value.final_approval_created
    assert value.outcome == "FINAL_APPROVAL_CREATED"
    assert set(value.paper_payload["persisted_final_approvals"]) == {
        "paper_strategy_approval", "paper_quantity_approval", "paper_risk_approval"
    }


def test_final_approval_persisted_in_expected_json_path_and_pipeline_finish_retry_no_duplicate_test():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    with sessions() as session:
        session.add(OnlinePipelineRun(
            run_id="orchestrator:natural:1", symbol="BTCUSDT", primary_timeframe="15m",
            closed_until_ms=BOUNDARY,
            closed_until_utc=datetime.fromtimestamp(BOUNDARY / 1000, tz=timezone.utc),
            status="RUNNING", started_at=EVALUATION, trigger_source="TEST",
            daemon_instance_id="test",
        ))
        session.add(PaperAccountBaselineRecord(
            baseline_id="baseline:test", account_id="account:production",
            accounting_session_id="session:production", currency="USDT",
            initial_balance=Decimal("100"), initialized_at=EVALUATION,
            semantic_version="PAPER_ACCOUNTING/1.0",
        ))
        session.commit()
    store = PipelineResultStore(sessions, clock=lambda: EVALUATION)
    assert store.finish("orchestrator:natural:1", natural_result(), freshness_status="READY")
    assert not store.finish("orchestrator:natural:1", natural_result(), freshness_status="READY")
    with sessions() as session:
        rows = tuple(session.scalars(select(OnlinePipelineResultRow)))
        run = session.scalar(select(OnlinePipelineRun))
    assert len(rows) == 1
    assert rows[0].paper_payload_json["persisted_final_approvals"]
    assert run.is_trade_signal and run.is_executable and run.order_approved
    assert run.execution_approved and run.position_size_approved


def _persisted_decision(payload):
    result = natural_result()
    return approval_adapter._PersistedDecision(
        run_pk=1, result_pk=1, run_id="orchestrator:natural:1", symbol="BTCUSDT",
        primary_timeframe="15m", closed_until_ms=BOUNDARY, status="COMPLETED",
        finished_at=EVALUATION, freshness_deadline_at=None, future_bars_used=False,
        is_trade_signal=True, is_executable=True, order_approved=True,
        execution_approved=True, position_opened=False, position_size_approved=True,
        analysis_status=result.analysis_status, setup_status=result.setup_status,
        strategy_status=result.strategy_status, risk_status=result.risk_status,
        paper_status=result.paper_status, analysis=result.analysis_payload,
        setup=result.setup_payload, strategy=result.strategy_payload,
        risk=result.risk_payload, paper=payload,
    )


def _classify(payload):
    adapter = object.__new__(approval_adapter.PaperProductionApprovalSourceAdapter)
    return adapter._classify(_persisted_decision(payload), EVALUATION_MS)


def test_final_approval_adapter_reads_new_natural_approval_and_selector_accepts_single_valid_test():
    value = materialize()
    classified = _classify(value.paper_payload)
    assert classified.outcome is approval_adapter.PaperProductionApprovalOutcome.ELIGIBLE_APPROVAL
    selected = ProductionEligibleApprovalSelector().select(
        (classified.candidate,), policy_version=MULTI_SYMBOL_SELECTION_POLICY_VERSION
    )
    assert selected.winner == classified.candidate


def test_final_approval_uses_persisted_quantity_authority_and_generator_does_not_recompute_quantity_test():
    value = materialize()
    payload = value.paper_payload
    typed = payload["controlled_quantity_approval"]
    triplet_quantity = payload["persisted_final_approvals"]["paper_quantity_approval"]
    final_risk = payload["persisted_final_approvals"]["paper_risk_approval"]
    assert typed == triplet_quantity
    assert final_risk["approved_quantity"] == typed["approved_quantity"]
    assert typed["approval_source"] == "CONTROLLED_PAPER_AUTHORITY"
    assert payload["quantity_sizing_audit"]["quantity_policy_version"] == QUANTITY_POLICY_VERSION


def test_final_approval_next_15m_validity_and_earliest_deadline_test():
    value = materialize()
    payload = value.paper_payload
    assert payload["approval_validity"]["policy_version"] == VALIDITY_POLICY_VERSION
    assert payload["approval_validity"]["source_candle_close_time_ms"] == SOURCE_CLOSE
    expected = SOURCE_CLOSE + DECISION_TIMEFRAME_MS
    deadlines = tuple(
        int(payload["persisted_final_approvals"][key]["valid_until_ms"])
        for key in ("paper_strategy_approval", "paper_quantity_approval", "paper_risk_approval")
    )
    assert min(deadlines) == expected
    assert derive_approval_valid_until_ms(SOURCE_CLOSE, stricter_valid_until_ms=(expected - 1,)) == expected - 1


def test_expired_component_no_final_approval_test():
    expired = materializer().materialize(
        SimpleNamespace(), run_id="orchestrator:natural:1", result=natural_result(),
        evaluation_time=datetime.fromtimestamp((SOURCE_CLOSE + DECISION_TIMEFRAME_MS + 1) / 1000, tz=timezone.utc),
    )
    assert not expired.final_approval_created
    assert "persisted_final_approvals" not in expired.paper_payload


def _status_result(layer: str, status: str) -> PipelineResult:
    value = natural_result()
    setattr(value, f"{layer}_status", status)
    return value


def test_strategy_rejected_no_final_approval_test():
    assert not materialize(_status_result("strategy", "REJECT")).final_approval_created


def test_strategy_deferred_no_final_approval_test():
    assert not materialize(_status_result("strategy", "WAIT")).final_approval_created


def test_risk_rejected_no_final_approval_test():
    assert not materialize(_status_result("risk", "REJECT")).final_approval_created


def test_risk_deferred_no_final_approval_test():
    assert not materialize(_status_result("risk", "WAIT")).final_approval_created


def test_quantity_rejected_and_zero_quantity_no_final_approval_test():
    for equity in (Decimal("0"), Decimal("0.01")):
        assert not materialize(equity=equity).final_approval_created


def test_min_notional_failure_no_final_approval_test():
    assert not materialize(equity=Decimal("0.01")).final_approval_created


def test_invalid_risk_distance_no_final_approval_test():
    value = natural_result(paper_payload=plan(hypothetical_stop_level=Decimal("100")).to_dict())
    assert not materialize(value).final_approval_created


def _mixed(path: str, key: str, value) -> PipelineResult:
    result = deepcopy(natural_result())
    getattr(result, path)[key] = value
    return result


def test_cross_run_component_mix_denied_test():
    value = materialize()
    altered = deepcopy(value.paper_payload)
    altered["persisted_final_approvals"]["paper_strategy_approval"]["pipeline_run_id"] = "other:run"
    classified = _classify(altered)
    assert classified.outcome is approval_adapter.PaperProductionApprovalOutcome.CAUSALITY_MISMATCH


def test_cross_symbol_component_mix_denied_test():
    assert not materialize(_mixed("risk_payload", "symbol", "ETHUSDT")).final_approval_created


def test_cross_candidate_component_mix_denied_test():
    assert not materialize(_mixed("setup_payload", "setup_id", "setup:other")).final_approval_created


def test_stale_source_candle_component_mix_denied_test():
    result = deepcopy(natural_result())
    result.market_data_payload["15m"]["last_close_time_ms"] -= DECISION_TIMEFRAME_MS
    assert not materialize(result).final_approval_created


def test_final_approval_replay_idempotency_and_concurrency_test():
    def issue(_):
        value = materialize()
        return (
            value.idempotency_key,
            value.paper_payload["final_approval_generation"]["final_approval_id"],
        )
    with ThreadPoolExecutor(max_workers=8) as pool:
        identities = tuple(pool.map(issue, range(32)))
    assert len(set(identities)) == 1


def test_multi_symbol_selector_ranking_unchanged_test():
    ranking = lambda risk_score, run: SimpleNamespace(
        risk_score=Decimal(risk_score), planned_risk_reward=Decimal("2"),
        strategy_score=Decimal("80"), closed_until_ms=BOUNDARY,
        source_run_id=run, final_approval_id=f"final:{run}",
    )
    low = SimpleNamespace(candidate_id="candidate:low", symbol="BTCUSDT", ranking=ranking("80", "run:1"))
    high = SimpleNamespace(candidate_id="candidate:high", symbol="ETHUSDT", ranking=ranking("90", "run:2"))
    selected = ProductionEligibleApprovalSelector().select(
        (low, high), policy_version=MULTI_SYMBOL_SELECTION_POLICY_VERSION
    )
    assert selected.winner is high
    assert selected.diagnostics.tie_broken_by == "risk_score_desc"


def test_non_eligible_pipeline_result_can_finish_without_final_approval_test():
    value = materialize(_status_result("paper", "NO_PLAN"))
    assert not value.final_approval_created
    assert value.outcome == "NOT_ELIGIBLE"
    assert "persisted_final_approvals" not in value.paper_payload


def test_policy_and_registry_versions_are_locked_test():
    value = materialize()
    metadata = value.paper_payload["final_approval_generation"]
    assert metadata["quantity_policy_version"] == QUANTITY_POLICY_VERSION
    assert metadata["validity_policy_version"] == VALIDITY_POLICY_VERSION
    assert metadata["instrument_registry_version"] == REGISTRY_VERSION
    default_fingerprint = NaturalFinalApprovalMaterializer(
        account_summary_source=lambda _: account()
    ).materialize(
        SimpleNamespace(), run_id="orchestrator:natural:1",
        result=natural_result(), evaluation_time=EVALUATION,
    ).paper_payload["persisted_final_approvals"]["paper_strategy_approval"]["configuration_fingerprint"]
    assert default_fingerprint.startswith("paper:approval-config:v1:")
