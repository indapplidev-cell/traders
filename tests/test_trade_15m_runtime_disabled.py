import pytest

from app.engine_orchestrator.parallel_profiles import DEPLOYED_PARALLEL_PROFILE_IDS
from app.engine_orchestrator.trade_profile import (
    ACTIVE_RUNTIME_PROFILE_IDS,
    DEFAULT_TRADE_PROFILE_ID,
    resolve_trade_profile,
)
from app.engine_paper.production_approval import (
    EXECUTION_PROFILE_BY_TIMEFRAME,
    EXECUTION_PROFILES_BY_TIMEFRAME,
    EXECUTION_TIMEFRAMES,
)
from scripts.engine_orchestrator_online_pipeline import build_parser


def test_15m_is_preserved_but_not_runtime_enabled():
    profile = resolve_trade_profile("trade-15m-v1")
    assert profile.paper_command_creation_enabled is False
    assert profile.position_opening_enabled is False
    assert DEFAULT_TRADE_PROFILE_ID == "trade-5m-v2"
    assert ACTIVE_RUNTIME_PROFILE_IDS == {"trade-5m-v2"}
    assert DEPLOYED_PARALLEL_PROFILE_IDS == {"trade-5m-v2"}


def test_15m_cannot_be_selected_for_generation_or_execution():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--trade-profile", "trade-15m-v1", "--once"])
    assert EXECUTION_TIMEFRAMES == ("5m",)
    assert "15m" not in EXECUTION_PROFILE_BY_TIMEFRAME
    assert "15m" not in EXECUTION_PROFILES_BY_TIMEFRAME
