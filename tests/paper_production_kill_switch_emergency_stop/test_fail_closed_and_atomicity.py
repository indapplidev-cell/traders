from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app.engine_safety import paper_production_control as safety


def fresh(tmp_path, *, fault=None, acl=lambda _path: True):
    return safety.PaperProductionSafetyControl(tmp_path / "control", acl_checker=acl, fault_injector=fault)


@pytest.mark.parametrize("mutation,code", [
    (lambda control: control.state_path.unlink(), "STATE_MISSING"),
    (lambda control: control.state_path.write_text("{", encoding="utf-8"), "CORRUPT_STATE"),
    (lambda control: control.state_path.write_text("{}", encoding="utf-8"), "INVALID_STATE_SHAPE"),
    (lambda control: control.audit_path.unlink(), "AUDIT_MISSING"),
    (lambda control: control.audit_path.write_text("{", encoding="utf-8"), "AUDIT_CORRUPT"),
    (lambda control: control.audit_path.write_text("", encoding="utf-8"), "AUDIT_EMPTY"),
])
def test_missing_or_corrupt_control_fails_closed(tmp_path, mutation, code):
    control = fresh(tmp_path)
    control.initialize_disabled(acknowledge=True)
    mutation(control)
    health = control.health()
    assert health.effective_state is safety.EffectiveState.FAIL_CLOSED
    assert health.health == "FAIL_CLOSED"
    gate = safety.PaperProductionMutationSafetyGate(control)
    with pytest.raises(safety.SafetyControlError):
        with gate.authorize_mutation(
            safety.MutationStage.ENTRY_EXECUTION,
            safety.PaperProductionMutationTarget("PRODUCTION", "PAPER", "BTCUSDT", "candidate:1", 1),
            safety.MutationPrerequisites(True, True, True, True, True),
        ):
            pass


def rewrite_state(control, transform):
    doc = json.loads(control.state_path.read_text(encoding="utf-8"))
    doc.pop("checksum_sha256")
    transform(doc)
    doc["checksum_sha256"] = safety.hashlib.sha256(safety._json_bytes(doc)).hexdigest()
    control.state_path.write_bytes(safety._json_bytes(doc))


@pytest.mark.parametrize("transform,code", [
    (lambda doc: doc.update(schema_version="future/99"), "UNKNOWN_SCHEMA"),
    (lambda doc: doc.update(state="UNKNOWN"), "INVALID_STATE"),
    (lambda doc: doc.update(generation=0), "INVALID_STATE"),
    (lambda doc: doc.update(environment="STAGING"), "INVALID_STATE"),
    (lambda doc: doc.update(trading_mode="LIVE"), "INVALID_STATE"),
])
def test_semantically_invalid_state_fails_closed(tmp_path, transform, code):
    control = fresh(tmp_path)
    control.initialize_disabled(acknowledge=True)
    rewrite_state(control, transform)
    with pytest.raises(safety.SafetyControlError, match=code):
        control.read_authoritative()
    assert control.health().effective_state is safety.EffectiveState.FAIL_CLOSED


def test_checksum_corruption_fails_closed(tmp_path):
    control = fresh(tmp_path)
    control.initialize_disabled(acknowledge=True)
    data = bytearray(control.state_path.read_bytes())
    data[data.index(b"DISABLED")] = ord("X")
    control.state_path.write_bytes(data)
    with pytest.raises(safety.SafetyControlError, match="CHECKSUM|INVALID_STATE"):
        control.read_authoritative()


def test_state_audit_mismatch_fails_closed(tmp_path):
    control = fresh(tmp_path)
    control.initialize_disabled(acknowledge=True)
    rewrite_state(control, lambda doc: doc.update(transition_id="00000000-0000-4000-8000-000000000099"))
    with pytest.raises(safety.SafetyControlError, match="STATE_AUDIT_MISMATCH"):
        control.read_authoritative()
    assert control.health().effective_state is safety.EffectiveState.FAIL_CLOSED


@pytest.mark.parametrize("change,code", [
    ({"generation_after": 2}, "AUDIT_GENERATION_NON_MONOTONIC"),
    ({"generation_before": 1}, "AUDIT_GENERATION_NON_MONOTONIC"),
    ({"to_state": "ARMED"}, "AUDIT_ILLEGAL_TRANSITION"),
    ({"schema_version": "future"}, "AUDIT_INVALID_EVENT"),
    ({"result": "FAIL"}, "AUDIT_INVALID_EVENT"),
])
def test_invalid_audit_fails_closed(tmp_path, change, code):
    control = fresh(tmp_path)
    control.initialize_disabled(acknowledge=True)
    event = json.loads(control.audit_path.read_text(encoding="utf-8"))
    event.update(change)
    control.audit_path.write_bytes(safety._json_bytes(event))
    with pytest.raises(safety.SafetyControlError, match=code):
        control.read_authoritative()


def test_duplicate_audit_transition_id_fails_closed(tmp_path):
    control = fresh(tmp_path)
    control.initialize_disabled(acknowledge=True)
    line = control.audit_path.read_bytes()
    control.audit_path.write_bytes(line + line)
    with pytest.raises(safety.SafetyControlError, match="DUPLICATE|GENERATION"):
        control.read_authoritative()


def test_unsafe_acl_fails_closed(tmp_path):
    control = fresh(tmp_path, acl=lambda _path: False)
    control.root.mkdir(parents=True)
    control.state_path.write_text("{}", encoding="utf-8")
    control.audit_path.write_text("{}", encoding="utf-8")
    control.interlock_path.write_text("0", encoding="utf-8")
    with pytest.raises(safety.SafetyControlError, match="UNSAFE_ACL"):
        control.read_authoritative()
    assert control.health().effective_state is safety.EffectiveState.FAIL_CLOSED


FAULT_POINTS = (
    "before lock", "after lock", "after current read", "after pending write",
    "after pending flush", "before replace", "after replace", "before audit append",
    "during audit append", "after audit append", "before unlock",
)


@pytest.mark.parametrize("point", FAULT_POINTS)
def test_fault_injection_never_publishes_partial_armed(tmp_path, passed_preflight, scope, point):
    control = fresh(tmp_path)
    control.initialize_disabled(acknowledge=True)
    fired = False

    def fault(candidate):
        nonlocal fired
        if candidate == point and not fired:
            fired = True
            raise safety.SafetyControlError("INJECTED_FAULT")

    control._fault = fault
    with pytest.raises(safety.SafetyControlError, match="INJECTED_FAULT"):
        control.transition(safety.PersistentState.ARMED, expected_generation=1,
                           reason=safety.ReasonCode.SAFETY_TEST, acknowledge=True,
                           acknowledge_paper_arming=True, preflight=passed_preflight, arming_scope=scope)
    assert fired
    assert not control.pending_path.exists()
    health = control.health()
    if point in {"after audit append", "before unlock"}:
        assert health.effective_state is safety.EffectiveState.ARMED
    elif point in {"after replace", "before audit append", "during audit append"}:
        assert health.effective_state is safety.EffectiveState.FAIL_CLOSED
    else:
        assert health.effective_state is safety.EffectiveState.DISABLED


def test_interlock_timeout_is_bounded_and_deterministic(control):
    competitor = safety.PaperProductionSafetyControl(control.root, interlock_timeout_seconds=0.02,
                                                     acl_checker=lambda _path: True)
    with control._lock():
        started = safety.time.monotonic()
        with pytest.raises(safety.SafetyControlError, match="INTERLOCK_BUSY"):
            with competitor._lock():
                pass
        elapsed = safety.time.monotonic() - started
    assert elapsed < 0.5


def test_invalid_interlock_timeout_fails_closed(tmp_path):
    control = safety.PaperProductionSafetyControl(tmp_path / "control", interlock_timeout_seconds=31,
                                                 acl_checker=lambda _path: True)
    with pytest.raises(safety.SafetyControlError, match="INVALID_INTERLOCK_TIMEOUT"):
        with control._lock():
            pass


def test_real_temp_acl_is_restrictive(tmp_path):
    control = safety.PaperProductionSafetyControl(tmp_path / "acl-control")
    control.initialize_disabled(acknowledge=True)
    assert all(safety.restrictive_acl_valid(path) for path in (
        control.root, control.state_path, control.audit_path, control.interlock_path,
    ))
