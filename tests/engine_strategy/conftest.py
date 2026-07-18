from __future__ import annotations

import pytest

from app.engine_setup.setup_candidate import SetupCandidate
from app.engine_setup.setup_diagnostics import SetupDiagnostics


@pytest.fixture
def candidate_factory():
    def build(**changes) -> SetupCandidate:
        values = {
            "setup_id": "setup:current:1",
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "closed_until_ms": 1_700_000_000_000,
            "created_at_ms": 1_700_000_000_001,
            "source_analysis_snapshot_id": "analysis:current:1",
            "source_regime": "UP",
            "source_confidence": 0.8,
            "source_action": "NO_ACTION",
            "source_entry_quality": "ACCEPTABLE",
            "status": "SETUP_CANDIDATE",
            "setup_type": "BREAKOUT_CONTINUATION",
            "direction_hint": "BULLISH",
            "confirmation_state": "CONFIRMED_BY_ANALYSIS",
            "setup_quality": "ACCEPTABLE",
            "quality_score": 72.0,
            "quality_reasons": [],
            "quality_warnings": [],
            "reason_codes": [],
            "invalidation_reasons": [],
            "diagnostics": SetupDiagnostics(
                has_structural_trigger=True,
                has_directional_context=True,
                is_actionable_setup_candidate=True,
                semantic_bucket="CANDIDATE_STRUCTURE",
            ),
            "context": {},
        }
        values.update(changes)
        status = values["status"]
        if "diagnostics" not in changes:
            if status == "NO_SETUP":
                values["diagnostics"] = SetupDiagnostics()
            elif status == "WAIT_FOR_CONFIRMATION":
                values["diagnostics"] = SetupDiagnostics(
                    has_structural_trigger=True,
                    has_confirmation_requirement=True,
                    semantic_bucket="PRE_SETUP_WAITING_CONFIRMATION",
                )
            elif status == "SETUP_INVALID":
                values["diagnostics"] = SetupDiagnostics(
                    has_invalidation_context=True,
                    semantic_bucket="INVALIDATED_STRUCTURE",
                )
        if status == "SETUP_INVALID" and not values["invalidation_reasons"]:
            values["invalidation_reasons"] = ["INVALID_CONTEXT"]
        return SetupCandidate(**values)

    return build
