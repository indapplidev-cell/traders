"""Runner consuming StrategyDecision objects and emitting safe RiskDecisions."""

from __future__ import annotations

import time
from collections.abc import AsyncIterable, AsyncIterator, Iterable

from app.engine_risk.risk_decision import RiskDecision, risk_decision_id
from app.engine_risk.risk_level import RiskLevel
from app.engine_risk.risk_policy import RiskPolicy
from app.engine_risk.risk_reason_codes import RiskReasonCode
from app.engine_risk.risk_status import RiskStatus
from app.engine_risk.risk_store import RiskStore
from app.engine_strategy.strategy_decision import StrategyDecision


class RiskRunner:
    def __init__(self, policy: RiskPolicy | None = None, store: RiskStore | None = None,
                 runtime_parameters: object | None = None) -> None:
        self.policy = policy or RiskPolicy()
        self.store = store or RiskStore()
        self.runtime_parameters = runtime_parameters

    def process_strategy_decision(self, strategy_decision: StrategyDecision) -> RiskDecision:
        if not isinstance(strategy_decision, StrategyDecision):
            raise TypeError("strategy_decision must be a StrategyDecision")
        try:
            decision = self.policy.evaluate(strategy_decision)
        except Exception as exc:
            decision = self._error_decision(strategy_decision, exc)
        self.store.save(decision)
        return decision

    def preview_strategy_decision(self, strategy_decision: StrategyDecision) -> RiskDecision:
        """Evaluate risk gates without reserving a research-flow slot.

        Scalping uses this preview to build and economically validate geometry
        before the authoritative reservation step.
        """
        if not isinstance(strategy_decision, StrategyDecision):
            raise TypeError("strategy_decision must be a StrategyDecision")
        try:
            decision = self.policy.evaluate_shadow(strategy_decision)
        except Exception as exc:
            decision = self._error_decision(strategy_decision, exc)
        return decision

    async def run_on_strategy_decisions(
        self, decisions: AsyncIterable[StrategyDecision] | Iterable[StrategyDecision],
    ) -> AsyncIterator[RiskDecision]:
        if hasattr(decisions, "__aiter__"):
            async for decision in decisions:  # type: ignore[union-attr]
                yield self.process_strategy_decision(decision)
        else:
            for decision in decisions:  # type: ignore[union-attr]
                yield self.process_strategy_decision(decision)

    def _error_decision(self, source: StrategyDecision, exc: Exception) -> RiskDecision:
        reason = RiskReasonCode.RISK_ERROR_PROCESSING_FAILED.value
        return RiskDecision(
            risk_decision_id=risk_decision_id(source.symbol, source.timeframe,
                                              source.closed_until_ms, source.decision_id),
            created_at_ms=time.time_ns() // 1_000_000,
            source_strategy_decision_id=source.decision_id,
            source_setup_id=source.source_setup_id,
            source_analysis_snapshot_id=source.source_analysis_snapshot_id,
            symbol=source.symbol, timeframe=source.timeframe,
            closed_until_ms=source.closed_until_ms,
            risk_status=RiskStatus.ERROR.value, risk_level=RiskLevel.ERROR.value,
            risk_score=None, risk_policy_version=self.policy.config.policy_version,
            source_decision_status=source.decision_status,
            source_strategy_type=source.strategy_type,
            source_strategy_quality=source.strategy_quality,
            source_strategy_score=source.strategy_score,
            direction_hint=source.direction_hint,
            risk_reasons=[reason, RiskReasonCode.RISK_NO_FUTURE_BARS_USED.value,
                          RiskReasonCode.RISK_NOT_EXECUTABLE.value,
                          RiskReasonCode.RISK_NOT_ORDER_APPROVED.value],
            risk_warnings=[f"{type(exc).__name__}: {exc}"],
            rejection_reasons=[reason], risk_context={"processing_error_type": type(exc).__name__},
        )
