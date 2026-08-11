from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from app.engine_safety import paper_production_control as safety


ALL_STAGES = tuple(safety.MutationStage)
GOOD_PREREQUISITES = safety.MutationPrerequisites(True, True, True, True, True)


def target(**changes):
    values = dict(
        environment="PRODUCTION", mode="PAPER", symbol="BTCUSDT",
        candidate_identity="candidate:1", current_generation=2,
        new_commands_before=0, open_positions_before=0,
    )
    values.update(changes)
    return safety.PaperProductionMutationTarget(**values)


def test_default_constants_and_no_remote_control_surface():
    assert safety.ENVIRONMENT == "PRODUCTION"
    assert safety.MODE == "PAPER"
    assert safety.DEFAULT_CONTROL_ROOT == Path(r"D:\disk_E\game_projects\traders\production_control\paper")
    source = Path(safety.__file__).read_text(encoding="utf-8")
    assert "FastAPI" not in source
    assert "POST /arm" not in source
    assert "DATABASE_URL" not in source
    assert "TRADERS_ML_POSTGRES_PASSWORD" not in source


def test_contracts_are_immutable(scope, passed_preflight):
    state = safety.PaperProductionSafetyState(
        safety.SCHEMA_VERSION, "PRODUCTION", "PAPER", safety.PersistentState.ARMED,
        2, safety.PersistentState.DISABLED, "2026-08-11T00:00:00Z",
        safety.ReasonCode.SAFETY_TEST, safety.OPERATOR_ROLE,
        "00000000-0000-4000-8000-000000000001", scope,
    )
    for value in (state, scope, passed_preflight, target(), GOOD_PREREQUISITES):
        with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
            value.generation = 999


@pytest.mark.parametrize("values", [
    (0, 1, ("BTCUSDT",), "PAPER", False),
    (1, 0, ("BTCUSDT",), "PAPER", False),
    (1, 1, (), "PAPER", False),
    (1, 1, ("btc",), "PAPER", False),
    (1, 1, ("BTCUSDT", "BTCUSDT"), "PAPER", False),
    (1, 1, ("ETHUSDT", "BTCUSDT"), "PAPER", False),
    (1, 1, ("BTCUSDT",), "LIVE", False),
    (1, 1, ("BTCUSDT",), "PAPER", True),
])
def test_invalid_arming_scopes_fail_closed(values):
    with pytest.raises(ValueError):
        safety.PaperProductionArmingScope(*values)


def test_initialize_is_disabled_generation_one_and_reconciled(control):
    state = control.read_authoritative()
    assert state.state is safety.PersistentState.DISABLED
    assert state.generation == 1
    assert state.previous_state is None
    assert state.arming_scope is None
    assert control.health().effective_state is safety.EffectiveState.DISABLED


def test_initialize_requires_acknowledgement(tmp_path):
    control = safety.PaperProductionSafetyControl(tmp_path / "control", acl_checker=lambda _path: True)
    with pytest.raises(safety.SafetyControlError, match="ACKNOWLEDGEMENT_REQUIRED"):
        control.initialize_disabled(acknowledge=False)
    assert not control.state_path.exists()


def test_initialize_never_overwrites_existing_control(control):
    before = control.state_path.read_bytes()
    with pytest.raises(safety.SafetyControlError, match="ALREADY_INITIALIZED"):
        control.initialize_disabled(acknowledge=True)
    assert control.state_path.read_bytes() == before


@pytest.mark.parametrize("stage", ALL_STAGES)
def test_disabled_denies_every_stage(control, stage):
    gate = safety.PaperProductionMutationSafetyGate(control)
    with pytest.raises(safety.SafetyControlError, match="MUTATION_DENIED_DISABLED"):
        with gate.authorize_mutation(stage, replace(target(), current_generation=1), GOOD_PREREQUISITES):
            pytest.fail("denied body must not run")


@pytest.mark.parametrize("stage", ALL_STAGES)
def test_emergency_stop_denies_every_stage(control, stage):
    control.transition(safety.PersistentState.EMERGENCY_STOP, expected_generation=1,
                       reason=safety.ReasonCode.SAFETY_TEST, acknowledge=True)
    gate = safety.PaperProductionMutationSafetyGate(control)
    with pytest.raises(safety.SafetyControlError, match="MUTATION_DENIED_EMERGENCY_STOP"):
        with gate.authorize_mutation(stage, target(), GOOD_PREREQUISITES):
            pytest.fail("denied body must not run")


def test_clear_emergency_stop_returns_only_disabled(control):
    stopped = control.transition(safety.PersistentState.EMERGENCY_STOP, expected_generation=1,
                                 reason=safety.ReasonCode.OPERATOR_EMERGENCY_STOP, acknowledge=True)
    cleared = control.transition(safety.PersistentState.DISABLED, expected_generation=stopped.generation,
                                 reason=safety.ReasonCode.CLEAR_EMERGENCY_STOP, acknowledge=True)
    assert cleared.state is safety.PersistentState.DISABLED
    assert cleared.arming_scope is None


def test_direct_emergency_stop_to_armed_is_impossible(control, passed_preflight, scope):
    stopped = control.transition(safety.PersistentState.EMERGENCY_STOP, expected_generation=1,
                                 reason=safety.ReasonCode.SAFETY_TEST, acknowledge=True)
    with pytest.raises(safety.SafetyControlError, match="ILLEGAL_TRANSITION"):
        control.transition(safety.PersistentState.ARMED, expected_generation=stopped.generation,
                           reason=safety.ReasonCode.SAFETY_TEST, acknowledge=True,
                           acknowledge_paper_arming=True, preflight=passed_preflight,
                           arming_scope=scope)


def test_emergency_stop_is_safe_idempotent_without_generation_increment(control):
    first = control.transition(safety.PersistentState.EMERGENCY_STOP, expected_generation=1,
                               reason=safety.ReasonCode.SAFETY_TEST, acknowledge=True)
    audit_before = control.audit_path.read_bytes()
    second = control.transition(safety.PersistentState.EMERGENCY_STOP, expected_generation=2,
                                reason=safety.ReasonCode.SAFETY_TEST, acknowledge=True)
    assert second == first
    assert second.generation == 2
    assert control.audit_path.read_bytes() == audit_before


def test_stale_generation_rejected_before_transition(control):
    with pytest.raises(safety.SafetyControlError, match="STALE_GENERATION"):
        control.transition(safety.PersistentState.EMERGENCY_STOP, expected_generation=0,
                           reason=safety.ReasonCode.SAFETY_TEST, acknowledge=True)


@pytest.mark.parametrize("index", range(9))
def test_every_arm_preflight_requirement_is_mandatory(control, passed_preflight, scope, index):
    values = list(passed_preflight.__dict__.values()) if hasattr(passed_preflight, "__dict__") else [
        getattr(passed_preflight, field) for field in passed_preflight.__slots__
    ]
    values[index] = False
    preflight = safety.ArmReadinessPreflight(*values)
    with pytest.raises(safety.SafetyControlError, match="ARM_PREFLIGHT_FAILED"):
        control.transition(safety.PersistentState.ARMED, expected_generation=1,
                           reason=safety.ReasonCode.OPERATOR_ARM, acknowledge=True,
                           acknowledge_paper_arming=True, preflight=preflight, arming_scope=scope)
    assert control.read_authoritative().state is safety.PersistentState.DISABLED


def test_no_trade_is_not_arm_preflight_requirement(passed_preflight):
    assert not hasattr(passed_preflight, "approval_candidate_eligible")
    assert passed_preflight.approval_source_adapter_ready


def test_arm_requires_separate_acknowledgement_and_scope(control, passed_preflight, scope):
    with pytest.raises(safety.SafetyControlError, match="PAPER_ARMING_ACKNOWLEDGEMENT_REQUIRED"):
        control.transition(safety.PersistentState.ARMED, expected_generation=1,
                           reason=safety.ReasonCode.OPERATOR_ARM, acknowledge=True,
                           preflight=passed_preflight, arming_scope=scope)
    with pytest.raises(safety.SafetyControlError, match="ARMING_SCOPE_REQUIRED"):
        control.transition(safety.PersistentState.ARMED, expected_generation=1,
                           reason=safety.ReasonCode.OPERATOR_ARM, acknowledge=True,
                           acknowledge_paper_arming=True, preflight=passed_preflight)


def test_armed_isolated_authorizes_exactly_one_stage(armed_control):
    calls = []
    composition = safety.ProductionPaperMutationComposition(
        safety.PaperProductionMutationSafetyGate(armed_control)
    )
    result = composition.run_one_atomic_stage(
        safety.MutationStage.COMMAND_INGESTION, target(), GOOD_PREREQUISITES,
        lambda: calls.append("atomic") or "done",
    )
    assert result == "done"
    assert calls == ["atomic"]


@pytest.mark.parametrize("stage", ALL_STAGES)
def test_live_is_always_denied(armed_control, stage):
    gate = safety.PaperProductionMutationSafetyGate(armed_control)
    with pytest.raises(safety.SafetyControlError, match="LIVE_OR_NON_PRODUCTION_TARGET_DENIED"):
        with gate.authorize_mutation(stage, target(mode="LIVE"), GOOD_PREREQUISITES):
            pass


@pytest.mark.parametrize("change,code", [
    ({"symbol": "ETHUSDT"}, "SYMBOL_SCOPE_DENIED"),
    ({"current_generation": 1}, "STALE_GENERATION"),
    ({"new_commands_before": 1}, "NEW_COMMAND_BUDGET_EXHAUSTED"),
    ({"open_positions_before": 1}, "OPEN_POSITION_BUDGET_EXHAUSTED"),
    ({"candidate_identity": ""}, "INVALID_CANDIDATE_IDENTITY"),
    ({"candidate_identity": "postgresql://forbidden"}, "INVALID_CANDIDATE_IDENTITY"),
])
def test_scope_generation_budget_and_identity_denials(armed_control, change, code):
    gate = safety.PaperProductionMutationSafetyGate(armed_control)
    with pytest.raises(safety.SafetyControlError, match=code):
        with gate.authorize_mutation(safety.MutationStage.COMMAND_INGESTION,
                                     target(**change), GOOD_PREREQUISITES):
            pass


@pytest.mark.parametrize("index", range(5))
def test_gate_is_conjunction_of_all_independent_prerequisites(armed_control, index):
    values = [True] * 5
    values[index] = False
    prerequisites = safety.MutationPrerequisites(*values)
    gate = safety.PaperProductionMutationSafetyGate(armed_control)
    with pytest.raises(safety.SafetyControlError, match="INDEPENDENT_READINESS_GATE_DENIED"):
        with gate.authorize_mutation(safety.MutationStage.ENTRY_EXECUTION, target(), prerequisites):
            pass


def test_status_is_read_only(control):
    state_before = control.state_path.read_bytes()
    audit_before = control.audit_path.read_bytes()
    report = safety._render_state(control)
    assert report["state"] == "DISABLED"
    assert report["effective_state"] == "DISABLED"
    assert report["health"] == "HEALTHY"
    assert control.state_path.read_bytes() == state_before
    assert control.audit_path.read_bytes() == audit_before


def test_cli_has_only_local_control_commands():
    parser = safety.build_parser()
    help_text = parser.format_help()
    assert "--root" in help_text
    source = Path(safety.__file__).read_text(encoding="utf-8")
    for command in ("status", "initialize-disabled", "arm", "disable", "emergency-stop", "clear-emergency-stop", "audit-status"):
        assert f'"{command}"' in source


def test_cli_live_arm_denied_before_any_write(tmp_path):
    root = tmp_path / "live-denied"
    result = safety.main([
        "--root", str(root), "arm", "--environment", "PRODUCTION", "--mode", "LIVE",
        "--expected-generation", "1", "--reason", "OPERATOR_ARM",
        "--acknowledge-production-control", "--acknowledge-paper-arming",
        "--schema", "0011_paper_close_causal_boundary_and_exit_evaluation_cursor",
        "--pitr-window-seconds", "86400", "--market-data-ready", "--approval-source-ready",
        "--wal-archive-health", "PASS", "--wal-unresolved-failures", "0", "--pitr-chain-valid",
        "--paper-runtime-enabled", "--max-new-commands", "1", "--max-open-positions", "1",
        "--allowed-symbol", "BTCUSDT",
    ])
    assert result == 2
    assert not root.exists()


def test_production_current_preflight_denial_reasons_are_exact():
    current = safety.ArmReadinessPreflight(False, False, True, True, True, True, True, False, True)
    assert current.findings == (
        "PAPER_SCHEMA_NOT_AT_REQUIRED_HEAD",
        "MINIMUM_24_HOUR_PITR_WINDOW_NOT_PROVEN",
        "PAPER_RUNTIME_NOT_EXPLICITLY_ENABLED",
    )


def test_reason_codes_are_bounded_non_secret_vocabulary():
    assert {item.value for item in safety.ReasonCode} == {
        "INITIALIZE_SAFE_DEFAULT", "OPERATOR_ARM", "OPERATOR_DISABLE",
        "OPERATOR_EMERGENCY_STOP", "CLEAR_EMERGENCY_STOP", "PREPARATION_CANARY", "SAFETY_TEST",
    }
    assert all(len(item.value) <= safety.MAX_REASON_LENGTH for item in safety.ReasonCode)


def test_audit_has_safe_bounded_fields_only(control):
    event = json.loads(control.audit_path.read_text(encoding="utf-8"))
    assert set(event) == {
        "schema_version", "transition_id", "timestamp_utc", "environment", "mode",
        "from_state", "to_state", "generation_before", "generation_after", "reason_code",
        "operator_role", "result", "state_checksum_sha256",
    }
    rendered = json.dumps(event)
    assert "://" not in rendered
    assert "password" not in rendered.lower()


def test_source_has_no_automatic_transition_trigger():
    source = Path(safety.__file__).read_text(encoding="utf-8")
    forbidden = ("auto_arm", "approval_signal", "healthy_market_auto", "auto_clear")
    assert not any(value in source.lower() for value in forbidden)


def test_module_imports_without_database_network_or_protected_binding(monkeypatch):
    command = [sys.executable, "-I", "-c", (
        "import sys;sys.path.insert(0,'.');"
        "import app.engine_safety.paper_production_control as m;"
        "print(m.ENVIRONMENT,m.MODE)"
    )]
    result = subprocess.run(command, cwd=Path(__file__).parents[2], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    assert result.stdout.strip() == "PRODUCTION PAPER"
