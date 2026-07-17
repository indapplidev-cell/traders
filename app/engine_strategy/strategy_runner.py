"""Runner that consumes SetupCandidate objects and emits decisions only."""

from __future__ import annotations

import time
from collections.abc import AsyncIterable, AsyncIterator, Iterable

from app.engine_setup.setup_candidate import SetupCandidate
from app.engine_strategy.strategy_decision import StrategyDecision, strategy_decision_id
from app.engine_strategy.strategy_filter import StrategyFilter
from app.engine_strategy.strategy_reason_codes import StrategyReasonCode
from app.engine_strategy.strategy_status import StrategyQuality, StrategyStatus
from app.engine_strategy.strategy_store import StrategyStore
from app.engine_strategy.strategy_type import StrategyType


class StrategyRunner:
    def __init__(self, strategy_filter: StrategyFilter | None = None,
                 store: StrategyStore | None = None) -> None:
        self.strategy_filter = strategy_filter or StrategyFilter()
        self.store = store or StrategyStore()

    def process_setup_candidate(self, setup_candidate: SetupCandidate) -> StrategyDecision:
        if not isinstance(setup_candidate, SetupCandidate):
            raise TypeError("setup_candidate must be a SetupCandidate")
        try:
            decision = self.strategy_filter.evaluate(setup_candidate)
        except Exception as exc:
            decision = self._error_decision(setup_candidate, exc)
        self.store.save(decision)
        return decision

    async def run_on_setup_candidates(
        self, candidates: AsyncIterable[SetupCandidate] | Iterable[SetupCandidate],
    ) -> AsyncIterator[StrategyDecision]:
        if hasattr(candidates, "__aiter__"):
            async for candidate in candidates:  # type: ignore[union-attr]
                yield self.process_setup_candidate(candidate)
        else:
            for candidate in candidates:  # type: ignore[union-attr]
                yield self.process_setup_candidate(candidate)

    @staticmethod
    def _error_decision(candidate: SetupCandidate, exc: Exception) -> StrategyDecision:
        reason = StrategyReasonCode.STRATEGY_ERROR_PROCESSING_FAILED.value
        return StrategyDecision(
            decision_id=strategy_decision_id(candidate.symbol, candidate.timeframe,
                                             candidate.closed_until_ms, candidate.setup_id),
            created_at_ms=time.time_ns() // 1_000_000,
            source_setup_id=candidate.setup_id,
            source_analysis_snapshot_id=candidate.source_analysis_snapshot_id,
            symbol=candidate.symbol, timeframe=candidate.timeframe,
            closed_until_ms=candidate.closed_until_ms,
            decision_status=StrategyStatus.ERROR.value,
            strategy_type=StrategyType.NO_STRATEGY.value,
            direction_hint=candidate.direction_hint, setup_status=candidate.status,
            setup_type=candidate.setup_type, setup_quality=candidate.setup_quality,
            setup_quality_score=candidate.quality_score, strategy_score=None,
            strategy_quality=StrategyQuality.ERROR.value,
            decision_reasons=[reason, StrategyReasonCode.STRATEGY_NO_FUTURE_BARS_USED.value,
                              StrategyReasonCode.STRATEGY_NOT_EXECUTABLE.value],
            decision_warnings=[f"{type(exc).__name__}: {exc}"],
            rejection_reasons=[], wait_reasons=[], required_next_layer=None,
            requires_risk_review=False, context={"processing_error_type": type(exc).__name__},
        )
