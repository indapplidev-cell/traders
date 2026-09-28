from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

from app.engine_paper.eligible_approval_ranking import ProductionEligibleApprovalSelector
from app.engine_paper.paper_exploration import (
    ExplorationBudgetDecision,
    PaperExplorationStore,
    exploration_eligible,
    exploration_execution_permitted,
)
from app.engine_paper.scalping_policy_v2 import (
    ADMISSION_PAPER_EXPLORATION,
    EMPIRICAL_AUTHORITY_ESTABLISHED,
    ExpectancyDecision,
)
from app.engine_paper.scalping_statistics import PaperOutcome, hierarchy_from_outcomes
from app.operator_control.production_executor import ProductionPaperFirstCanaryExecutor


POPULATION = "empirical-authority-population-v1:shared"
FINGERPRINT = "a" * 64


def decision(**changes):
    values = dict(
        admitted=False,
        expected_value_bps=-18.0,
        probability=0.26,
        reason="EMPIRICAL_SUFFICIENT_NEGATIVE_EV",
        dynamic_required_net_rr=2.75,
        candidate_net_rr=2.94,
        empirical_authority_status=EMPIRICAL_AUTHORITY_ESTABLISHED,
        empirical_ev_net_bps=-18.0,
        authority_population_id=POPULATION,
        authority_observation_set_fingerprint=FINGERPRINT,
    )
    values.update(changes)
    return ExpectancyDecision(**values)


def test_sole_blocker_eligibility_and_rr_floor():
    assert exploration_eligible(
        decision(), candidate_net_rr=2.94, profile_id="trade-5m-v2",
        execution_mode="PAPER", enabled=True,
    )
    assert not exploration_eligible(
        decision(), candidate_net_rr=2.74, profile_id="trade-5m-v2",
        execution_mode="PAPER", enabled=True,
    )


def test_other_reject_profile_flag_and_live_cannot_bypass():
    assert not exploration_eligible(
        decision(reason="ECONOMIC_GEOMETRY_NOT_FEASIBLE"), candidate_net_rr=4.0,
        profile_id="trade-5m-v2", execution_mode="PAPER", enabled=True,
    )
    assert not exploration_eligible(
        decision(), candidate_net_rr=4.0, profile_id="trade-15m-v1",
        execution_mode="PAPER", enabled=True,
    )
    assert not exploration_eligible(
        decision(), candidate_net_rr=4.0, profile_id="trade-5m-v2",
        execution_mode="PAPER", enabled=False,
    )
    assert not exploration_execution_permitted(
        admission_mode=ADMISSION_PAPER_EXPLORATION, execution_mode="LIVE",
        live_allowed=True, trade_profile_id="trade-5m-v2", enabled=True,
    )


def _outcome(population: str, *, updated: datetime):
    return SimpleNamespace(
        refinement_details={
            "admission_mode": ADMISSION_PAPER_EXPLORATION,
            "authority_population_id": population,
        },
        updated_at=updated,
    )


class RowsStore(PaperExplorationStore):
    def __init__(self, rows):
        self.rows = tuple(rows)

    def _rows(self):
        return self.rows


def _position(*, state="CLOSED", opened, closed=None, pnl="1"):
    return SimpleNamespace(
        state=state, opened_at=opened, closed_at=closed,
        entry_quantity=Decimal("1"), average_entry_price=Decimal("100"),
        realized_pnl=Decimal(pnl),
    )


def test_one_open_probe_and_cross_symbol_authority_budget():
    now = datetime(2026, 9, 28, 12, tzinfo=timezone.utc)
    store = RowsStore(((
        _outcome(POPULATION, updated=now - timedelta(minutes=5)),
        _position(state="OPEN", opened=now - timedelta(minutes=5)),
    ),))
    btc = store.evaluate_budget(POPULATION, now=now)
    fet = store.evaluate_budget(POPULATION, now=now)
    assert not btc.permitted and btc.block_reason == "EXPLORATION_POSITION_ALREADY_OPEN"
    assert fet == btc


def test_cooldown_and_rolling_24h_budgets_with_deterministic_clock():
    now = datetime(2026, 9, 28, 12, tzinfo=timezone.utc)
    one = (
        _outcome(POPULATION, updated=now - timedelta(hours=2)),
        _position(
            opened=now - timedelta(hours=2), closed=now - timedelta(hours=1), pnl="1"
        ),
    )
    store = RowsStore((one,))
    assert store.evaluate_budget(POPULATION, now=now).block_reason == (
        "EXPLORATION_AUTHORITY_COOLDOWN_ACTIVE"
    )
    assert store.evaluate_budget(POPULATION, now=now + timedelta(hours=6)).permitted

    two = (
        _outcome(POPULATION, updated=now - timedelta(hours=8)),
        _position(
            opened=now - timedelta(hours=8), closed=now - timedelta(hours=7), pnl="-1"
        ),
    )
    exhausted = RowsStore((one, two)).evaluate_budget(POPULATION, now=now)
    # Cooldown is evaluated first; after it expires, the rolling cap remains.
    assert RowsStore((one, two)).evaluate_budget(
        POPULATION, now=now + timedelta(hours=6)
    ).block_reason == "EXPLORATION_AUTHORITY_24H_BUDGET_EXHAUSTED"
    assert exhausted.block_reason == "EXPLORATION_AUTHORITY_COOLDOWN_ACTIVE"


def test_global_rolling_24h_budget_is_shared_across_authorities():
    now = datetime(2026, 9, 28, 12, tzinfo=timezone.utc)
    rows = tuple(
        (
            _outcome(f"population:{index}", updated=now - timedelta(hours=9 - index)),
            _position(
                opened=now - timedelta(hours=9 - index),
                closed=now - timedelta(hours=8 - index),
                pnl="1",
            ),
        )
        for index in range(2)
    )
    decision = RowsStore(rows).evaluate_budget("population:new", now=now)
    assert decision.block_reason == "EXPLORATION_GLOBAL_24H_BUDGET_EXHAUSTED"
    assert decision.global_24h == 2 and decision.authority_24h == 0


def test_restart_replay_preserves_budget_and_recovery_evidence():
    now = datetime(2026, 9, 28, 12, tzinfo=timezone.utc)
    rows = ((
        _outcome(POPULATION, updated=now - timedelta(hours=8)),
        _position(
            opened=now - timedelta(hours=8), closed=now - timedelta(hours=7), pnl="2"
        ),
    ),)
    before = RowsStore(rows).evaluate_budget(POPULATION, now=now)
    after = RowsStore(rows).evaluate_budget(POPULATION, now=now)
    assert before == after
    evidence = RowsStore(rows).recovery_evidence(POPULATION)
    assert evidence.exploration_closed_count == 1
    assert evidence.exploration_wins == 1 and evidence.exploration_losses == 0
    assert evidence.exploration_ev_net_bps == 200.0


def test_setup_fallback_population_identity_is_shared_cross_symbol():
    outcomes = tuple(
        PaperOutcome(
            symbol=f"S{index}", setup_type="SCALP_MOMENTUM_CONTINUATION",
            direction="BEARISH" if index % 2 else "BULLISH", regime="UNKNOWN",
            cost_bucket="MEDIUM", won=index < 7,
            parameter_set_id="set", resolved_config_hash="hash",
            net_return_bps=10.0 if index < 7 else -10.0,
            position_id=f"position:{index}",
        )
        for index in range(20)
    )
    btc = hierarchy_from_outcomes(
        outcomes, symbol="BTCUSDT", setup_type="SCALP_MOMENTUM_CONTINUATION",
        direction="BEARISH", regime="EXPANSION", cost_bucket="MEDIUM",
        parameter_set_id="set", resolved_config_hash="hash",
    ).parents[2]
    fet = hierarchy_from_outcomes(
        outcomes, symbol="FETUSDT", setup_type="SCALP_MOMENTUM_CONTINUATION",
        direction="BEARISH", regime="EXPANSION", cost_bucket="MEDIUM",
        parameter_set_id="set", resolved_config_hash="hash",
    ).parents[2]
    assert btc.level == fet.level == "setup"
    assert btc.bucket_key != fet.bucket_key
    assert btc.authority_population_id == fet.authority_population_id
    assert btc.observation_set_fingerprint == fet.observation_set_fingerprint


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    symbol: str
    ranking: object
    admission_mode: str = "NORMAL_EMPIRICAL_ADMISSION"
    exploration_provenance: dict[str, object] | None = None


class Budget:
    def __init__(self, permitted=True, reason=None):
        self.permitted = permitted
        self.reason = reason
        self.seen = []

    def evaluate_budget(self, population_id, *, now):
        self.seen.append(population_id)
        return ExplorationBudgetDecision(
            self.permitted, self.reason, 0, 0, 0, 0, None, None
        )


class Outcomes:
    def __init__(self):
        self.observed = None

    def unconsumed_candidates(self, values):
        return tuple(values)

    def observe_selection(self, candidates, selection, **kwargs):
        self.observed = (tuple(candidates), selection, kwargs)


def _candidate(name, symbol, *, exploration=False):
    ranking = SimpleNamespace(
        risk_score=Decimal("80"), planned_risk_reward=Decimal("3"),
        strategy_score=Decimal("70"), closed_until_ms=1_900_000_000_000,
        source_run_id=f"run:{name}", final_approval_id=f"approval:{name}",
    )
    return Candidate(
        name, symbol, ranking,
        ADMISSION_PAPER_EXPLORATION if exploration else "NORMAL_EMPIRICAL_ADMISSION",
        {"authority_population_id": POPULATION} if exploration else {},
    )


def _executor(budget):
    value = object.__new__(ProductionPaperFirstCanaryExecutor)
    value._selector = ProductionEligibleApprovalSelector()
    value._outcome_store = Outcomes()
    value._exploration_store = budget
    value._clock = lambda: datetime(2026, 9, 28, 12, tzinfo=timezone.utc)
    value.last_selection_diagnostics = None
    return value


def test_normal_priority_and_same_mechanics(monkeypatch):
    monkeypatch.setenv("PAPER_EXPLORATION_ENABLED", "true")
    normal = _candidate("normal", "BTCUSDT")
    probe = _candidate("probe", "FETUSDT", exploration=True)
    executor = _executor(Budget())
    canary = SimpleNamespace(
        selection_policy_version="eligible-approval-ranking-v1",
        universe_version_id="universe", current_control_generation=1,
    )
    results = (SimpleNamespace(symbol_results=(
        SimpleNamespace(candidate=probe), SimpleNamespace(candidate=normal),
    )),)
    selected = executor._select_candidate(canary, results)
    assert selected.winner is normal
    assert executor._outcome_store.observed[2]["selection_reasons"][probe.candidate_id] == (
        "NORMAL_COMMAND_TAKES_PRECEDENCE"
    )
    # Admission/provenance are the only differences; geometry/ranking is reused.
    assert (
        probe.ranking.risk_score,
        probe.ranking.planned_risk_reward,
        probe.ranking.strategy_score,
        probe.ranking.closed_until_ms,
    ) == (
        normal.ranking.risk_score,
        normal.ranking.planned_risk_reward,
        normal.ranking.strategy_score,
        normal.ranking.closed_until_ms,
    )


def test_exploration_budget_selection_and_shared_population(monkeypatch):
    monkeypatch.setenv("PAPER_EXPLORATION_ENABLED", "true")
    budget = Budget()
    executor = _executor(budget)
    canary = SimpleNamespace(
        selection_policy_version="eligible-approval-ranking-v1",
        universe_version_id="universe", current_control_generation=1,
    )
    values = (_candidate("btc", "BTCUSDT", exploration=True), _candidate("fet", "FETUSDT", exploration=True))
    result = executor._select_candidate(
        canary, (SimpleNamespace(symbol_results=tuple(SimpleNamespace(candidate=x) for x in values)),)
    )
    assert result.winner is not None
    assert budget.seen == [POPULATION, POPULATION]
    assert len(executor._outcome_store.observed[0]) == 2
