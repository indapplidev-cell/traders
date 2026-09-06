from uuid import uuid4

from sqlalchemy import select

from app.db.paper_models import ScalpingOpportunityRecord
from app.engine_orchestrator.trade_profile import ACTIVE_RUNTIME_PROFILE_IDS
from app.engine_paper.scalping_opportunity_registry import PostgresScalpingOpportunityRegistry
from app.engine_paper.scalping_policy_v2 import evaluate_expectancy
from app.engine_paper.scalping_statistics import PaperOutcome, hierarchy_from_outcomes


def _outcomes(count: int, wins: int):
    return tuple(PaperOutcome(
        symbol="BTCUSDT" if index < 3 else "ETHUSDT",
        setup_type="SCALP_BREAKOUT",
        direction="BULLISH",
        regime="UP",
        cost_bucket="LOW",
        won=index < wins,
    ) for index in range(count))


def test_integrated_probability_ev_and_fail_closed_scenarios(natural_e2e_sessions):
    hierarchy = hierarchy_from_outcomes(
        _outcomes(30, 24), symbol="ADAUSDT", setup_type="SCALP_BREAKOUT",
        direction="BULLISH", regime="UP", cost_bucket="LOW",
    )
    positive = evaluate_expectancy(
        net_win_bps=120, net_loss_bps=50, bucket=hierarchy.exact,
        parent_buckets=hierarchy.parents, minimum_samples=20,
    )
    negative = evaluate_expectancy(
        net_win_bps=20, net_loss_bps=80, bucket=hierarchy.exact,
        parent_buckets=hierarchy.parents, minimum_samples=20,
    )
    absent = evaluate_expectancy(
        net_win_bps=120, net_loss_bps=50, bucket=None,
        parent_buckets=(), minimum_samples=20, static_net_rr=99,
    )
    assert positive.admitted is True
    assert positive.fallback_level == "setup_direction_regime"
    assert positive.p_win_conservative is not None
    assert positive.dynamic_required_net_rr is not None
    assert negative.admitted is False
    assert absent.admitted is False
    assert absent.reason == "INSUFFICIENT_STATISTICAL_AUTHORITY_NO_TRADE"


def test_postgres_causal_duplicate_restart_and_structural_reset(natural_e2e_sessions):
    key = "opportunity:i5:" + uuid4().hex
    first_process = PostgresScalpingOpportunityRegistry(natural_e2e_sessions)
    assert first_process.claim(key).admitted is True
    first_process.bind_plan(key, "paper:plan:" + uuid4().hex)
    command_id = "command:" + uuid4().hex
    position_id = "position:" + uuid4().hex
    first_process.bind_command(key, command_id)
    first_process.bind_position_for_command(command_id, position_id)

    restarted_process = PostgresScalpingOpportunityRegistry(natural_e2e_sessions)
    duplicate = restarted_process.claim(key)
    assert duplicate.admitted is False
    assert duplicate.prior_execution_position_id == position_id

    child = "opportunity:i5:reset:" + uuid4().hex
    restarted_process.structural_reset(
        key, child, reason="STRUCTURE_CHANGED", evidence="new confirmed setup",
    )
    reset_claim = restarted_process.claim(child)
    assert reset_claim.admitted is True
    assert reset_claim.causal_parent_id == key
    with natural_e2e_sessions() as session:
        assert session.scalar(select(ScalpingOpportunityRecord).where(
            ScalpingOpportunityRecord.causal_opportunity_id == key
        )).state == "EXECUTED"


def test_disabled_profiles_have_no_runtime_authority(natural_e2e_sessions):
    assert ACTIVE_RUNTIME_PROFILE_IDS == frozenset({"trade-5m-v2"})
