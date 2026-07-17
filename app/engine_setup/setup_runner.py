"""Runner connecting completed analysis snapshots to setup discovery only."""

from __future__ import annotations

import time
from collections.abc import AsyncIterable, AsyncIterator, Iterable

from app.engine_analysis.analysis_snapshot import AnalysisSnapshot
from app.engine_setup.setup_candidate import SetupCandidate, setup_candidate_id
from app.engine_setup.setup_detector import SetupDetector
from app.engine_setup.setup_diagnostics import SetupDiagnostics, SetupSemanticBucket
from app.engine_setup.setup_reason_codes import SetupReasonCode
from app.engine_setup.setup_status import ConfirmationState, DirectionHint, SetupQuality, SetupStatus
from app.engine_setup.setup_store import SetupStore
from app.engine_setup.setup_type import SetupType
from app.engine_setup.setup_quality_diagnostics import diagnose_setup_quality


class SetupRunner:
    def __init__(self, detector: SetupDetector, store: SetupStore) -> None:
        self.detector = detector
        self.store = store

    def process_analysis_snapshot(self, analysis_snapshot: AnalysisSnapshot) -> SetupCandidate:
        if not isinstance(analysis_snapshot, AnalysisSnapshot):
            raise TypeError("analysis_snapshot must be an AnalysisSnapshot")
        try:
            candidate = self.detector.detect(analysis_snapshot)
        except Exception as exc:
            candidate = self._error_candidate(analysis_snapshot, exc)
        self.store.save(candidate)
        return candidate

    async def run_on_analysis_snapshots(
        self,
        snapshots: AsyncIterable[AnalysisSnapshot] | Iterable[AnalysisSnapshot],
    ) -> AsyncIterator[SetupCandidate]:
        if hasattr(snapshots, "__aiter__"):
            async for snapshot in snapshots:  # type: ignore[union-attr]
                yield self.process_analysis_snapshot(snapshot)
        else:
            for snapshot in snapshots:  # type: ignore[union-attr]
                yield self.process_analysis_snapshot(snapshot)

    @staticmethod
    def _error_candidate(snapshot: AnalysisSnapshot, exc: Exception) -> SetupCandidate:
        status = SetupStatus.ERROR.value
        setup_type = SetupType.NO_SETUP.value
        diagnostics = SetupDiagnostics(
            has_invalidation_context=True,
            semantic_bucket=SetupSemanticBucket.ERROR_BUCKET.value,
            diagnostic_reasons=[SetupReasonCode.SETUP_PROCESSING_ERROR.value],
        )
        quality = diagnose_setup_quality(
            status=status, setup_type=setup_type, direction_hint=DirectionHint.NONE.value,
            confirmation_state=ConfirmationState.NOT_APPLICABLE.value, diagnostics=diagnostics,
            reason_codes=[SetupReasonCode.SETUP_PROCESSING_ERROR.value],
            source_analysis_entry_quality=snapshot.entry_quality,
            source_confidence=snapshot.confidence, source_regime=snapshot.regime,
            source_impulse_phase=snapshot.impulse_phase,
        )
        return SetupCandidate(
            setup_id=setup_candidate_id(snapshot.symbol, snapshot.timeframe,
                                        snapshot.closed_until_ms, setup_type, status),
            symbol=snapshot.symbol.upper(),
            timeframe=snapshot.timeframe,
            closed_until_ms=snapshot.closed_until_ms,
            created_at_ms=time.time_ns() // 1_000_000,
            source_analysis_snapshot_id=snapshot.snapshot_id,
            source_regime=snapshot.regime,
            source_confidence=snapshot.confidence,
            source_action=snapshot.action,
            source_impulse_phase=snapshot.impulse_phase,
            source_entry_quality=snapshot.entry_quality,
            status=status,
            setup_type=setup_type,
            direction_hint=DirectionHint.NONE.value,
            confirmation_state=ConfirmationState.NOT_APPLICABLE.value,
            setup_quality=SetupQuality.UNKNOWN.value,
            quality_score=quality.quality_score,
            quality_diagnostics=quality,
            quality_reasons=quality.quality_reasons,
            quality_warnings=quality.quality_warnings,
            reason_codes=[SetupReasonCode.SETUP_PROCESSING_ERROR.value],
            invalidation_reasons=[],
            diagnostics=diagnostics,
            context={"processing_error": f"{type(exc).__name__}: {exc}"},
        )
