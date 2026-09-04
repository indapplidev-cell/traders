from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.engine_paper.production_approval import (
    PaperProductionApprovalOutcome,
    PaperProductionApprovalReadiness,
)
from app.engine_safety.production_control_root import (
    PRODUCTION_CONTROL_ROOT_KEY,
    resolve_production_control_root,
)
from app.server_api import paper_runtime_observation as observation
from app.server_api.schemas.paper import PaperControlStatus


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _recovery(root: Path, *, now: datetime, gap: bool = False) -> None:
    base = root / "base" / "base-1"
    (base / "pg_wal").mkdir(parents=True)
    (base / "backup_label").write_text(
        "START WAL LOCATION: 1/92000028 (file 000000010000000100000092)\n"
        "START TIMELINE: 1\n",
        encoding="utf-8",
    )
    (base / "pg_wal" / "000000010000000100000092").write_bytes(b"")
    archive = root / "wal_archive"
    archive.mkdir()
    names = ["000000010000000100000092", "000000010000000100000094"] if gap else [
        "000000010000000100000092", "000000010000000100000093"
    ]
    for name in names:
        path = archive / name
        path.write_bytes(b"")
        os.utime(path, (now.timestamp(), now.timestamp()))
    _write_json(root / "catalog" / "catalog.json", {
        "schema": "TRADERS_ML_BACKUP_CATALOG_V1",
        "entries": [{
            "artifact_type": "BASE",
            "source_class": "PRODUCTION",
            "verification_status": "PUBLISHED",
            "recovery_anchor_valid": True,
            "relative_path": "base/base-1",
            "created_at": (now - timedelta(days=2)).isoformat().replace("+00:00", "Z"),
        }],
    })
    _write_json(root / "catalog" / "wal_ack_daemon_state.json", {
        "schema": "TRADERS_ML_WAL_ACK_DAEMON_STATE_V1",
        "status": "RUNNING",
        "error_class": "NONE",
        "export_backlog_count": 0,
        "pending_archive_status_count": 0,
        "updated_at": now.isoformat().replace("+00:00", "Z"),
    })


def test_shared_production_control_root_default_override_and_rejection() -> None:
    assert resolve_production_control_root({}).as_posix().endswith("/run/traders-control")
    assert resolve_production_control_root({PRODUCTION_CONTROL_ROOT_KEY: "/run/shared-control"}).as_posix().endswith("/run/shared-control")
    with pytest.raises(ValueError, match="PRODUCTION_CONTROL_ROOT_INVALID"):
        resolve_production_control_root({PRODUCTION_CONTROL_ROOT_KEY: "relative/control"})


def test_readonly_and_control_runtime_use_only_shared_resolver() -> None:
    root = Path(__file__).resolve().parents[2]
    readonly = (root / "app/server_api/runtime.py").read_text(encoding="utf-8")
    control = (root / "app/operator_control/runtime.py").read_text(encoding="utf-8")
    assert "resolve_production_control_root()" in readonly
    assert "resolve_production_control_root()" in control
    assert "/run/traders-control" not in readonly
    assert "/run/traders-control" not in control


def test_current_wal_and_pitr_chain_are_observed_and_gap_fails_closed(tmp_path: Path) -> None:
    now = datetime(2026, 8, 13, 20, tzinfo=timezone.utc)
    good = tmp_path / "good"
    _recovery(good, now=now)
    assert observation._pitr_readiness(good, now) == (True, True)
    lineage = observation._pitr_lineage(good, now)
    assert lineage.lineage_valid is True and lineage.physical_gap is False
    assert lineage.lineage_start is not None and lineage.lineage_end is not None
    assert lineage.contiguous_duration_seconds >= 24 * 60 * 60
    gap = tmp_path / "gap"
    _recovery(gap, now=now, gap=True)
    assert observation._pitr_readiness(gap, now) == (False, False)


def test_disabled_runtime_configuration_is_exact_and_live_safe(tmp_path: Path) -> None:
    _write_json(tmp_path / observation.RUNTIME_CONFIGURATION_NAME, {
        "auto_arm": False, "auto_start": False, "daemon_enabled": False,
        "dry_run": True, "live_enabled": False, "runtime_enabled": False,
        "scheduler_enabled": False, "state": "DEPLOYED_DISABLED",
    })
    assert observation._runtime_configuration_ready(tmp_path)
    payload = json.loads((tmp_path / observation.RUNTIME_CONFIGURATION_NAME).read_text())
    payload["live_enabled"] = True
    _write_json(tmp_path / observation.RUNTIME_CONFIGURATION_NAME, payload)
    assert not observation._runtime_configuration_ready(tmp_path)


def test_market_health_accepts_exact_current_and_existing_grace_semantics(tmp_path: Path) -> None:
    now = datetime(2026, 8, 13, 20, tzinfo=timezone.utc)
    snapshots = [{
        "symbol": symbol, "timeframe": timeframe, "status": "OK",
        "missing_count": 0, "freshness_lag_candles": 0, "last_error": None,
        "stored_open_time_ms": 100, "expected_open_time_ms": 100,
    } for symbol in observation.MARKET_SYMBOLS for timeframe in observation.TIMEFRAME_ALLOWLIST]
    payload = {
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "overall_status": "OK", "symbols": list(observation.MARKET_SYMBOLS),
        "timeframes": list(observation.TIMEFRAME_ALLOWLIST), "snapshots": snapshots,
    }
    _write_json(tmp_path / "latest_health.json", payload)
    assert observation._market_data_readiness(tmp_path, now)

    expected_open = int(now.timestamp() * 1000) - 60_000
    for item in snapshots:
        if item["timeframe"] == "1m":
            item.update(status="RECOVERING", freshness_lag_candles=1,
                        expected_open_time_ms=expected_open,
                        stored_open_time_ms=expected_open - 60_000)
    payload["overall_status"] = "RECOVERING"
    _write_json(tmp_path / "latest_health.json", payload)
    assert observation._market_data_readiness(tmp_path, now)

    # The producer may retain aggregate OK during the same boundary grace
    # window; readiness is governed by the explicit lag/boundary fields.
    for item in snapshots:
        if item["timeframe"] == "1m":
            item["status"] = "OK"
    payload["overall_status"] = "OK"
    _write_json(tmp_path / "latest_health.json", payload)
    assert observation._market_data_readiness(tmp_path, now)

    snapshots[0]["missing_count"] = 1
    _write_json(tmp_path / "latest_health.json", payload)
    assert not observation._market_data_readiness(tmp_path, now)


def test_production_observation_populates_authoritative_sources(monkeypatch, tmp_path: Path) -> None:
    clock_values = iter((
        datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc),
        datetime(2026, 8, 31, 12, 0, 15, tzinfo=timezone.utc),
    ))
    heartbeat_read_at = []
    source = observation.ProductionPaperRuntimeObservationSource(
        lambda: None,
        lambda: PaperControlStatus(
            state="ARMED", effective_state="ARMED", generation=6,
            health="HEALTHY", emergency_stop_available=True,
            audit_health="PASS", state_audit_reconciliation="PASS",
        ),
        runtime_root=tmp_path,
        recovery_root=tmp_path,
        runtime_health_root=tmp_path,
        clock=lambda: next(clock_values),
    )
    source._approval = SimpleNamespace(read=lambda request: SimpleNamespace(
        readiness=PaperProductionApprovalReadiness.HEALTHY_NO_ELIGIBLE_APPROVAL,
        outcome=PaperProductionApprovalOutcome.NO_TRADE_SIGNAL,
    ))
    monkeypatch.setattr(observation, "_runtime_configuration_ready", lambda root: True)
    monkeypatch.setattr(observation, "_market_data_readiness", lambda root, now: True)
    monkeypatch.setattr(observation, "load_production_identity", lambda root: object())
    monkeypatch.setattr(observation, "_pitr_lineage", lambda root, now: observation.PitrLineageObservation(
        wal_ready=True, pitr_ready=True, lineage_valid=True,
    ))
    monkeypatch.setattr(observation, "_runtime_principal_ready", lambda sessions: True)
    def runtime_health(root, now):
        heartbeat_read_at.append(now)
        return {
            "runtime_enabled": True, "daemon_enabled": True, "scheduler_enabled": True,
            "mutation_enabled": True, "approval_watcher_active": True,
            "selector_active": True, "execution_worker_active": True,
            "approval_ticks": 2, "execution_ticks": 3,
        }
    monkeypatch.setattr(observation, "read_paper_runtime_health", runtime_health)

    value = source()

    assert value.environment == "production"
    assert value.market_data_adapter_ready is True
    assert value.approval_source_adapter_ready is True
    assert value.current_approval_availability == "NO_TRADE_SIGNAL"
    assert value.wal_ready is value.pitr_ready is True
    assert value.runtime_enabled is value.runtime_config_ready is True
    assert value.daemon_enabled is value.scheduler_enabled is True
    assert value.paper_principal_ready is value.kill_switch_ready is True
    assert value.canary_scope_valid is True
    assert value.mutation_enabled is True and value.live_enabled is False
    assert value.worker_running is True
    assert heartbeat_read_at == [datetime(2026, 8, 31, 12, 0, 15, tzinfo=timezone.utc)]


def test_selected_execution_projection_is_identity_bound_and_terminal_visible() -> None:
    outcome = SimpleNamespace(
        pipeline_run_id="orchestrator:run-sui", symbol="SUIUSDT",
        trade_profile_id="trade-5m-v1", boundary_closed_at_ms=1788279600000,
        candidate_id="candidate:sui", final_approval_id="approval:sui",
        paper_plan_id="plan:sui", approval_valid_until_ms=1788279899999,
        selector_state="SELECTED", selector_rank=1,
        first_observed_at=datetime(2026, 9, 1, 16, 20, 58, tzinfo=timezone.utc),
        updated_at=datetime(2026, 9, 1, 16, 25, 31, tzinfo=timezone.utc),
        lifecycle_state="EXPIRED_BEFORE_EXECUTION", command_id=None,
        terminal_reason="EXPIRED_BEFORE_EXECUTION", selector_reason=None,
        attempt_count=8, control_generation=6,
    )

    class Result:
        def one_or_none(self):
            return outcome, None, None, None

    class FakeSession:
        def __enter__(self): return self
        def __exit__(self, *_): return None
        def execute(self, _statement): return Result()

    source = observation.ProductionPaperRuntimeObservationSource(
        lambda: FakeSession(), lambda: None
    )
    value = source._current_execution()
    assert value is not None
    assert value["source_run_id"] == outcome.pipeline_run_id
    assert value["candidate_id"] == outcome.candidate_id
    assert value["approval_id"] == outcome.final_approval_id
    assert value["command_status"] == "EXPIRED"
    assert value["terminal_reason"] == "EXPIRED_BEFORE_EXECUTION"
    assert value["selected_at"] == "2026-09-01T16:20:58.000Z"
    assert value["scheduler_last_observed_at"] == "2026-09-01T16:25:31.000Z"
    assert value["policy_generation"] == 6
    assert value["policy_reason_source"] == "READONLY_PAPER_READINESS_CURRENT_SNAPSHOT"


@pytest.mark.parametrize(
    "command_status,position_state,expected_lifecycle",
    (
        ("PROCESSING", "OPEN", "POSITION_OPEN"),
        ("PROCESSING", "CLOSING", "POSITION_CLOSING"),
        ("COMPLETED", "CLOSED", "COMPLETED"),
    ),
)
def test_position_state_advances_command_lifecycle_projection(
    command_status: str, position_state: str, expected_lifecycle: str
) -> None:
    outcome = SimpleNamespace(
        pipeline_run_id="orchestrator:run-eth", symbol="ETHUSDT",
        trade_profile_id="trade-5m-v2", boundary_closed_at_ms=1788534300000,
        candidate_id="candidate:eth", final_approval_id="approval:eth",
        paper_plan_id="plan:eth", approval_valid_until_ms=1788534599999,
        selector_state="SELECTED", selector_rank=1,
        first_observed_at=datetime(2026, 9, 4, 15, 5, tzinfo=timezone.utc),
        updated_at=datetime(2026, 9, 4, 15, 6, tzinfo=timezone.utc),
        lifecycle_state="COMMAND_CREATED", command_id="command:eth",
        terminal_reason=None, selector_reason=None, attempt_count=1,
        control_generation=12,
    )

    class Result:
        def one_or_none(self):
            return outcome, command_status, "position:eth", position_state

    class FakeSession:
        def __enter__(self): return self
        def __exit__(self, *_): return None
        def execute(self, _statement): return Result()

    value = observation.ProductionPaperRuntimeObservationSource(
        lambda: FakeSession(), lambda: None
    )._current_execution()
    assert value is not None
    assert value["command_status"] == command_status
    assert value["position_status"] == position_state
    assert value["lifecycle_state"] == expected_lifecycle
    assert not (
        value["position_status"] in {"OPEN", "CLOSING", "CLOSED"}
        and value["command_status"] == "PENDING"
    )


@pytest.mark.parametrize("failure", ("market", "approval", "control", "runtime", "pitr", "principal"))
def test_each_authoritative_failure_remains_fail_closed(monkeypatch, tmp_path: Path, failure: str) -> None:
    def control():
        if failure == "control":
            raise RuntimeError("unavailable")
        return PaperControlStatus(
            state="DISABLED", effective_state="DISABLED", generation=3,
            health="HEALTHY", emergency_stop_available=True,
            audit_health="PASS", state_audit_reconciliation="PASS",
        )

    source = observation.ProductionPaperRuntimeObservationSource(
        lambda: None, control, runtime_root=tmp_path, recovery_root=tmp_path,
        runtime_health_root=tmp_path,
    )
    source._approval = SimpleNamespace(read=lambda request: (_ for _ in ()).throw(RuntimeError()) if failure == "approval" else SimpleNamespace(readiness=PaperProductionApprovalReadiness.READY, outcome=PaperProductionApprovalOutcome.ELIGIBLE_APPROVAL))
    monkeypatch.setattr(observation, "_runtime_configuration_ready", lambda root: failure != "runtime")
    monkeypatch.setattr(observation, "_market_data_readiness", lambda root, now: failure != "market")
    monkeypatch.setattr(observation, "load_production_identity", lambda root: object())
    monkeypatch.setattr(observation, "_pitr_readiness", lambda root, now: (failure != "pitr", failure != "pitr"))
    monkeypatch.setattr(observation, "_runtime_principal_ready", lambda sessions: failure != "principal")
    monkeypatch.setattr(
        observation,
        "read_paper_runtime_health",
        lambda root, now: None if failure == "runtime" else {
            "runtime_enabled": True, "daemon_enabled": True, "scheduler_enabled": True,
            "mutation_enabled": True, "approval_watcher_active": True,
            "selector_active": True, "execution_worker_active": True,
            "approval_ticks": 1, "execution_ticks": 1,
        },
    )

    value = source()
    checks = {
        "market": value.market_data_adapter_ready,
        "approval": value.approval_source_adapter_ready,
        "control": value.kill_switch_ready,
        "runtime": value.runtime_config_ready,
        "pitr": value.pitr_ready,
        "principal": value.paper_principal_ready,
    }
    assert checks[failure] is False
