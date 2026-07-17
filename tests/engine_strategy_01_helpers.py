from __future__ import annotations

from app.engine_setup.setup_candidate import SetupCandidate
from app.engine_setup.setup_diagnostics import SetupDiagnostics


def candidate(**changes) -> SetupCandidate:
    values = dict(
        setup_id="setup:1", symbol="BTCUSDT", timeframe="15m",
        closed_until_ms=1_700_000_000_000, created_at_ms=1_700_000_000_001,
        source_analysis_snapshot_id="analysis:1", source_regime="UP", source_confidence=.8,
        source_action="NO_ACTION", source_entry_quality="ACCEPTABLE",
        status="SETUP_CANDIDATE", setup_type="BREAKOUT_CONTINUATION",
        direction_hint="BULLISH", confirmation_state="CONFIRMED_BY_ANALYSIS",
        setup_quality="ACCEPTABLE", quality_score=72.0, reason_codes=[],
        invalidation_reasons=[], quality_reasons=[], quality_warnings=[],
        diagnostics=SetupDiagnostics(
            has_structural_trigger=True, has_directional_context=True,
            is_actionable_setup_candidate=True, semantic_bucket="CANDIDATE_STRUCTURE"),
        context={},
    )
    values.update(changes)
    status = values["status"]
    if "diagnostics" not in changes:
        if status == "NO_SETUP":
            values["diagnostics"] = SetupDiagnostics()
        elif status == "WAIT_FOR_CONFIRMATION":
            values["diagnostics"] = SetupDiagnostics(
                has_structural_trigger=True, has_confirmation_requirement=True,
                semantic_bucket="PRE_SETUP_WAITING_CONFIRMATION")
        elif status in {"SETUP_INVALID", "ERROR"}:
            values["diagnostics"] = SetupDiagnostics(
                has_invalidation_context=True,
                semantic_bucket="INVALIDATED_STRUCTURE" if status == "SETUP_INVALID" else "ERROR_BUCKET")
    if status == "SETUP_INVALID" and not values["invalidation_reasons"]:
        values["invalidation_reasons"] = ["INVALID_CONTEXT"]
    if status == "ERROR" and "SETUP_PROCESSING_ERROR" not in values["reason_codes"]:
        values["reason_codes"] = [*values["reason_codes"], "SETUP_PROCESSING_ERROR"]
    return SetupCandidate(**values)


def input_record(**changes):
    values = dict(
        record_id="historical:1", symbol="BTCUSDT", timeframe="15m",
        closed_until_ms=1_700_000_000_000,
        closed_until_utc="2023-11-14T22:13:20Z", setup_id="setup:1",
        analysis_snapshot_id="analysis:1", analysis_regime="UP", analysis_confidence=.8,
        analysis_action="NO_ACTION", analysis_impulse_phase="NO_IMPULSE",
        setup_status="SETUP_CANDIDATE", setup_type="BREAKOUT_CONTINUATION",
        setup_quality="ACCEPTABLE", quality_score=72.0, direction_hint="BULLISH",
        confirmation_state="CONFIRMED_BY_ANALYSIS", semantic_bucket="CANDIDATE_STRUCTURE",
        reason_codes=[], invalidation_reasons=[], diagnostic_reasons=[], quality_reasons=[],
        quality_warnings=[], has_hard_invalidation=False, has_conflict=False,
        future_bars_used=False, is_trade_signal=False,
    )
    values.update(changes)
    return values
