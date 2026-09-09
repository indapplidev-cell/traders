from pathlib import Path

import pytest
import yaml

from app.config.trade_parameters import ACTIVE_SCALPING_V2_PARAMETER_SET, load_trade_parameters
from app.config.yaml_authority import RISK_POLICY, RUNTIME_POLICY, RiskPolicy, authority_hash
from app.engine_orchestrator.runtime_parameters import resolve_runtime_parameters


def test_domain_yaml_is_typed_required_and_fail_closed():
    raw = RISK_POLICY.model_dump(mode="python")
    del raw["profiles"]["trade-5m-v2"]["risk_per_trade_bps"]
    with pytest.raises(Exception):
        RiskPolicy.model_validate(raw)


def test_active_set_semantics_and_full_authority_hash_are_bound():
    runtime = resolve_runtime_parameters("trade-5m-v2")
    assert runtime.impulse_absolute_threshold_pct == 3.0
    assert runtime.impulse_atr_multiplier == 2.5
    assert runtime.minimum_planned_rr == 0.6
    assert runtime.risk_per_trade_bps == 5.0
    assert runtime.geometry_minimum_target_bps == 60.0
    assert runtime.resolved_config_hash == ACTIVE_SCALPING_V2_PARAMETER_SET.resolved_config_hash
    assert authority_hash({"probe": 1}) != authority_hash({"probe": 2})


def test_disabled_15m_and_no_legacy_5m_fallback():
    assert RUNTIME_POLICY.profiles["trade-15m-v1"].enabled is False
    with pytest.raises(ValueError):
        resolve_runtime_parameters("trade-5m-v1")


def test_runtime_provenance_is_yaml_visible():
    provenance = resolve_runtime_parameters("trade-5m-v2").public_provenance()
    assert len(provenance["authoritative_parameters"]) >= 80
    impulse = provenance["authoritative_parameters"]["signal.impulse_absolute_threshold_pct"]
    assert impulse["source_file"] == "config/trading/trade_parameters.yaml"
    assert impulse["source_kind"] == "AUTHORITATIVE_YAML"
    risk = provenance["authoritative_parameters"]["risk.risk_per_trade_bps"]
    assert risk["source_file"] == "config/trading/risk_policy.yaml"
    assert provenance["operational_policy"]["collector.poll_seconds"]["value"] == 2.0
    assert provenance["operational_policy"]["orchestrator.poll_interval_seconds"]["value"] == 10.0
