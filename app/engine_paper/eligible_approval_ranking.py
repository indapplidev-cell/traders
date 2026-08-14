"""Versioned, deterministic selection among already-eligible PAPER approvals."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Final, Protocol, Sequence


LEGACY_EXACTLY_ONE_POLICY_VERSION: Final = "exactly-one-eligible-v1"
MULTI_SYMBOL_SELECTION_POLICY_VERSION: Final = "eligible-approval-ranking-v1"
DEFAULT_NEW_CANARY_SELECTION_POLICY_VERSION: Final = MULTI_SYMBOL_SELECTION_POLICY_VERSION
SELECTION_MODE: Final = "DETERMINISTIC_RANKING"
RANKING_FIELDS: Final = (
    "risk_score_desc",
    "planned_risk_reward_desc",
    "strategy_score_desc",
    "closed_until_ms_desc",
    "source_run_id_asc",
    "final_approval_id_asc",
    "candidate_id_asc",
    "symbol_asc",
)
FINAL_TIE_BREAK: Final = "candidate_id_asc_then_symbol_asc"


class RankingInputs(Protocol):
    risk_score: Decimal | None
    planned_risk_reward: Decimal
    strategy_score: Decimal | None
    closed_until_ms: int
    source_run_id: str
    final_approval_id: str


class EligibleCandidate(Protocol):
    candidate_id: str
    symbol: str
    ranking: RankingInputs


@dataclass(frozen=True, slots=True)
class EligibleApprovalSelectionDiagnostics:
    eligible_count: int
    winner_candidate_id: str | None
    winner_symbol: str | None
    policy_version: str
    ranking_fields: tuple[str, ...]
    tie_broken_by: str | None
    duplicate_count: int = 0

    def safe_report(self) -> dict[str, object]:
        return {
            "eligible_count": self.eligible_count,
            "winner_candidate_id": self.winner_candidate_id,
            "winner_symbol": self.winner_symbol,
            "ranking_policy_version": self.policy_version,
            "ranking_fields": list(self.ranking_fields),
            "tie_broken_by": self.tie_broken_by,
            "duplicate_count": self.duplicate_count,
        }


@dataclass(frozen=True, slots=True)
class EligibleApprovalSelectionResult:
    winner: EligibleCandidate | None
    diagnostics: EligibleApprovalSelectionDiagnostics
    failure_code: str | None = None


def _descending_decimal(value: Decimal) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError("invalid required ranking decimal")
    return -value


def _key(candidate: EligibleCandidate) -> tuple[object, ...]:
    ranking = candidate.ranking
    if (
        isinstance(ranking.closed_until_ms, bool)
        or not isinstance(ranking.closed_until_ms, int)
        or ranking.closed_until_ms < 0
        or not ranking.source_run_id
        or not ranking.final_approval_id
        or not candidate.candidate_id
        or not candidate.symbol
    ):
        raise ValueError("invalid required ranking identity")
    for value in (ranking.risk_score, ranking.strategy_score):
        if not isinstance(value, Decimal) or not value.is_finite() or value < 0 or value > 100:
            raise ValueError("ranking score outside 0..100")
    if (
        not isinstance(ranking.planned_risk_reward, Decimal)
        or not ranking.planned_risk_reward.is_finite()
        or ranking.planned_risk_reward <= 0
    ):
        raise ValueError("planned risk/reward must be positive")
    return (
        _descending_decimal(ranking.risk_score),
        _descending_decimal(ranking.planned_risk_reward),
        _descending_decimal(ranking.strategy_score),
        -ranking.closed_until_ms,
        ranking.source_run_id,
        ranking.final_approval_id,
        candidate.candidate_id,
        candidate.symbol,
    )


class ProductionEligibleApprovalSelector:
    """Pure total-order selector; input eligibility is established upstream."""

    def select(
        self,
        candidates: Sequence[EligibleCandidate],
        *,
        policy_version: str,
    ) -> EligibleApprovalSelectionResult:
        by_identity: dict[str, EligibleCandidate] = {}
        try:
            for candidate in candidates:
                if not candidate.candidate_id:
                    raise ValueError("missing candidate identity")
                previous = by_identity.get(candidate.candidate_id)
                if previous is not None and previous != candidate:
                    raise ValueError("conflicting logical approval duplicate")
                by_identity.setdefault(candidate.candidate_id, candidate)
            unique = tuple(by_identity.values())
        except (AttributeError, TypeError, ValueError):
            return self._failure(len(candidates), policy_version, "INVALID_RANKING_CANDIDATE")

        duplicate_count = len(candidates) - len(unique)
        if policy_version == LEGACY_EXACTLY_ONE_POLICY_VERSION:
            if len(unique) > 1:
                return self._failure(
                    len(unique), policy_version, "APPROVAL_SOURCE_AMBIGUOUS",
                    duplicate_count=duplicate_count,
                )
            winner = unique[0] if unique else None
            return EligibleApprovalSelectionResult(
                winner,
                EligibleApprovalSelectionDiagnostics(
                    len(unique), winner.candidate_id if winner else None,
                    winner.symbol if winner else None, policy_version, (),
                    "only_eligible_candidate" if winner else None, duplicate_count,
                ),
            )
        if policy_version != MULTI_SYMBOL_SELECTION_POLICY_VERSION:
            return self._failure(len(unique), policy_version, "SELECTION_POLICY_NOT_SUPPORTED")
        try:
            keys = {candidate.candidate_id: _key(candidate) for candidate in unique}
        except (AttributeError, ArithmeticError, TypeError, ValueError):
            return self._failure(len(unique), policy_version, "INVALID_RANKING_CANDIDATE")
        if not unique:
            return EligibleApprovalSelectionResult(
                None,
                EligibleApprovalSelectionDiagnostics(
                    0, None, None, policy_version, RANKING_FIELDS, None, duplicate_count,
                ),
            )

        ordered = sorted(unique, key=lambda item: keys[item.candidate_id])
        winner = ordered[0]
        criterion = "only_eligible_candidate"
        if len(ordered) > 1:
            winner_key, runner_up_key = keys[winner.candidate_id], keys[ordered[1].candidate_id]
            criterion = next(
                field for field, left, right in zip(RANKING_FIELDS, winner_key, runner_up_key)
                if left != right
            )
        return EligibleApprovalSelectionResult(
            winner,
            EligibleApprovalSelectionDiagnostics(
                len(unique), winner.candidate_id, winner.symbol, policy_version,
                RANKING_FIELDS, criterion, duplicate_count,
            ),
        )

    @staticmethod
    def _failure(
        count: int,
        policy_version: str,
        code: str,
        *,
        duplicate_count: int = 0,
    ) -> EligibleApprovalSelectionResult:
        return EligibleApprovalSelectionResult(
            None,
            EligibleApprovalSelectionDiagnostics(
                count, None, None, policy_version,
                RANKING_FIELDS if policy_version == MULTI_SYMBOL_SELECTION_POLICY_VERSION else (),
                None, duplicate_count,
            ),
            code,
        )


__all__ = (
    "DEFAULT_NEW_CANARY_SELECTION_POLICY_VERSION",
    "EligibleApprovalSelectionDiagnostics",
    "EligibleApprovalSelectionResult",
    "FINAL_TIE_BREAK",
    "LEGACY_EXACTLY_ONE_POLICY_VERSION",
    "MULTI_SYMBOL_SELECTION_POLICY_VERSION",
    "ProductionEligibleApprovalSelector",
    "RANKING_FIELDS",
    "SELECTION_MODE",
)
