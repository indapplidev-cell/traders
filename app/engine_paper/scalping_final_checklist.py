"""Mechanical Scalping final-approval checklist with no analytic authority."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class ScalpingFinalApprovalChecklist:
    market_data_fresh: bool
    setup_valid: bool
    strategy_admitted: bool
    geometry_valid: bool
    target_valid: bool
    cost_gate_pass: bool
    risk_pass: bool
    opportunity_not_duplicate: bool
    singleton_valid: bool
    entry_still_valid: bool
    authority_valid: bool

    @property
    def passed(self) -> bool:
        return all(asdict(self).values())

    def to_dict(self) -> dict[str, bool]:
        return {**asdict(self), "passed": self.passed}


def evaluate_scalping_final_checklist(**facts: bool) -> ScalpingFinalApprovalChecklist:
    """Copy already-proven facts into a checklist; derive no new market view."""
    return ScalpingFinalApprovalChecklist(**facts)
