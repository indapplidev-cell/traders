from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select

from app.db.paper_models import (
    PaperExecutionCommandRecord,
    PaperFillRecord,
    PaperOrderRecord,
    PaperPlanExecutionOutcomeRecord,
    PaperPositionRecord,
)
from app.engine_orchestrator.orchestrator_models import OnlinePipelineResultRow, OnlinePipelineRun
from app.engine_paper.paper_exploration import (
    PaperExplorationStore,
    exploration_eligible,
    exploration_execution_permitted,
)
from app.engine_paper.scalping_policy_v2 import ADMISSION_PAPER_EXPLORATION, evaluate_expectancy
from app.engine_paper.scalping_statistics import PostgresPaperOutcomeStatisticsSource


SET_ID = "scalping-v2-set-2"
CONFIG_HASH = "exploration-e2e-config"
SETUP = "SCALP_MOMENTUM_CONTINUATION"
POPULATION = "empirical-authority-population-v1:e2e-shared"


def _persist_closed(session, index: int, *, exploration: bool, won: bool) -> None:
    now = datetime(2026, 9, 20, tzinfo=timezone.utc) + timedelta(hours=index)
    boundary_ms = int((now - timedelta(minutes=1)).timestamp() * 1000)
    suffix = f"{index:02d}"
    run_id = f"explore-e2e-run-{suffix}"
    command_id = f"explore-e2e-command-{suffix}"
    entry_order_id = f"explore-e2e-entry-order-{suffix}"
    exit_order_id = f"explore-e2e-exit-order-{suffix}"
    entry_fill_id = f"explore-e2e-entry-fill-{suffix}"
    exit_fill_id = f"explore-e2e-exit-fill-{suffix}"
    position_id = f"explore-e2e-position-{suffix}"
    symbol = "FETUSDT" if exploration else f"T{index:02d}USDT"
    pnl = Decimal("0.5") if exploration else (Decimal("0.2") if won else Decimal("-0.3"))
    context = {
        "parameter_set_id": SET_ID,
        "resolved_config_hash": CONFIG_HASH,
        "admission_mode_at_entry": (
            ADMISSION_PAPER_EXPLORATION if exploration else "EMPIRICAL"
        ),
    }
    if exploration:
        context.update({
            "exploration_id": "paper-exploration:v1:e2e",
            "exploration_policy_version": "limited-paper-exploration-v1",
            "authority_population_id": POPULATION,
            "authority_observation_set_fingerprint": "f" * 64,
            "normal_admission_result": "REJECTED",
            "normal_reject_reason": "SCALPING_EMPIRICAL_EXPECTANCY_REJECTED",
            "exploration_eligible": True,
        })
    session.add(OnlinePipelineRun(
        run_id=run_id, trade_profile_id="trade-5m-v2", profile_mode="PRODUCTION_SEARCH",
        symbol=symbol, primary_timeframe="5m", closed_until_ms=boundary_ms,
        closed_until_utc=now - timedelta(minutes=1), status="COMPLETED",
        started_at=now - timedelta(minutes=2), finished_at=now - timedelta(minutes=1),
        duration_ms=1000, trigger_source="TEST", daemon_instance_id="exploration-e2e",
        future_bars_used=False, is_trade_signal=True, is_executable=True,
        order_approved=True, execution_approved=True, position_opened=True,
        position_size_approved=True,
    ))
    session.flush()
    session.add(OnlinePipelineResultRow(
        run_id=run_id, trade_profile_id="trade-5m-v2", profile_mode="PRODUCTION_SEARCH",
        symbol=symbol, primary_timeframe="5m", closed_until_ms=boundary_ms,
        market_data_payload_json={}, analysis_payload_json={"regime": "UNKNOWN"},
        setup_payload_json={"setup_id": f"setup-{suffix}", "setup_type": SETUP},
        strategy_payload_json={}, risk_payload_json={},
        paper_payload_json={"paper_plan_id": f"plan-{suffix}", "paper_context": context},
        module_reasons_json={}, module_warnings_json={}, safety_counters_json={},
    ))
    session.add(PaperExecutionCommandRecord(
        command_id=command_id, idempotency_key=f"idem-command-{suffix}", mode="PAPER",
        symbol=symbol, side="LONG", order_type="MARKET_SIMULATED",
        requested_quantity=Decimal("1"), requested_notional=Decimal("100"),
        entry_reference_price=Decimal("100"), stop_price=Decimal("99"),
        target_price=Decimal("103"), strategy_decision_id=f"strategy-{suffix}",
        risk_decision_id=f"risk-{suffix}", setup_id=f"setup-{suffix}",
        pipeline_run_id=run_id, analysis_result_id=f"analysis-{suffix}",
        closed_until_ms=boundary_ms, created_at=now, valid_until_ms=boundary_ms + 60_000,
        configuration_fingerprint="config", simulation_policy_id="simulation",
        fee_policy_id="fee", slippage_policy_id="slippage", latency_policy_id="latency",
        final_paper_approval=True, input_health_status="CURRENT", future_bars_used=False,
        processing_status="COMPLETED",
    ))
    for role, order_id, fill_id, price in (
        ("ENTRY", entry_order_id, entry_fill_id, Decimal("100")),
        ("EXIT", exit_order_id, exit_fill_id, Decimal("100.5") if won or exploration else Decimal("99.7")),
    ):
        session.add(PaperOrderRecord(
            order_id=order_id, command_id=command_id,
            idempotency_key=f"idem-{role.lower()}-{suffix}", order_role=role,
            mode="PAPER", symbol=symbol, side="LONG", order_type="MARKET_SIMULATED",
            state="FILLED", requested_quantity=Decimal("1"), filled_quantity=Decimal("1"),
            average_fill_price=price, total_fees=Decimal("0"), created_at=now,
            updated_at=now, version=1, reason_code="PAPER_ORDER_FILLED",
            applied_fill_id=fill_id,
        ))
        session.flush()
        session.add(PaperFillRecord(
            fill_id=fill_id, order_id=order_id, idempotency_key=f"idem-fill-{role.lower()}-{suffix}",
            fill_role=role, symbol=symbol, side="LONG", quantity=Decimal("1"), price=price,
            fee_amount=Decimal("0"), fee_asset="USDT", filled_at=now,
            source_closed_until_ms=boundary_ms, simulation_policy_id="simulation",
            slippage_policy_id="slippage", fee_policy_id="fee", latency_policy_id="latency",
            future_bars_used=False,
        ))
    session.flush()
    session.add(PaperPositionRecord(
        position_id=position_id, mode="PAPER", symbol=symbol, side="LONG", state="CLOSED",
        entry_order_id=entry_order_id, entry_fill_id=entry_fill_id,
        entry_quantity=Decimal("1"), remaining_quantity=Decimal("0"),
        average_entry_price=Decimal("100"), average_exit_price=Decimal("100.5") if won or exploration else Decimal("99.7"),
        entry_fees=Decimal("0"), exit_fees=Decimal("0"), realized_pnl=pnl,
        unrealized_pnl=Decimal("0"), stop_price=Decimal("99"), target_price=Decimal("103"),
        opened_at=now, closed_at=now + timedelta(minutes=5), last_mark_price=Decimal("100"),
        last_mark_closed_until_ms=boundary_ms + 300_000, version=2,
        reason_code="PAPER_POSITION_CLOSED", exit_fill_id=exit_fill_id,
        created_at=now, updated_at=now + timedelta(minutes=5),
    ))
    if exploration:
        session.add(PaperPlanExecutionOutcomeRecord(
            pipeline_run_id=run_id, paper_plan_id=f"plan-{suffix}",
            final_approval_id=f"approval-{suffix}", candidate_id=f"candidate-{suffix}",
            symbol=symbol, trade_profile_id="trade-5m-v2", universe_id="trading-universe-v3",
            boundary_closed_at_ms=boundary_ms, plan_created_at_ms=boundary_ms + 1,
            approval_valid_until_ms=boundary_ms + 60_000, selector_state="SELECTED",
            selector_reason=None, selector_rank=1, selected_winner=True,
            lifecycle_state="COMMAND_CREATED", terminal_reason=None, command_id=command_id,
            control_generation=1, runtime_enabled=True, daemon_enabled=True,
            scheduler_enabled=True, mutation_enabled=True, live_enabled=False,
            attempt_count=1, first_observed_at=now, updated_at=now,
            refinement_details={
                "admission_mode": ADMISSION_PAPER_EXPLORATION,
                "authority_population_id": POPULATION,
                "exploration_selected": True,
            },
        ))


def test_limited_exploration_closed_evidence_is_durable_and_normal_authority_isolated(
    natural_e2e_sessions,
):
    with natural_e2e_sessions() as session, session.begin():
        for index in range(20):
            _persist_closed(session, index, exploration=False, won=index < 7)
        _persist_closed(session, 20, exploration=True, won=True)

    source = PostgresPaperOutcomeStatisticsSource(natural_e2e_sessions)
    hierarchy = source.resolve(
        symbol="FETUSDT", setup_type=SETUP, direction="BULLISH", regime="EXPANSION",
        cost_bucket="MEDIUM", parameter_set_id=SET_ID, resolved_config_hash=CONFIG_HASH,
    )
    selected = hierarchy.parents[2]
    assert selected.samples == 20 and selected.wins == 7
    normal = evaluate_expectancy(
        net_win_bps=120, net_loss_bps=40, bucket=hierarchy.exact,
        parent_buckets=hierarchy.parents, minimum_samples=20,
    )
    assert not normal.admitted and normal.reason == "EMPIRICAL_SUFFICIENT_NEGATIVE_EV"
    assert exploration_eligible(
        normal, candidate_net_rr=4.0, profile_id="trade-5m-v2",
        execution_mode="PAPER", enabled=True,
    )
    assert exploration_execution_permitted(
        admission_mode=ADMISSION_PAPER_EXPLORATION, execution_mode="PAPER",
        live_allowed=False, trade_profile_id="trade-5m-v2", enabled=True,
    )

    recovery = PaperExplorationStore(natural_e2e_sessions).recovery_evidence(POPULATION)
    assert recovery.exploration_closed_count == 1
    assert recovery.exploration_wins == 1 and recovery.exploration_losses == 0
    with natural_e2e_sessions() as session:
        assert session.scalar(select(func.count()).select_from(PaperExecutionCommandRecord).where(
            PaperExecutionCommandRecord.pipeline_run_id == "explore-e2e-run-20"
        )) == 1
        command = session.scalar(select(PaperExecutionCommandRecord).where(
            PaperExecutionCommandRecord.pipeline_run_id == "explore-e2e-run-20"
        ))
        assert command.mode == "PAPER"
