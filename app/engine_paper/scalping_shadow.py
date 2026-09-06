"""Causal 5m geometry and economics for shadow cohorts and production gating.

The module has no command, order, fill, position, or private API dependency.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal, ROUND_DOWN, ROUND_UP
from hashlib import sha256
from math import isfinite
from statistics import median
from typing import Iterable

from app.engine_paper.paper_reason_codes import PaperReasonCode as R
from app.engine_paper.scalping_policy_v2 import (
    PROFILE_ID as V2_PROFILE_ID,
    RR_EV_POLICY_VERSION as V2_RR_EV_POLICY_VERSION,
    TARGET_POLICY_VERSION as V2_TARGET_POLICY_VERSION,
    EmpiricalSetupBucket,
    evaluate_expectancy,
)


GEOMETRY_CALCULATION_VERSION = "scalping-cost-aware-geometry-v2"
COST_MODEL_VERSION = "scalping-round-trip-net-pnl-v2"
RR_POLICY_VERSION = "scalping-required-net-rr-v2"
TARGET_POLICY_VERSION = "scalping-causal-cost-aware-target-v2"
PAPER_PRICE_QUANTUM = Decimal("0.00000001")

TARGET_PRIORITY = {
    "LOCAL_5M_LIQUIDITY": 0,
    "LOCAL_5M": 0,  # compatibility alias
    "RECENT_5M_SWING": 1,
    "LOCAL_RANGE_BOUNDARY": 2,
    "STRUCTURAL": 3,
    "15M": 4,
    "HIGHER_TF": 4,  # compatibility alias; timeframe resolves the exact tier
    "1H": 5,
}
@dataclass(frozen=True, slots=True)
class CausalTarget:
    price: float
    source_type: str
    known_at_ms: int
    validated: bool = True
    relevant: bool = True
    achievable: bool = True
    timeframe: str | None = None
    source_detail: str | None = None

    def __post_init__(self) -> None:
        if self.source_type not in TARGET_PRIORITY:
            raise ValueError("unsupported target source type")
        if not isfinite(float(self.price)) or self.price <= 0:
            raise ValueError("target price must be positive and finite")

    @property
    def resolved_timeframe(self) -> str:
        if self.timeframe:
            return self.timeframe.lower()
        return {
            "LOCAL_5M_LIQUIDITY": "5m",
            "LOCAL_5M": "5m", "STRUCTURAL": "5m", "15M": "15m",
            "RECENT_5M_SWING": "5m", "LOCAL_RANGE_BOUNDARY": "5m",
            "1H": "1h", "HIGHER_TF": "unknown",
        }[self.source_type]


@dataclass(frozen=True, slots=True)
class ShadowCostInputs:
    entry_fee_bps: float = 10.0
    exit_fee_bps: float = 10.0
    entry_slippage_bps: float = 2.0
    exit_slippage_bps: float = 2.0
    safety_margin_bps: float = 3.0
    adverse_fill_reserve_bps: float = 0.0
    spread_bps: float | None = None
    depth_impact_bps: float | None = None
    fee_source: str = "CONFIGURED_CONSERVATIVE_FEE_ASSUMPTION_NOT_AUTHORITATIVE"
    commission_authoritative: bool = False
    commission_symbol: str | None = None
    commission_snapshot_id: str | None = None
    commission_fetched_at: str | None = None
    entry_liquidity_role: str = "TAKER"
    exit_liquidity_role: str = "TAKER"
    bnb_discount_state: str = "NOT_APPLICABLE"
    special_commission_state: str = "NOT_APPLICABLE"
    tax_commission_state: str = "NOT_APPLICABLE"
    cost_policy_version: str = "scalping-round-trip-net-pnl-v2"
    spread_source: str | None = None
    depth_impact_source: str | None = None
    spread_authoritative: bool = False
    depth_authoritative: bool = False
    bid: float | None = None
    ask: float | None = None
    buy_vwap: float | None = None
    sell_vwap: float | None = None
    economic_input_timestamp_ms: int | None = None
    economic_capture_started_at_ms: int | None = None
    decision_cutoff_timestamp_ms: int | None = None
    economic_input_source: str | None = None
    reference_quantity: float | None = None
    reference_notional: float | None = None
    maximum_age_ms: int = 5_000
    require_causal_timestamp: bool = False
    connection_generation: int = 0
    market_source_status: str = "NOT_EVALUATED"
    fee_source_status: str = "NOT_EVALUATED"
    book_source_status: str = "NOT_EVALUATED"
    cost_model_status: str = "NOT_READY"
    last_success_at: str | None = None
    last_failure_at: str | None = None
    recovered_at: str | None = None
    rehydration_duration_ms: float | None = None
    fee_watermark: str | None = None
    fee_authorization_valid_until: str | None = None
    commission_snapshot_age_seconds: float | None = None
    commission_provenance: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        values = (
            self.entry_fee_bps, self.exit_fee_bps, self.entry_slippage_bps,
            self.exit_slippage_bps, self.safety_margin_bps,
            self.adverse_fill_reserve_bps,
        )
        if any(not isfinite(float(value)) or float(value) < 0 for value in values):
            raise ValueError("cost components must be finite and non-negative")
        optional_prices = (
            self.bid, self.ask, self.buy_vwap, self.sell_vwap,
            self.reference_quantity, self.reference_notional,
        )
        if any(value is not None and (not isfinite(float(value)) or float(value) <= 0)
               for value in optional_prices):
            raise ValueError("economic prices must be positive and finite")
        if self.bid is not None and self.ask is not None and self.ask <= self.bid:
            raise ValueError("economic bid/ask geometry is invalid")
        if self.maximum_age_ms <= 0:
            raise ValueError("maximum_age_ms must be positive")

    @property
    def economic_input_age_ms(self) -> int | None:
        if self.economic_input_timestamp_ms is None or self.decision_cutoff_timestamp_ms is None:
            return None
        return self.decision_cutoff_timestamp_ms - self.economic_input_timestamp_ms

    @property
    def causally_usable(self) -> bool:
        age = self.economic_input_age_ms
        return bool(
            self.spread_authoritative and self.depth_authoritative
            and age is not None and 0 <= age <= self.maximum_age_ms
        )


@dataclass(frozen=True, slots=True)
class ShadowGeometryCandidate:
    trade_profile_id: str
    symbol: str
    boundary_ms: int
    direction: str
    entry: float
    causal_invalidation: float | None
    atr: float | None
    targets: tuple[CausalTarget, ...] = ()
    setup_identity: str | None = None
    structural_setup: bool = True
    strategy_admitted: bool = True
    repeat_candidate: bool = False
    regime_consistent: bool = True
    direction_consistent: bool = True

    def __post_init__(self) -> None:
        if self.trade_profile_id != V2_PROFILE_ID:
            raise ValueError("scalping evaluator accepts only trade-5m-v2")
        if self.direction not in {"BULLISH", "BEARISH"}:
            raise ValueError("direction must be BULLISH or BEARISH")
        if not isfinite(float(self.entry)) or self.entry <= 0:
            raise ValueError("entry must be positive and finite")

    @property
    def candidate_id(self) -> str:
        raw = f"{self.trade_profile_id}:{self.symbol.upper()}:{self.boundary_ms}:{self.direction}"
        return f"shadow-geometry:{sha256(raw.encode()).hexdigest()[:20]}"

    @property
    def opportunity_id(self) -> str:
        # This is the stable causal family identity. Boundary-specific target
        # and stop evolution belongs in the churn timeline and must not create
        # a new opportunity on every adjacent candle.
        raw = (
            f"{self.trade_profile_id}:{self.symbol.upper()}:{self.direction}:"
            f"{self.setup_identity or 'UNKNOWN_SETUP'}"
        )
        return f"opportunity:{sha256(raw.encode()).hexdigest()[:24]}"


@dataclass(frozen=True, slots=True)
class ShadowGeometryConfig:
    atr_buffer_multiplier: float
    stop_envelope_bps: float
    minimum_target_diagnostic_bps: float
    minimum_positive_edge_bps: float = 1.0
    production_rr_floor: float = 1.5
    max_depth_impact_bps: float = 20.0
    minimum_net_edge_shadow_cohorts_bps: tuple[float, ...] = (10.0, 15.0, 20.0)
    rr_shadow_cohorts: tuple[float, ...] = (1.0, 1.2, 1.5)
    profile_id: str = V2_PROFILE_ID
    empirical_bucket: EmpiricalSetupBucket | None = None
    parent_buckets: tuple[EmpiricalSetupBucket, ...] = ()
    minimum_empirical_samples: int = 20
    minimum_expected_value_bps: float = 0.0
    minimum_positive_ev_r: float = 0.0
    minimum_ev_reserve_r: float = 0.0

    def __post_init__(self) -> None:
        if self.atr_buffer_multiplier not in {0.25, 0.5, 0.75, 1.0}:
            raise ValueError("ATR multiplier is outside the declared shadow cohorts")
        if self.stop_envelope_bps not in {50.0, 65.0, 80.0}:
            raise ValueError("stop envelope is outside the declared shadow cohorts")
        if self.minimum_target_diagnostic_bps not in {45.0, 60.0, 80.0}:
            raise ValueError("target diagnostic is outside the declared shadow cohorts")
        if not isfinite(float(self.minimum_positive_edge_bps)) or self.minimum_positive_edge_bps < 0:
            raise ValueError("minimum positive edge must be finite and non-negative")
        if self.profile_id != V2_PROFILE_ID:
            raise ValueError("scalping geometry config accepts only trade-5m-v2")
        if self.production_rr_floor not in {0.2, 0.4, 0.6}:
            raise ValueError("v2 RR floor must be a declared dynamic cohort")
        if self.minimum_net_edge_shadow_cohorts_bps != (10.0, 15.0, 20.0):
            raise ValueError("minimum net-edge cohorts must be 10/15/20 bps")
        if self.rr_shadow_cohorts != (1.0, 1.2, 1.5):
            raise ValueError("RR cohorts must be 1.0/1.2/1.5")


@dataclass(slots=True)
class ShadowGeometryDiagnostic:
    trade_profile_id: str
    symbol: str
    boundary: int
    candidate_id: str
    opportunity_id: str
    entry: float
    causal_invalidation: float | None = None
    causal_invalidation_distance_bps: float | None = None
    atr: float | None = None
    atr_buffer_multiplier: float | None = None
    atr_buffer_bps: float | None = None
    raw_stop: float | None = None
    final_stop: float | None = None
    stop_distance_bps: float | None = None
    stop_envelope_bps: float | None = None
    stop_envelope_pass: bool | None = None
    target_source_type: str | None = None
    causal_target: float | None = None
    target_distance_bps: float | None = None
    target_available: bool = False
    causal_target_exists: bool = False
    economically_actionable_target_exists: bool = False
    minimum_positive_edge_bps: float | None = None
    minimum_actionable_target_bps: float | None = None
    minimum_economically_valid_target_bps: float | None = None
    minimum_economically_valid_target_price: float | None = None
    geometry_feasibility_result: str | None = None
    target_considerations: list[dict[str, object]] = field(default_factory=list)
    target_candidates_considered: int = 0
    first_causal_target: dict[str, object] | None = None
    first_actionable_target: dict[str, object] | None = None
    next_target_considered: str | None = None
    minimum_target_diagnostic_bps: float | None = None
    minimum_target_diagnostic_pass: bool | None = None
    gross_reward_bps: float | None = None
    gross_risk_bps: float | None = None
    gross_rr: float | None = None
    entry_fee_bps: float | None = None
    exit_fee_bps: float | None = None
    spread_bps: float | None = None
    entry_slippage_bps: float | None = None
    exit_slippage_bps: float | None = None
    depth_impact_bps: float | None = None
    safety_margin_bps: float | None = None
    adverse_fill_reserve_bps: float | None = None
    total_cost_bps: float | None = None
    effective_total_cost_bps: float | None = None
    expected_net_edge_bps: float | None = None
    net_reward_bps: float | None = None
    effective_risk_bps: float | None = None
    net_rr: float | None = None
    break_even_win_rate: float | None = None
    empirical_win_probability: float | None = None
    expected_value_bps: float | None = None
    expectancy_gate_reason: str | None = None
    p_win_raw: float | None = None
    p_win_adjusted: float | None = None
    p_win_conservative: float | None = None
    estimated_p_win: float | None = None
    conservative_p_win: float | None = None
    probability_bucket: str | None = None
    probability_sample_size: int = 0
    probability_parent_sample_size: int = 0
    probability_fallback_level: str | None = None
    probability_confidence_method: str | None = None
    probability_estimator_version: str | None = None
    dynamic_required_net_rr: float | None = None
    break_even_net_rr: float | None = None
    candidate_net_rr: float | None = None
    expected_ev_r: float | None = None
    min_required_ev: float | None = None
    ev_reserve: float | None = None
    admission_decision: str | None = None
    admission_reason: str | None = None
    fee_source: str | None = None
    commission_authoritative: bool = False
    commission_symbol: str | None = None
    commission_snapshot_id: str | None = None
    commission_fetched_at: str | None = None
    entry_liquidity_role: str | None = None
    exit_liquidity_role: str | None = None
    round_trip_commission_bps: float | None = None
    bnb_discount_state: str | None = None
    special_commission_state: str | None = None
    tax_commission_state: str | None = None
    cost_policy_version: str | None = None
    spread_source: str | None = None
    depth_impact_source: str | None = None
    bid: float | None = None
    ask: float | None = None
    buy_vwap: float | None = None
    sell_vwap: float | None = None
    economic_input_timestamp_ms: int | None = None
    economic_capture_started_at_ms: int | None = None
    decision_cutoff_timestamp_ms: int | None = None
    economic_input_age_ms: int | None = None
    economic_input_source: str | None = None
    reference_quantity: float | None = None
    reference_notional: float | None = None
    connection_generation: int = 0
    market_source_status: str = "NOT_EVALUATED"
    fee_source_status: str = "NOT_EVALUATED"
    book_source_status: str = "NOT_EVALUATED"
    cost_model_status: str = "NOT_READY"
    last_success_at: str | None = None
    last_failure_at: str | None = None
    recovered_at: str | None = None
    rehydration_duration_ms: float | None = None
    fee_watermark: str | None = None
    fee_authorization_valid_until: str | None = None
    commission_snapshot_age_seconds: float | None = None
    commission_provenance: dict[str, object] = field(default_factory=dict)
    economic_gate_enabled: bool = True
    economic_gate_pass: bool = False
    rr_cohorts_gross: dict[str, bool] = field(default_factory=dict)
    rr_cohorts_net: dict[str, bool] = field(default_factory=dict)
    net_edge_cohorts: dict[str, bool] = field(default_factory=dict)
    rejection_stage: str | None = None
    rejection_reason: str | None = None
    raw_reason: str | None = None
    valid_plan: bool = False
    final_shadow_approval: bool = False
    execution_eligible: bool = False
    required_rr: float | None = None
    geometry_calculation_version: str = GEOMETRY_CALCULATION_VERSION
    cost_model_version: str = COST_MODEL_VERSION
    rr_policy_version: str = RR_POLICY_VERSION
    target_policy_version: str = TARGET_POLICY_VERSION
    price_normalization_quantum: str = str(PAPER_PRICE_QUANTUM)

    def reject(self, stage: str, reason: str) -> "ShadowGeometryDiagnostic":
        self.rejection_stage = stage
        self.rejection_reason = reason
        self.raw_reason = reason
        return self

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _bps(distance: float, entry: float) -> float:
    return round(abs(distance) / entry * 10_000.0, 8)


def _normalized_price(
    price: float, *, direction: str, role: str
) -> float:
    """Normalize conservatively to the PAPER execution storage quantum.

    Stop rounding may only move away from entry; target rounding may only move
    toward entry.  Neither operation can manufacture a better RR.
    """

    value = Decimal(str(price))
    if role == "STOP":
        rounding = ROUND_DOWN if direction == "BULLISH" else ROUND_UP
    elif role == "TARGET":
        rounding = ROUND_DOWN if direction == "BULLISH" else ROUND_UP
    else:
        raise ValueError("unsupported price normalization role")
    return float(value.quantize(PAPER_PRICE_QUANTUM, rounding=rounding))


def compute_net_economics(
    *, gross_reward_bps: float, gross_risk_bps: float, total_cost_bps: float
) -> tuple[float, float, float | None]:
    """Authoritative round-trip net-PnL semantics used by construction/gate."""

    values = (gross_reward_bps, gross_risk_bps, total_cost_bps)
    if any(not isfinite(float(value)) or float(value) < 0 for value in values):
        raise ValueError("invalid cost-model input")
    if gross_risk_bps <= 0:
        raise ValueError("gross risk must be positive")
    net_reward = round(gross_reward_bps - total_cost_bps, 8)
    net_risk = round(gross_risk_bps + total_cost_bps, 8)
    net_rr = None if net_reward <= 0 else round(net_reward / net_risk, 8)
    return net_reward, net_risk, net_rr


def minimum_reward_bps_for_net_rr(
    *, gross_risk_bps: float, total_cost_bps: float, required_net_rr: float
) -> float:
    """Return the gross target distance required by the net-PnL equation."""

    if (
        not isfinite(float(required_net_rr))
        or required_net_rr <= 0
        or not isfinite(float(gross_risk_bps))
        or gross_risk_bps <= 0
        or not isfinite(float(total_cost_bps))
        or total_cost_bps < 0
    ):
        raise ValueError("invalid minimum-target input")
    return round(
        total_cost_bps + required_net_rr * (gross_risk_bps + total_cost_bps),
        8,
    )


def minimum_target_price_for_net_rr(
    *, entry: float, direction: str, minimum_reward_bps: float
) -> float:
    distance = entry * minimum_reward_bps / 10_000.0
    raw = entry + distance if direction == "BULLISH" else entry - distance
    return _normalized_price(raw, direction=direction, role="TARGET")


def _causal_targets(candidate: ShadowGeometryCandidate) -> list[CausalTarget]:
    def favorable(target: CausalTarget) -> bool:
        return target.price > candidate.entry if candidate.direction == "BULLISH" else target.price < candidate.entry

    known = [
        target for target in candidate.targets
        if target.known_at_ms <= candidate.boundary_ms
        and target.validated and target.relevant and target.achievable and favorable(target)
    ]
    # Traverse every distinct causal level in hierarchy order. A farther
    # same-tier level is reached only after all nearer levels fail actionability.
    ordered = sorted(
        known,
        key=lambda target: (
            TARGET_PRIORITY[target.source_type], abs(target.price - candidate.entry),
            target.known_at_ms, target.source_detail or "",
        ),
    )
    selected: list[CausalTarget] = []
    seen: set[tuple[str, str, float]] = set()
    for target in ordered:
        identity = (target.source_type, target.resolved_timeframe, round(target.price, 12))
        if identity not in seen:
            seen.add(identity)
            selected.append(target)
    return selected


def _target_trace_base(
    candidate: ShadowGeometryCandidate,
    target: CausalTarget,
    index: int,
) -> dict[str, object]:
    future_safe = target.known_at_ms <= candidate.boundary_ms
    direction_valid = (
        target.price > candidate.entry
        if candidate.direction == "BULLISH"
        else target.price < candidate.entry
    )
    causal_valid = bool(target.validated and future_safe)
    still_relevant = bool(target.relevant and target.achievable)
    reason = None
    if not future_safe:
        reason = "FUTURE_TARGET"
    elif not target.validated:
        reason = "TARGET_NOT_VALIDATED"
    elif not direction_valid:
        reason = "WRONG_DIRECTION"
    elif not target.relevant:
        reason = "TARGET_NOT_RELEVANT"
    elif not target.achievable:
        reason = "TARGET_NOT_REACHABLE_WITHIN_SCALP_HORIZON"
    return {
        "target_candidate_index": index,
        "target_source": target.source_type,
        "source_type": target.source_type,
        "target_timeframe": target.resolved_timeframe,
        "target_price": target.price,
        "price": target.price,
        "target_distance_bps": _bps(target.price - candidate.entry, candidate.entry),
        "distance_bps": _bps(target.price - candidate.entry, candidate.entry),
        "causal_valid": causal_valid,
        "causal": causal_valid,
        "future_safe": future_safe,
        "direction_valid": direction_valid,
        "directionally_valid": direction_valid,
        "still_relevant": still_relevant,
        "transaction_cost_floor_bps": None,
        "gross_rr": None,
        "expected_net_edge_bps": None,
        "net_rr": None,
        "actionable": False,
        "economically_actionable": False,
        "reject_reason": reason,
        "rejection_reason": reason,
        "source_detail": target.source_detail,
    }


def evaluate_scalping_shadow(
    candidate: ShadowGeometryCandidate,
    costs: ShadowCostInputs,
    config: ShadowGeometryConfig,
) -> ShadowGeometryDiagnostic:
    """Evaluate in causal order and preserve every value known before rejection."""
    result = ShadowGeometryDiagnostic(
        trade_profile_id=candidate.trade_profile_id,
        symbol=candidate.symbol.upper(), boundary=candidate.boundary_ms,
        candidate_id=candidate.candidate_id, entry=candidate.entry,
        opportunity_id=candidate.opportunity_id,
        causal_invalidation=candidate.causal_invalidation, atr=candidate.atr,
        atr_buffer_multiplier=config.atr_buffer_multiplier,
        stop_envelope_bps=config.stop_envelope_bps,
        minimum_target_diagnostic_bps=config.minimum_target_diagnostic_bps,
        minimum_positive_edge_bps=config.minimum_positive_edge_bps,
        entry_fee_bps=costs.entry_fee_bps,
        exit_fee_bps=costs.exit_fee_bps,
        entry_slippage_bps=costs.entry_slippage_bps,
        exit_slippage_bps=costs.exit_slippage_bps,
        safety_margin_bps=costs.safety_margin_bps,
        adverse_fill_reserve_bps=costs.adverse_fill_reserve_bps,
        spread_bps=costs.spread_bps,
        depth_impact_bps=costs.depth_impact_bps,
        fee_source=costs.fee_source,
        commission_authoritative=costs.commission_authoritative,
        commission_symbol=costs.commission_symbol,
        commission_snapshot_id=costs.commission_snapshot_id,
        commission_fetched_at=costs.commission_fetched_at,
        entry_liquidity_role=costs.entry_liquidity_role,
        exit_liquidity_role=costs.exit_liquidity_role,
        round_trip_commission_bps=costs.entry_fee_bps + costs.exit_fee_bps,
        bnb_discount_state=costs.bnb_discount_state,
        special_commission_state=costs.special_commission_state,
        tax_commission_state=costs.tax_commission_state,
        cost_policy_version=costs.cost_policy_version,
        spread_source=costs.spread_source,
        depth_impact_source=costs.depth_impact_source,
        bid=costs.bid,
        ask=costs.ask,
        buy_vwap=costs.buy_vwap,
        sell_vwap=costs.sell_vwap,
        economic_input_timestamp_ms=costs.economic_input_timestamp_ms,
        economic_capture_started_at_ms=costs.economic_capture_started_at_ms,
        decision_cutoff_timestamp_ms=costs.decision_cutoff_timestamp_ms,
        economic_input_age_ms=costs.economic_input_age_ms,
        economic_input_source=costs.economic_input_source,
        reference_quantity=costs.reference_quantity,
        reference_notional=costs.reference_notional,
        connection_generation=costs.connection_generation,
        market_source_status=costs.market_source_status,
        fee_source_status=costs.fee_source_status,
        book_source_status=costs.book_source_status,
        cost_model_status=costs.cost_model_status,
        last_success_at=costs.last_success_at,
        last_failure_at=costs.last_failure_at,
        recovered_at=costs.recovered_at,
        rehydration_duration_ms=costs.rehydration_duration_ms,
        fee_watermark=costs.fee_watermark,
        fee_authorization_valid_until=costs.fee_authorization_valid_until,
        commission_snapshot_age_seconds=costs.commission_snapshot_age_seconds,
        commission_provenance=dict(costs.commission_provenance),
        required_rr=config.production_rr_floor,
        rr_policy_version=(V2_RR_EV_POLICY_VERSION if config.profile_id == V2_PROFILE_ID else RR_POLICY_VERSION),
        target_policy_version=(V2_TARGET_POLICY_VERSION if config.profile_id == V2_PROFILE_ID else TARGET_POLICY_VERSION),
    )
    invalidation = candidate.causal_invalidation
    if invalidation is None:
        return result.reject("CAUSAL_INVALIDATION", R.PAPER_NO_PLAN_MISSING_INVALIDATION_LEVEL.value)
    correct_side = invalidation < candidate.entry if candidate.direction == "BULLISH" else invalidation > candidate.entry
    if not correct_side:
        return result.reject("CAUSAL_INVALIDATION", R.PAPER_REJECT_INVALID_LEVEL_GEOMETRY.value)
    result.causal_invalidation_distance_bps = _bps(invalidation - candidate.entry, candidate.entry)
    if candidate.atr is None or not isfinite(float(candidate.atr)) or candidate.atr < 0:
        return result.reject("ATR_BUFFER", R.PAPER_NO_PLAN_MISSING_STOP_LEVEL.value)
    buffer = candidate.atr * config.atr_buffer_multiplier
    result.atr_buffer_bps = _bps(buffer, candidate.entry)
    stop = invalidation - buffer if candidate.direction == "BULLISH" else invalidation + buffer
    result.raw_stop = stop
    result.final_stop = _normalized_price(
        stop, direction=candidate.direction, role="STOP"
    )  # never clipped toward entry to satisfy an envelope
    result.stop_distance_bps = _bps(
        result.final_stop - candidate.entry, candidate.entry
    )
    result.gross_risk_bps = result.stop_distance_bps
    result.stop_envelope_pass = result.stop_distance_bps <= config.stop_envelope_bps
    if not result.stop_envelope_pass:
        return result.reject(
            "STOP_ENVELOPE", R.SCALP_REJECT_CAUSAL_STOP_TOO_WIDE.value
        )

    trace_targets = sorted(
        candidate.targets,
        key=lambda target: (
            TARGET_PRIORITY[target.source_type], abs(target.price - candidate.entry),
            target.known_at_ms, target.source_detail or "",
        ),
    )
    result.target_considerations = [
        _target_trace_base(candidate, target, index)
        for index, target in enumerate(trace_targets)
    ]
    result.target_candidates_considered = len(result.target_considerations)
    trace_by_identity = {
        (item["target_source"], item["target_timeframe"], item["target_price"]): item
        for item in result.target_considerations
    }
    targets = _causal_targets(candidate)
    if not targets:
        return result.reject("CAUSAL_TARGET", R.PAPER_NO_PLAN_MISSING_TARGET_LEVEL.value)
    result.causal_target_exists = True
    result.target_available = True
    nearest = targets[0]
    result.first_causal_target = dict(
        trace_by_identity[(nearest.source_type, nearest.resolved_timeframe, nearest.price)]
    )
    result.target_source_type = nearest.source_type
    result.causal_target = nearest.price
    result.target_distance_bps = _bps(nearest.price - candidate.entry, candidate.entry)
    result.minimum_target_diagnostic_pass = result.target_distance_bps >= config.minimum_target_diagnostic_bps

    if costs.spread_bps is None or not costs.spread_authoritative:
        return result.reject(
            "NET_COST_GATE", R.PAPER_NO_PLAN_MISSING_AUTHORITATIVE_SPREAD.value
        )
    if costs.depth_impact_bps is None or not costs.depth_authoritative:
        return result.reject("NET_COST_GATE", R.PAPER_NO_PLAN_MISSING_DEPTH_IMPACT.value)
    if candidate.trade_profile_id == V2_PROFILE_ID and not costs.commission_authoritative:
        return result.reject(
            "NET_COST_GATE", "PAPER_NO_PLAN_NON_AUTHORITATIVE_COMMISSION"
        )
    if costs.require_causal_timestamp and not costs.causally_usable:
        return result.reject("NET_COST_GATE", "PAPER_NO_PLAN_STALE_OR_FUTURE_ECONOMIC_INPUT")
    if costs.spread_bps < 0 or costs.depth_impact_bps < 0:
        return result.reject("NET_COST_GATE", R.PAPER_REJECT_INVALID_LEVEL_GEOMETRY.value)
    if costs.depth_impact_bps > config.max_depth_impact_bps:
        return result.reject("NET_COST_GATE", R.PAPER_REJECT_DEPTH_IMPACT_TOO_HIGH.value)

    total_cost = (
        costs.entry_fee_bps + costs.exit_fee_bps + costs.entry_slippage_bps
        + costs.exit_slippage_bps + costs.spread_bps + costs.depth_impact_bps
        + costs.safety_margin_bps + costs.adverse_fill_reserve_bps
    )
    result.total_cost_bps = round(total_cost, 8)
    result.effective_total_cost_bps = result.total_cost_bps
    result.minimum_actionable_target_bps = round(
        total_cost + config.minimum_positive_edge_bps, 8
    )
    try:
        result.minimum_economically_valid_target_bps = (
            minimum_reward_bps_for_net_rr(
                gross_risk_bps=result.gross_risk_bps,
                total_cost_bps=total_cost,
                required_net_rr=config.production_rr_floor,
            )
        )
        result.minimum_economically_valid_target_price = (
            minimum_target_price_for_net_rr(
                entry=candidate.entry,
                direction=candidate.direction,
                minimum_reward_bps=result.minimum_economically_valid_target_bps,
            )
        )
    except ValueError:
        return result.reject("COST_MODEL", R.COST_MODEL_INVALID.value)

    selected: tuple[CausalTarget, float, float, float, float, float] | None = None
    for index, target in enumerate(targets):
        normalized_target = _normalized_price(
            target.price, direction=candidate.direction, role="TARGET"
        )
        reward = _bps(normalized_target - candidate.entry, candidate.entry)
        gross_rr = round(reward / result.gross_risk_bps, 8)
        try:
            edge, effective_risk, net_rr = compute_net_economics(
                gross_reward_bps=reward,
                gross_risk_bps=result.gross_risk_bps,
                total_cost_bps=total_cost,
            )
        except ValueError:
            return result.reject("COST_MODEL", R.COST_MODEL_INVALID.value)
        result.effective_risk_bps = effective_risk
        result.target_source_type = target.source_type
        result.causal_target = normalized_target
        result.target_distance_bps = reward
        result.gross_reward_bps = reward
        result.gross_rr = gross_rr
        result.expected_net_edge_bps = edge
        result.net_reward_bps = edge
        result.net_rr = net_rr
        result.break_even_win_rate = (
            None if net_rr is None else round(
                result.effective_risk_bps / (result.effective_risk_bps + edge), 8
            )
        )
        result.economic_gate_pass = edge >= config.minimum_positive_edge_bps
        result.rr_cohorts_gross = {
            f"{rr:.2f}": gross_rr >= rr for rr in config.rr_shadow_cohorts
        }
        result.rr_cohorts_net = {
            f"{rr:.2f}": net_rr is not None and net_rr >= rr
            for rr in config.rr_shadow_cohorts
        }
        result.net_edge_cohorts = {
            f"{threshold:.2f}": edge > threshold
            for threshold in config.minimum_net_edge_shadow_cohorts_bps
        }
        edge_pass = (
            edge > 0
            if config.minimum_positive_edge_bps == 0
            else edge >= config.minimum_positive_edge_bps
        )
        actionable = (
            reward > total_cost
            and edge_pass
            and net_rr is not None
            and net_rr >= config.production_rr_floor
        )
        reason = None
        if reward <= total_cost or not edge_pass:
            reason = "BELOW_ECONOMIC_FLOOR"
        elif net_rr is None or net_rr < config.production_rr_floor:
            reason = "BELOW_REQUIRED_NET_RR"
        trace = trace_by_identity[(target.source_type, target.resolved_timeframe, target.price)]
        trace.update({
            "transaction_cost_floor_bps": result.minimum_actionable_target_bps,
            "gross_rr": gross_rr,
            "expected_net_edge_bps": edge,
            "net_rr": net_rr,
            "actionable": actionable,
            "economically_actionable": actionable,
            "reject_reason": reason,
            "rejection_reason": reason,
        })
        if index == 0:
            result.first_causal_target = dict(trace)
        if index + 1 < len(targets):
            trace["next_target_considered"] = targets[index + 1].source_type
        if actionable:
            result.first_actionable_target = dict(trace)
            selected = (
                target, normalized_target, reward, edge, gross_rr, net_rr
            )
            break

    if selected is None:
        result.next_target_considered = None
        result.geometry_feasibility_result = "INFEASIBLE"
        return result.reject(
            "ECONOMIC_GEOMETRY",
            R.ECONOMIC_GEOMETRY_NOT_FEASIBLE.value,
        )

    target, normalized_target, reward, edge, gross_rr, net_rr = selected
    result.economically_actionable_target_exists = True
    result.geometry_feasibility_result = "FEASIBLE"
    result.target_source_type = target.source_type
    result.causal_target = normalized_target
    result.target_distance_bps = reward
    result.gross_reward_bps = reward
    result.gross_rr = gross_rr
    result.expected_net_edge_bps = edge
    result.net_reward_bps = edge
    result.net_rr = net_rr
    result.break_even_win_rate = round(
        result.effective_risk_bps / (result.effective_risk_bps + result.net_reward_bps), 8
    )
    expectancy = evaluate_expectancy(
        net_win_bps=result.net_reward_bps,
        net_loss_bps=result.effective_risk_bps,
        bucket=config.empirical_bucket,
        parent_buckets=config.parent_buckets,
        minimum_samples=config.minimum_empirical_samples,
        minimum_expected_value_bps=config.minimum_expected_value_bps,
        minimum_positive_ev_r=config.minimum_positive_ev_r,
        minimum_ev_reserve_r=config.minimum_ev_reserve_r,
        static_net_rr=result.net_rr,
        static_minimum_net_rr=config.production_rr_floor,
    ) if config.profile_id == V2_PROFILE_ID else None
    if expectancy is not None:
        result.empirical_win_probability = expectancy.probability
        result.p_win_raw = expectancy.p_win_raw
        result.p_win_adjusted = expectancy.p_win_adjusted
        result.p_win_conservative = expectancy.p_win_conservative
        result.estimated_p_win = expectancy.p_win_adjusted
        result.conservative_p_win = expectancy.p_win_conservative
        result.probability_bucket = expectancy.bucket_key
        result.probability_sample_size = expectancy.sample_size
        result.probability_parent_sample_size = expectancy.parent_sample_size
        result.probability_fallback_level = expectancy.fallback_level
        result.probability_confidence_method = expectancy.confidence_method
        result.probability_estimator_version = expectancy.estimator_version
        result.dynamic_required_net_rr = expectancy.dynamic_required_net_rr
        result.break_even_net_rr = (
            None if expectancy.p_win_conservative in (None, 0)
            else (1 - expectancy.p_win_conservative) / expectancy.p_win_conservative
        )
        result.candidate_net_rr = expectancy.candidate_net_rr
        result.expected_ev_r = expectancy.expected_ev_r
        result.min_required_ev = config.minimum_positive_ev_r
        result.ev_reserve = expectancy.ev_reserve
        result.admission_decision = "PASS" if expectancy.admitted else "REJECT"
        result.admission_reason = expectancy.reason
        result.expected_value_bps = expectancy.expected_value_bps
        result.expectancy_gate_reason = expectancy.reason
        if not expectancy.admitted:
            return result.reject("EXPECTANCY_GATE", "SCALPING_EMPIRICAL_EXPECTANCY_REJECTED")
    result.economic_gate_pass = True
    result.rr_cohorts_gross = {
        f"{rr:.2f}": result.gross_rr >= rr for rr in config.rr_shadow_cohorts
    }
    result.rr_cohorts_net = {
        f"{rr:.2f}": result.net_rr >= rr for rr in config.rr_shadow_cohorts
    }
    # Residual gate recomputes exactly the same economics after normalization.
    if result.net_rr < config.production_rr_floor:
        rr_reason = "POST_NORMALIZATION_NET_RR_BELOW_POLICY"
        if result.first_actionable_target is not None:
            result.first_actionable_target["reject_reason"] = rr_reason
            result.first_actionable_target["rejection_reason"] = rr_reason
        for trace in result.target_considerations:
            if trace.get("target_price") == target.price and trace.get("actionable"):
                trace["reject_reason"] = rr_reason
                trace["rejection_reason"] = rr_reason
        return result.reject(
            "RR_GATE",
            R.PRECISION_NORMALIZATION_INVALIDATED_RR.value,
        )
    result.valid_plan = True
    result.final_shadow_approval = True
    return result


def _percentile90(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, int(0.9 * len(ordered) + 0.999999) - 1)]


def summarize_shadow_configuration(
    diagnostics: Iterable[ShadowGeometryDiagnostic],
) -> dict[str, object]:
    rows = list(diagnostics)
    reasons = [row.rejection_reason for row in rows]
    numeric = lambda name: [float(value) for row in rows if (value := getattr(row, name)) is not None]
    stop_values = numeric("stop_distance_bps")
    return {
        "analyzed": len(rows),
        "structural_setups": len(rows),
        "strategy_admitted": len(rows),
        "geometry_valid": sum(row.stop_envelope_pass is True and row.target_available for row in rows),
        "actionable_targets": sum(row.economically_actionable_target_exists for row in rows),
        "stop_too_wide": reasons.count(R.PAPER_NO_PLAN_CAUSAL_STOP_TOO_WIDE_FOR_PROFILE.value),
        "missing_target": reasons.count(R.PAPER_NO_PLAN_MISSING_TARGET_LEVEL.value),
        "no_actionable_target": reasons.count(
            R.PAPER_NO_PLAN_TARGET_NOT_ECONOMICALLY_ACTIONABLE.value
        ),
        "cost_gate_passed": sum(row.economic_gate_pass for row in rows),
        "gross_rr_ge_threshold": sum(row.rr_cohorts_gross.get("1.50", False) for row in rows),
        "net_rr_ge_threshold": sum(row.rr_cohorts_net.get("1.50", False) for row in rows),
        "valid_plans": sum(row.valid_plan for row in rows),
        "final_shadow_approvals": sum(row.final_shadow_approval for row in rows),
        "median_stop_distance_bps": median(stop_values) if stop_values else None,
        "p90_stop_distance_bps": _percentile90(stop_values),
        "median_target_distance_bps": median(numeric("target_distance_bps")) if numeric("target_distance_bps") else None,
        "median_gross_rr": median(numeric("gross_rr")) if numeric("gross_rr") else None,
        "median_net_rr": median(numeric("net_rr")) if numeric("net_rr") else None,
        "median_expected_net_edge_bps": median(numeric("expected_net_edge_bps")) if numeric("expected_net_edge_bps") else None,
        "median_break_even_win_rate": median(numeric("break_even_win_rate")) if numeric("break_even_win_rate") else None,
    }
