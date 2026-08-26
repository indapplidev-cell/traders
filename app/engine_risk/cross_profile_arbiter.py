"""Inactive future cross-profile arbiter contract; no execution integration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CrossProfileDecision(StrEnum):
    ALLOW_SINGLE_CANDIDATE = "ALLOW_SINGLE_CANDIDATE"
    DENY_SAME_SYMBOL_DOUBLE_EXPOSURE = "DENY_SAME_SYMBOL_DOUBLE_EXPOSURE"
    CROSS_TIMEFRAME_CONFLICT = "CROSS_TIMEFRAME_CONFLICT"
    DENY_MAX_CONCURRENT_POSITIONS = "DENY_MAX_CONCURRENT_POSITIONS"
    DENY_TOTAL_OPEN_RISK = "DENY_TOTAL_OPEN_RISK"
    DENY_SAME_DIRECTION_EXPOSURE = "DENY_SAME_DIRECTION_EXPOSURE"
    DENY_CORRELATED_EXPOSURE = "DENY_CORRELATED_EXPOSURE"


@dataclass(frozen=True, slots=True)
class ProfileApprovalCandidate:
    trade_profile_id: str
    symbol: str
    direction: str
    final_approval_id: str
    risk_bps: float = 0.0
    correlation_group: str | None = None


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
        existing_positions: tuple[ProfileApprovalCandidate, ...] = (),
        max_concurrent_positions: int = 3,
        max_total_open_risk_bps: float = 50.0,
        max_same_direction_positions: int = 2,
        max_correlated_positions: int = 1,
    ) -> CrossProfileArbiterResult:
        if not candidates:
            return CrossProfileArbiterResult(
                CrossProfileDecision.ALLOW_SINGLE_CANDIDATE.value, None
            )
        symbols = {item.symbol.upper() for item in candidates}
        exposed_symbols = {
            item.upper() for item in symbols_with_existing_or_planned_exposure
        } | {item.symbol.upper() for item in existing_positions}
        if symbols & exposed_symbols:
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
        combined = (*existing_positions, *candidates)
        if len(combined) > max_concurrent_positions:
            return CrossProfileArbiterResult(
                CrossProfileDecision.DENY_MAX_CONCURRENT_POSITIONS.value, None
            )
        if sum(max(0.0, float(item.risk_bps)) for item in combined) > max_total_open_risk_bps:
            return CrossProfileArbiterResult(
                CrossProfileDecision.DENY_TOTAL_OPEN_RISK.value, None
            )
        direction_counts = {
            direction: sum(item.direction == direction for item in combined)
            for direction in {item.direction for item in combined}
        }
        if any(count > max_same_direction_positions for count in direction_counts.values()):
            return CrossProfileArbiterResult(
                CrossProfileDecision.DENY_SAME_DIRECTION_EXPOSURE.value, None
            )
        correlation_counts = {
            group: sum(item.correlation_group == group for item in combined)
            for group in {item.correlation_group for item in combined if item.correlation_group}
        }
        if any(count > max_correlated_positions for count in correlation_counts.values()):
            return CrossProfileArbiterResult(
                CrossProfileDecision.DENY_CORRELATED_EXPOSURE.value, None
            )
        selected = candidates[0] if len(candidates) == 1 else None
        return CrossProfileArbiterResult(
            CrossProfileDecision.ALLOW_SINGLE_CANDIDATE.value, selected
        )
