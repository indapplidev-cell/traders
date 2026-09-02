"""Independent Scalping v2 policy identity and empirical economics gate."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


PROFILE_ID = "trade-5m-v2"
SETUP_POLICY_VERSION = "scalping-micro-setup-v2"
ENTRY_POLICY_VERSION = "scalping-next-closed-1m-entry-v2"
STOP_POLICY_VERSION = "scalping-causal-volatility-stop-v2"
TARGET_POLICY_VERSION = "scalping-nearest-viable-target-v3"
RR_EV_POLICY_VERSION = "scalping-empirical-ev-v1"
TTL_POLICY_VERSION = "scalping-short-lifecycle-v2"
RISK_POLICY_VERSION = "scalping-risk-capped-v2"
COST_POLICY_VERSION = "scalping-round-trip-net-pnl-v2"


def policy_provenance() -> dict[str, str]:
    """Complete candidate identity persisted with every v2 PAPER plan."""
    return {
        "scalping_profile_version": PROFILE_ID,
        "setup_policy_version": SETUP_POLICY_VERSION,
        "entry_policy_version": ENTRY_POLICY_VERSION,
        "stop_policy_version": STOP_POLICY_VERSION,
        "target_policy_version": TARGET_POLICY_VERSION,
        "rr_ev_policy_version": RR_EV_POLICY_VERSION,
        "cost_policy_version": COST_POLICY_VERSION,
        "ttl_policy_version": TTL_POLICY_VERSION,
        "risk_policy_version": RISK_POLICY_VERSION,
    }


@dataclass(frozen=True, slots=True)
class EmpiricalSetupBucket:
    setup_type: str
    direction: str
    samples: int
    wins: int

    def __post_init__(self) -> None:
        if self.samples < 0 or not 0 <= self.wins <= self.samples:
            raise ValueError("invalid empirical setup bucket")

    @property
    def probability(self) -> float:
        """Laplace-smoothed historical probability; never an invented score."""
        return (self.wins + 1) / (self.samples + 2)


@dataclass(frozen=True, slots=True)
class ExpectancyDecision:
    admitted: bool
    expected_value_bps: float | None
    probability: float | None
    reason: str


def evaluate_expectancy(
    *, net_win_bps: float, net_loss_bps: float,
    bucket: EmpiricalSetupBucket | None,
    minimum_samples: int = 20,
    minimum_expected_value_bps: float = 0.0,
    static_net_rr: float | None = None,
    static_minimum_net_rr: float = 0.4,
) -> ExpectancyDecision:
    """Use empirical EV when supported, otherwise a stricter static fallback."""
    if any(not isfinite(float(value)) or float(value) <= 0 for value in (net_win_bps, net_loss_bps)):
        raise ValueError("net win/loss must be positive and finite")
    if bucket is None or bucket.samples < minimum_samples:
        admitted = static_net_rr is not None and static_net_rr >= static_minimum_net_rr
        return ExpectancyDecision(
            admitted, None, None,
            "INSUFFICIENT_BUCKET_STATIC_RR_PASS" if admitted else "INSUFFICIENT_BUCKET_STATIC_RR_REJECT",
        )
    probability = bucket.probability
    expected_value = probability * net_win_bps - (1 - probability) * net_loss_bps
    return ExpectancyDecision(
        expected_value >= minimum_expected_value_bps,
        expected_value,
        probability,
        "EMPIRICAL_EV_PASS" if expected_value >= minimum_expected_value_bps else "EMPIRICAL_EV_REJECT",
    )


__all__ = (
    "COST_POLICY_VERSION", "ENTRY_POLICY_VERSION", "EmpiricalSetupBucket", "ExpectancyDecision",
    "PROFILE_ID", "RISK_POLICY_VERSION", "RR_EV_POLICY_VERSION",
    "SETUP_POLICY_VERSION", "STOP_POLICY_VERSION", "TARGET_POLICY_VERSION",
    "TTL_POLICY_VERSION", "evaluate_expectancy", "policy_provenance",
)
