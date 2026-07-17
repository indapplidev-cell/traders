"""Runner consuming only RiskDecision and emitting PaperTradePlan."""

from __future__ import annotations

import time
from collections.abc import AsyncIterable, AsyncIterator, Iterable

from app.engine_paper.paper_config import PaperConfig
from app.engine_paper.paper_context import PaperContext
from app.engine_paper.paper_errors import PaperLevelError
from app.engine_paper.paper_level_builder import PaperLevelBuilder
from app.engine_paper.paper_plan_policy import PaperPlanPolicy
from app.engine_paper.paper_plan_type import paper_plan_type_for
from app.engine_paper.paper_reason_codes import PaperReasonCode as R
from app.engine_paper.paper_store import PaperStore
from app.engine_paper.paper_trade_plan import PaperTradePlan, paper_plan_id
from app.engine_risk.risk_decision import RiskDecision


class PaperRunner:
    def __init__(self, config: PaperConfig | None = None, store: PaperStore | None = None) -> None:
        self.config = config or PaperConfig()
        self.policy = PaperPlanPolicy(self.config)
        self.level_builder = PaperLevelBuilder(self.config)
        self.store = store or PaperStore()

    def process_risk_decision(self, risk_decision: RiskDecision) -> PaperTradePlan:
        if not isinstance(risk_decision, RiskDecision):
            raise TypeError("risk_decision must be a RiskDecision")
        try:
            plan = self._process(risk_decision)
        except Exception as exc:
            plan = self._error_plan(risk_decision, exc)
        self.store.save(plan)
        return plan

    async def run_on_risk_decisions(
        self, decisions: AsyncIterable[RiskDecision] | Iterable[RiskDecision],
    ) -> AsyncIterator[PaperTradePlan]:
        if hasattr(decisions, "__aiter__"):
            async for decision in decisions:  # type: ignore[union-attr]
                yield self.process_risk_decision(decision)
        else:
            for decision in decisions:  # type: ignore[union-attr]
                yield self.process_risk_decision(decision)

    def _process(self, source: RiskDecision) -> PaperTradePlan:
        gate = self.policy.evaluate(source)
        if not gate.proceed:
            return self._base_plan(
                source, status=gate.status, quality=gate.quality,
                reasons=[gate.reason] if gate.reason else [],
                rejection=[gate.reason] if gate.status == "REJECT" and gate.reason else [],
                wait=[gate.reason] if gate.status == "WAIT" and gate.reason else [],
            )
        context = PaperContext.from_risk_decision(source)
        try:
            levels = self.level_builder.build(context, source.direction_hint)
        except PaperLevelError as exc:
            missing = exc.reason.startswith("PAPER_NO_PLAN_MISSING_")
            reasons = ([R.PAPER_NO_PLAN_MISSING_CAUSAL_LEVELS.value, exc.reason]
                       if missing else [exc.reason])
            return self._base_plan(
                source, status="NO_PLAN" if missing else "REJECT",
                quality="UNKNOWN" if missing else "REJECTED", reasons=reasons,
                rejection=[] if missing else [exc.reason], context=context,
            )
        low_risk_reason = (R.PAPER_PLAN_READY_LOW_RISK.value if source.risk_level == "LOW"
                           else R.PAPER_PLAN_READY_ACCEPTABLE_RISK.value)
        return self._base_plan(
            source, status="PAPER_PLAN_READY", quality=gate.quality, context=context,
            reasons=[low_risk_reason, R.PAPER_PLAN_READY_VALID_LEVELS.value,
                     R.PAPER_PLAN_READY_MIN_RR_MET.value],
            entry=levels.entry, invalidation=levels.invalidation, stop=levels.stop,
            target=levels.target, planned_rr=levels.planned_rr,
            entry_source=levels.entry_source, invalidation_source=levels.invalidation_source,
            stop_source=levels.stop_source, target_source=levels.target_source,
        )

    def _base_plan(self, source: RiskDecision, *, status: str, quality: str,
                   reasons: list[str], rejection: list[str] | None = None,
                   wait: list[str] | None = None, context: PaperContext | None = None,
                   entry: float | None = None, invalidation: float | None = None,
                   stop: float | None = None, target: float | None = None,
                   planned_rr: float | None = None, entry_source: str | None = None,
                   invalidation_source: str | None = None, stop_source: str | None = None,
                   target_source: str | None = None, warnings: list[str] | None = None) -> PaperTradePlan:
        confirmations = [R.PAPER_NO_FUTURE_BARS_USED.value, R.PAPER_ONLY_NOT_EXECUTABLE.value,
                         R.PAPER_NOT_ORDER_APPROVED.value, R.PAPER_NOT_POSITION_OPENED.value]
        direction = source.direction_hint if source.direction_hint in {
            "BULLISH", "BEARISH", "NEUTRAL", "NONE"} else "NONE"
        return PaperTradePlan(
            paper_plan_id=paper_plan_id(source.symbol, source.timeframe, source.closed_until_ms,
                                        source.risk_decision_id),
            created_at_ms=time.time_ns() // 1_000_000,
            source_risk_decision_id=source.risk_decision_id,
            source_strategy_decision_id=source.source_strategy_decision_id,
            source_setup_id=source.source_setup_id,
            source_analysis_snapshot_id=source.source_analysis_snapshot_id,
            symbol=source.symbol, timeframe=source.timeframe,
            closed_until_ms=source.closed_until_ms, paper_status=status,
            paper_plan_type=paper_plan_type_for(source.source_strategy_type),
            paper_direction=direction, source_risk_status=source.risk_status,
            source_risk_level=source.risk_level, source_risk_score=source.risk_score,
            source_strategy_type=source.source_strategy_type,
            source_strategy_quality=source.source_strategy_quality,
            source_direction_hint=direction,
            hypothetical_entry_reference=entry,
            hypothetical_invalidation_level=invalidation,
            hypothetical_stop_level=stop, hypothetical_target_level=target,
            planned_rr=planned_rr, entry_reference_source=entry_source,
            invalidation_source=invalidation_source, stop_source=stop_source,
            target_source=target_source, plan_quality=quality,
            plan_score=source.risk_score if status == "PAPER_PLAN_READY" else None,
            plan_reasons=list(dict.fromkeys([*reasons, *confirmations])),
            plan_warnings=list(warnings or []), rejection_reasons=list(rejection or []),
            wait_reasons=list(wait or []),
            paper_context={"plan_policy_version": self.config.plan_policy_version,
                           "causal_primitives": (context.to_dict() if context else {})},
        )

    def _error_plan(self, source: RiskDecision, exc: Exception) -> PaperTradePlan:
        reason = R.PAPER_ERROR_PROCESSING_FAILED.value
        return self._base_plan(source, status="ERROR", quality="ERROR", reasons=[reason],
                               rejection=[reason], warnings=[f"{type(exc).__name__}: {exc}"])
