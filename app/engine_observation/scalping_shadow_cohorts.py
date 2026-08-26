"""Factor-isolated Scalping research cohorts with zero trading authority."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Mapping


SCALPING_SHADOW_FACTORS: Final = {
    "strategy_threshold": (55.0, 60.0, 65.0),
    "not_evaluated_handling": ("LEGACY_WEAK_CAP", "SCORE_FROM_EVALUATED_COMPONENTS"),
    "atr_buffer": (0.25, 0.50, 0.75),
    "stop_envelope_bps": (50.0, 65.0, 80.0),
    "minimum_target_bps": (45.0, 60.0, 80.0),
    "minimum_net_edge_bps": (10.0, 15.0, 20.0),
    "minimum_rr": (1.0, 1.2, 1.5),
    "risk_per_trade_bps": (10.0, 15.0, 20.0, 25.0),
    "entry_ttl_seconds": (30, 60, 120),
    "time_stop_minutes": (15, 30, 45),
}


@dataclass(frozen=True, slots=True)
class ScalpingShadowCohort:
    cohort_id: str
    factor: str
    value: object
    parameters: Mapping[str, object]
    execution_eligible: bool = False
    mutates_production_trading_state: bool = False


def isolated_cohorts(
    base: Mapping[str, object], *, factor: str
) -> tuple[ScalpingShadowCohort, ...]:
    if factor not in SCALPING_SHADOW_FACTORS or factor not in base:
        raise ValueError("declared factor and base value are required")
    result = []
    for value in SCALPING_SHADOW_FACTORS[factor]:
        parameters = {**base, factor: value}
        result.append(ScalpingShadowCohort(
            cohort_id=f"scalping-shadow:{factor}:{value}",
            factor=factor, value=value, parameters=parameters,
        ))
    return tuple(result)
