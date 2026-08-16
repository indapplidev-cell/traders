"""Bounded read-only projection of the persisted 15m trading funnel."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine_orchestrator.orchestrator_models import OnlinePipelineResultRow, OnlinePipelineRun
from app.engine_paper.eligible_approval_ranking import (
    MULTI_SYMBOL_SELECTION_POLICY_VERSION,
    ProductionEligibleApprovalSelector,
)
from app.engine_paper.production_approval import (
    PaperProductionApprovalRequest,
    PaperProductionApprovalScope,
    PaperProductionApprovalSourceAdapter,
)
from app.trading_universe.domain import TradingUniverseVersion


PROJECTION_VERSION: Final = "trading-funnel-v1"
PRIMARY_TIMEFRAME: Final = "15m"
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


def _first_reason(row: OnlinePipelineRun, result: OnlinePipelineResultRow | None) -> str | None:
    if row.error_code:
        return row.error_code
    if result is not None:
        generation = _mapping(_mapping(result.paper_payload_json).get("final_approval_generation"))
        if generation.get("outcome") not in (None, "FINAL_APPROVAL_CREATED", "NOT_ELIGIBLE"):
            return str(generation.get("reason_code") or generation["outcome"])
        reasons = _mapping(result.module_reasons_json)
        for stage in ("paper", "risk", "strategy", "setup", "analysis"):
            values = _reasons(reasons.get(stage))
            if values:
                return values[0]
    return row.final_reason


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
    trace["PAPER_TRADE_PLAN"] = "PASS" if str(row.paper_status or paper.get("paper_status") or "") == "PAPER_PLAN_READY" else "REJECTED"
    if trace["PAPER_TRADE_PLAN"] != "PASS":
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
    trace["VALIDITY_APPROVED"] = "PASS" if valid_until_ms is not None and valid_until_ms > now_ms else "REJECTED"
    trace["FINAL_APPROVAL"] = "PASS" if len(approvals) == 3 else "NOT_REACHED"
    meta.update({
        "final_approval_id": generation.get("final_approval_id") or risk_approval.get("approval_id"),
        "valid_until_ms": valid_until_ms,
        "risk_score": risk.get("risk_score"),
        "strategy_score": strategy.get("strategy_score"),
        "planned_risk_reward": paper.get("planned_risk_reward"),
    })
    if valid_until_ms is not None and valid_until_ms <= now_ms:
        meta["forced_reason"] = "APPROVAL_EXPIRED"
    return trace, meta


class TradingFunnelReadRepository:
    """One bounded query plus the existing production eligibility adapter."""

    def __init__(self, session_factory: Callable[[], Session], universe_source: Callable[[], TradingUniverseVersion]) -> None:
        self._session_factory = session_factory
        self._universe_source = universe_source

    def project(self, now_ms: int) -> dict[str, Any]:
        universe = self._universe_source()
        start_ms = now_ms - MAX_HORIZON_MS
        statement = (
            select(OnlinePipelineRun, OnlinePipelineResultRow)
            .outerjoin(OnlinePipelineResultRow, OnlinePipelineResultRow.run_id == OnlinePipelineRun.run_id)
            .where(
                OnlinePipelineRun.primary_timeframe == PRIMARY_TIMEFRAME,
                OnlinePipelineRun.symbol.in_(universe.symbols),
                OnlinePipelineRun.closed_until_ms >= start_ms,
                OnlinePipelineRun.closed_until_ms <= now_ms,
            )
            .order_by(OnlinePipelineRun.closed_until_ms.desc(), OnlinePipelineRun.symbol.asc())
            .limit(len(universe.symbols) * 18)
        )
        with self._session_factory() as session:
            rows = tuple(session.execute(statement))
        eligibility = PaperProductionApprovalSourceAdapter(self._session_factory).read(
            PaperProductionApprovalRequest(
                PaperProductionApprovalScope(symbols=universe.symbols, start_ms=start_ms),
                request_id="readonly-funnel", as_of_ms=now_ms,
            )
        )
        eligible_by_run = {item.source_run_id: item.candidate for item in eligibility.symbol_results if item.candidate is not None}
        return build_projection(rows, universe, now_ms, eligible_by_run)


def build_projection(rows: tuple[tuple[OnlinePipelineRun, OnlinePipelineResultRow | None], ...], universe: TradingUniverseVersion,
                     now_ms: int, eligible_by_run: Mapping[str, object] | None = None) -> dict[str, Any]:
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

    def cycle(boundary: int | None) -> dict[str, Any] | None:
        if boundary is None:
            return None
        pairs = by_boundary[boundary]
        items, counts = [], Counter()
        candidates = []
        latest_update = boundary
        for row, result in pairs:
            trace, meta = _stage_trace(row, result, now_ms)
            candidate = eligible_by_run.get(row.run_id)
            if candidate is not None:
                trace["ELIGIBLE"] = "PASS"
                candidates.append(candidate)
            elif trace["FINAL_APPROVAL"] == "PASS":
                trace["ELIGIBLE"] = "REJECTED"
            for stage, status in trace.items():
                if status == "PASS":
                    counts[stage] += 1
            updated_ms = max(filter(None, (_ms(row.updated_at), _ms(row.finished_at), _ms(result.created_at) if result else None)), default=boundary)
            latest_update = max(latest_update, updated_ms)
            reason = meta.get("forced_reason") or _first_reason(row, result)
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
                "updated_at_ms": updated_ms, "stage_trace": trace,
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
        return {
            "boundary_close_ms": boundary, "boundary_start_ms": boundary - BOUNDARY_MS,
            "symbols_expected": len(universe.symbols), "symbols_seen": len(seen),
            "symbols_processed": len(processed), "cycle_complete": processed == set(universe.symbols),
            "stage_counts": {stage: counts[stage] for stage in STAGES},
            "items": sorted(items, key=lambda value: value["symbol"]),
            "eligible_competitors": [{"rank": ranks[item.lineage.source_run_id], "symbol": item.symbol,
                                      "candidate_id": item.candidate_id, "final_approval_id": item.lineage.final_approval_id}
                                     for item in ordered],
            "winner_symbol": selection.winner.symbol if selection.winner else None,
            "winner_candidate_id": selection.winner.candidate_id if selection.winner else None,
            "latest_pipeline_update_ms": latest_update,
        }

    def rolling(window_ms: int) -> dict[str, Any]:
        selected = [pair for boundary, pairs in by_boundary.items() if now_ms - window_ms <= boundary <= now_ms for pair in pairs]
        counts = Counter()
        for row, result in selected:
            trace, _ = _stage_trace(row, result, now_ms)
            if row.run_id in eligible_by_run:
                trace["ELIGIBLE"] = "PASS"
            for stage, status in trace.items():
                if status == "PASS": counts[stage] += 1
        return {"window_ms": window_ms, "boundary_count": len({row.closed_until_ms for row, _ in selected}),
                "stage_counts": {stage: counts[stage] for stage in STAGES[:-2]}}

    current = cycle(current_boundary)
    latest = current["latest_pipeline_update_ms"] if current else None
    age = None if latest is None else max(0, now_ms - latest)
    return {
        "projection_version": PROJECTION_VERSION, "decision_timeframe": PRIMARY_TIMEFRAME,
        "universe_id": universe.version_id, "selection_policy_version": MULTI_SYMBOL_SELECTION_POLICY_VERSION,
        "count_unit": {stage: "SYMBOL" for stage in STAGES},
        "current_cycle": current, "last_completed_cycle": cycle(last_completed_boundary),
        "rolling_1h": rolling(60 * 60 * 1000), "rolling_4h": rolling(4 * 60 * 60 * 1000),
        "projection_generated_at_ms": now_ms, "latest_pipeline_update_ms": latest,
        "age_ms": age, "freshness_state": "NOT_AVAILABLE" if age is None else "CURRENT" if age <= BOUNDARY_MS * 2 else "STALE",
        "query_time_horizon_ms": MAX_HORIZON_MS,
    }
