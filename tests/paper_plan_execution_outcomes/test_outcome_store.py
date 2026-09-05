from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.paper_models import PaperPlanExecutionOutcomeRecord
from app.engine_orchestrator.orchestrator_models import OnlinePipelineResultRow
from app.engine_paper.eligible_approval_ranking import ProductionEligibleApprovalSelector
from app.engine_paper.plan_execution_outcome import PaperPlanExecutionOutcomeStore


BOUNDARY = 1_900_000_000_000
VALID_UNTIL = BOUNDARY + 299_999
NOW = datetime.fromtimestamp((BOUNDARY + 30_000) / 1000, timezone.utc)


def candidate(run_id: str, risk: str = "90"):
    final = f"approval:{run_id}"
    return SimpleNamespace(
        candidate_id=f"candidate:{run_id}",
        symbol="SOLUSDT",
        trade_profile_id="trade-5m-v1",
        valid_until_ms=VALID_UNTIL,
        watermark=SimpleNamespace(closed_until_ms=BOUNDARY),
        lineage=SimpleNamespace(source_run_id=run_id, final_approval_id=final),
        ranking=SimpleNamespace(
            risk_score=Decimal(risk), planned_risk_reward=Decimal("2"),
            strategy_score=Decimal("80"), closed_until_ms=BOUNDARY,
            source_run_id=run_id, final_approval_id=final,
        ),
    )


def sessions():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session, session.begin():
        for run_id in ("run:one", "run:two"):
            session.add(OnlinePipelineResultRow(
                run_id=run_id, symbol="SOLUSDT", primary_timeframe="5m",
                closed_until_ms=BOUNDARY,
                market_data_payload_json={}, analysis_payload_json={},
                setup_payload_json={}, strategy_payload_json={}, risk_payload_json={},
                paper_payload_json={
                    "paper_plan_id": f"paper:{run_id}",
                    "created_at_ms": BOUNDARY + 1,
                },
                module_reasons_json={}, module_warnings_json={}, safety_counters_json={},
                created_at=NOW, trade_profile_id="trade-5m-v1",
                profile_mode="PRODUCTION_SEARCH",
            ))
    return engine, factory


def test_selection_policy_block_and_expiry_are_durable_and_idempotent():
    engine, factory = sessions()
    store = PaperPlanExecutionOutcomeStore(factory)
    values = (candidate("run:one", "90"), candidate("run:two", "80"))
    selection = ProductionEligibleApprovalSelector().select(
        values, policy_version="eligible-approval-ranking-v1"
    )
    store.observe_selection(
        values, selection, universe_id="trading-universe-v2",
        control_generation=6, observed_at=NOW,
    )
    store.record_attempt(
        "run:one", blocker_codes=("WAL_NOT_READY", "PITR_NOT_READY"),
        observed_at=NOW,
    )
    assert store.expire_due(VALID_UNTIL + 1, observed_at=NOW) == 2
    assert store.expire_due(VALID_UNTIL + 1, observed_at=NOW) == 0
    with factory() as session:
        first = session.get(PaperPlanExecutionOutcomeRecord, "run:one")
        second = session.get(PaperPlanExecutionOutcomeRecord, "run:two")
        assert first.selector_state == "SELECTED" and first.selector_rank == 1
        assert first.selector_reason == "WAL_NOT_READY,PITR_NOT_READY"
        assert first.attempt_count == 1
        assert first.lifecycle_state == "EXPIRED_BEFORE_EXECUTION"
        assert first.terminal_reason == "EXPIRED_BEFORE_EXECUTION"
        assert second.selector_state == "NOT_SELECTED" and second.selector_rank == 2
        assert second.selector_reason == "LOWER_SELECTOR_RANK"
        assert second.lifecycle_state == "EXPIRED_BEFORE_EXECUTION"
    engine.dispose()


def test_successful_retry_records_one_command_without_duplicate_plan_row():
    engine, factory = sessions()
    store = PaperPlanExecutionOutcomeStore(factory)
    value = candidate("run:one")
    selection = ProductionEligibleApprovalSelector().select(
        (value,), policy_version="eligible-approval-ranking-v1"
    )
    store.observe_selection(
        (value,), selection, universe_id="trading-universe-v2",
        control_generation=6, observed_at=NOW,
    )
    store.observe_selection(
        (value,), selection, universe_id="trading-universe-v2",
        control_generation=6, observed_at=NOW,
    )
    store.record_attempt("run:one", command_id="paper:command:one", observed_at=NOW)
    with factory() as session:
        rows = session.query(PaperPlanExecutionOutcomeRecord).all()
        assert len(rows) == 1
        assert rows[0].command_id == "paper:command:one"
        assert rows[0].lifecycle_state == "COMMAND_CREATED"
        assert rows[0].attempt_count == 1
        assert rows[0].refinement_details["selected_to_command_latency_ms"] == 0.0
    engine.dispose()


def test_refinement_is_exact_identity_restart_safe_and_terminal_once():
    engine, factory = sessions()
    store = PaperPlanExecutionOutcomeStore(factory)
    value = candidate("run:one")
    object.__setattr__(value, "trade_profile_id", "trade-5m-v2")
    selection = ProductionEligibleApprovalSelector().select(
        (value,), policy_version="eligible-approval-ranking-v1"
    )
    store.observe_selection(
        (value,), selection, universe_id="trading-universe-v2",
        control_generation=12, observed_at=NOW,
    )
    ready = SimpleNamespace(
        refinement_identity="entry-refinement:exact",
        mode="AUTHORITATIVE", state="READY_TO_ENTER",
        reason="ENTRY_REFINEMENT_CONFIRMED",
        refinement_started_at=NOW, refinement_finished_at=NOW,
        refinement_valid_from_ms=BOUNDARY + 30_000,
        refinement_valid_until_ms=VALID_UNTIL,
        details=lambda: {
            "one_min_candle_open_ms": BOUNDARY,
            "one_min_candle_close_ms": BOUNDARY + 60_000,
            "planned_entry": "100", "refined_entry_reference": "100.01",
        },
    )
    assert store.record_refinement("run:one", ready) == (
        "READY_TO_ENTER", "ENTRY_REFINEMENT_CONFIRMED", "AUTHORITATIVE"
    )
    # A restarted store returns the first terminal result rather than replacing
    # it with a later observation or creating a second identity.
    restarted = PaperPlanExecutionOutcomeStore(factory)
    later = SimpleNamespace(**{
        **ready.__dict__, "state": "REJECTED_1M",
        "reason": "ENTRY_REFINEMENT_PRICE_DRIFT_TOO_LARGE",
    })
    assert restarted.record_refinement("run:one", later) == (
        "READY_TO_ENTER", "ENTRY_REFINEMENT_CONFIRMED", "AUTHORITATIVE"
    )
    with factory() as session:
        row = session.get(PaperPlanExecutionOutcomeRecord, "run:one")
        assert row.refinement_identity == "entry-refinement:exact"
        assert row.refinement_state == "READY_TO_ENTER"
        assert row.refinement_valid_until_ms <= row.approval_valid_until_ms
    engine.dispose()


def test_pending_shadow_refinement_expires_terminally_without_replaying_command():
    engine, factory = sessions()
    store = PaperPlanExecutionOutcomeStore(factory)
    value = candidate("run:one")
    selection = ProductionEligibleApprovalSelector().select(
        (value,), policy_version="eligible-approval-ranking-v1"
    )
    store.observe_selection(
        (value,), selection, universe_id="trading-universe-v2",
        control_generation=12, observed_at=NOW,
    )
    waiting = SimpleNamespace(
        refinement_identity="entry-refinement:shadow",
        mode="SHADOW", state="WAITING_FOR_1M",
        reason="ENTRY_REFINEMENT_WAITING_1M_CLOSE",
        refinement_started_at=NOW, refinement_finished_at=None,
        refinement_valid_from_ms=BOUNDARY + 30_000,
        refinement_valid_until_ms=VALID_UNTIL,
        details=lambda: {"state": "WAITING_FOR_1M"},
    )
    store.record_refinement("run:one", waiting)
    store.record_attempt("run:one", command_id="paper:command:shadow", observed_at=NOW)
    assert store.pending_shadow_refinement_run_ids() == frozenset({"run:one"})
    assert store.expire_shadow_refinements(VALID_UNTIL + 1, observed_at=NOW) == 1
    assert store.pending_shadow_refinement_run_ids() == frozenset()
    with factory() as session:
        row = session.get(PaperPlanExecutionOutcomeRecord, "run:one")
        assert row.command_id == "paper:command:shadow"
        assert row.refinement_state == "EXPIRED_1M"
        assert row.refinement_reason == "ENTRY_REFINEMENT_WINDOW_EXPIRED"
    engine.dispose()
