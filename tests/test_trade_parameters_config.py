from pathlib import Path

import pytest

from app.config.trade_parameters import CONFIG_PATH, SCALPING_V2, TRADE_PARAMETERS, load_trade_parameters
from app.engine_orchestrator.runtime_parameters import resolve_runtime_parameters
from app.engine_orchestrator.trade_profile import ACTIVE_RUNTIME_PROFILE_IDS, TRADE_PROFILES


def test_authoritative_config_loads_and_drives_runtime_baseline():
    assert CONFIG_PATH.as_posix().endswith("config/trading/trade_parameters.yaml")
    assert TRADE_PARAMETERS.schema_version == 1
    assert len(TRADE_PARAMETERS.config_hash) == 64
    runtime = resolve_runtime_parameters("trade-5m-v2")
    assert runtime.risk_per_trade_bps == SCALPING_V2.risk.risk_per_trade_bps == 10
    assert runtime.portfolio_max_concurrent_positions == SCALPING_V2.risk.max_open_positions == 2
    assert runtime.minimum_planned_rr == SCALPING_V2.geometry.minimum_planned_rr == 0.4
    assert runtime.public_provenance()["trade_parameter_config_hash"] == TRADE_PARAMETERS.config_hash
    assert ACTIVE_RUNTIME_PROFILE_IDS == frozenset({"trade-5m-v2"})
    assert "trade-5m-v1" not in TRADE_PROFILES
    assert TRADE_PARAMETERS.profiles.trade_15m_v1.enabled is False


@pytest.mark.parametrize("mutation", [
    lambda value: value.replace("schema_version: 1", "schema_version: 2"),
    lambda value: value.replace("    risk:\n", "    unknown_section: true\n    risk:\n", 1),
    lambda value: value.replace("      risk_per_trade_bps: 10.0\n", "", 1),
    lambda value: value.replace(
        "      risk_per_trade_bps: 10.0\n",
        "      risk_per_trade_bps: 10.0\n      risk_per_trade_bps: 11.0\n", 1,
    ),
])
def test_invalid_missing_unknown_and_duplicate_fields_fail_closed(tmp_path: Path, mutation):
    invalid = tmp_path / "trade_parameters.yaml"
    invalid.write_text(mutation(CONFIG_PATH.read_text(encoding="utf-8")), encoding="utf-8")
    with pytest.raises(RuntimeError, match="invalid authoritative trade parameters"):
        load_trade_parameters(invalid)


def test_hash_is_deterministic():
    assert load_trade_parameters().config_hash == load_trade_parameters().config_hash
