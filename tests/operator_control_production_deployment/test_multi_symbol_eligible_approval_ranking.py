from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from itertools import permutations
from types import SimpleNamespace

import pytest

from app.engine_paper.eligible_approval_ranking import (
    LEGACY_EXACTLY_ONE_POLICY_VERSION,
    MULTI_SYMBOL_SELECTION_POLICY_VERSION,
    ProductionEligibleApprovalSelector,
    RANKING_FIELDS,
)
from app.engine_paper.production_approval import (
    PaperProductionApprovalRequest,
    PaperProductionApprovalScope,
    PaperProductionApprovalSourceAdapter,
    SYMBOL_ALLOWLIST,
)
from app.trading_universe.domain import PREPARED_NEXT_TRADING_UNIVERSE
from app.operator_control.production_executor import _candidate_entry_fill_window_missed
from app.engine_paper.production_preparation import (
    EXPECTED_PREVIOUS_ALEMBIC,
    PaperPreparationPhase,
    PaperProductionTargetGuard,
    classify_preparation_phase,
)
from tests.paper_production_approval_source_adapter.test_adapter_contract import (
    FakeReader,
    FakeSession,
    eligible_row,
)


def candidate(symbol: str, ordinal: int, **ranking_changes):
    source = PaperProductionApprovalSourceAdapter(
        lambda: FakeSession(),
        reader=FakeReader({"BTCUSDT": (eligible_row(),)}),
        monotonic=iter((1.0, 1.001)).__next__,
    )
    result = source.read(PaperProductionApprovalRequest(
        PaperProductionApprovalScope(("BTCUSDT",)), "ranking-fixture", 1_900_000_005_000
    ))
    base = result.candidates[0]
    ranking = replace(
        base.ranking,
        source_run_id=f"run:{ordinal:02d}",
        final_approval_id=f"approval:{ordinal:02d}",
        **ranking_changes,
    )
    return replace(
        base,
        candidate_id=f"candidate:{ordinal:02d}",
        symbol=symbol,
        ranking=ranking,
    )


def select(values, policy=MULTI_SYMBOL_SELECTION_POLICY_VERSION):
    return ProductionEligibleApprovalSelector().select(tuple(values), policy_version=policy)


def test_zero_and_single_candidate_contract_and_legacy_compatibility():
    empty = select(())
    assert empty.winner is None and empty.failure_code is None
    only = candidate("BTCUSDT", 1)
    assert select((only,)).winner is only
    assert select((only,), LEGACY_EXACTLY_ONE_POLICY_VERSION).winner is only


def test_continuous_candidate_rejects_only_a_missed_entry_fill_window():
    boundary_ms = 1_900_000_000_000
    base = candidate("BTCUSDT", 1, closed_until_ms=boundary_ms)
    timely = SimpleNamespace(
        ranking=base.ranking,
        paper_risk_approval=SimpleNamespace(
            approved_at=datetime.fromtimestamp((boundary_ms + 59_999) / 1000, timezone.utc)
        ),
    )
    late = SimpleNamespace(
        ranking=base.ranking,
        paper_risk_approval=SimpleNamespace(
            approved_at=datetime.fromtimestamp((boundary_ms + 60_001) / 1000, timezone.utc)
        ),
    )

    assert _candidate_entry_fill_window_missed(timely) is False
    assert _candidate_entry_fill_window_missed(late) is True


@pytest.mark.parametrize("count", (2, 3, 10))
def test_every_valid_nonempty_multi_candidate_set_has_exactly_one_winner(count):
    values = [candidate(SYMBOL_ALLOWLIST[index], index) for index in range(count)]
    result = select(values)
    assert result.failure_code is None and result.winner is not None
    assert result.diagnostics.eligible_count == count
    assert result.diagnostics.ranking_fields == RANKING_FIELDS


def test_rank_one_is_selected_and_lower_ranks_have_canonical_reason():
    values = [candidate(SYMBOL_ALLOWLIST[index], index) for index in range(3)]
    ordered = sorted(values, key=lambda item: item.ranking.source_run_id)
    result = select(tuple(reversed(values)))
    assert result.winner is ordered[0]
    outcomes = {
        item.candidate_id: (
            "SELECTED", None
        ) if item is result.winner else (
            "NOT_SELECTED", "LOWER_SELECTOR_RANK"
        )
        for item in values
    }
    assert sum(state == "SELECTED" for state, _reason in outcomes.values()) == 1
    assert all(
        reason == "LOWER_SELECTOR_RANK"
        for state, reason in outcomes.values()
        if state == "NOT_SELECTED"
    )


@pytest.mark.parametrize(
    "field,lower,higher",
    (
        ("risk_score", Decimal("80"), Decimal("81")),
        ("planned_risk_reward", Decimal("1.5"), Decimal("1.6")),
        ("strategy_score", Decimal("70"), Decimal("71")),
        ("closed_until_ms", 1_900_000_000_000, 1_900_000_000_001),
    ),
)
def test_each_quality_or_freshness_direction_is_explicit(field, lower, higher):
    left = candidate("BTCUSDT", 1, **{field: lower})
    right = candidate("ETHUSDT", 2, **{field: higher})
    # Neutralize earlier fields so only the parametrized field differs.
    defaults = dict(risk_score=Decimal("80"), planned_risk_reward=Decimal("1.5"), strategy_score=Decimal("70"),
                    closed_until_ms=1_900_000_000_000)
    left_values = {**defaults, field: lower}
    right_values = {**defaults, field: higher}
    left = replace(left, ranking=replace(left.ranking, **left_values))
    right = replace(right, ranking=replace(right.ranking, **right_values))
    assert select((left, right)).winner is right


def test_input_permutations_and_exact_business_tie_are_deterministic():
    values = tuple(candidate(symbol, index) for index, symbol in enumerate(
        ("BTCUSDT", "ETHUSDT", "SOLUSDT"), start=1
    ))
    # Equalize all business values; stable persisted identity remains.
    values = tuple(replace(value, ranking=replace(
        value.ranking, risk_score=values[0].ranking.risk_score,
        planned_risk_reward=values[0].ranking.planned_risk_reward,
        strategy_score=values[0].ranking.strategy_score,
        closed_until_ms=values[0].ranking.closed_until_ms,
    )) for value in values)
    winners = {select(order).winner.candidate_id for order in permutations(values)}
    assert winners == {"candidate:01"}


def test_logical_duplicate_is_deduplicated_and_conflicting_duplicate_fails_closed():
    value = candidate("BTCUSDT", 1)
    duplicate = replace(value)
    result = select((value, duplicate))
    assert result.winner is value and result.diagnostics.duplicate_count == 1
    corrupt = replace(duplicate, symbol="ETHUSDT", ranking=replace(duplicate.ranking, risk_score=Decimal("99")))
    assert select((value, corrupt)).failure_code == "INVALID_RANKING_CANDIDATE"


def test_legacy_policy_still_fails_closed_for_existing_canary_lineage():
    values = (candidate("BTCUSDT", 1), candidate("ETHUSDT", 2))
    assert select(values, LEGACY_EXACTLY_ONE_POLICY_VERSION).failure_code == "APPROVAL_SOURCE_AMBIGUOUS"


def test_legacy_single_candidate_does_not_gain_new_ranking_requirements():
    value = candidate("BTCUSDT", 1)
    value = replace(value, ranking=replace(value.ranking, risk_score=None, strategy_score=None))
    assert select((value,), LEGACY_EXACTLY_ONE_POLICY_VERSION).winner is value
    assert select((value,)).failure_code == "INVALID_RANKING_CANDIDATE"


def test_current_v1_and_future_v2_universes_are_rankable_without_activation():
    v1 = [candidate(symbol, index) for index, symbol in enumerate(("BTCUSDT", "ETHUSDT"), 1)]
    assert select(v1).winner is not None
    assert SYMBOL_ALLOWLIST == PREPARED_NEXT_TRADING_UNIVERSE.symbols
    v2 = [candidate(symbol, index) for index, symbol in enumerate(SYMBOL_ALLOWLIST, 1)]
    assert len(v2) == 10 and select(v2).winner is not None
    assert PREPARED_NEXT_TRADING_UNIVERSE.activation_state.value == "PREPARED_NOT_ACTIVE"


def test_same_candidate_set_produces_same_winner_for_independent_workers():
    values = tuple(candidate(symbol, index) for index, symbol in enumerate(SYMBOL_ALLOWLIST, 1))
    first = ProductionEligibleApprovalSelector().select(
        values, policy_version=MULTI_SYMBOL_SELECTION_POLICY_VERSION
    )
    second = ProductionEligibleApprovalSelector().select(
        tuple(reversed(values)), policy_version=MULTI_SYMBOL_SELECTION_POLICY_VERSION
    )
    assert first.winner.candidate_id == second.winner.candidate_id


def test_deployment_accepts_only_the_current_exact_predecessor_for_incremental_migration():
    assert EXPECTED_PREVIOUS_ALEMBIC == "0019_first_class_15m_domain"
    assert classify_preparation_phase(
        EXPECTED_PREVIOUS_ALEMBIC, preparation_complete=False
    ) is PaperPreparationPhase.PARTIAL_RESUMABLE
    assert PaperProductionTargetGuard(
        "traders-production-primary", expected_start_alembic=EXPECTED_PREVIOUS_ALEMBIC
    ).expected_start_alembic == EXPECTED_PREVIOUS_ALEMBIC
    assert classify_preparation_phase(
        "0014_unrecognized", preparation_complete=False
    ) is PaperPreparationPhase.INCOMPATIBLE


@pytest.mark.parametrize("field,value", (
    ("risk_score", Decimal("NaN")), ("strategy_score", Decimal("Infinity")),
    ("planned_risk_reward", Decimal("0")), ("source_run_id", ""),
))
def test_missing_corrupt_or_nonfinite_required_ranking_value_fails_closed(field, value):
    item = candidate("BTCUSDT", 1)
    item = replace(item, ranking=replace(item.ranking, **{field: value}))
    assert select((item,)).failure_code == "INVALID_RANKING_CANDIDATE"
