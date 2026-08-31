"""Runner consuming only RiskDecision and emitting PaperTradePlan."""

from __future__ import annotations

import time
from collections.abc import AsyncIterable, AsyncIterator, Iterable
from decimal import Decimal

from app.engine_paper.paper_config import PaperConfig
from app.engine_paper.paper_context import PaperContext
from app.engine_paper.paper_level_builder import PaperLevelBuilder, PaperLevelEvaluation
from app.engine_paper.paper_plan_policy import PaperPlanPolicy
from app.engine_paper.paper_plan_type import paper_plan_type_for
from app.engine_paper.paper_reason_codes import PaperReasonCode as R
from app.engine_paper.paper_store import PaperStore
from app.engine_paper.paper_trade_plan import PaperTradePlan, paper_plan_id
from app.engine_risk.risk_decision import RiskDecision


class PaperRunner:
    def __init__(self, config: PaperConfig | None = None, store: PaperStore | None = None,
                 runtime_parameters: object | None = None) -> None:
        if config is None and runtime_parameters is not None:
            config = PaperConfig(
                minimum_planned_rr=float(runtime_parameters.minimum_planned_rr),
                entry_fee_bps=float(runtime_parameters.economics_entry_fee_bps),
                exit_fee_bps=float(runtime_parameters.economics_exit_fee_bps),
                entry_slippage_bps=float(runtime_parameters.economics_entry_slippage_bps),
                exit_slippage_bps=float(runtime_parameters.economics_exit_slippage_bps),
                cost_safety_margin_bps=float(runtime_parameters.cost_safety_margin_bps),
                minimum_net_edge_bps=float(runtime_parameters.economics_minimum_net_edge_bps),
            )
        self.config = config or PaperConfig()
        self.runtime_parameters = runtime_parameters
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
        attempt = self.level_builder.evaluate(context, source.direction_hint)
        evidence = self._domain_evidence(context, attempt)
        if attempt.rejection_reason is not None and not attempt.geometry_pass:
            missing = attempt.rejection_reason.startswith("PAPER_NO_PLAN_MISSING_")
            reasons = ([R.PAPER_NO_PLAN_MISSING_CAUSAL_LEVELS.value, attempt.rejection_reason]
                       if missing else [attempt.rejection_reason])
            return self._base_plan(
                source, status="NO_PLAN" if missing else "REJECT",
                quality="UNKNOWN" if missing else "REJECTED", reasons=reasons,
                rejection=[] if missing else [attempt.rejection_reason], context=context,
                evidence=evidence,
                entry=attempt.entry, invalidation=attempt.invalidation,
                stop=attempt.stop, target=attempt.target,
                planned_rr=attempt.raw_rr, entry_source=attempt.entry_source,
                invalidation_source=attempt.invalidation_source,
                stop_source=attempt.stop_source, target_source=attempt.target_source,
            )
        if attempt.rejection_reason is not None and not attempt.target_pass:
            missing = attempt.rejection_reason.startswith("PAPER_NO_PLAN_MISSING_")
            reasons = ([R.PAPER_NO_PLAN_MISSING_CAUSAL_LEVELS.value, attempt.rejection_reason]
                       if missing else [attempt.rejection_reason])
            return self._base_plan(
                source, status="NO_PLAN" if missing else "REJECT",
                quality="UNKNOWN" if missing else "REJECTED", reasons=reasons,
                rejection=[] if missing else [attempt.rejection_reason], context=context,
                evidence=evidence, entry=attempt.entry,
                invalidation=attempt.invalidation, stop=attempt.stop,
                target=attempt.target, planned_rr=attempt.raw_rr,
                entry_source=attempt.entry_source,
                invalidation_source=attempt.invalidation_source,
                stop_source=attempt.stop_source, target_source=attempt.target_source,
            )
        economics = evidence["net_cost_gate"]
        if economics["gate_decision"] != "PASS":
            reason = R.PAPER_REJECT_NET_COST_GATE.value
            return self._base_plan(
                source, status="REJECT", quality="REJECTED", reasons=[reason],
                rejection=[reason], context=context, evidence=evidence,
                entry=attempt.entry, invalidation=attempt.invalidation,
                stop=attempt.stop, target=attempt.target,
                planned_rr=attempt.raw_rr, entry_source=attempt.entry_source,
                invalidation_source=attempt.invalidation_source,
                stop_source=attempt.stop_source, target_source=attempt.target_source,
            )
        if not attempt.rr_pass:
            reason = attempt.rejection_reason or R.PAPER_REJECT_LOW_PLANNED_RR.value
            return self._base_plan(
                source, status="REJECT", quality="REJECTED", reasons=[reason],
                rejection=[reason], context=context, evidence=evidence,
                entry=attempt.entry, invalidation=attempt.invalidation,
                stop=attempt.stop, target=attempt.target,
                planned_rr=attempt.raw_rr, entry_source=attempt.entry_source,
                invalidation_source=attempt.invalidation_source,
                stop_source=attempt.stop_source, target_source=attempt.target_source,
            )
        low_risk_reason = (R.PAPER_PLAN_READY_LOW_RISK.value if source.risk_level == "LOW"
                           else R.PAPER_PLAN_READY_ACCEPTABLE_RISK.value)
        return self._base_plan(
            source, status="PAPER_PLAN_READY", quality=gate.quality, context=context,
            reasons=[low_risk_reason, R.PAPER_PLAN_READY_VALID_LEVELS.value,
                     R.PAPER_PLAN_READY_MIN_RR_MET.value],
            entry=attempt.entry, invalidation=attempt.invalidation, stop=attempt.stop,
            target=attempt.target, planned_rr=attempt.raw_rr,
            entry_source=attempt.entry_source,
            invalidation_source=attempt.invalidation_source,
            stop_source=attempt.stop_source, target_source=attempt.target_source,
            evidence=evidence,
        )

    def _base_plan(self, source: RiskDecision, *, status: str, quality: str,
                   reasons: list[str], rejection: list[str] | None = None,
                   wait: list[str] | None = None, context: PaperContext | None = None,
                   entry: float | None = None, invalidation: float | None = None,
                   stop: float | None = None, target: float | None = None,
                   planned_rr: float | None = None, entry_source: str | None = None,
                   invalidation_source: str | None = None, stop_source: str | None = None,
                   target_source: str | None = None, warnings: list[str] | None = None,
                   evidence: dict[str, object] | None = None) -> PaperTradePlan:
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
                           "causal_primitives": (context.to_dict() if context else {}),
                           **(evidence or {})},
        )

    def _domain_evidence(
        self, context: PaperContext, attempt: PaperLevelEvaluation,
    ) -> dict[str, object]:
        geometry = attempt.to_dict()
        entry = attempt.entry
        target = attempt.target
        risk_distance = attempt.risk_distance
        reward_distance = attempt.reward_distance
        gross_move_bps_decimal = (
            None if entry is None or target is None or entry <= 0
            else abs(Decimal(str(target)) - Decimal(str(entry)))
            / Decimal(str(entry)) * Decimal("10000")
        )
        risk_bps_decimal = (
            None if entry is None or risk_distance is None or entry <= 0
            else Decimal(str(risk_distance)) / Decimal(str(entry)) * Decimal("10000")
        )
        total_cost_decimal = sum((Decimal(str(value)) for value in (
            self.config.entry_fee_bps, self.config.exit_fee_bps,
            self.config.entry_slippage_bps, self.config.exit_slippage_bps,
            self.config.cost_safety_margin_bps,
        )), Decimal("0"))
        net_edge_decimal = (
            None if gross_move_bps_decimal is None
            else gross_move_bps_decimal - total_cost_decimal
        )
        effective_rr_decimal = (
            None if net_edge_decimal is None or risk_bps_decimal is None
            else max(Decimal("0"), net_edge_decimal)
            / (risk_bps_decimal + total_cost_decimal)
        )
        gate_pass = (
            net_edge_decimal is not None
            and net_edge_decimal >= Decimal(str(self.config.minimum_net_edge_bps))
        )
        gross_move_bps = (
            None if gross_move_bps_decimal is None else float(gross_move_bps_decimal)
        )
        net_edge_bps = (
            None if net_edge_decimal is None else float(net_edge_decimal)
        )
        effective_rr = (
            None if effective_rr_decimal is None else float(effective_rr_decimal)
        )
        total_cost_bps = float(total_cost_decimal)
        target_source_evidence = self._target_source_evidence(context, attempt)
        runtime_id = getattr(self.runtime_parameters, "parameter_set_id", None)
        geometry.update({
            "effective_rr": None if effective_rr is None else round(effective_rr, 8),
            "target_provenance": target_source_evidence,
            "stop_provenance": {
                "source_type": attempt.invalidation_source,
                "source_timeframe": getattr(self.runtime_parameters, "trigger_timeframe", None),
                "raw_source_value": attempt.invalidation,
                "buffer_source": attempt.buffer_source,
                "buffer_value": attempt.buffer_value,
                "derived_rule_version": "causal-invalidation-volatility-buffer-v1",
                "final_normalized_value": attempt.stop,
            },
        })
        return {
            "canonical_domain_evaluation": geometry,
            "net_cost_gate": {
                "model_version": self.config.economic_policy_version,
                "runtime_parameter_set_id": runtime_id,
                "gross_expected_outcome": attempt.reward_distance,
                "gross_expected_outcome_bps": gross_move_bps,
                "estimated_trading_fees_bps": (
                    self.config.entry_fee_bps + self.config.exit_fee_bps
                ),
                "estimated_slippage_bps": (
                    self.config.entry_slippage_bps + self.config.exit_slippage_bps
                ),
                "safety_margin_bps": self.config.cost_safety_margin_bps,
                "total_estimated_cost_bps": total_cost_bps,
                "net_expected_outcome_bps": net_edge_bps,
                "gate_threshold_bps": self.config.minimum_net_edge_bps,
                "gate_decision": "PASS" if gate_pass else (
                    "REJECT" if gross_move_bps is not None else "NOT_REACHED"
                ),
                "gate_reason": (
                    "NET_EXPECTED_OUTCOME_MEETS_THRESHOLD" if gate_pass
                    else "NET_EXPECTED_OUTCOME_BELOW_THRESHOLD"
                    if gross_move_bps is not None else "GEOMETRY_NOT_AVAILABLE"
                ),
                "deterministic": True,
            },
        }

    @staticmethod
    def _target_source_evidence(
        context: PaperContext, attempt: PaperLevelEvaluation,
    ) -> dict[str, object]:
        candidates = tuple(context.causal_target_candidates or ())
        matched = next((item for item in candidates if item.get("price") == attempt.target), {})
        return {
            "source_type": attempt.target_source,
            "source_timeframe": matched.get("timeframe"),
            "source_candle_or_window": matched.get("known_at_ms"),
            "source_signal_or_model_output": matched.get("source_detail"),
            "derived_rule_version": "opposite-causal-level-v1",
            "raw_source_value": attempt.target,
            "final_normalized_value": attempt.target,
            "source_evidence": dict(matched),
        }

    def _error_plan(self, source: RiskDecision, exc: Exception) -> PaperTradePlan:
        reason = R.PAPER_ERROR_PROCESSING_FAILED.value
        return self._base_plan(source, status="ERROR", quality="ERROR", reasons=[reason],
                               rejection=[reason], warnings=[f"{type(exc).__name__}: {exc}"])
