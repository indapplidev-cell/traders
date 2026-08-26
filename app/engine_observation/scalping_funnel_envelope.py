"""Diagnostic 10-symbol daily funnel envelope; never an admission quota."""

from __future__ import annotations

from typing import Final, Mapping


SCALPING_DAILY_FUNNEL_ENVELOPE: Final = {
    "evaluations": (2880, 2880),
    "setups": (300, 700),
    "strategy_candidates": (100, 300),
    "geometry_valid": (50, 150),
    "net_cost_viable": (30, 100),
    "final_approvals": (20, 60),
    "actual_entries": (10, 30),
}


def diagnose_scalping_funnel(counts: Mapping[str, int]) -> dict[str, object]:
    stages: dict[str, object] = {}
    for stage, (minimum, maximum) in SCALPING_DAILY_FUNNEL_ENVELOPE.items():
        observed = counts.get(stage)
        status = (
            "NOT_OBSERVED" if observed is None else
            "BELOW_ENVELOPE" if observed < minimum else
            "ABOVE_ENVELOPE" if observed > maximum else "WITHIN_ENVELOPE"
        )
        stages[stage] = {
            "observed": observed, "minimum": minimum, "maximum": maximum,
            "status": status,
        }
    return {"diagnostic_only": True, "admission_quota": False, "stages": stages}
