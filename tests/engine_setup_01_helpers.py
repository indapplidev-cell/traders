from __future__ import annotations

from app.engine_analysis.analysis_snapshot import AnalysisSnapshot


def analysis_snapshot(**changes) -> AnalysisSnapshot:
    values = dict(
        symbol="BTCUSDT",
        timeframe="15m",
        closed_until_ms=1_700_000_000_000,
        created_at_ms=1_700_000_000_001,
        market_data_health="OK",
        degraded=False,
        enough_data=True,
        regime="UP",
        confidence=0.8,
        action="NO_ACTION",
        impulse_phase="NO_IMPULSE",
        entry_quality="ACCEPTABLE",
        reason_codes=[],
        analysis_context={},
        status="ANALYZED",
    )
    values.update(changes)
    return AnalysisSnapshot.for_window(**values)
