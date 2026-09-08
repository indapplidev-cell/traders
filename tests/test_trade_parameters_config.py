from pathlib import Path
import os
import subprocess
import sys

import pytest

from app.config.trade_parameters import (
    ACTIVE_SCALPING_V2_PARAMETER_SET, CONFIG_PATH, SCALPING_V2,
    TRADE_PARAMETERS, load_trade_parameters,
)
from app.engine_orchestrator.runtime_parameters import resolve_runtime_parameters
from app.engine_orchestrator.trade_profile import ACTIVE_RUNTIME_PROFILE_IDS, TRADE_PROFILES


def test_authoritative_config_loads_and_drives_active_named_set():
    assert CONFIG_PATH.as_posix().endswith("config/trading/trade_parameters.yaml")
    assert TRADE_PARAMETERS.schema_version == 1
    assert len(TRADE_PARAMETERS.config_hash) == 64
    runtime = resolve_runtime_parameters("trade-5m-v2")
    assert runtime.risk_per_trade_bps == SCALPING_V2.risk.risk_per_trade_bps == 5
    assert runtime.portfolio_max_concurrent_positions == SCALPING_V2.risk.max_open_positions == 2
    assert runtime.minimum_planned_rr == SCALPING_V2.geometry.minimum_planned_rr == 0.6
    assert runtime.parameter_set_id == "scalping-v2-set-2"
    assert runtime.resolved_config_hash == ACTIVE_SCALPING_V2_PARAMETER_SET.resolved_config_hash
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


def test_named_sets_inherit_exact_overrides_and_preserve_baseline():
    baseline = TRADE_PARAMETERS.resolve_scalping_v2_parameter_set("scalping-v2-set-1")
    interim = TRADE_PARAMETERS.resolve_scalping_v2_parameter_set("scalping-v2-set-2")
    assert baseline.resolved_config_hash == "074244034d0969cafdfa779013819eeaeeb710d4e29aa17fc3010c7f87315b1f"
    assert interim.resolved_config_hash != baseline.resolved_config_hash
    assert baseline.parameters == TRADE_PARAMETERS.profiles.trade_5m_v2
    assert interim.parameters.geometry.minimum_planned_rr == 0.6
    assert interim.parameters.risk.risk_per_trade_bps == 5
    assert interim.parameters.geometry.target_min_bps == 60
    assert interim.parameters.economics.min_ev_reserve_r == 0.05
    assert interim.parameters.exit_policy.stale_position.hard_timeout_seconds == 1200
    assert interim.parameters.costs == baseline.parameters.costs
    assert interim.parameters.risk.max_open_positions == baseline.parameters.risk.max_open_positions
    assert interim.parameters.risk.max_new_commands_per_cycle == 1
    assert interim.parameters.risk.total_open_risk_limit_bps == 50
    assert interim.parameters.entry_refinement_1m.mode == "SHADOW"
    assert interim.parameters.exit_policy.stale_position.mode == "SHADOW"


def test_selector_switch_rollback_cutoff_and_fail_closed(tmp_path: Path):
    source = CONFIG_PATH.read_text(encoding="utf-8")
    set_one_path = tmp_path / "set-one.yaml"
    set_one_path.write_text(source.replace(
        "active_parameter_set: scalping-v2-set-2",
        "active_parameter_set: scalping-v2-set-1",
    ), encoding="utf-8")
    set_one = load_trade_parameters(set_one_path).resolve_scalping_v2_parameter_set()
    set_two = load_trade_parameters().resolve_scalping_v2_parameter_set()
    assert set_one.id == "scalping-v2-set-1"
    assert set_two.id == "scalping-v2-set-2"
    assert set_two.activation_cycle_boundary_ms == 1788885600000
    assert TRADE_PARAMETERS.resolve_scalping_v2_for_cycle(1788885599999).id == "scalping-v2-set-1"
    assert TRADE_PARAMETERS.resolve_scalping_v2_for_cycle(1788885600000).id == "scalping-v2-set-2"
    # A cycle freezes this immutable object; a subsequent selector load cannot mutate it.
    frozen_cycle = set_one
    assert frozen_cycle.id == "scalping-v2-set-1"
    assert set_two.id == "scalping-v2-set-2"
    rollback = load_trade_parameters(set_one_path).resolve_scalping_v2_parameter_set()
    assert rollback.id == "scalping-v2-set-1"

    unknown_path = tmp_path / "unknown.yaml"
    unknown_path.write_text(source.replace(
        "active_parameter_set: scalping-v2-set-2",
        "active_parameter_set: scalping-v2-set-999",
    ), encoding="utf-8")
    with pytest.raises(RuntimeError, match="UNKNOWN_PARAMETER_SET"):
        load_trade_parameters(unknown_path).resolve_scalping_v2_parameter_set()

    invalid_path = tmp_path / "invalid.yaml"
    invalid_path.write_text(source.replace(
        "geometry.minimum_planned_rr: 0.6",
        "geometry.minimum_planned_rr: -1",
    ), encoding="utf-8")
    with pytest.raises(RuntimeError, match="INVALID_PARAMETER_SET"):
        load_trade_parameters(invalid_path).resolve_scalping_v2_parameter_set()


def test_packaged_runtime_can_bind_authoritative_config_path(tmp_path: Path):
    runtime_config = tmp_path / "trade_parameters.yaml"
    runtime_config.write_bytes(CONFIG_PATH.read_bytes())
    environment = os.environ.copy()
    environment["TRADERS_TRADE_PARAMETERS_PATH"] = str(runtime_config)

    completed = subprocess.run(
        [sys.executable, "-c", "from app.config.trade_parameters import CONFIG_PATH; print(CONFIG_PATH)"],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert Path(completed.stdout.strip()) == runtime_config


def test_all_production_images_copy_and_bind_authoritative_config():
    dockerfile = (Path(__file__).resolve().parents[1] / "Dockerfile").read_text(encoding="utf-8")

    assert dockerfile.count(
        "COPY config/trading/trade_parameters.yaml ./config/trading/trade_parameters.yaml"
    ) == 3
    assert dockerfile.count(
        "TRADERS_TRADE_PARAMETERS_PATH=/service/config/trading/trade_parameters.yaml"
    ) == 3
