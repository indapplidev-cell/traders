from types import SimpleNamespace

import pytest

from app.engine_orchestrator.runtime_parameters import RUNTIME_PROFILE_PARAMETERS, resolve_runtime_parameters
from app.engine_orchestrator.trade_profile import SCALPING_PROFILE_IDS, TRADE_PROFILES, resolve_trade_profile
from app.engine_paper.scalping_paper_runner import ScalpingPaperRunner
from app.engine_paper.scalping_shadow import ShadowGeometryCandidate


def test_v1_has_no_registered_profile_or_runtime_parameters():
    assert "trade-5m-v1" not in TRADE_PROFILES
    assert "trade-5m-v1" not in RUNTIME_PROFILE_PARAMETERS
    assert SCALPING_PROFILE_IDS == {"trade-5m-v2"}
    with pytest.raises(ValueError, match="unsupported trade profile"):
        resolve_trade_profile("trade-5m-v1")
    with pytest.raises(ValueError, match="runtime parameter set missing"):
        resolve_runtime_parameters("trade-5m-v1")


def test_v1_cannot_enter_scalping_geometry_or_paper_execution():
    with pytest.raises(ValueError, match="only trade-5m-v2"):
        ShadowGeometryCandidate(
            trade_profile_id="trade-5m-v1", symbol="BTCUSDT", boundary_ms=1,
            direction="BULLISH", entry=100, causal_invalidation=99, atr=1,
        )
    with pytest.raises(ValueError, match="requires trade-5m-v2"):
        ScalpingPaperRunner(runtime_parameters=SimpleNamespace(
            profile_id="trade-5m-v1", minimum_planned_rr=1.5,
        ))
