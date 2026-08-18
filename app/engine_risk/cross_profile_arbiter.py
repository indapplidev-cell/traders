"""Inactive future cross-profile arbiter contract; no execution integration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CrossProfileDecision(StrEnum):
    ALLOW_SINGLE_CANDIDATE = "ALLOW_SINGLE_CANDIDATE"
    DENY_SAME_SYMBOL_DOUBLE_EXPOSURE = "DENY_SAME_SYMBOL_DOUBLE_EXPOSURE"
    CROSS_TIMEFRAME_CONFLICT = "CROSS_TIMEFRAME_CONFLICT"


@dataclass(frozen=True, slots=True)
class ProfileApprovalCandidate:
    trade_profile_id: str
    symbol: str
    direction: str
    final_approval_id: str


@dataclass(frozen=True, slots=True)
class CrossProfileArbiterResult:
    decision: str
    selected: ProfileApprovalCandidate | None
    global_account_equity_authority_shared: bool = True
    global_open_position_budget_shared: bool = True
    global_daily_risk_budget_shared: bool = True
    automatic_execution_allowed: bool = False


class FutureCrossProfileArbiter:
    """Design-only fail-closed arbiter. It never exposes an execution method."""

    def evaluate(
        self,
        candidates: tuple[ProfileApprovalCandidate, ...],
        *,
        symbols_with_existing_or_planned_exposure: frozenset[str] = frozenset(),
    ) -> CrossProfileArbiterResult:
        if not candidates:
            return CrossProfileArbiterResult(
                CrossProfileDecision.ALLOW_SINGLE_CANDIDATE.value, None
            )
        symbols = {item.symbol.upper() for item in candidates}
        if symbols & {item.upper() for item in symbols_with_existing_or_planned_exposure}:
            return CrossProfileArbiterResult(
                CrossProfileDecision.DENY_SAME_SYMBOL_DOUBLE_EXPOSURE.value, None
            )
        by_symbol: dict[str, list[ProfileApprovalCandidate]] = {}
        for candidate in candidates:
            by_symbol.setdefault(candidate.symbol.upper(), []).append(candidate)
        for items in by_symbol.values():
            if len(items) > 1:
                if len({item.direction for item in items}) > 1:
                    return CrossProfileArbiterResult(
                        CrossProfileDecision.CROSS_TIMEFRAME_CONFLICT.value, None
                    )
                return CrossProfileArbiterResult(
                    CrossProfileDecision.DENY_SAME_SYMBOL_DOUBLE_EXPOSURE.value, None
                )
        selected = candidates[0] if len(candidates) == 1 else None
        return CrossProfileArbiterResult(
            CrossProfileDecision.ALLOW_SINGLE_CANDIDATE.value, selected
        )
