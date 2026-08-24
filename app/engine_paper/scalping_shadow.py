"""Causal 5m geometry and economics for isolated/shadow evaluation only.

The module has no command, order, fill, position, or private API dependency.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from math import isfinite
from statistics import median
from typing import Iterable

from app.engine_paper.paper_reason_codes import PaperReasonCode as R


TARGET_PRIORITY = {"LOCAL_5M": 0, "STRUCTURAL": 1, "HIGHER_TF": 2}
RR_COHORTS = (1.0, 1.2, 1.5)


@dataclass(frozen=True, slots=True)
class CausalTarget:
    price: float
    source_type: str
    known_at_ms: int
    validated: bool = True
    relevant: bool = True
    achievable: bool = True

    def __post_init__(self) -> None:
        if self.source_type not in TARGET_PRIORITY:
            raise ValueError("unsupported target source type")


@dataclass(frozen=True, slots=True)
class ShadowCostInputs:
    entry_fee_bps: float = 10.0
    exit_fee_bps: float = 10.0
    entry_slippage_bps: float = 2.0
    exit_slippage_bps: float = 2.0
    safety_margin_bps: float = 3.0
    spread_bps: float | None = None
    depth_impact_bps: float | None = None
    fee_source: str = "CONFIGURED_CONSERVATIVE_FEE_ASSUMPTION"
    spread_source: str | None = None
    depth_impact_source: str | None = None
    spread_authoritative: bool = False
    depth_authoritative: bool = False

    def __post_init__(self) -> None:
        values = (
            self.entry_fee_bps, self.exit_fee_bps, self.entry_slippage_bps,
            self.exit_slippage_bps, self.safety_margin_bps,
        )
        if any(not isfinite(float(value)) or float(value) < 0 for value in values):
            raise ValueError("cost components must be finite and non-negative")


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
    structural_setup: bool = True
    strategy_admitted: bool = True
    repeat_candidate: bool = False
    regime_consistent: bool = True
    direction_consistent: bool = True

    def __post_init__(self) -> None:
        if self.trade_profile_id != "trade-5m-v1":
            raise ValueError("scalping shadow evaluator accepts only trade-5m-v1")
        if self.direction not in {"BULLISH", "BEARISH"}:
            raise ValueError("direction must be BULLISH or BEARISH")
        if not isfinite(float(self.entry)) or self.entry <= 0:
            raise ValueError("entry must be positive and finite")

    @property
    def candidate_id(self) -> str:
        raw = f"{self.trade_profile_id}:{self.symbol.upper()}:{self.boundary_ms}:{self.direction}"
        return f"shadow-geometry:{sha256(raw.encode()).hexdigest()[:20]}"


@dataclass(frozen=True, slots=True)
class ShadowGeometryConfig:
    atr_buffer_multiplier: float
    stop_envelope_bps: float
    minimum_target_diagnostic_bps: float
    production_rr_floor: float = 1.5
    max_depth_impact_bps: float = 20.0

    def __post_init__(self) -> None:
        if self.atr_buffer_multiplier not in {0.25, 0.5, 0.75, 1.0}:
            raise ValueError("ATR multiplier is outside the declared shadow cohorts")
        if self.stop_envelope_bps not in {50.0, 65.0, 80.0}:
            raise ValueError("stop envelope is outside the declared shadow cohorts")
        if self.minimum_target_diagnostic_bps not in {45.0, 60.0, 80.0}:
            raise ValueError("target diagnostic is outside the declared shadow cohorts")
        if self.production_rr_floor != 1.5:
            raise ValueError("production RR floor must remain 1.5")


@dataclass(slots=True)
class ShadowGeometryDiagnostic:
    trade_profile_id: str
    symbol: str
    boundary: int
    candidate_id: str
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
    total_cost_bps: float | None = None
    expected_net_edge_bps: float | None = None
    net_reward_bps: float | None = None
    effective_risk_bps: float | None = None
    net_rr: float | None = None
    break_even_win_rate: float | None = None
    fee_source: str | None = None
    spread_source: str | None = None
    depth_impact_source: str | None = None
    economic_gate_enabled: bool = True
    economic_gate_pass: bool = False
    rr_cohorts_gross: dict[str, bool] = field(default_factory=dict)
    rr_cohorts_net: dict[str, bool] = field(default_factory=dict)
    rejection_stage: str | None = None
    rejection_reason: str | None = None
    raw_reason: str | None = None
    valid_plan: bool = False
    final_shadow_approval: bool = False
    execution_eligible: bool = False

    def reject(self, stage: str, reason: str) -> "ShadowGeometryDiagnostic":
        self.rejection_stage = stage
        self.rejection_reason = reason
        self.raw_reason = reason
        return self

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _bps(distance: float, entry: float) -> float:
    return round(abs(distance) / entry * 10_000.0, 8)


def _select_target(candidate: ShadowGeometryCandidate) -> CausalTarget | None:
    def favorable(target: CausalTarget) -> bool:
        return target.price > candidate.entry if candidate.direction == "BULLISH" else target.price < candidate.entry

    known = [
        target for target in candidate.targets
        if target.known_at_ms <= candidate.boundary_ms
        and target.validated and target.relevant and target.achievable and favorable(target)
    ]
    if not known:
        return None
    best_priority = min(TARGET_PRIORITY[target.source_type] for target in known)
    same_tier = [target for target in known if TARGET_PRIORITY[target.source_type] == best_priority]
    return min(same_tier, key=lambda target: abs(target.price - candidate.entry))


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
        causal_invalidation=candidate.causal_invalidation, atr=candidate.atr,
        atr_buffer_multiplier=config.atr_buffer_multiplier,
        stop_envelope_bps=config.stop_envelope_bps,
        minimum_target_diagnostic_bps=config.minimum_target_diagnostic_bps,
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
    result.final_stop = stop  # never clipped toward entry to satisfy an envelope
    result.stop_distance_bps = _bps(stop - candidate.entry, candidate.entry)
    result.gross_risk_bps = result.stop_distance_bps
    result.stop_envelope_pass = result.stop_distance_bps <= config.stop_envelope_bps
    if not result.stop_envelope_pass:
        return result.reject(
            "STOP_ENVELOPE", R.PAPER_NO_PLAN_CAUSAL_STOP_TOO_WIDE_FOR_PROFILE.value
        )

    target = _select_target(candidate)
    if target is None:
        return result.reject("CAUSAL_TARGET", R.PAPER_NO_PLAN_MISSING_TARGET_LEVEL.value)
    result.target_available = True
    result.target_source_type = target.source_type
    result.causal_target = target.price
    result.target_distance_bps = _bps(target.price - candidate.entry, candidate.entry)
    result.gross_reward_bps = result.target_distance_bps
    result.minimum_target_diagnostic_pass = (
        result.target_distance_bps >= config.minimum_target_diagnostic_bps
    )
    result.gross_rr = round(result.gross_reward_bps / result.gross_risk_bps, 8)

    result.entry_fee_bps = costs.entry_fee_bps
    result.exit_fee_bps = costs.exit_fee_bps
    result.entry_slippage_bps = costs.entry_slippage_bps
    result.exit_slippage_bps = costs.exit_slippage_bps
    result.safety_margin_bps = costs.safety_margin_bps
    result.spread_bps = costs.spread_bps
    result.depth_impact_bps = costs.depth_impact_bps
    result.fee_source = costs.fee_source
    result.spread_source = costs.spread_source
    result.depth_impact_source = costs.depth_impact_source
    if costs.spread_bps is None or not costs.spread_authoritative:
        return result.reject(
            "NET_COST_GATE", R.PAPER_NO_PLAN_MISSING_AUTHORITATIVE_SPREAD.value
        )
    if costs.depth_impact_bps is None or not costs.depth_authoritative:
        return result.reject("NET_COST_GATE", R.PAPER_NO_PLAN_MISSING_DEPTH_IMPACT.value)
    if costs.spread_bps < 0 or costs.depth_impact_bps < 0:
        return result.reject("NET_COST_GATE", R.PAPER_REJECT_INVALID_LEVEL_GEOMETRY.value)
    if costs.depth_impact_bps > config.max_depth_impact_bps:
        return result.reject("NET_COST_GATE", R.PAPER_REJECT_DEPTH_IMPACT_TOO_HIGH.value)

    total_cost = (
        costs.entry_fee_bps + costs.exit_fee_bps + costs.entry_slippage_bps
        + costs.exit_slippage_bps + costs.spread_bps + costs.depth_impact_bps
        + costs.safety_margin_bps
    )
    result.total_cost_bps = round(total_cost, 8)
    result.expected_net_edge_bps = round(result.gross_reward_bps - total_cost, 8)
    result.net_reward_bps = result.expected_net_edge_bps
    result.effective_risk_bps = round(result.gross_risk_bps + total_cost, 8)
    if result.net_reward_bps <= 0:
        return result.reject("NET_COST_GATE", R.PAPER_REJECT_NEGATIVE_NET_EDGE.value)
    result.net_rr = round(result.net_reward_bps / result.effective_risk_bps, 8)
    result.break_even_win_rate = round(
        result.effective_risk_bps / (result.effective_risk_bps + result.net_reward_bps), 8
    )
    result.economic_gate_pass = True
    result.rr_cohorts_gross = {f"{rr:.2f}": result.gross_rr >= rr for rr in RR_COHORTS}
    result.rr_cohorts_net = {f"{rr:.2f}": result.net_rr >= rr for rr in RR_COHORTS}
    if result.gross_rr < config.production_rr_floor:
        return result.reject("GROSS_RR", R.PAPER_REJECT_LOW_GROSS_RR.value)
    if result.net_rr < config.production_rr_floor:
        return result.reject("NET_RR", R.PAPER_REJECT_LOW_NET_RR.value)
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
        "stop_too_wide": reasons.count(R.PAPER_NO_PLAN_CAUSAL_STOP_TOO_WIDE_FOR_PROFILE.value),
        "missing_target": reasons.count(R.PAPER_NO_PLAN_MISSING_TARGET_LEVEL.value),
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
