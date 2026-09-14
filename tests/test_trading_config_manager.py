from __future__ import annotations

import os
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from app.config.trade_parameters import CONFIG_PATH
from app.config.trading_config_manager import TradingConfigManager
from app.engine_orchestrator.runtime_parameters import _runtime_parameters
from app.engine_orchestrator.trade_profile import resolve_trade_profile
from app.server_api.app_factory import create_app


class Clock:
    def __init__(self, seconds: float = 1_900_000_010.0) -> None:
        self.seconds = seconds
        self.ticks = 0.0

    def time(self) -> float:
        return self.seconds

    def monotonic(self) -> float:
        return self.ticks

    def advance(self, seconds: float) -> None:
        self.seconds += seconds
        self.ticks += seconds


def _copy(tmp_path: Path) -> Path:
    path = tmp_path / "trade_parameters.yaml"
    path.write_bytes(CONFIG_PATH.read_bytes())
    return path


def _mutate(path: Path, dotted: str, value, *, atomic: bool = False) -> None:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw["scalping_v2"]["parameter_sets"]["set_2"]["overrides"][dotted] = value
    target = path.with_suffix(".saving") if atomic else path
    target.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    if atomic:
        os.replace(target, path)


def _stage(manager: TradingConfigManager, clock: Clock) -> None:
    assert manager.poll_once() is False
    clock.advance(0.31)
    assert manager.poll_once() is True


def test_valid_save_stages_then_activates_only_at_safe_boundary(tmp_path: Path):
    path = _copy(tmp_path)
    clock = Clock()
    manager = TradingConfigManager(path, clock=clock.time, monotonic=clock.monotonic)
    old = manager.get_active_snapshot()
    new_value = old.resolved.parameters.geometry.minimum_planned_rr + 0.01

    _mutate(path, "geometry.minimum_planned_rr", new_value)
    _stage(manager, clock)
    status = manager.status()
    assert status["config_reload_status"] == "PENDING_SAFE_BOUNDARY"
    assert status["config_pending_generation"] > old.generation
    assert manager.get_active_snapshot() is old
    pending_boundary = status["config_pending_activation_boundary_ms"]
    assert manager.activate_due(pending_boundary - 1) is False
    assert manager.activate_due(pending_boundary) is True

    active = manager.get_active_snapshot()
    assert active.generation > old.generation
    assert active.resolved.parameters.geometry.minimum_planned_rr == new_value
    diagnostic = manager.status()["parameters"]["geometry.minimum_planned_rr"]
    assert diagnostic["source_yaml_path"].endswith(
        "parameter_sets.set_2.overrides.geometry.minimum_planned_rr"
    )
    assert diagnostic["override_status"] is True
    assert manager.snapshot_for_cycle(pending_boundary - 1) is old
    assert manager.snapshot_for_cycle(pending_boundary) is active


def test_invalid_yaml_keeps_last_known_good_and_fixed_file_auto_recovers(tmp_path: Path):
    path = _copy(tmp_path)
    clock = Clock()
    manager = TradingConfigManager(path, clock=clock.time, monotonic=clock.monotonic)
    old = manager.get_active_snapshot()
    path.write_text("schema_version: [", encoding="utf-8")
    assert manager.poll_once() is False
    clock.advance(0.31)
    assert manager.poll_once() is False
    assert manager.status()["config_reload_status"] == "RELOAD_FAILED"
    assert manager.get_active_snapshot() is old

    path.write_bytes(CONFIG_PATH.read_bytes())
    _mutate(path, "geometry.minimum_planned_rr", 0.77)
    _stage(manager, clock)
    boundary = manager.status()["config_pending_activation_boundary_ms"]
    assert manager.activate_due(boundary)
    assert manager.get_active_snapshot().resolved.parameters.geometry.minimum_planned_rr == 0.77


def test_atomic_replace_and_rapid_saves_activate_final_stable_value(tmp_path: Path):
    path = _copy(tmp_path)
    clock = Clock()
    manager = TradingConfigManager(path, clock=clock.time, monotonic=clock.monotonic)

    _mutate(path, "geometry.minimum_planned_rr", 0.71, atomic=True)
    assert manager.poll_once() is False
    clock.advance(0.1)
    _mutate(path, "geometry.minimum_planned_rr", 0.72, atomic=True)
    assert manager.poll_once() is False
    clock.advance(0.31)
    assert manager.poll_once() is True
    boundary = manager.status()["config_pending_activation_boundary_ms"]
    manager.activate_due(boundary)
    assert manager.get_active_snapshot().resolved.parameters.geometry.minimum_planned_rr == 0.72


def test_base_override_semantics_runtime_api_parity_and_restart(tmp_path: Path):
    path = _copy(tmp_path)
    clock = Clock()
    manager = TradingConfigManager(path, clock=clock.time, monotonic=clock.monotonic)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw["profiles"]["trade-5m-v2"]["signal"]["strategy_minimum_score"] = 81.0
    raw["profiles"]["trade-5m-v2"]["geometry"]["minimum_planned_rr"] = 9.0
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    _stage(manager, clock)
    boundary = manager.status()["config_pending_activation_boundary_ms"]
    manager.activate_due(boundary)

    active = manager.get_active_snapshot()
    runtime = _runtime_parameters(resolve_trade_profile("trade-5m-v2"), active.resolved)
    api = manager.status()
    assert runtime.risk_minimum_strategy_score == 81.0
    assert api["parameters"]["signal.strategy_minimum_score"]["effective_value"] == 81.0
    assert api["parameters"]["signal.strategy_minimum_score"]["source_layer"] == "BASE_PROFILE"
    # The active set override remains authoritative over the edited base field.
    assert runtime.minimum_planned_rr != 9.0
    assert api["parameters"]["geometry.minimum_planned_rr"]["override_status"] is True
    assert runtime.minimum_planned_rr == api["parameters"]["geometry.minimum_planned_rr"]["effective_value"]

    restarted = TradingConfigManager(path, clock=clock.time, monotonic=clock.monotonic)
    assert restarted.get_active_snapshot().resolved.parameters.signal.strategy_minimum_score == 81.0
    assert restarted.get_active_snapshot().generation == active.generation


def test_missing_file_does_not_replace_active_snapshot(tmp_path: Path):
    path = _copy(tmp_path)
    clock = Clock()
    manager = TradingConfigManager(path, clock=clock.time, monotonic=clock.monotonic)
    active = manager.get_active_snapshot()
    moved = path.with_suffix(".tmp")
    os.replace(path, moved)
    assert manager.poll_once() is False
    assert manager.get_active_snapshot() is active
    assert manager.status()["config_reload_status"] == "RELOAD_FAILED"


def test_readonly_diagnostics_endpoint_projects_canonical_snapshot():
    response = TestClient(create_app()).get("/api/v1/trading/config")
    assert response.status_code == 200
    body = response.json()
    assert body["config_reload_status"] in {"ACTIVE", "PENDING_SAFE_BOUNDARY"}
    assert body["config_active_generation"] > 0
    assert body["active_parameter_set"] == "scalping-v2-set-2"
    assert body["parameters"]["geometry.minimum_planned_rr"]["effective_value"] > 0
