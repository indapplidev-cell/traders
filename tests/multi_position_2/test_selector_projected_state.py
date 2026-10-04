from decimal import Decimal
from types import SimpleNamespace

from app.engine_paper.eligible_approval_ranking import (
    MULTI_SYMBOL_SELECTION_POLICY_VERSION,
    ProductionEligibleApprovalSelector,
)


def _candidate(rank: int, symbol: str | None = None):
    return SimpleNamespace(
        candidate_id=f"candidate-{rank}",
        symbol=symbol or f"SYMBOL{rank}USDT",
        ranking=SimpleNamespace(
            risk_score=Decimal(str(100 - rank)),
            planned_risk_reward=Decimal("2"),
            strategy_score=Decimal("80"),
            closed_until_ms=1_800_000_000_000,
            source_run_id=f"run-{rank}",
            final_approval_id=f"approval-{rank}",
        ),
    )


def _select(candidates, **overrides):
    values = dict(
        policy_version=MULTI_SYMBOL_SELECTION_POLICY_VERSION,
        limit=2,
        reserved_positions=0,
        existing_open_risk_bps=Decimal("0"),
        risk_per_trade_bps=Decimal("5"),
        max_positions=2,
        max_total_open_risk_bps=Decimal("50"),
    )
    values.update(overrides)
    return ProductionEligibleApprovalSelector().select(candidates, **values)


def test_empty_book_selects_only_rank_one_and_two() -> None:
    selection = _select((_candidate(3), _candidate(2), _candidate(1)))

    assert [value.candidate_id for value in selection.winners] == [
        "candidate-1", "candidate-2",
    ]
    assert "candidate-3" not in {
        value.candidate_id for value in selection.winners
    }


def test_one_reserved_position_admits_at_most_one_new_candidate() -> None:
    selection = _select(
        (_candidate(1), _candidate(2), _candidate(3)),
        reserved_positions=1,
        existing_open_risk_bps=Decimal("5"),
    )

    assert [value.candidate_id for value in selection.winners] == ["candidate-1"]
    assert selection.rejected_top_rank_reasons == (
        ("candidate-2", "PORTFOLIO_REJECT_MAX_CONCURRENT_POSITIONS"),
    )


def test_two_reserved_positions_admit_no_new_candidate() -> None:
    selection = _select(
        (_candidate(1), _candidate(2)),
        reserved_positions=2,
        existing_open_risk_bps=Decimal("10"),
    )

    assert selection.winners == ()
    assert selection.winner is None


def test_rank_two_failure_does_not_backfill_rank_three() -> None:
    selection = _select(
        (_candidate(1, "BTCUSDT"), _candidate(2, "BTCUSDT"), _candidate(3)),
    )

    assert [value.candidate_id for value in selection.winners] == ["candidate-1"]
    assert selection.rejected_top_rank_reasons == (
        ("candidate-2", "PORTFOLIO_REJECT_DUPLICATE_OR_OPPOSING_SYMBOL"),
    )
    assert "candidate-3" not in {
        value.candidate_id for value in selection.winners
    }


def test_rank_two_projected_risk_includes_rank_one_reservation() -> None:
    selection = _select(
        (_candidate(1), _candidate(2), _candidate(3)),
        existing_open_risk_bps=Decimal("42"),
    )

    assert [value.candidate_id for value in selection.winners] == ["candidate-1"]
    assert selection.rejected_top_rank_reasons == (
        ("candidate-2", "PORTFOLIO_REJECT_TOTAL_OPEN_RISK"),
    )
    assert "candidate-3" not in {
        value.candidate_id for value in selection.winners
    }


def test_total_risk_and_per_trade_risk_are_not_relaxed() -> None:
    selection = _select(
        (_candidate(1), _candidate(2)),
        existing_open_risk_bps=Decimal("46"),
    )

    assert selection.winners == ()
    assert selection.rejected_top_rank_reasons[0] == (
        "candidate-1", "PORTFOLIO_REJECT_TOTAL_OPEN_RISK",
    )
