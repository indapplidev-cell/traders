"""Bounded read-only projection of persisted 15m and 5m trading funnels."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from threading import Lock
from time import monotonic
from typing import Any, Final

from sqlalchemy import func, select, text, tuple_
from sqlalchemy.orm import Session, load_only

from app.engine_orchestrator.orchestrator_models import OnlinePipelineResultRow, OnlinePipelineRun
from app.engine_paper.eligible_approval_ranking import (
    MULTI_SYMBOL_SELECTION_POLICY_VERSION,
    ProductionEligibleApprovalSelector,
)
from app.engine_paper.production_approval import (
    MAX_RUN_LOOKBACK,
    PaperProductionApprovalSourceAdapter,
)
from app.trading_universe.domain import TradingUniverseVersion
from app.engine_orchestrator.trade_profile import (
    DEFAULT_TRADE_PROFILE_ID,
    TradeProfileMode,
    resolve_trade_profile,
)
from app.server_api.schema_compatibility import (
    ReadonlySchemaCapability,
    ReadonlySchemaCapabilityBridge,
)
from app.db.paper_models import (
    PaperExecutionCommandRecord,
    PaperOrderRecord,
    PaperPlanExecutionOutcomeRecord,
    PaperPositionRecord,
)


PROJECTION_VERSION: Final = "trading-funnel-v1"
PRIMARY_TIMEFRAME: Final = "15m"  # legacy exports retained for callers/tests
BOUNDARY_MS: Final = 15 * 60 * 1000
MAX_HORIZON_MS: Final = 4 * 60 * 60 * 1000 + BOUNDARY_MS
TERMINAL_RUN_STATUSES: Final = frozenset({
    "COMPLETED", "SKIPPED_DUPLICATE_WINDOW", "SKIPPED_FRESHNESS_NOT_OK",
    "SKIPPED_FRESHNESS_TIMEOUT", "SKIPPED_NOT_ENOUGH_DATA", "MODULE_ERROR", "ERROR",
})
STAGES: Final = (
    "ANALYSIS", "STRUCTURAL_SETUP", "STRATEGY_ELIGIBLE", "RISK_APPROVED",
    "PAPER_TRADE_PLAN", "QUANTITY_APPROVED", "VALIDITY_APPROVED",
    "FINAL_APPROVAL", "ELIGIBLE", "SELECTOR_WINNER",
)
CANONICAL_DOWNSTREAM_STAGES: Final = (
    "ANALYSIS_QUALIFIED",
    "STRUCTURAL_SETUP",
    "STRATEGY_ADMITTED",
    "RISK_COMPATIBILITY_ADMITTED",
    "GEOMETRY_VALID",
    "TARGET_VALID",
    "NET_COST_PASS",
    "RR_PASS",
    "RISK_ADMITTED",
    "PORTFOLIO_ADMITTED",
    "FINAL_APPROVAL",
    "PAPER_PLAN",
)
ROW_CACHE_TTL_SECONDS: Final = 30.0


@dataclass(frozen=True, slots=True)
class _ShadowRanking:
    risk_score: Decimal
    planned_risk_reward: Decimal
    strategy_score: Decimal
    closed_until_ms: int
    source_run_id: str
    final_approval_id: str


@dataclass(frozen=True, slots=True)
class _ShadowLineage:
    source_run_id: str
    final_approval_id: str


@dataclass(frozen=True, slots=True)
class _ShadowEligibleCandidate:
    candidate_id: str
    symbol: str
    ranking: _ShadowRanking
    lineage: _ShadowLineage


def _ms(value: datetime | None) -> int | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return int(value.timestamp() * 1000)


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _reasons(value: object) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if item]
    return [str(value)] if value else []


def _decimal(value: object) -> Decimal | None:
    try:
        number = Decimal(str(value))
    except (ArithmeticError, TypeError, ValueError):
        return None
    return number if number.is_finite() else None


def _first_present(*values: object) -> object | None:
    return next((value for value in values if value is not None), None)


def _decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _absolute_distance(left: object, right: object) -> str | None:
    first, second = _decimal(left), _decimal(right)
    return _decimal_text(abs(first - second)) if first is not None and second is not None else None


def _sum_decimals(*values: object) -> str | None:
    numbers = tuple(_decimal(value) for value in values)
    return (
        _decimal_text(sum((value for value in numbers if value is not None), Decimal("0")))
        if numbers and all(value is not None for value in numbers)
        else None
    )


def _percent_from_bps(value: object) -> str | None:
    number = _decimal(value)
    return _decimal_text(number / Decimal("100")) if number is not None else None


def _ratio_percent(numerator: object, denominator: object) -> str | None:
    top, bottom = _decimal(numerator), _decimal(denominator)
    if top is None or bottom is None or bottom == 0:
        return None
    return _decimal_text(top / bottom * Decimal("100"))


def _product(left: object, right: object) -> str | None:
    first, second = _decimal(left), _decimal(right)
    return _decimal_text(first * second) if first is not None and second is not None else None


def _profile_screen_contexts(
    row: OnlinePipelineRun,
    result: OnlinePipelineResultRow | None,
    *,
    terminal_reason: str | None,
) -> dict[str, dict[str, Any]]:
    """Project allowlisted facts for profile-aware read-only screens."""
    if result is None:
        unavailable = {
            "profile_id": row.trade_profile_id,
            "symbol": row.symbol,
            "primary_timeframe": row.primary_timeframe,
            "boundary_closed_at_ms": row.closed_until_ms,
            "updated_at_ms": _ms(row.updated_at) or row.closed_until_ms,
            "availability_state": "UNAVAILABLE",
            "no_data_reason": row.error_code or row.final_reason or "PROFILE_DATA_UNAVAILABLE",
        }
        return {
            "profile_market": dict(unavailable),
            "profile_analysis": dict(unavailable),
            "profile_scenario": dict(unavailable),
        }

    analysis = _mapping(result.analysis_payload_json)
    analysis_context = _mapping(analysis.get("analysis_context"))
    scalping = _mapping(analysis_context.get("scalping"))
    setup = _mapping(result.setup_payload_json)
    strategy = _mapping(result.strategy_payload_json)
    risk = _mapping(result.risk_payload_json)
    paper = _mapping(result.paper_payload_json)
    diagnostic = _mapping(
        _mapping(paper.get("paper_context")).get("scalping_geometry_diagnostics")
    )
    planned = _mapping(paper.get("shadow_plan")) or paper
    entry_zone = _mapping(setup.get("entry_zone"))
    reference_price = _first_present(
        planned.get("hypothetical_entry_reference"), diagnostic.get("entry"),
        entry_zone.get("lower"), entry_zone.get("upper"),
    )
    direction = _first_present(
        setup.get("direction_hint"), strategy.get("direction_hint"),
        paper.get("paper_direction"),
    )
    updated_at_ms = _ms(result.created_at) or _ms(row.updated_at) or row.closed_until_ms
    base = {
        "profile_id": row.trade_profile_id,
        "symbol": row.symbol,
        "primary_timeframe": row.primary_timeframe,
        "boundary_closed_at_ms": row.closed_until_ms,
        "updated_at_ms": updated_at_ms,
        "availability_state": "AVAILABLE",
        "no_data_reason": None,
    }
    profile_market = {
        **base,
        "reference_price": reference_price,
        "market_state": scalping.get("market_regime") or analysis.get("regime"),
        "scenario_summary": setup.get("setup_type"),
        "strategy_summary": strategy.get("decision_status"),
        "risk_summary": risk.get("risk_status"),
        "geometry_summary": (
            "PASS" if diagnostic.get("stop_envelope_pass") is True
            else "REJECTED" if diagnostic else "NOT_REACHED"
        ),
        "terminal_reason": terminal_reason,
    }
    profile_analysis = {
        **base,
        "status": analysis.get("status") or row.analysis_status,
        "regime": scalping.get("market_regime") or analysis.get("regime"),
        "direction": direction,
        "confidence": analysis.get("confidence"),
        "structure_state": analysis.get("structure_state") or analysis_context.get("structure_state"),
        "impulse_phase": analysis.get("impulse_phase"),
        "entry_evidence_strength": scalping.get("entry_evidence_strength"),
        "entry_quality": analysis.get("entry_quality"),
        "support_level": setup.get("support_level"),
        "resistance_level": setup.get("resistance_level"),
        "breakout_level": setup.get("breakout_level"),
        "invalidation_level": _first_present(
            diagnostic.get("causal_invalidation"), paper.get("hypothetical_invalidation_level"),
        ),
        "terminal_reason": terminal_reason,
    }
    setup_status = setup.get("setup_status") or setup.get("status")
    profile_scenario = {
        **base,
        "scenario_type": setup.get("scenario") or setup.get("setup_type"),
        "status": setup_status,
        "quality": setup.get("setup_quality"),
        "quality_score": setup.get("quality_score"),
        "direction": direction,
        "terminal_reason": terminal_reason,
        "entry_context": setup.get("entry_zone"),
        "invalidation_level": _first_present(
            diagnostic.get("causal_invalidation"), paper.get("hypothetical_invalidation_level"),
        ),
        "target_source": diagnostic.get("target_source_type"),
    }
    if setup_status in {None, "NO_SETUP"}:
        profile_scenario["no_data_reason"] = terminal_reason or "NO_STRUCTURAL_SCENARIO"
    return {
        "profile_market": profile_market,
        "profile_analysis": profile_analysis,
        "profile_scenario": profile_scenario,
    }


def _first_reason(row: OnlinePipelineRun, result: OnlinePipelineResultRow | None) -> str | None:
    if row.error_code:
        return row.error_code
    if result is not None:
        shadow_generation = _mapping(
            _mapping(result.paper_payload_json).get("shadow_final_approval_generation")
        )
        if shadow_generation.get("outcome") not in (
            None, "SHADOW_FINAL_APPROVAL_CREATED", "NOT_ELIGIBLE"
        ):
            return str(
                shadow_generation.get("reason_code")
                or shadow_generation["outcome"]
            )
        generation = _mapping(_mapping(result.paper_payload_json).get("final_approval_generation"))
        if generation.get("outcome") not in (None, "FINAL_APPROVAL_CREATED", "NOT_ELIGIBLE"):
            return str(generation.get("reason_code") or generation["outcome"])
        reasons = _mapping(result.module_reasons_json)
        for stage in ("paper", "risk", "strategy", "setup", "analysis"):
            values = _reasons(reasons.get(stage))
            if values:
                return values[0]
    return row.final_reason


def _status_from_legacy(value: str) -> str:
    return {
        "PASS": "PASS",
        "PENDING": "PENDING",
        "DEFERRED": "DEFERRED",
        "ERROR": "ERROR",
        "REJECTED": "REJECTED",
    }.get(value, "NOT_REACHED")


def _downstream_trace(
    result: OnlinePipelineResultRow | None,
    legacy_trace: Mapping[str, str],
    *,
    scalping: bool,
    now_ms: int | None = None,
    include_detail: bool = True,
) -> tuple[dict[str, str], dict[str, Any]]:
    """Return the server-authoritative downstream observability projection.

    The projection deliberately does not reinterpret missing historical facts as
    failures. Missing historical gate evidence remains UNAVAILABLE instead of a
    false zero or a fabricated pass/rejection.
    """
    trace = {stage: "NOT_REACHED" for stage in CANONICAL_DOWNSTREAM_STAGES}
    detail: dict[str, Any] = {}
    trace["ANALYSIS_QUALIFIED"] = _status_from_legacy(
        legacy_trace.get("ANALYSIS", "NOT_REACHED")
    )
    trace["STRUCTURAL_SETUP"] = _status_from_legacy(
        legacy_trace.get("STRUCTURAL_SETUP", "NOT_REACHED")
    )
    trace["STRATEGY_ADMITTED"] = _status_from_legacy(
        legacy_trace.get("STRATEGY_ELIGIBLE", "NOT_REACHED")
    )
    trace["RISK_COMPATIBILITY_ADMITTED"] = _status_from_legacy(
        legacy_trace.get("RISK_APPROVED", "NOT_REACHED")
    )
    if result is None:
        return trace, detail

    setup = _mapping(result.setup_payload_json)
    strategy = _mapping(result.strategy_payload_json)
    risk = _mapping(result.risk_payload_json)
    paper = _mapping(result.paper_payload_json)
    context = _mapping(paper.get("paper_context"))
    scalping_policy = _mapping(context.get("scalping_policy_provenance"))
    diagnostic = (
        _mapping(context.get("scalping_geometry_diagnostics"))
        or _mapping(context.get("canonical_domain_evaluation"))
    )
    net_cost_gate = _mapping(context.get("net_cost_gate"))
    portfolio_gate = _mapping(paper.get("portfolio_gate"))
    portfolio_measured = _mapping(portfolio_gate.get("measured"))
    portfolio_limits = _mapping(portfolio_gate.get("limits"))
    target_provenance = _mapping(diagnostic.get("target_provenance"))
    stop_provenance = _mapping(diagnostic.get("stop_provenance"))
    checklist = _mapping(paper.get("final_approval_checklist"))
    approvals = _mapping(paper.get("persisted_final_approvals"))
    shadow_approvals = _mapping(paper.get("shadow_approvals"))
    planned = _mapping(paper.get("shadow_plan")) or paper
    quantity_approval = (
        _mapping(approvals.get("paper_quantity_approval"))
        or _mapping(paper.get("controlled_quantity_approval"))
        or _mapping(shadow_approvals.get("shadow_quantity_approval"))
    )
    sizing = (
        _mapping(paper.get("quantity_sizing_audit"))
        or _mapping(quantity_approval.get("sizing_audit"))
    )
    validity = _mapping(paper.get("approval_validity")) or _mapping(
        paper.get("validity_policy")
    )

    compatibility_pass = trace["RISK_COMPATIBILITY_ADMITTED"] == "PASS"
    if compatibility_pass:
        if diagnostic:
            trace["GEOMETRY_VALID"] = (
                "PASS" if (
                    diagnostic.get("stop_envelope_pass") is True
                    or diagnostic.get("geometry_pass") is True
                )
                else "REJECTED"
            )
        else:
            trace["GEOMETRY_VALID"] = "UNAVAILABLE"
    if trace["GEOMETRY_VALID"] == "PASS":
        if diagnostic.get("rejection_stage") == "ECONOMIC_GEOMETRY":
            trace["TARGET_VALID"] = "REJECTED"
        elif (
            diagnostic.get("causal_target_exists") is True
            or diagnostic.get("target_pass") is True
        ):
            trace["TARGET_VALID"] = "PASS"
        elif diagnostic:
            trace["TARGET_VALID"] = "REJECTED"
        else:
            trace["TARGET_VALID"] = "UNAVAILABLE"
    if trace["TARGET_VALID"] == "PASS":
        if (
            diagnostic.get("economic_gate_pass") is True
            or net_cost_gate.get("gate_decision") == "PASS"
        ):
            trace["NET_COST_PASS"] = "PASS"
        elif diagnostic or net_cost_gate:
            trace["NET_COST_PASS"] = "REJECTED"
        else:
            trace["NET_COST_PASS"] = "UNAVAILABLE"
    if trace["NET_COST_PASS"] == "PASS":
        if (
            diagnostic.get("valid_plan") is True
            or diagnostic.get("rr_pass") is True
        ):
            trace["RR_PASS"] = "PASS"
        elif diagnostic:
            trace["RR_PASS"] = "REJECTED"
        else:
            trace["RR_PASS"] = "UNAVAILABLE"

    authoritative_risk = _mapping(approvals.get("paper_risk_approval"))
    if authoritative_risk:
        trace["RISK_ADMITTED"] = "PASS"
    elif (
        trace["RR_PASS"] == "PASS"
        and risk.get("risk_status") in {
            "RISK_PRE_APPROVED_RESEARCH", "RISK_APPROVED"
        }
    ):
        trace["RISK_ADMITTED"] = "PASS"
    elif trace["RR_PASS"] == "PASS":
        # A missing approval is not proof of an authoritative rejection.
        trace["RISK_ADMITTED"] = "UNAVAILABLE"

    if trace["RISK_ADMITTED"] == "PASS":
        trace["PORTFOLIO_ADMITTED"] = (
            "PASS" if portfolio_gate.get("decision") == "PASS"
            else "REJECTED" if portfolio_gate.get("decision") == "REJECT"
            else "UNAVAILABLE"
        )
    trace["FINAL_APPROVAL"] = _status_from_legacy(
        legacy_trace.get("FINAL_APPROVAL", "NOT_REACHED")
    )
    trace["PAPER_PLAN"] = _status_from_legacy(
        legacy_trace.get("PAPER_TRADE_PLAN", "NOT_REACHED")
    )
    if not include_detail:
        return trace, detail

    geometry_reason = diagnostic.get("rejection_reason") or diagnostic.get("raw_reason")
    entry = _first_present(
        planned.get("hypothetical_entry_reference"), diagnostic.get("entry")
    )
    stop = _first_present(
        planned.get("hypothetical_stop_level"), diagnostic.get("final_stop"),
        diagnostic.get("stop")
    )
    target = _first_present(
        planned.get("hypothetical_target_level"), diagnostic.get("causal_target"),
        diagnostic.get("target")
    )
    # Scalping v2 persists the causal primitives and policy lineage directly in
    # paper_context.  Older funnel projection code only understood the 15m
    # nested provenance shape, which made reached PASS fields look unavailable.
    # Derive the display shape exclusively from those persisted v2 facts; this
    # is observability enrichment and does not alter the trading decision.
    if scalping_policy and not stop_provenance:
        stop_provenance = {
            "source_timeframe": "5m",
            "source_candle_or_window": planned.get("closed_until_ms"),
            "source_signal_or_model_output": "causal_invalidation",
            "derived_rule_version": scalping_policy.get("stop_policy_version"),
            "raw_source_value": diagnostic.get("causal_invalidation"),
            "final_normalized_value": stop,
        }
    if scalping_policy and not target_provenance:
        chosen_target = next((
            _mapping(value)
            for value in diagnostic.get("target_considerations", ())
            if isinstance(value, Mapping)
            and value.get("economically_actionable") is True
        ), {})
        target_provenance = {
            "source_timeframe": chosen_target.get("target_timeframe"),
            "source_candle_or_window": planned.get("closed_until_ms"),
            "source_signal_or_model_output": (
                chosen_target.get("source_detail")
                or diagnostic.get("target_source_type")
            ),
            "derived_rule_version": scalping_policy.get("target_policy_version"),
            "raw_source_value": chosen_target.get("target_price"),
            "final_normalized_value": target,
        }
    valid_values = [
        int(value["valid_until_ms"])
        for value in (*approvals.values(), *shadow_approvals.values())
        if isinstance(value, Mapping) and value.get("valid_until_ms") is not None
    ]
    valid_until_ms = validity.get("valid_until_ms")
    if valid_until_ms is None and valid_values:
        valid_until_ms = min(valid_values)
    source_close_ms = (
        validity.get("source_candle_close_time_ms")
        or validity.get("source_close_ms")
        or planned.get("closed_until_ms")
    )
    ttl_ms = validity.get("entry_ttl_ms")
    if ttl_ms is None and valid_until_ms is not None and source_close_ms is not None:
        ttl_ms = int(valid_until_ms) - int(source_close_ms)
    approved_quantity = _first_present(
        quantity_approval.get("approved_quantity"),
        sizing.get("normalized_quantity"),
    )
    paper_equity = sizing.get("paper_equity_at_approval")
    risk_amount = sizing.get("risk_budget")
    required_rr = _first_present(
        context.get("production_rr_floor"),
        context.get("minimum_planned_rr"),
        _mapping(paper.get("causal_levels")).get("minimum_planned_rr"),
    )
    detail.update({
        "opportunity_id": (
            diagnostic.get("opportunity_id")
            or _mapping(context.get("causal_primitives")).get("opportunity_id")
            or setup.get("opportunity_id") or setup.get("setup_id")
        ),
        "paper_plan_id": planned.get("paper_plan_id"),
        "setup_policy_version": scalping_policy.get("setup_policy_version"),
        "entry_policy_version": scalping_policy.get("entry_policy_version"),
        "setup_type": setup.get("setup_type"),
        "strategy_type": strategy.get("strategy_type") or strategy.get("source_strategy_type"),
        "strategy_score": strategy.get("strategy_final_score") or strategy.get("strategy_score"),
        "strategy_admission": trace["STRATEGY_ADMITTED"],
        "risk_compatibility": risk.get("risk_status"),
        "entry_price": entry,
        "entry_source": planned.get("entry_reference_source"),
        "stop_price": stop,
        "stop_source": planned.get("stop_source") or diagnostic.get("stop_source"),
        "stop_provenance": stop_provenance or None,
        "stop_source_timeframe": stop_provenance.get("source_timeframe"),
        "stop_rule_version": stop_provenance.get("derived_rule_version"),
        "stop_distance_absolute": _absolute_distance(entry, stop),
        "geometry_status": trace["GEOMETRY_VALID"],
        "geometry_reason": (
            geometry_reason
            or ("GEOMETRY_VALID" if trace["GEOMETRY_VALID"] == "PASS" else None)
        ),
        "stop_distance_bps": diagnostic.get("stop_distance_bps"),
        "stop_distance_percent": _percent_from_bps(diagnostic.get("stop_distance_bps")),
        "atr": diagnostic.get("atr"),
        "atr_buffer_multiplier": diagnostic.get("atr_buffer_multiplier"),
        "atr_buffer_bps": diagnostic.get("atr_buffer_bps"),
        "target_price": target,
        "target_distance_absolute": _absolute_distance(entry, target),
        "target_status": trace["TARGET_VALID"],
        "target_distance_bps": diagnostic.get("target_distance_bps"),
        "target_distance_percent": _percent_from_bps(diagnostic.get("target_distance_bps")),
        "target_source": diagnostic.get("target_source_type") or diagnostic.get("target_source"),
        "target_provenance": target_provenance or None,
        "target_source_timeframe": target_provenance.get("source_timeframe"),
        "target_source_window": target_provenance.get("source_candle_or_window"),
        "target_rule_version": target_provenance.get("derived_rule_version"),
        "minimum_economically_valid_target_bps": diagnostic.get(
            "minimum_economically_valid_target_bps"
        ),
        "minimum_economically_valid_target_price": diagnostic.get(
            "minimum_economically_valid_target_price"
        ),
        "geometry_feasibility_result": diagnostic.get(
            "geometry_feasibility_result"
        ),
        "target_candidates_considered": diagnostic.get(
            "target_candidates_considered"
        ),
        "spread_bps": diagnostic.get("spread_bps"),
        "depth_impact_bps": diagnostic.get("depth_impact_bps"),
        "entry_fee_bps": diagnostic.get("entry_fee_bps"),
        "exit_fee_bps": diagnostic.get("exit_fee_bps"),
        "fee_estimate_bps": _first_present(
            net_cost_gate.get("estimated_trading_fees_bps"),
            _sum_decimals(
                diagnostic.get("entry_fee_bps"), diagnostic.get("exit_fee_bps")
            ),
        ),
        "entry_slippage_bps": diagnostic.get("entry_slippage_bps"),
        "exit_slippage_bps": diagnostic.get("exit_slippage_bps"),
        "slippage_estimate_bps": _first_present(
            net_cost_gate.get("estimated_slippage_bps"),
            _sum_decimals(
                diagnostic.get("entry_slippage_bps"),
                diagnostic.get("exit_slippage_bps"),
            ),
        ),
        "safety_margin_bps": _first_present(
            net_cost_gate.get("safety_margin_bps"),
            diagnostic.get("safety_margin_bps"),
        ),
        "total_modeled_cost_bps": _first_present(
            net_cost_gate.get("total_estimated_cost_bps"),
            diagnostic.get("total_cost_bps"),
        ),
        "gross_rr": _first_present(
            diagnostic.get("gross_rr"), diagnostic.get("raw_rr"),
            planned.get("planned_rr")
        ),
        "net_rr": _first_present(
            diagnostic.get("net_rr"), diagnostic.get("effective_rr")
        ),
        "required_rr": required_rr,
        "expected_net_edge_bps": _first_present(
            net_cost_gate.get("net_expected_outcome_bps"),
            diagnostic.get("expected_net_edge_bps"),
        ),
        "cost_gate_decision": _first_present(
            net_cost_gate.get("gate_decision"),
            "PASS" if diagnostic.get("economic_gate_pass") is True else None,
            "REJECT" if diagnostic.get("economic_gate_pass") is False else None,
        ),
        "cost_gate_reason": _first_present(
            net_cost_gate.get("gate_reason"),
            diagnostic.get("expectancy_gate_reason"),
            "ECONOMIC_GATE_PASS"
            if diagnostic.get("economic_gate_pass") is True else None,
            diagnostic.get("rejection_reason"),
        ),
        "cost_model_version": (
            diagnostic.get("cost_model_version")
            or net_cost_gate.get("model_version")
        ),
        "rr_policy_version": diagnostic.get("rr_policy_version"),
        "target_policy_version": diagnostic.get("target_policy_version"),
        "price_normalization_quantum": diagnostic.get(
            "price_normalization_quantum"
        ),
        "break_even_win_rate": diagnostic.get("break_even_win_rate"),
        "rr_status": trace["RR_PASS"],
        "rr_reason": (
            geometry_reason if trace["RR_PASS"] == "REJECTED"
            else diagnostic.get("expectancy_gate_reason")
            or ("RR_AND_EXPECTANCY_PASS" if trace["RR_PASS"] == "PASS" else None)
        ),
        "authoritative_risk": (
            authoritative_risk.get("status") or "PASS"
            if authoritative_risk else None
        ),
        "risk_percent": _ratio_percent(risk_amount, paper_equity),
        "risk_amount": risk_amount,
        "paper_equity_basis": paper_equity,
        "planned_quantity": approved_quantity,
        "quantity_status": (
            quantity_approval.get("status")
            or _mapping(paper.get("final_approval_generation")).get(
                "quantity_authority_status"
            )
        ),
        "quantity_step": sizing.get("applicable_quantity_step"),
        "quantity_minimum": sizing.get("applicable_min_quantity"),
        "quantity_maximum": sizing.get("applicable_max_quantity"),
        "notional_minimum": sizing.get("applicable_min_notional"),
        "notional_maximum": sizing.get("applicable_max_notional"),
        "planned_notional": _product(approved_quantity, entry),
        "portfolio": portfolio_gate or None,
        "portfolio_decision": portfolio_gate.get("decision"),
        "portfolio_reason": portfolio_gate.get("reason_code"),
        "portfolio_policy_version": portfolio_gate.get("policy_version"),
        "portfolio_active_positions": portfolio_measured.get("active_position_count"),
        "portfolio_projected_risk_bps": portfolio_measured.get(
            "projected_total_open_risk_bps"
        ),
        "portfolio_max_positions": portfolio_limits.get("max_concurrent_positions"),
        "portfolio_max_risk_bps": portfolio_limits.get("max_total_open_risk_bps"),
        "geometry_calculation_version": (
            diagnostic.get("geometry_calculation_version")
            or diagnostic.get("calculation_version")
        ),
        "final_approval": trace["FINAL_APPROVAL"],
        "paper_plan": trace["PAPER_PLAN"],
        "plan_created_at_ms": planned.get("created_at_ms"),
        "valid_from": quantity_approval.get("approved_at"),
        "valid_until_ms": valid_until_ms,
        "ttl_ms": ttl_ms,
        "expiry_status": (
            None if valid_until_ms is None or now_ms is None
            else "VALID" if int(valid_until_ms) > now_ms else "EXPIRED"
        ),
        "source_boundary_close_ms": planned.get("closed_until_ms"),
        "economic_input_timestamp_ms": diagnostic.get("economic_input_timestamp_ms"),
        "economic_input_source": diagnostic.get("economic_input_source"),
        "spread_source": diagnostic.get("spread_source"),
        "depth_impact_source": diagnostic.get("depth_impact_source"),
        "fee_source": diagnostic.get("fee_source"),
        "checklist_risk_pass": checklist.get("risk_pass"),
        "checklist_cost_gate_pass": checklist.get("cost_gate_pass"),
        "checklist_final_pass": checklist.get("passed"),
        "shadow_final_approval": _mapping(
            shadow_approvals.get("shadow_final_approval")
        ).get("status"),
    })
    return trace, detail


def _specific_terminal_reason(
    row: OnlinePipelineRun,
    result: OnlinePipelineResultRow | None,
    downstream_trace: Mapping[str, str],
) -> str | None:
    if result is None:
        return row.error_code or row.final_reason
    reasons = _mapping(result.module_reasons_json)
    paper = _mapping(result.paper_payload_json)
    diagnostic = _mapping(
        _mapping(paper.get("paper_context")).get("scalping_geometry_diagnostics")
    )
    diagnostic_reason = diagnostic.get("rejection_reason") or diagnostic.get("raw_reason")
    if diagnostic_reason and any(
        downstream_trace.get(stage) == "REJECTED"
        for stage in ("GEOMETRY_VALID", "TARGET_VALID", "NET_COST_PASS", "RR_PASS")
    ):
        return str(diagnostic_reason)
    module_by_stage = (
        ("STRATEGY_ADMITTED", "strategy"),
        ("STRUCTURAL_SETUP", "setup"),
        ("ANALYSIS_QUALIFIED", "analysis"),
        ("RISK_COMPATIBILITY_ADMITTED", "risk"),
        ("PAPER_PLAN", "paper"),
    )
    for stage, module in module_by_stage:
        if downstream_trace.get(stage) in {"REJECTED", "ERROR", "DEFERRED"}:
            values = _reasons(reasons.get(module))
            if values:
                return values[0]
    return _first_reason(row, result)


def _stage_trace(row: OnlinePipelineRun, result: OnlinePipelineResultRow | None, now_ms: int) -> tuple[dict[str, str], dict[str, Any]]:
    trace = {stage: "NOT_REACHED" for stage in STAGES}
    meta: dict[str, Any] = {}
    if row.status not in TERMINAL_RUN_STATUSES:
        trace["ANALYSIS"] = "PENDING"
        return trace, meta
    if result is None:
        trace["ANALYSIS"] = "ERROR" if row.status in {"ERROR", "MODULE_ERROR"} else "REJECTED"
        return trace, meta
    analysis, setup, strategy, risk, paper = (
        _mapping(result.analysis_payload_json), _mapping(result.setup_payload_json),
        _mapping(result.strategy_payload_json), _mapping(result.risk_payload_json),
        _mapping(result.paper_payload_json),
    )
    trace["ANALYSIS"] = "ERROR" if row.analysis_status == "ERROR" else "PASS"
    if trace["ANALYSIS"] != "PASS":
        return trace, meta
    setup_status = str(row.setup_status or setup.get("status") or "")
    trace["STRUCTURAL_SETUP"] = "PASS" if setup_status == "SETUP_CANDIDATE" else (
        "ERROR" if setup_status == "ERROR" else "DEFERRED" if setup_status == "WAIT_FOR_CONFIRMATION" else "REJECTED"
    )
    meta["candidate_id"] = setup.get("setup_id")
    meta["direction"] = setup.get("direction_hint") or strategy.get("direction_hint") or paper.get("paper_direction")
    if trace["STRUCTURAL_SETUP"] != "PASS":
        return trace, meta
    strategy_status = str(row.strategy_status or strategy.get("decision_status") or "")
    trace["STRATEGY_ELIGIBLE"] = "PASS" if strategy_status == "ALLOW_RESEARCH_TRADE_PLAN" else (
        "DEFERRED" if strategy_status == "WAIT" else "ERROR" if strategy_status == "ERROR" else "REJECTED"
    )
    if trace["STRATEGY_ELIGIBLE"] != "PASS":
        return trace, meta
    risk_status = str(row.risk_status or risk.get("risk_status") or "")
    trace["RISK_APPROVED"] = "PASS" if risk_status in {"RISK_PRE_APPROVED_RESEARCH", "RISK_APPROVED"} else (
        "DEFERRED" if risk_status == "WAIT" else "ERROR" if risk_status == "ERROR" else "REJECTED"
    )
    if trace["RISK_APPROVED"] != "PASS":
        return trace, meta
    shadow_plan = _mapping(paper.get("shadow_plan"))
    shadow_mode = bool(shadow_plan) or str(paper.get("paper_status") or "") == "SHADOW_SEARCH"
    plan_status = (
        str(shadow_plan.get("paper_status") or paper.get("shadow_plan_status") or "")
        if shadow_mode else str(row.paper_status or paper.get("paper_status") or "")
    )
    trace["PAPER_TRADE_PLAN"] = "PASS" if plan_status == "PAPER_PLAN_READY" else (
        "DEFERRED" if plan_status == "WAIT" else
        "ERROR" if plan_status == "ERROR" else "REJECTED"
    )
    if trace["PAPER_TRADE_PLAN"] != "PASS":
        return trace, meta
    if shadow_mode:
        approvals = _mapping(paper.get("shadow_approvals"))
        quantity = _mapping(approvals.get("shadow_quantity_approval"))
        validity = _mapping(approvals.get("shadow_validity_approval"))
        final = _mapping(approvals.get("shadow_final_approval"))
        generation = _mapping(paper.get("shadow_final_approval_generation"))
        quantity_status = str(generation.get("quantity_authority_status") or "")
        attempted_stage = str(generation.get("stage") or "")
        outcome = generation.get("outcome")
        failed = outcome not in (
            None, "SHADOW_FINAL_APPROVAL_CREATED", "NOT_ELIGIBLE"
        )
        trace["QUANTITY_APPROVED"] = (
            "PASS" if quantity.get("status") == "PASS" else
            "REJECTED" if quantity_status == "REJECTED" else "NOT_REACHED"
        )
        if trace["QUANTITY_APPROVED"] != "PASS":
            if failed and attempted_stage == "FINAL_APPROVAL":
                trace["FINAL_APPROVAL"] = (
                    "ERROR" if generation.get("status") == "ERROR" else "REJECTED"
                )
            return trace, meta
        valid_until_ms = (
            int(validity["valid_until_ms"])
            if validity.get("valid_until_ms") is not None else None
        )
        trace["VALIDITY_APPROVED"] = (
            "PASS" if validity.get("status") == "PASS"
            and valid_until_ms is not None
            else "REJECTED"
        )
        trace["FINAL_APPROVAL"] = (
            "PASS" if final.get("status") == "PASS"
            and generation.get("outcome") == "SHADOW_FINAL_APPROVAL_CREATED"
            else "ERROR" if generation.get("status") == "ERROR"
            else "REJECTED" if failed else "NOT_REACHED"
        )
        candidate = _mapping(paper.get("shadow_final_approval_candidate"))
        meta.update({
            "final_approval_id": final.get("approval_id")
            or generation.get("final_approval_id"),
            "valid_until_ms": valid_until_ms,
            "risk_score": candidate.get("risk_score") or risk.get("risk_score"),
            "strategy_score": candidate.get("strategy_score")
            or strategy.get("strategy_score"),
            "planned_risk_reward": candidate.get("planned_risk_reward")
            or shadow_plan.get("planned_rr"),
            "shadow_execution_eligible": bool(candidate.get("execution_eligible")),
            "validity_current": valid_until_ms is not None and valid_until_ms > now_ms,
        })
        if valid_until_ms is not None and valid_until_ms <= now_ms:
            meta["forced_reason"] = "SHADOW_APPROVAL_EXPIRED"
        return trace, meta
    approvals = _mapping(paper.get("persisted_final_approvals"))
    quantity = _mapping(approvals.get("paper_quantity_approval"))
    risk_approval = _mapping(approvals.get("paper_risk_approval"))
    generation = _mapping(paper.get("final_approval_generation"))
    materializer_outcome = generation.get("outcome")
    materializer_failed = materializer_outcome not in (
        None, "FINAL_APPROVAL_CREATED", "NOT_ELIGIBLE"
    )
    quantity_status = str(generation.get("quantity_authority_status") or "")
    attempted_stage = str(generation.get("stage") or "")
    trace["QUANTITY_APPROVED"] = "PASS" if quantity else "NOT_REACHED"
    if not quantity:
        if quantity_status == "REJECTED":
            trace["QUANTITY_APPROVED"] = "REJECTED"
        elif quantity_status == "PASS":
            trace["QUANTITY_APPROVED"] = "PASS"
        if materializer_failed:
            if attempted_stage == "VALIDITY_APPROVED":
                trace["VALIDITY_APPROVED"] = "REJECTED"
            elif attempted_stage == "FINAL_APPROVAL" or (
                not attempted_stage and materializer_outcome == "PAPER_INPUT_IDENTITY_INVALID"
            ):
                trace["FINAL_APPROVAL"] = (
                    "ERROR" if generation.get("status") == "ERROR" else "REJECTED"
                )
        return trace, meta
    valid_values = [int(value["valid_until_ms"]) for value in approvals.values()
                    if isinstance(value, Mapping) and value.get("valid_until_ms") is not None]
    valid_until_ms = min(valid_values) if len(valid_values) == 3 else None
    trace["VALIDITY_APPROVED"] = "PASS" if valid_until_ms is not None else "REJECTED"
    trace["FINAL_APPROVAL"] = "PASS" if len(approvals) == 3 else "NOT_REACHED"
    meta.update({
        "final_approval_id": generation.get("final_approval_id") or risk_approval.get("approval_id"),
        "valid_until_ms": valid_until_ms,
        "risk_score": risk.get("risk_score"),
        "strategy_score": strategy.get("strategy_score"),
        "planned_risk_reward": paper.get("planned_risk_reward"),
        "validity_current": valid_until_ms is not None and valid_until_ms > now_ms,
    })
    if valid_until_ms is not None and valid_until_ms <= now_ms:
        meta["forced_reason"] = "APPROVAL_EXPIRED"
    return trace, meta


def _shadow_candidate(
    row: OnlinePipelineRun,
    result: OnlinePipelineResultRow | None,
    trace: Mapping[str, str],
    now_ms: int,
) -> _ShadowEligibleCandidate | None:
    if result is None or trace.get("FINAL_APPROVAL") != "PASS" or trace.get(
        "VALIDITY_APPROVED"
    ) != "PASS":
        return None
    payload = _mapping(result.paper_payload_json)
    candidate = _mapping(payload.get("shadow_final_approval_candidate"))
    if (
        candidate.get("status") != "ELIGIBLE"
        or candidate.get("execution_eligible") is not False
        or candidate.get("persisted_final_approval_created") is not False
        or not isinstance(candidate.get("valid_until_ms"), int)
        or int(candidate["valid_until_ms"]) <= now_ms
    ):
        return None
    try:
        candidate_id = str(candidate["candidate_id"])
        final_approval_id = str(candidate["final_approval_id"])
        source_run_id = str(candidate["source_run_id"])
        symbol = str(candidate["symbol"])
        ranking = _ShadowRanking(
            Decimal(str(candidate["risk_score"])),
            Decimal(str(candidate["planned_risk_reward"])),
            Decimal(str(candidate["strategy_score"])),
            int(candidate["closed_until_ms"]),
            source_run_id,
            final_approval_id,
        )
        if source_run_id != row.run_id or symbol != row.symbol:
            return None
        return _ShadowEligibleCandidate(
            candidate_id, symbol, ranking,
            _ShadowLineage(source_run_id, final_approval_id),
        )
    except (ArithmeticError, KeyError, TypeError, ValueError):
        return None


class TradingFunnelReadRepository:
    """One bounded query with authoritative in-memory eligibility classification."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        universe_source: Callable[[], TradingUniverseVersion],
        *,
        schema_capabilities: ReadonlySchemaCapabilityBridge | None = None,
        monotonic_clock: Callable[[], float] = monotonic,
        load_lifecycle: bool = True,
    ) -> None:
        self._session_factory = session_factory
        self._universe_source = universe_source
        self._schema_capabilities = schema_capabilities
        self._monotonic = monotonic_clock
        self._load_lifecycle_enabled = load_lifecycle
        self._cache_lock = Lock()
        self._row_cache: dict[
            str,
            tuple[
                float,
                tuple[
                    tuple[OnlinePipelineRun, OnlinePipelineResultRow | None],
                    ...,
                ],
            ],
        ] = {}

    def _load_rows(
        self,
        profile: object,
        universe: TradingUniverseVersion,
        start_ms: int,
        now_ms: int,
    ) -> tuple[tuple[OnlinePipelineRun, OnlinePipelineResultRow | None], ...]:
        profile_id = profile.trade_profile_id
        with self._cache_lock:
            current = self._monotonic()
            cached_entry = self._row_cache.get(profile_id)
            if (
                cached_entry is not None
                and current - cached_entry[0] < ROW_CACHE_TTL_SECONDS
            ):
                return cached_entry[1]
            # Release the expired ORM/JSON graph before materializing its
            # replacement.  The 5m horizon contains 490 run/result pairs and
            # retaining both generations at once can exceed the bounded
            # Readonly container memory limit.  The lock preserves single-
            # flight loading, so removing the stale value cannot create a
            # duplicate query or expose an empty result to another request.
            self._row_cache.pop(profile_id, None)
            cached_entry = None
            with self._session_factory() as session:
                if self._schema_capabilities is None:
                    revisions = tuple(session.execute(text(
                        "SELECT version_num FROM alembic_version ORDER BY version_num"
                    )).scalars())
                    profile_schema_ready = revisions in {
                        ("0017_parallel_trade_profiles",),
                        ("0018_promote_5m_production_search",),
                        ("0019_first_class_15m_domain",),
                        ("0020_paper_plan_execution_outcomes",),
                        ("0021_independent_scalping_profile_v2",),
                        ("0023_scalping_v2_journal_causality",),
                        ("0024_continuous_paper_authority",),
                        ("0025_paper_budget_policy",),
                    }
                else:
                    profile_schema_ready = self._schema_capabilities.snapshot().has(
                        ReadonlySchemaCapability.PARALLEL_TRADE_PROFILES
                    )
                if not profile_schema_ready and profile_id != DEFAULT_TRADE_PROFILE_ID:
                    rows = ()
                else:
                    predicates = (
                        OnlinePipelineRun.primary_timeframe == profile.trigger_timeframe,
                        OnlinePipelineRun.symbol.in_(universe.symbols),
                        OnlinePipelineRun.closed_until_ms >= start_ms,
                        OnlinePipelineRun.closed_until_ms <= now_ms,
                    )
                    profile_predicates = (
                        (OnlinePipelineRun.trade_profile_id == profile_id,)
                        if profile_schema_ready
                        else ()
                    )
                    statement = (
                        select(OnlinePipelineRun, OnlinePipelineResultRow)
                        .options(
                            load_only(
                                OnlinePipelineRun.id,
                                OnlinePipelineRun.run_id,
                                OnlinePipelineRun.trade_profile_id,
                                OnlinePipelineRun.symbol,
                                OnlinePipelineRun.primary_timeframe,
                                OnlinePipelineRun.closed_until_ms,
                                OnlinePipelineRun.status,
                                OnlinePipelineRun.finished_at,
                                OnlinePipelineRun.freshness_deadline_at,
                                OnlinePipelineRun.future_bars_used,
                                OnlinePipelineRun.is_trade_signal,
                                OnlinePipelineRun.is_executable,
                                OnlinePipelineRun.order_approved,
                                OnlinePipelineRun.execution_approved,
                                OnlinePipelineRun.position_opened,
                                OnlinePipelineRun.position_size_approved,
                                OnlinePipelineRun.analysis_status,
                                OnlinePipelineRun.setup_status,
                                OnlinePipelineRun.strategy_status,
                                OnlinePipelineRun.risk_status,
                                OnlinePipelineRun.paper_status,
                                OnlinePipelineRun.error_code,
                                OnlinePipelineRun.final_reason,
                                OnlinePipelineRun.updated_at,
                            ),
                            load_only(
                                OnlinePipelineResultRow.id,
                                OnlinePipelineResultRow.trade_profile_id,
                                OnlinePipelineResultRow.primary_timeframe,
                                OnlinePipelineResultRow.analysis_payload_json,
                                OnlinePipelineResultRow.setup_payload_json,
                                OnlinePipelineResultRow.strategy_payload_json,
                                OnlinePipelineResultRow.risk_payload_json,
                                OnlinePipelineResultRow.paper_payload_json,
                                OnlinePipelineResultRow.module_reasons_json,
                                OnlinePipelineResultRow.created_at,
                            ),
                        )
                        .outerjoin(
                            OnlinePipelineResultRow,
                            (
                                (OnlinePipelineResultRow.run_id == OnlinePipelineRun.run_id)
                                & (OnlinePipelineResultRow.trade_profile_id == OnlinePipelineRun.trade_profile_id)
                                & (OnlinePipelineResultRow.profile_mode == OnlinePipelineRun.profile_mode)
                                & (OnlinePipelineResultRow.symbol == OnlinePipelineRun.symbol)
                                & (OnlinePipelineResultRow.primary_timeframe == OnlinePipelineRun.primary_timeframe)
                                & (OnlinePipelineResultRow.closed_until_ms == OnlinePipelineRun.closed_until_ms)
                            ),
                        )
                        .where(*profile_predicates, *predicates)
                        .order_by(
                            OnlinePipelineRun.closed_until_ms.desc(),
                            OnlinePipelineRun.symbol.asc(),
                            OnlinePipelineRun.id.desc(),
                            OnlinePipelineResultRow.id.desc(),
                        )
                        .limit(
                            len(universe.symbols)
                            * (50 if profile.trigger_timeframe == "5m" else 18)
                        )
                    )
                    rows = tuple(session.execute(statement))
                    if profile.trigger_timeframe == "5m":
                        # Keep the latest persisted successful PAPER plans
                        # selectable after they age out of the rolling 4h
                        # funnel window.  This is one bounded set query (never
                        # one query per symbol); its causal payload is rendered
                        # unchanged and is not mixed with current quotes.
                        detail_statement = (
                            select(OnlinePipelineRun, OnlinePipelineResultRow)
                            .outerjoin(
                                OnlinePipelineResultRow,
                                (
                                    (OnlinePipelineResultRow.run_id == OnlinePipelineRun.run_id)
                                    & (OnlinePipelineResultRow.trade_profile_id == OnlinePipelineRun.trade_profile_id)
                                    & (OnlinePipelineResultRow.profile_mode == OnlinePipelineRun.profile_mode)
                                    & (OnlinePipelineResultRow.symbol == OnlinePipelineRun.symbol)
                                    & (OnlinePipelineResultRow.primary_timeframe == OnlinePipelineRun.primary_timeframe)
                                    & (OnlinePipelineResultRow.closed_until_ms == OnlinePipelineRun.closed_until_ms)
                                ),
                            )
                            .where(
                                *profile_predicates,
                                OnlinePipelineRun.primary_timeframe
                                == profile.trigger_timeframe,
                                OnlinePipelineRun.symbol.in_(universe.symbols),
                                OnlinePipelineRun.closed_until_ms
                                >= now_ms - 7 * 24 * 60 * 60 * 1000,
                                OnlinePipelineRun.closed_until_ms <= now_ms,
                                OnlinePipelineRun.paper_status
                                == "PAPER_PLAN_READY",
                            )
                            .order_by(
                                OnlinePipelineRun.closed_until_ms.desc(),
                                OnlinePipelineRun.symbol.asc(),
                            )
                            .limit(len(universe.symbols) * 10)
                        )
                        known_run_ids = {row.run_id for row, _ in rows}
                        latest_plan_by_symbol: dict[
                            str,
                            tuple[OnlinePipelineRun, OnlinePipelineResultRow | None],
                        ] = {}
                        for pair in session.execute(detail_statement):
                            plan_run = pair[0]
                            if (
                                plan_run.run_id not in known_run_ids
                                and plan_run.symbol not in latest_plan_by_symbol
                            ):
                                latest_plan_by_symbol[plan_run.symbol] = pair
                        historical_plans = tuple(
                            latest_plan_by_symbol.values()
                        )
                        rows = (*rows, *historical_plans)
            self._row_cache[profile_id] = (current, rows)
            return rows

    def project(self, now_ms: int, trade_profile_id: str = DEFAULT_TRADE_PROFILE_ID) -> dict[str, Any]:
        profile = resolve_trade_profile(trade_profile_id)
        boundary_ms = 5 * 60 * 1000 if profile.trigger_timeframe == "5m" else BOUNDARY_MS
        max_horizon_ms = 4 * 60 * 60 * 1000 + boundary_ms
        universe = self._universe_source()
        start_ms = now_ms - max_horizon_ms
        rows = self._load_rows(profile, universe, start_ms, now_ms)
        eligible_by_run: dict[str, object] = {}
        production_eligibility_by_run: dict[str, object] = {}
        if profile.mode != TradeProfileMode.SHADOW_SEARCH.value:
            # The bounded funnel query has already loaded the exact persisted
            # run/result pairs required by the production approval classifier.
            # Reusing them avoids ten redundant per-symbol DB round trips on
            # every 5m desktop refresh while retaining the authoritative
            # lineage, quantity, validity and approval checks.
            recent_by_symbol: dict[
                str,
                list[tuple[OnlinePipelineRun, OnlinePipelineResultRow]],
            ] = {symbol: [] for symbol in universe.symbols}
            for run, result in rows:
                recent = recent_by_symbol.get(run.symbol)
                if (
                    recent is not None
                    and len(recent) < MAX_RUN_LOOKBACK
                    and result is not None
                    and run.status == "COMPLETED"
                ):
                    recent.append((run, result))
            classifier = PaperProductionApprovalSourceAdapter(
                self._session_factory
            )
            for recent in recent_by_symbol.values():
                if not recent:
                    continue
                latest_rank = (recent[0][0].closed_until_ms, recent[0][0].id)
                tied = [
                    pair
                    for pair in recent
                    if (pair[0].closed_until_ms, pair[0].id) == latest_rank
                ]
                if len(tied) != 1:
                    continue
                classified = classifier.classify_loaded_decision(
                    tied[0][0], tied[0][1], now_ms
                )
                if classified.source_run_id:
                    production_eligibility_by_run[classified.source_run_id] = classified
                if classified.candidate is not None:
                    eligible_by_run[classified.source_run_id] = classified.candidate
        lifecycle_by_run = (
            self._load_lifecycle(tuple(row.run_id for row, _ in rows))
            if self._load_lifecycle_enabled else {}
        )
        return build_projection(
            rows,
            universe,
            now_ms,
            eligible_by_run,
            profile.trade_profile_id,
            production_eligibility_by_run,
            lifecycle_by_run,
        )

    def _load_lifecycle(self, run_ids: tuple[str, ...]) -> dict[str, dict[str, Any]]:
        """Load the complete bounded PAPER lifecycle in one aggregate query."""
        if not run_ids:
            return {}
        statement = (
            select(
                PaperExecutionCommandRecord.pipeline_run_id,
                PaperExecutionCommandRecord.command_id,
                PaperExecutionCommandRecord.processing_status,
                PaperOrderRecord.order_id,
                PaperOrderRecord.state,
                PaperOrderRecord.applied_fill_id,
                PaperPositionRecord.position_id,
                PaperPositionRecord.state,
                PaperPositionRecord.reason_code,
            )
            .outerjoin(
                PaperOrderRecord,
                (PaperOrderRecord.command_id == PaperExecutionCommandRecord.command_id)
                & (PaperOrderRecord.order_role == "ENTRY"),
            )
            .outerjoin(
                PaperPositionRecord,
                PaperPositionRecord.entry_order_id == PaperOrderRecord.order_id,
            )
            .where(PaperExecutionCommandRecord.pipeline_run_id.in_(run_ids))
            .order_by(PaperExecutionCommandRecord.pipeline_run_id.asc())
            .limit(len(run_ids))
        )
        outcome_capable = (
            self._schema_capabilities is None
            or self._schema_capabilities.snapshot().has(
                ReadonlySchemaCapability.PAPER_PLAN_EXECUTION_OUTCOMES
            )
        )
        with self._session_factory() as session:
            rows = tuple(session.execute(statement))
            outcome_rows = (
                tuple(session.execute(
                    select(PaperPlanExecutionOutcomeRecord).where(
                        PaperPlanExecutionOutcomeRecord.pipeline_run_id.in_(run_ids)
                    ).limit(len(run_ids))
                ).scalars())
                if outcome_capable else ()
            )
        values = {
            str(row[0]): {
                "execution_intent": "PAPER_COMMAND_CREATED",
                "command_id": row[1], "command_status": row[2],
                "order_id": row[3], "order_status": row[4],
                "fill_id": row[5],
                "fill_status": "FILLED" if row[5] is not None else "NOT_REACHED",
                "position_id": row[6], "position_status": row[7],
                "terminal_result": row[8],
            }
            for row in rows
        }
        for outcome in outcome_rows:
            lifecycle = values.setdefault(outcome.pipeline_run_id, {})
            lifecycle.update({
                "execution_intent": (
                    "PAPER_COMMAND_CREATED" if lifecycle.get("command_id")
                    else "PAPER_PLAN_OBSERVED"
                ),
                "selector_state": outcome.selector_state,
                "selector_reason": outcome.selector_reason,
                "selector_rank": outcome.selector_rank,
                "selected_winner": outcome.selected_winner,
                "candidate_id": outcome.candidate_id,
                "approval_valid_until_ms": outcome.approval_valid_until_ms,
                "command_id": lifecycle.get("command_id") or outcome.command_id,
                "command_status": lifecycle.get("command_status") or (
                    {
                        "PLAN_OBSERVED": "PENDING_CREATE",
                        "BLOCKED_BY_POLICY": "BLOCKED",
                        "EXECUTION_FAILED": "FAILED",
                        "EXPIRED_BEFORE_EXECUTION": "EXPIRED",
                    }.get(outcome.lifecycle_state, "NOT_CREATED")
                    if outcome.command_id is None else "PENDING"
                ),
                "terminal_result": lifecycle.get("terminal_result") or outcome.terminal_reason,
                "lifecycle_state": outcome.lifecycle_state,
                "attempt_count": outcome.attempt_count,
                "control_generation": outcome.control_generation,
                "policy_evaluated_at": outcome.updated_at,
                "policy_generation": outcome.control_generation,
                "policy_reason_source": "READONLY_PAPER_READINESS_CURRENT_SNAPSHOT",
                "policy_source_timestamp": outcome.updated_at,
            })
        return values

    def export_rows(
        self,
        trade_profile_id: str,
        from_ms: int,
        to_ms: int,
        symbol: str | None,
        limit: int,
        after: tuple[int, str, str] | None = None,
    ) -> tuple[tuple[OnlinePipelineRun, OnlinePipelineResultRow | None], ...]:
        """Load one deterministic bounded export page without cache or per-row SQL."""
        profile = resolve_trade_profile(trade_profile_id)
        universe = self._universe_source()
        predicates = (
            OnlinePipelineRun.trade_profile_id == profile.trade_profile_id,
            OnlinePipelineRun.primary_timeframe == profile.trigger_timeframe,
            OnlinePipelineRun.symbol.in_(universe.symbols),
            OnlinePipelineRun.closed_until_ms >= from_ms,
            OnlinePipelineRun.closed_until_ms <= to_ms,
        )
        if symbol is not None:
            predicates += (OnlinePipelineRun.symbol == symbol,)
        if after is not None:
            predicates += (
                tuple_(
                    OnlinePipelineRun.closed_until_ms,
                    OnlinePipelineRun.symbol,
                    OnlinePipelineRun.run_id,
                ) > after,
            )
        statement = (
            select(OnlinePipelineRun, OnlinePipelineResultRow)
            .outerjoin(
                OnlinePipelineResultRow,
                (OnlinePipelineResultRow.run_id == OnlinePipelineRun.run_id)
                & (OnlinePipelineResultRow.trade_profile_id == OnlinePipelineRun.trade_profile_id)
                & (OnlinePipelineResultRow.profile_mode == OnlinePipelineRun.profile_mode)
                & (OnlinePipelineResultRow.symbol == OnlinePipelineRun.symbol)
                & (OnlinePipelineResultRow.primary_timeframe == OnlinePipelineRun.primary_timeframe)
                & (OnlinePipelineResultRow.closed_until_ms == OnlinePipelineRun.closed_until_ms),
            )
            .where(*predicates)
            .order_by(
                OnlinePipelineRun.closed_until_ms.asc(), OnlinePipelineRun.symbol.asc(),
                OnlinePipelineRun.run_id.asc(),
            )
            .limit(limit + 1)
        )
        with self._session_factory() as session:
            return tuple(session.execute(statement))

    def export_bounds(
        self, trade_profile_id: str, symbol: str | None,
    ) -> tuple[int | None, int | None]:
        """Load retained authoritative bounds once, before a paged snapshot begins."""
        profile = resolve_trade_profile(trade_profile_id)
        universe = self._universe_source()
        predicates = (
            OnlinePipelineRun.trade_profile_id == profile.trade_profile_id,
            OnlinePipelineRun.primary_timeframe == profile.trigger_timeframe,
            OnlinePipelineRun.symbol.in_(universe.symbols),
        )
        if symbol is not None:
            predicates += (OnlinePipelineRun.symbol == symbol,)
        statement = select(
            func.min(OnlinePipelineRun.closed_until_ms),
            func.max(OnlinePipelineRun.closed_until_ms),
        ).where(*predicates)
        with self._session_factory() as session:
            lower, upper = session.execute(statement).one()
        return (
            None if lower is None else int(lower),
            None if upper is None else int(upper),
        )

    def export_outcomes(self, run_ids: tuple[str, ...]) -> dict[str, dict[str, object]]:
        """Bulk-load PAPER lifecycle facts for the already bounded run identities."""
        if not run_ids:
            return {}
        statement = (
            select(
                PaperExecutionCommandRecord.pipeline_run_id,
                PaperExecutionCommandRecord.command_id,
                PaperPositionRecord,
            )
            .outerjoin(
                PaperOrderRecord,
                (PaperOrderRecord.command_id == PaperExecutionCommandRecord.command_id)
                & (PaperOrderRecord.order_role == "ENTRY"),
            )
            .outerjoin(PaperPositionRecord, PaperPositionRecord.entry_order_id == PaperOrderRecord.order_id)
            .where(PaperExecutionCommandRecord.pipeline_run_id.in_(run_ids))
            .order_by(PaperExecutionCommandRecord.pipeline_run_id.asc())
            .limit(len(run_ids))
        )
        with self._session_factory() as session:
            rows = tuple(session.execute(statement))
        outcomes: dict[str, dict[str, object]] = {}
        for run_id, command_id, position in rows:
            outcomes[run_id] = {
                "command_id": command_id,
                "position_id": None if position is None else position.position_id,
                "entry_time_utc": None if position is None else position.opened_at,
                "exit_time_utc": None if position is None else position.closed_at,
                "holding_time_seconds": (
                    None if position is None or position.closed_at is None
                    else (position.closed_at - position.opened_at).total_seconds()
                ),
                "exit_reason": None if position is None else position.reason_code,
                "net_pnl": None if position is None else position.realized_pnl,
                "fees": None if position is None else position.entry_fees + position.exit_fees,
            }
        return outcomes


def build_projection(rows: tuple[tuple[OnlinePipelineRun, OnlinePipelineResultRow | None], ...], universe: TradingUniverseVersion,
                     now_ms: int, eligible_by_run: Mapping[str, object] | None = None,
                     trade_profile_id: str = DEFAULT_TRADE_PROFILE_ID,
                     production_eligibility_by_run: Mapping[str, object] | None = None,
                     lifecycle_by_run: Mapping[str, Mapping[str, Any]] | None = None) -> dict[str, Any]:
    profile = resolve_trade_profile(trade_profile_id)
    boundary_ms = 5 * 60 * 1000 if profile.trigger_timeframe == "5m" else BOUNDARY_MS
    max_horizon_ms = 4 * 60 * 60 * 1000 + boundary_ms
    eligible_by_run = eligible_by_run or {}
    production_eligibility_by_run = production_eligibility_by_run or {}
    lifecycle_by_run = lifecycle_by_run or {}
    by_boundary: dict[int, list[tuple[OnlinePipelineRun, OnlinePipelineResultRow | None]]] = {}
    for pair in rows:
        by_boundary.setdefault(int(pair[0].closed_until_ms), []).append(pair)
    boundaries = sorted(by_boundary, reverse=True)
    current_boundary = boundaries[0] if boundaries else None
    complete_boundaries = [boundary for boundary in boundaries if {
        row.symbol for row, _ in by_boundary[boundary] if row.status in TERMINAL_RUN_STATUSES
    } == set(universe.symbols)]
    last_completed_boundary = next((value for value in complete_boundaries if value != current_boundary), None)
    detail_source_by_symbol: dict[str, tuple[tuple[int, int], str, int]] = {}
    if profile.trigger_timeframe == "5m":
        for detail_row, detail_result in rows:
            if detail_result is None:
                continue
            detail_paper = _mapping(detail_result.paper_payload_json)
            detail_diagnostic = _mapping(
                _mapping(detail_paper.get("paper_context")).get(
                    "scalping_geometry_diagnostics"
                )
            )
            detail_setup = _mapping(detail_result.setup_payload_json)
            detail_strategy = _mapping(detail_result.strategy_payload_json)
            detail_risk = _mapping(detail_result.risk_payload_json)
            detail_admitted = (
                (detail_row.setup_status or detail_setup.get("status"))
                == "SETUP_CANDIDATE"
                and (
                    detail_row.strategy_status
                    or detail_strategy.get("decision_status")
                ) == "ALLOW_RESEARCH_TRADE_PLAN"
                and (detail_row.risk_status or detail_risk.get("risk_status"))
                in {"RISK_PRE_APPROVED_RESEARCH", "RISK_APPROVED"}
            )
            detail_validity = _mapping(
                detail_paper.get("approval_validity")
            ) or _mapping(detail_paper.get("validity_policy"))
            detail_approvals = _mapping(
                detail_paper.get("persisted_final_approvals")
            )
            detail_shadow_approvals = _mapping(
                detail_paper.get("shadow_approvals")
            )
            detail_valid_values = [
                int(value["valid_until_ms"])
                for value in (
                    *detail_approvals.values(),
                    *detail_shadow_approvals.values(),
                )
                if isinstance(value, Mapping)
                and value.get("valid_until_ms") is not None
            ]
            detail_valid_until_ms = detail_validity.get("valid_until_ms")
            if detail_valid_until_ms is None and detail_valid_values:
                detail_valid_until_ms = min(detail_valid_values)
            detail_plan_current = (
                detail_valid_until_ms is not None
                and int(detail_valid_until_ms) > now_ms
            )
            detail_priority = (
                4 if detail_admitted and detail_paper.get("paper_status") == "PAPER_PLAN_READY" and detail_plan_current
                else 3 if detail_admitted and detail_diagnostic.get("rejection_stage") == "RR_GATE"
                else 2 if detail_admitted and detail_paper.get("paper_status") == "PAPER_PLAN_READY"
                else 1 if detail_admitted
                else 0
            )
            if detail_priority == 0:
                continue
            detail_rank = (detail_priority, int(detail_row.closed_until_ms))
            detail_previous = detail_source_by_symbol.get(detail_row.symbol)
            if detail_previous is None or detail_rank > detail_previous[0]:
                detail_source_by_symbol[detail_row.symbol] = (
                    detail_rank,
                    detail_row.run_id,
                    int(detail_row.closed_until_ms),
                )
    detail_boundaries = {
        value[2] for value in detail_source_by_symbol.values()
    }
    historical_plan_boundaries_4h = {
        int(row.closed_until_ms)
        for row, _result in rows
        if now_ms - 4 * 60 * 60 * 1000 <= int(row.closed_until_ms) <= now_ms
        and _stage_trace(row, _result, now_ms)[0]["PAPER_TRADE_PLAN"] == "PASS"
    }
    cycle_cache: dict[int, dict[str, Any]] = {}

    def cycle(boundary: int | None) -> dict[str, Any] | None:
        if boundary is None:
            return None
        if boundary in cycle_cache:
            return cycle_cache[boundary]
        pairs = by_boundary[boundary]
        items, counts = [], Counter()
        downstream_counts, downstream_rejected = Counter(), Counter()
        downstream_observed = Counter()
        downstream_reasons: dict[str, Counter[str]] = {
            stage: Counter() for stage in CANONICAL_DOWNSTREAM_STAGES
        }
        candidates = []
        latest_update = boundary
        for row, result in pairs:
            trace, meta = _stage_trace(row, result, now_ms)
            downstream_trace, downstream_detail = _downstream_trace(
                result,
                trace,
                scalping=profile.trigger_timeframe == "5m",
                now_ms=now_ms,
                include_detail=boundary in {
                    current_boundary, last_completed_boundary
                } or boundary in detail_boundaries
                or boundary in historical_plan_boundaries_4h,
            )
            candidate = eligible_by_run.get(row.run_id)
            production_eligibility = production_eligibility_by_run.get(row.run_id)
            if candidate is None and profile.mode == TradeProfileMode.SHADOW_SEARCH.value:
                candidate = _shadow_candidate(row, result, trace, now_ms)
            if candidate is not None and not meta.get("validity_current", False):
                candidate = None
            if candidate is not None:
                trace["ELIGIBLE"] = "PASS"
                candidates.append(candidate)
            elif trace["FINAL_APPROVAL"] == "PASS":
                trace["ELIGIBLE"] = "REJECTED"
            for stage, status in trace.items():
                if status == "PASS":
                    counts[stage] += 1
            for stage, status in downstream_trace.items():
                if status not in {"NOT_APPLICABLE", "UNAVAILABLE"}:
                    downstream_observed[stage] += 1
                if status == "PASS":
                    downstream_counts[stage] += 1
                elif status in {"REJECTED", "ERROR", "DEFERRED"}:
                    downstream_rejected[stage] += 1
            updated_ms = max(filter(None, (_ms(row.updated_at), _ms(row.finished_at), _ms(result.created_at) if result else None)), default=boundary)
            latest_update = max(latest_update, updated_ms)
            reason = meta.get("forced_reason") or _specific_terminal_reason(
                row, result, downstream_trace
            )
            for stage, status in downstream_trace.items():
                if status in {"REJECTED", "ERROR", "DEFERRED"} and reason:
                    downstream_reasons[stage][str(reason)] += 1
            generation = _mapping(
                _mapping(result.paper_payload_json).get("final_approval_generation")
            ) if result is not None else {}
            reason_detail = generation.get("safe_reason_detail") or reason
            profile_contexts = _profile_screen_contexts(
                row, result, terminal_reason=reason
            )
            lifecycle = dict(lifecycle_by_run.get(row.run_id, {}))
            execution_terminal = lifecycle.get("terminal_result")
            persisted_execution_terminal = execution_terminal
            if (
                execution_terminal is None
                and trace["FINAL_APPROVAL"] == "PASS"
                and not meta.get("validity_current", False)
                and lifecycle.get("command_id") is None
            ):
                execution_terminal = "EXPIRED_BEFORE_EXECUTION"
            if persisted_execution_terminal is not None:
                # A persisted execution result is authoritative after selection.
                # Approval TTL may elapse later, but it must not overwrite an
                # already-created command/position with APPROVAL_EXPIRED in UI.
                reason = execution_terminal
                reason_detail = execution_terminal
                profile_contexts = _profile_screen_contexts(
                    row, result, terminal_reason=reason
                )
            execution_lifecycle_state = lifecycle.get("lifecycle_state")
            if lifecycle.get("position_id") is not None:
                execution_lifecycle_state = "EXECUTED_TO_PAPER_POSITION"
            elif execution_lifecycle_state is None and execution_terminal:
                execution_lifecycle_state = execution_terminal
            current_stage = next((stage for stage in reversed(STAGES[:-1]) if trace[stage] != "NOT_REACHED"), "ANALYSIS")
            items.append({
                "symbol": row.symbol, "source_run_id": row.run_id,
                "candidate_id": meta.get("candidate_id"), "direction": meta.get("direction"),
                "current_stage": current_stage, "stage_status": trace[current_stage],
                "source_reason_code": reason, "source_reason_detail_safe": reason_detail,
                "ui_reason_category": current_stage, "final_approval_id": meta.get("final_approval_id"),
                "eligible": candidate is not None, "selector_rank": None, "selected_winner": False,
                "execution_eligible": (
                    profile.mode != TradeProfileMode.SHADOW_SEARCH.value
                    and candidate is not None
                ),
                "production_eligibility_outcome": (
                    "NOT_APPLICABLE"
                    if profile.mode == TradeProfileMode.SHADOW_SEARCH.value
                    else getattr(
                        getattr(production_eligibility, "outcome", None),
                        "value",
                        "NOT_CLASSIFIED",
                    )
                ),
                "production_eligibility_classified_at_ms": getattr(
                    production_eligibility, "classified_at_ms", None
                ),
                "production_eligibility_first_rejection_reason": (
                    None
                    if production_eligibility is None
                    or getattr(production_eligibility, "candidate", None) is not None
                    else getattr(
                        getattr(production_eligibility, "outcome", None),
                        "value",
                        None,
                    )
                ),
                "source_market_data_snapshot_id": getattr(
                    production_eligibility, "source_market_data_snapshot_id", None
                ),
                "approval_valid_until_ms": getattr(
                    production_eligibility, "valid_until_ms", None
                ) or lifecycle.get("approval_valid_until_ms"),
                "updated_at_ms": updated_ms, "stage_trace": trace,
                "downstream_stage_trace": downstream_trace,
                "downstream_current_stage": next(
                    (
                        stage for stage in reversed(CANONICAL_DOWNSTREAM_STAGES)
                        if downstream_trace[stage]
                        not in {"NOT_REACHED", "NOT_APPLICABLE", "UNAVAILABLE"}
                    ),
                    "ANALYSIS_QUALIFIED",
                ),
                "terminal_reason_code": execution_terminal or reason,
                "downstream_detail": {
                    "profile": profile.trade_profile_id,
                    "cycle_boundary_ms": boundary,
                    **downstream_detail,
                    "terminal_reason": execution_terminal or reason,
                    "updated_at_ms": updated_ms,
                    "plan_status": downstream_trace["PAPER_PLAN"],
                    "plan_state": downstream_trace["PAPER_PLAN"],
                    "quantity_approval_status": trace["QUANTITY_APPROVED"],
                    "final_approval_status": downstream_trace["FINAL_APPROVAL"],
                    "execution_intent": lifecycle.get(
                        "execution_intent", "NOT_REACHED"
                    ),
                    "selector_state": lifecycle.get(
                        "selector_state",
                        (
                            "EXPIRED"
                            if profile.trade_profile_id == "trade-5m-v2"
                            and execution_terminal == "EXPIRED_BEFORE_EXECUTION"
                            else "NOT_REACHED"
                            if profile.trade_profile_id == "trade-5m-v2"
                            else "LEGACY_NOT_OBSERVED"
                            if execution_terminal
                            else "NOT_REACHED"
                        ),
                    ),
                    "selector_reason": lifecycle.get("selector_reason"),
                    "selector_rank": lifecycle.get("selector_rank"),
                    "selected_winner": lifecycle.get("selected_winner"),
                    "command_id": lifecycle.get("command_id"),
                    "command_status": lifecycle.get("command_status", "NOT_REACHED"),
                    "command_state": lifecycle.get("command_status", "NOT_REACHED"),
                    "order_id": lifecycle.get("order_id"),
                    "order_status": lifecycle.get("order_status", "NOT_REACHED"),
                    "fill_id": lifecycle.get("fill_id"),
                    "fill_status": lifecycle.get("fill_status", "NOT_REACHED"),
                    "position_id": lifecycle.get("position_id"),
                    "position_status": (
                        lifecycle.get("position_status")
                        or ("OPENED" if row.position_opened else "NOT_REACHED")
                    ),
                    "position_state": (
                        lifecycle.get("position_status")
                        or ("OPENED" if row.position_opened else "NOT_REACHED")
                    ),
                    "execution_block_reason": (
                        execution_terminal
                        if execution_lifecycle_state == "BLOCKED_BY_POLICY"
                        else None
                    ),
                    "budget_state": (
                        f"BLOCKED:{execution_terminal}"
                        if execution_terminal in {
                            "DAILY_COMMAND_BUDGET_EXHAUSTED",
                            "DAILY_LOSS_BUDGET_EXHAUSTED",
                            "DAILY_RISK_BUDGET_EXHAUSTED",
                            "MAX_CONSECUTIVE_LOSSES_REACHED",
                        }
                        else "NOT_BLOCKED"
                    ),
                    "execution_terminal_result": execution_terminal,
                    "execution_lifecycle_state": execution_lifecycle_state,
                    "execution_attempt_count": lifecycle.get("attempt_count", 0),
                    "control_generation": lifecycle.get("control_generation"),
                    "policy_evaluated_at": lifecycle.get("policy_evaluated_at"),
                    "policy_generation": lifecycle.get("policy_generation"),
                    "policy_reason_source": lifecycle.get("policy_reason_source"),
                    "policy_source_timestamp": lifecycle.get("policy_source_timestamp"),
                },
                "risk_score": meta.get("risk_score"), "strategy_score": meta.get("strategy_score"),
                "planned_risk_reward": meta.get("planned_risk_reward"),
                **profile_contexts,
            })
        materialized_symbols = {item["symbol"] for item in items}
        for symbol in universe.symbols:
            if symbol in materialized_symbols:
                continue
            trace = {stage: "NOT_REACHED" for stage in STAGES}
            downstream_trace = {
                stage: "NOT_REACHED" for stage in CANONICAL_DOWNSTREAM_STAGES
            }
            placeholder_id = (
                f"not-reached:{profile.trade_profile_id}:{symbol}:{boundary}"
            )
            items.append({
                "symbol": symbol,
                "source_run_id": placeholder_id,
                "candidate_id": None,
                "direction": None,
                "current_stage": "ANALYSIS",
                "stage_status": "NOT_REACHED",
                "source_reason_code": "SYMBOL_NOT_REACHED_AT_BOUNDARY",
                "source_reason_detail_safe": "no pipeline run exists for this symbol and boundary",
                "ui_reason_category": "ANALYSIS",
                "final_approval_id": None,
                "eligible": False,
                "selector_rank": None,
                "selected_winner": False,
                "execution_eligible": False,
                "production_eligibility_outcome": "NOT_CLASSIFIED",
                "production_eligibility_classified_at_ms": None,
                "production_eligibility_first_rejection_reason": None,
                "source_market_data_snapshot_id": None,
                "approval_valid_until_ms": None,
                "updated_at_ms": boundary,
                "stage_trace": trace,
                "downstream_stage_trace": downstream_trace,
                "downstream_current_stage": "ANALYSIS_QUALIFIED",
                "terminal_reason_code": "SYMBOL_NOT_REACHED_AT_BOUNDARY",
                "downstream_detail": {
                    "profile": profile.trade_profile_id,
                    "cycle_boundary_ms": boundary,
                    "terminal_reason": "SYMBOL_NOT_REACHED_AT_BOUNDARY",
                    "updated_at_ms": boundary,
                    "plan_status": "NOT_REACHED",
                    "quantity_approval_status": "NOT_REACHED",
                    "final_approval_status": "NOT_REACHED",
                    "execution_intent": "NOT_REACHED",
                    "command_id": None,
                    "command_status": "NOT_REACHED",
                    "order_id": None,
                    "order_status": "NOT_REACHED",
                    "fill_id": None,
                    "fill_status": "NOT_REACHED",
                    "position_id": None,
                    "position_status": "NOT_REACHED",
                    "execution_terminal_result": None,
                },
                "risk_score": None,
                "strategy_score": None,
                "planned_risk_reward": None,
                "profile_market": {},
                "profile_analysis": {},
                "profile_scenario": {},
            })
        selection = ProductionEligibleApprovalSelector().select(candidates, policy_version=MULTI_SYMBOL_SELECTION_POLICY_VERSION)
        ordered = sorted(candidates, key=lambda c: (
            -c.ranking.risk_score, -c.ranking.planned_risk_reward, -c.ranking.strategy_score,
            -c.ranking.closed_until_ms, c.ranking.source_run_id, c.ranking.final_approval_id,
            c.candidate_id, c.symbol,
        )) if not selection.failure_code else []
        ranks = {item.lineage.source_run_id: index + 1 for index, item in enumerate(ordered)}
        projected_winner = None
        for item in items:
            lifecycle = lifecycle_by_run.get(item["source_run_id"], {})
            if profile.mode == TradeProfileMode.SHADOW_SEARCH.value:
                item["selector_rank"] = ranks.get(item["source_run_id"])
                item["selected_winner"] = bool(
                    selection.winner
                    and item["source_run_id"] == selection.winner.lineage.source_run_id
                )
            else:
                # Production SELECTED is the executor's persisted selection,
                # never a decorative historical replay of the ranker.
                item["selector_rank"] = lifecycle.get("selector_rank")
                item["selected_winner"] = lifecycle.get("selected_winner") is True
            if item["selected_winner"]:
                projected_winner = item
                item["stage_trace"]["SELECTOR_WINNER"] = "PASS"
                counts["SELECTOR_WINNER"] += 1
                item["current_stage"] = "SELECTOR_WINNER"
                item["stage_status"] = "PASS"
            elif item["eligible"]:
                item["current_stage"] = "ELIGIBLE"
                item["stage_status"] = "PASS"
        seen = {row.symbol for row, _ in pairs}
        processed = {row.symbol for row, _ in pairs if row.status in TERMINAL_RUN_STATUSES}
        value = {
            "boundary_close_ms": boundary, "boundary_start_ms": boundary - boundary_ms,
            "symbols_expected": len(universe.symbols), "symbols_seen": len(seen),
            "symbols_processed": len(processed), "cycle_complete": processed == set(universe.symbols),
            "stage_counts": {stage: counts[stage] for stage in STAGES},
            "downstream_stage_counts": {
                stage: (
                    downstream_counts[stage]
                    if downstream_observed[stage] else None
                )
                for stage in CANONICAL_DOWNSTREAM_STAGES
            },
            "stage_rejected_count": {
                stage: downstream_rejected[stage]
                for stage in CANONICAL_DOWNSTREAM_STAGES
                if downstream_observed[stage]
            },
            "dominant_rejection_reason": {
                stage: (
                    downstream_reasons[stage].most_common(1)[0][0]
                    if downstream_reasons[stage] else None
                )
                for stage in CANONICAL_DOWNSTREAM_STAGES
            },
            "items": sorted(
                items,
                key=lambda value: (
                    str(value["source_run_id"]).startswith("not-reached:"),
                    value["symbol"],
                ),
            ),
            "eligible_competitors": [{"rank": ranks[item.lineage.source_run_id], "symbol": item.symbol,
                                      "candidate_id": item.candidate_id, "final_approval_id": item.lineage.final_approval_id}
                                     for item in ordered],
            "winner_symbol": projected_winner["symbol"] if projected_winner else None,
            "winner_candidate_id": (
                lifecycle_by_run.get(projected_winner["source_run_id"], {}).get("candidate_id")
                if projected_winner else None
            ) or (projected_winner["candidate_id"] if projected_winner else None),
            "latest_pipeline_update_ms": latest_update,
        }
        cycle_cache[boundary] = value
        return value

    def rolling(window_ms: int) -> dict[str, Any]:
        selected = [pair for boundary, pairs in by_boundary.items() if now_ms - window_ms <= boundary <= now_ms for pair in pairs]
        selected_boundaries = {row.closed_until_ms for row, _ in selected}
        completed = sum(
            1 for boundary in selected_boundaries
            if {row.symbol for row, _ in by_boundary[boundary] if row.status in TERMINAL_RUN_STATUSES} == set(universe.symbols)
        )
        counts = Counter()
        downstream_counts, downstream_rejected = Counter(), Counter()
        downstream_observed = Counter()
        downstream_reasons: dict[str, Counter[str]] = {
            stage: Counter() for stage in CANONICAL_DOWNSTREAM_STAGES
        }
        for row, result in selected:
            trace, _ = _stage_trace(row, result, now_ms)
            downstream_trace, _ = _downstream_trace(
                result,
                trace,
                scalping=profile.trigger_timeframe == "5m",
                now_ms=now_ms,
                include_detail=False,
            )
            if row.run_id in eligible_by_run or (
                profile.mode == TradeProfileMode.SHADOW_SEARCH.value
                and _shadow_candidate(row, result, trace, now_ms) is not None
            ):
                trace["ELIGIBLE"] = "PASS"
            for stage, status in trace.items():
                if status == "PASS": counts[stage] += 1
            reason = _specific_terminal_reason(row, result, downstream_trace)
            for stage, status in downstream_trace.items():
                if status not in {"NOT_APPLICABLE", "UNAVAILABLE"}:
                    downstream_observed[stage] += 1
                if status == "PASS":
                    downstream_counts[stage] += 1
                elif status in {"REJECTED", "ERROR", "DEFERRED"}:
                    downstream_rejected[stage] += 1
                    if reason:
                        downstream_reasons[stage][str(reason)] += 1
        selected_run_ids = {row.run_id for row, _result in selected}
        execution = tuple(
            lifecycle_by_run[run_id]
            for run_id in selected_run_ids
            if run_id in lifecycle_by_run
        )
        selector_winner_count = sum(
            bool(value.get("selected_winner")) for value in execution
        )
        command_count = sum(value.get("command_id") is not None for value in execution)
        position_open_count = sum(value.get("position_id") is not None for value in execution)
        position_closed_count = sum(
            value.get("position_status") == "CLOSED" for value in execution
        )
        stage_passage_count = {
            "analysis": counts["ANALYSIS"],
            "setup": counts["STRUCTURAL_SETUP"],
            "geometry": downstream_counts["GEOMETRY_VALID"],
            "target": downstream_counts["TARGET_VALID"],
            "final_pick": downstream_counts["FINAL_CHECK_PASS"],
            "approval": counts["FINAL_APPROVAL"],
            "plan": counts["PAPER_TRADE_PLAN"],
        }
        scale = (60 * 60 * 1000) / window_ms
        per_hour = {
            **{name: value * scale for name, value in stage_passage_count.items()},
            "selected": selector_winner_count * scale,
            "command": command_count * scale,
            "position_open": position_open_count * scale,
            "position_closed": position_closed_count * scale,
        }
        return {"window_ms": window_ms, "boundary_count": len(selected_boundaries),
                "completed_cycle_count": completed,
                "stage_counts": {stage: counts[stage] for stage in STAGES[:-2]},
                "downstream_stage_counts": {
                    stage: downstream_counts[stage] if downstream_observed[stage] else None
                    for stage in CANONICAL_DOWNSTREAM_STAGES
                },
                "stage_rejected_count": {
                    stage: downstream_rejected[stage]
                    for stage in CANONICAL_DOWNSTREAM_STAGES
                    if downstream_observed[stage]
                },
                "dominant_rejection_reason": {
                    stage: downstream_reasons[stage].most_common(1)[0][0]
                    if downstream_reasons[stage] else None
                    for stage in CANONICAL_DOWNSTREAM_STAGES
                },
                "cadence": {
                    "profile_id": profile.trade_profile_id,
                    "profile_version": profile.trade_profile_id.rsplit("-", 1)[-1],
                    "window_ms": window_ms,
                    "per_hour": per_hour,
                    "stage_passage_count": stage_passage_count,
                    "selector_winner_count": selector_winner_count,
                    "command_count": command_count,
                    "trade_count": position_open_count,
                    "position_closed_count": position_closed_count,
                }}

    current = cycle(current_boundary)
    detail_by_symbol: dict[str, dict[str, Any]] = {}
    for detail_symbol, (_rank, detail_run_id, detail_boundary) in (
        detail_source_by_symbol.items()
    ):
        detail_cycle = cycle(detail_boundary)
        if detail_cycle is None:
            continue
        detail_item = next(
            (
                item for item in detail_cycle["items"]
                if item["source_run_id"] == detail_run_id
            ),
            None,
        )
        if detail_item is not None:
            detail_by_symbol[detail_symbol] = detail_item
    latest = current["latest_pipeline_update_ms"] if current else None
    historical_paper_plans_4h: list[dict[str, Any]] = []
    for boundary, pairs in sorted(by_boundary.items(), reverse=True):
        if not now_ms - 4 * 60 * 60 * 1000 <= boundary <= now_ms:
            continue
        plan_run_ids = {
            row.run_id for row, result in pairs
            if _stage_trace(row, result, now_ms)[0]["PAPER_TRADE_PLAN"] == "PASS"
        }
        if not plan_run_ids:
            continue
        plan_cycle = cycle(boundary)
        historical_paper_plans_4h.extend(
            item for item in plan_cycle["items"]
            if item["source_run_id"] in plan_run_ids
        )
    age = None if latest is None else max(0, now_ms - latest)
    metric_stages = {
        "analysis_count": "ANALYSIS",
        "setup_count": "STRUCTURAL_SETUP",
        "strategy_approval_count": "STRATEGY_ELIGIBLE",
        "risk_approval_count": "RISK_APPROVED",
        "paper_plan_count": "PAPER_TRADE_PLAN",
        "quantity_approval_count": "QUANTITY_APPROVED",
        "validity_approval_count": "VALIDITY_APPROVED",
        "final_approval_count": "FINAL_APPROVAL",
    }
    metrics = Counter()
    for row, result in (pair for pairs in by_boundary.values() for pair in pairs):
        trace, _ = _stage_trace(row, result, now_ms)
        for metric, stage in metric_stages.items():
            metrics[metric] += int(trace[stage] == "PASS")
        if result is not None:
            shadow_candidate = _mapping(
                _mapping(result.paper_payload_json).get("shadow_final_approval_candidate")
            )
            metrics["shadow_final_approval_candidate_count"] += int(
                shadow_candidate.get("status") in {"CANDIDATE", "PLAN_READY", "ELIGIBLE"}
            )
    freshness_state = "NOT_AVAILABLE" if age is None else "CURRENT" if age <= boundary_ms * 2 else "STALE"
    return {
        "projection_version": PROJECTION_VERSION,
        "trade_profile_id": profile.trade_profile_id,
        "trade_mode": profile.trade_mode,
        "display_i18n_key": profile.display_i18n_key,
        "primary_timeframe": profile.primary_timeframe,
        "entry_timeframes": list(profile.entry_timeframes),
        "context_timeframes": list(profile.context_timeframes),
        "trigger_timeframe": profile.trigger_timeframe,
        "profile_mode": profile.mode,
        "decision_timeframe": profile.trigger_timeframe,
        "universe_id": universe.version_id,
        "universe_symbols": list(universe.symbols),
        "selection_policy_version": MULTI_SYMBOL_SELECTION_POLICY_VERSION,
        "count_unit": {stage: "SYMBOL" for stage in STAGES},
        "downstream_stage_order": list(CANONICAL_DOWNSTREAM_STAGES),
        "downstream_count_unit": {
            stage: "SYMBOL" for stage in CANONICAL_DOWNSTREAM_STAGES
        },
        "current_cycle": current, "last_completed_cycle": cycle(last_completed_boundary),
        "detail_candidates": [
            detail_by_symbol[symbol]
            for symbol in universe.symbols
            if symbol in detail_by_symbol
        ],
        "historical_paper_plans_4h": historical_paper_plans_4h,
        "rolling_1h": rolling(60 * 60 * 1000), "rolling_4h": rolling(4 * 60 * 60 * 1000),
        "projection_generated_at_ms": now_ms, "latest_pipeline_update_ms": latest,
        "age_ms": age, "freshness_state": freshness_state,
        "query_time_horizon_ms": max_horizon_ms,
        "expected_1h_cycle_count": 12 if profile.trigger_timeframe == "5m" else 4,
        "expected_4h_cycle_count": 48 if profile.trigger_timeframe == "5m" else 16,
        "paper_command_creation_enabled": profile.paper_command_creation_enabled,
        "position_opening_enabled": profile.position_opening_enabled,
        "profile_metrics": {
            "trade_profile_id": profile.trade_profile_id,
            "profile_version": profile.trade_profile_id.rsplit("-", 1)[-1],
            "trade_mode": profile.trade_mode,
            "trigger_timeframe": profile.trigger_timeframe,
            **{name: metrics[name] for name in metric_stages},
            "shadow_final_approval_candidate_count": metrics["shadow_final_approval_candidate_count"],
        },
        "profile_health": {
            "trade_profile_id": profile.trade_profile_id,
            "trade_mode": profile.trade_mode,
            "trigger_timeframe": profile.trigger_timeframe,
            "mode": profile.mode,
            "last_completed_boundary_ms": complete_boundaries[0] if complete_boundaries else None,
            "last_batch_size": current["symbols_processed"] if current else 0,
            "health": freshness_state,
        },
    }
