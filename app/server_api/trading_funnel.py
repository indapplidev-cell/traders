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
    failures.  In particular, Portfolio has no independent persisted decision in
    the current pipeline and therefore remains UNAVAILABLE instead of a false 0.
    """
    if not scalping:
        return (
            {stage: "NOT_APPLICABLE" for stage in CANONICAL_DOWNSTREAM_STAGES},
            {},
        )

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
    diagnostic = _mapping(context.get("scalping_geometry_diagnostics"))
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
                "PASS" if diagnostic.get("stop_envelope_pass") is True
                else "REJECTED"
            )
        else:
            trace["GEOMETRY_VALID"] = "UNAVAILABLE"
    if trace["GEOMETRY_VALID"] == "PASS":
        if diagnostic.get("causal_target_exists") is True:
            trace["TARGET_VALID"] = "PASS"
        elif diagnostic:
            trace["TARGET_VALID"] = "REJECTED"
        else:
            trace["TARGET_VALID"] = "UNAVAILABLE"
    if trace["TARGET_VALID"] == "PASS":
        if diagnostic.get("economic_gate_pass") is True:
            trace["NET_COST_PASS"] = "PASS"
        elif diagnostic:
            trace["NET_COST_PASS"] = "REJECTED"
        else:
            trace["NET_COST_PASS"] = "UNAVAILABLE"
    if trace["NET_COST_PASS"] == "PASS":
        if diagnostic.get("valid_plan") is True:
            trace["RR_PASS"] = "PASS"
        elif diagnostic:
            trace["RR_PASS"] = "REJECTED"
        else:
            trace["RR_PASS"] = "UNAVAILABLE"

    authoritative_risk = _mapping(approvals.get("paper_risk_approval"))
    if authoritative_risk:
        trace["RISK_ADMITTED"] = "PASS"
    elif trace["RR_PASS"] == "PASS":
        # A missing approval is not proof of an authoritative rejection.
        trace["RISK_ADMITTED"] = "UNAVAILABLE"

    # Portfolio is not independently serialized by the current pipeline.  A
    # final approval proves the full final materialization succeeded, but it
    # does not justify inventing a distinct Portfolio decision.
    trace["PORTFOLIO_ADMITTED"] = "UNAVAILABLE"
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
        planned.get("hypothetical_stop_level"), diagnostic.get("final_stop")
    )
    target = _first_present(
        planned.get("hypothetical_target_level"), diagnostic.get("causal_target")
    )
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
        "opportunity_id": diagnostic.get("opportunity_id") or setup.get("setup_id"),
        "paper_plan_id": planned.get("paper_plan_id"),
        "setup_type": setup.get("setup_type"),
        "strategy_type": strategy.get("strategy_type") or strategy.get("source_strategy_type"),
        "strategy_score": strategy.get("strategy_final_score") or strategy.get("strategy_score"),
        "strategy_admission": trace["STRATEGY_ADMITTED"],
        "risk_compatibility": risk.get("risk_status"),
        "entry_price": entry,
        "entry_source": planned.get("entry_reference_source"),
        "stop_price": stop,
        "stop_source": planned.get("stop_source"),
        "stop_distance_absolute": _absolute_distance(entry, stop),
        "geometry_status": trace["GEOMETRY_VALID"],
        "geometry_reason": geometry_reason,
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
        "target_source": diagnostic.get("target_source_type"),
        "spread_bps": diagnostic.get("spread_bps"),
        "depth_impact_bps": diagnostic.get("depth_impact_bps"),
        "entry_fee_bps": diagnostic.get("entry_fee_bps"),
        "exit_fee_bps": diagnostic.get("exit_fee_bps"),
        "fee_estimate_bps": _sum_decimals(
            diagnostic.get("entry_fee_bps"), diagnostic.get("exit_fee_bps")
        ),
        "entry_slippage_bps": diagnostic.get("entry_slippage_bps"),
        "exit_slippage_bps": diagnostic.get("exit_slippage_bps"),
        "slippage_estimate_bps": _sum_decimals(
            diagnostic.get("entry_slippage_bps"),
            diagnostic.get("exit_slippage_bps"),
        ),
        "safety_margin_bps": diagnostic.get("safety_margin_bps"),
        "total_modeled_cost_bps": diagnostic.get("total_cost_bps"),
        "gross_rr": _first_present(
            diagnostic.get("gross_rr"), planned.get("planned_rr")
        ),
        "net_rr": diagnostic.get("net_rr"),
        "required_rr": required_rr,
        "expected_net_edge_bps": diagnostic.get("expected_net_edge_bps"),
        "break_even_win_rate": diagnostic.get("break_even_win_rate"),
        "rr_status": trace["RR_PASS"],
        "rr_reason": geometry_reason if trace["RR_PASS"] == "REJECTED" else None,
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
        "portfolio": None,
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
    ) -> None:
        self._session_factory = session_factory
        self._universe_source = universe_source
        self._schema_capabilities = schema_capabilities
        self._monotonic = monotonic_clock
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
                            OnlinePipelineResultRow.run_id == OnlinePipelineRun.run_id,
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
                if classified.candidate is not None:
                    eligible_by_run[classified.source_run_id] = classified.candidate
        return build_projection(rows, universe, now_ms, eligible_by_run, profile.trade_profile_id)

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
            .outerjoin(OnlinePipelineResultRow, OnlinePipelineResultRow.run_id == OnlinePipelineRun.run_id)
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
                     trade_profile_id: str = DEFAULT_TRADE_PROFILE_ID) -> dict[str, Any]:
    profile = resolve_trade_profile(trade_profile_id)
    boundary_ms = 5 * 60 * 1000 if profile.trigger_timeframe == "5m" else BOUNDARY_MS
    max_horizon_ms = 4 * 60 * 60 * 1000 + boundary_ms
    eligible_by_run = eligible_by_run or {}
    by_boundary: dict[int, list[tuple[OnlinePipelineRun, OnlinePipelineResultRow | None]]] = {}
    for pair in rows:
        by_boundary.setdefault(int(pair[0].closed_until_ms), []).append(pair)
    boundaries = sorted(by_boundary, reverse=True)
    current_boundary = boundaries[0] if boundaries else None
    complete_boundaries = [boundary for boundary in boundaries if {
        row.symbol for row, _ in by_boundary[boundary] if row.status in TERMINAL_RUN_STATUSES
    } == set(universe.symbols)]
    last_completed_boundary = next((value for value in complete_boundaries if value != current_boundary), None)
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
                },
            )
            candidate = eligible_by_run.get(row.run_id)
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
                "terminal_reason_code": reason,
                "downstream_detail": {
                    "profile": profile.trade_profile_id,
                    "cycle_boundary_ms": boundary,
                    **downstream_detail,
                    "terminal_reason": reason,
                    "updated_at_ms": updated_ms,
                    "plan_status": downstream_trace["PAPER_PLAN"],
                    "quantity_approval_status": trace["QUANTITY_APPROVED"],
                    "final_approval_status": downstream_trace["FINAL_APPROVAL"],
                    "order_status": "UNAVAILABLE",
                    "fill_status": "UNAVAILABLE",
                    "position_status": (
                        "OPENED" if row.position_opened else "NOT_OPENED"
                    ),
                },
                "risk_score": meta.get("risk_score"), "strategy_score": meta.get("strategy_score"),
                "planned_risk_reward": meta.get("planned_risk_reward"),
            })
        selection = ProductionEligibleApprovalSelector().select(candidates, policy_version=MULTI_SYMBOL_SELECTION_POLICY_VERSION)
        ordered = sorted(candidates, key=lambda c: (
            -c.ranking.risk_score, -c.ranking.planned_risk_reward, -c.ranking.strategy_score,
            -c.ranking.closed_until_ms, c.ranking.source_run_id, c.ranking.final_approval_id,
            c.candidate_id, c.symbol,
        )) if not selection.failure_code else []
        ranks = {item.lineage.source_run_id: index + 1 for index, item in enumerate(ordered)}
        winner_run = selection.winner.lineage.source_run_id if selection.winner else None
        for item in items:
            item["selector_rank"] = ranks.get(item["source_run_id"])
            item["selected_winner"] = item["source_run_id"] == winner_run
            if item["selected_winner"]:
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
            "items": sorted(items, key=lambda value: value["symbol"]),
            "eligible_competitors": [{"rank": ranks[item.lineage.source_run_id], "symbol": item.symbol,
                                      "candidate_id": item.candidate_id, "final_approval_id": item.lineage.final_approval_id}
                                     for item in ordered],
            "winner_symbol": selection.winner.symbol if selection.winner else None,
            "winner_candidate_id": selection.winner.candidate_id if selection.winner else None,
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
                }}

    current = cycle(current_boundary)
    detail_by_symbol: dict[str, tuple[tuple[int, int], dict[str, Any]]] = {}
    for detail_boundary in boundaries:
        detail_cycle = cycle(detail_boundary)
        if detail_cycle is None:
            continue
        for item in detail_cycle["items"]:
            downstream = item["downstream_stage_trace"]
            priority = (
                3 if downstream.get("PAPER_PLAN") == "PASS"
                else 2 if downstream.get("RR_PASS") == "REJECTED"
                else 1 if downstream.get("STRATEGY_ADMITTED") == "PASS"
                else 0
            )
            if priority == 0:
                continue
            rank = (priority, detail_boundary)
            previous = detail_by_symbol.get(item["symbol"])
            if previous is None or rank > previous[0]:
                detail_by_symbol[item["symbol"]] = (rank, item)
    pair_by_run = {row.run_id: (row, result) for row, result in rows}
    for _rank, item in detail_by_symbol.values():
        if "entry_price" in item["downstream_detail"]:
            continue
        source_pair = pair_by_run.get(item["source_run_id"])
        if source_pair is None:
            continue
        source_row, source_result = source_pair
        source_trace, _meta = _stage_trace(source_row, source_result, now_ms)
        _source_downstream, source_detail = _downstream_trace(
            source_result,
            source_trace,
            scalping=profile.trigger_timeframe == "5m",
            now_ms=now_ms,
        )
        item["downstream_detail"].update(source_detail)
    latest = current["latest_pipeline_update_ms"] if current else None
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
        "universe_id": universe.version_id, "selection_policy_version": MULTI_SYMBOL_SELECTION_POLICY_VERSION,
        "count_unit": {stage: "SYMBOL" for stage in STAGES},
        "downstream_stage_order": list(CANONICAL_DOWNSTREAM_STAGES),
        "downstream_count_unit": {
            stage: "SYMBOL" for stage in CANONICAL_DOWNSTREAM_STAGES
        },
        "current_cycle": current, "last_completed_cycle": cycle(last_completed_boundary),
        "detail_candidates": [
            detail_by_symbol[symbol][1]
            for symbol in universe.symbols
            if symbol in detail_by_symbol
        ],
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
