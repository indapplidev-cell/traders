from __future__ import annotations

import pytest

from app.engine_analysis.analysis_snapshot import AnalysisSnapshot
from app.engine_setup.setup_context import SetupContext


@pytest.fixture
def context_factory():
    def build(**changes) -> SetupContext:
        values = {
            "regime": "UP",
            "confidence": 0.8,
            "action": "NO_ACTION",
            "impulse_phase": "NO_IMPULSE",
            "entry_quality": "ACCEPTABLE",
            "reason_codes": (),
            "analysis_context": {},
        }
        values.update(changes)
        return SetupContext(**values)

    return build


@pytest.fixture
def analysis_snapshot_factory():
    def build(**changes) -> AnalysisSnapshot:
        values = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "closed_until_ms": 1_700_000_000_000,
            "created_at_ms": 1_700_000_000_001,
            "market_data_health": "OK",
            "degraded": False,
            "enough_data": True,
            "regime": "UP",
            "confidence": 0.8,
            "action": "NO_ACTION",
            "impulse_phase": "IMPULSE_EXTENSION",
            "entry_quality": "ACCEPTABLE",
            "reason_codes": ["BREAKOUT_HELD_WITH_FOLLOW_THROUGH"],
            "analysis_context": {},
            "status": "ANALYZED",
        }
        values.update(changes)
        return AnalysisSnapshot.for_window(**values)

    return build
