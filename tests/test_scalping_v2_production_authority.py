import pytest

from app.engine_orchestrator.parallel_profiles import DEPLOYED_PARALLEL_PROFILE_IDS
from app.engine_orchestrator.runtime_parameters import resolve_runtime_parameters
from app.engine_orchestrator.trade_profile import (
    ACTIVE_RUNTIME_PROFILE_IDS,
    ACTIVE_SCALPING_PROFILE_ID,
)
from app.engine_paper.production_approval import (
    EXECUTION_PROFILE_BY_TIMEFRAME,
    EXECUTION_PROFILES_BY_TIMEFRAME,
)
from app.operator_control.continuation_worker import DEFAULT_POLL_SECONDS
from app.operator_control.runtime import READONLY_CURRENT_SNAPSHOT_TIMEOUT_SECONDS
from scripts.engine_orchestrator_online_pipeline import build_parser


def test_v2_is_the_only_active_scalping_runtime_profile():
    assert ACTIVE_SCALPING_PROFILE_ID == "trade-5m-v2"
    assert ACTIVE_RUNTIME_PROFILE_IDS == {"trade-15m-v1", "trade-5m-v2"}
    assert DEPLOYED_PARALLEL_PROFILE_IDS == ACTIVE_RUNTIME_PROFILE_IDS
    assert EXECUTION_PROFILE_BY_TIMEFRAME["5m"] == "trade-5m-v2"
    assert EXECUTION_PROFILES_BY_TIMEFRAME["5m"] == {"trade-5m-v2"}


def test_v1_is_historical_only_and_cannot_start_a_new_runtime_or_plan():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--trade-profile", "trade-5m-v1", "--once"])
    assert "trade-5m-v1" not in EXECUTION_PROFILES_BY_TIMEFRAME["5m"]


def test_v2_short_ttl_has_bounded_dispatch_margin():
    parameters = resolve_runtime_parameters("trade-5m-v2")
    assert parameters.execution_entry_ttl_seconds == 30
    assert DEFAULT_POLL_SECONDS == 5
    assert DEFAULT_POLL_SECONDS * 2 < parameters.execution_entry_ttl_seconds
    assert READONLY_CURRENT_SNAPSHOT_TIMEOUT_SECONDS == 10
