"""Independent Scalping v2 policy identity and empirical economics gate."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from statistics import NormalDist

from app.config.trade_parameters import SCALPING_V2


PROFILE_ID = "trade-5m-v2"
SETUP_POLICY_VERSION = "scalping-micro-setup-v2"
ENTRY_POLICY_VERSION = "scalping-next-closed-1m-entry-v2"
STOP_POLICY_VERSION = "scalping-causal-volatility-stop-v2"
TARGET_POLICY_VERSION = "scalping-nearest-viable-target-v3"
RR_EV_POLICY_VERSION = "scalping-conservative-hierarchy-v2"
PROBABILITY_ESTIMATOR_VERSION = "hierarchical-beta-wilson-v1"
CONFIDENCE_METHOD = "WILSON_ONE_SIDED_LOWER_BOUND"
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
    level: str = "exact"
    bucket_key: str | None = None

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
    fallback_level: str | None = None
    bucket_key: str | None = None
    p_win_raw: float | None = None
    p_win_adjusted: float | None = None
    p_win_conservative: float | None = None
    sample_size: int = 0
    parent_sample_size: int = 0
    estimator_version: str = PROBABILITY_ESTIMATOR_VERSION
    confidence_method: str = CONFIDENCE_METHOD
    dynamic_required_net_rr: float | None = None
    candidate_net_rr: float | None = None
    expected_ev_r: float | None = None
    ev_reserve: float | None = None


@dataclass(frozen=True, slots=True)
class ProbabilityEstimate:
    p_win_raw: float
    p_win_adjusted: float
    p_win_conservative: float
    sample_size: int
    parent_sample_size: int
    estimator_version: str
    confidence_method: str
    bucket_key: str
    fallback_level: str


def estimate_conservative_probability(
    bucket: EmpiricalSetupBucket, *, parent_sample_size: int = 0,
    confidence_level: float = SCALPING_V2.economics.probability_confidence_level,
    prior_alpha: float = SCALPING_V2.economics.prior_alpha,
    prior_beta: float = SCALPING_V2.economics.prior_beta,
) -> ProbabilityEstimate:
    """Return raw, beta-smoothed and Wilson-lower probabilities."""
    if bucket.samples <= 0:
        raise ValueError("probability estimation requires a non-empty bucket")
    raw = bucket.wins / bucket.samples
    adjusted = (bucket.wins + prior_alpha) / (
        bucket.samples + prior_alpha + prior_beta
    )
    z = NormalDist().inv_cdf(confidence_level)
    n = bucket.samples + prior_alpha + prior_beta
    denominator = 1 + z * z / n
    centre = adjusted + z * z / (2 * n)
    margin = z * sqrt((adjusted * (1 - adjusted) + z * z / (4 * n)) / n)
    conservative = max(0.0, (centre - margin) / denominator)
    return ProbabilityEstimate(
        raw, adjusted, conservative, bucket.samples, parent_sample_size,
        PROBABILITY_ESTIMATOR_VERSION, CONFIDENCE_METHOD,
        bucket.bucket_key or f"{bucket.setup_type}|{bucket.direction}", bucket.level,
    )


def evaluate_expectancy(
    *, net_win_bps: float, net_loss_bps: float,
    bucket: EmpiricalSetupBucket | None,
    minimum_samples: int = 20,
    minimum_expected_value_bps: float = 0.0,
    minimum_positive_ev_r: float = SCALPING_V2.economics.min_positive_ev_r,
    minimum_ev_reserve_r: float = SCALPING_V2.economics.min_ev_reserve_r,
    parent_buckets: tuple[EmpiricalSetupBucket, ...] = (),
    static_net_rr: float | None = None,  # historical caller compatibility; never authoritative
    static_minimum_net_rr: float = 0.4,  # historical caller compatibility; never authoritative
) -> ExpectancyDecision:
    """Select the first sufficiently sampled hierarchy level or fail closed."""
    if any(not isfinite(float(value)) or float(value) <= 0 for value in (net_win_bps, net_loss_bps)):
        raise ValueError("net win/loss must be positive and finite")
    selected = next(
        (item for item in ((bucket,) if bucket is not None else ()) + parent_buckets
         if item.samples >= minimum_samples),
        None,
    )
    if selected is None:
        return ExpectancyDecision(
            False, None, None, "INSUFFICIENT_STATISTICAL_AUTHORITY_NO_TRADE",
            fallback_level="none", bucket_key=None,
        )
    selected_index = (((bucket,) if bucket is not None else ()) + parent_buckets).index(selected)
    hierarchy = ((bucket,) if bucket is not None else ()) + parent_buckets
    parent_size = hierarchy[selected_index + 1].samples if selected_index + 1 < len(hierarchy) else 0
    estimate = estimate_conservative_probability(selected, parent_sample_size=parent_size)
    probability = estimate.p_win_conservative
    expected_value = probability * net_win_bps - (1 - probability) * net_loss_bps
    candidate_net_rr = net_win_bps / net_loss_bps
    break_even_rr = (1 - probability) / probability
    dynamic_required_net_rr = max(
        break_even_rr + minimum_ev_reserve_r,
        (1 - probability + minimum_positive_ev_r) / probability,
    )
    expected_ev_r = probability * candidate_net_rr - (1 - probability)
    ev_reserve = candidate_net_rr - break_even_rr
    admitted = (
        expected_value >= minimum_expected_value_bps
        and candidate_net_rr >= dynamic_required_net_rr
        and expected_ev_r >= minimum_positive_ev_r
        and ev_reserve >= minimum_ev_reserve_r
    )
    return ExpectancyDecision(
        admitted,
        expected_value,
        probability,
        "DYNAMIC_NET_RR_CONSERVATIVE_EV_PASS" if admitted else "DYNAMIC_NET_RR_CONSERVATIVE_EV_REJECT",
        fallback_level=selected.level,
        bucket_key=selected.bucket_key or f"{selected.setup_type}|{selected.direction}",
        p_win_raw=estimate.p_win_raw,
        p_win_adjusted=estimate.p_win_adjusted,
        p_win_conservative=estimate.p_win_conservative,
        sample_size=estimate.sample_size,
        parent_sample_size=estimate.parent_sample_size,
        dynamic_required_net_rr=dynamic_required_net_rr,
        candidate_net_rr=candidate_net_rr,
        expected_ev_r=expected_ev_r,
        ev_reserve=ev_reserve,
    )


__all__ = (
    "COST_POLICY_VERSION", "ENTRY_POLICY_VERSION", "EmpiricalSetupBucket", "ExpectancyDecision",
    "CONFIDENCE_METHOD", "PROBABILITY_ESTIMATOR_VERSION", "ProbabilityEstimate",
    "PROFILE_ID", "RISK_POLICY_VERSION", "RR_EV_POLICY_VERSION",
    "SETUP_POLICY_VERSION", "STOP_POLICY_VERSION", "TARGET_POLICY_VERSION",
    "TTL_POLICY_VERSION", "estimate_conservative_probability", "evaluate_expectancy", "policy_provenance",
)
