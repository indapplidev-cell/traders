from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.engine_safety import paper_production_control as safety


PREFLIGHT = safety.ArmReadinessPreflight(True, True, True, True, True, True, True, True, True)
SCOPE = safety.PaperProductionArmingScope(1, 1, ("BTCUSDT",))
PREREQUISITES = safety.MutationPrerequisites(True, True, True, True, True)


def attempt(control, target):
    try:
        return control.transition(
            target, expected_generation=1, reason=safety.ReasonCode.SAFETY_TEST,
            acknowledge=True, acknowledge_paper_arming=target is safety.PersistentState.ARMED,
            preflight=PREFLIGHT if target is safety.PersistentState.ARMED else None,
            arming_scope=SCOPE if target is safety.PersistentState.ARMED else None,
        ).state.value
    except safety.SafetyControlError as error:
        return str(error)


def test_two_arms_same_generation_at_most_one_succeeds(control):
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(control, safety.PersistentState.ARMED), range(2)))
    assert results.count("ARMED") == 1
    assert results.count("STALE_GENERATION") == 1
    assert control.read_authoritative().generation == 2


def test_emergency_stop_wins_then_stale_arm_cannot_overwrite(control):
    stopped = attempt(control, safety.PersistentState.EMERGENCY_STOP)
    armed = attempt(control, safety.PersistentState.ARMED)
    assert stopped == "EMERGENCY_STOP"
    assert armed == "STALE_GENERATION"
    assert control.read_authoritative().state is safety.PersistentState.EMERGENCY_STOP


def test_disable_vs_emergency_stop_conflict_has_one_success(tmp_path):
    armed_control = safety.PaperProductionSafetyControl(
        tmp_path / "disable-stop", acl_checker=lambda _path: True
    )
    armed_control.initialize_disabled(acknowledge=True)
    armed_control.transition(
        safety.PersistentState.ARMED, expected_generation=1,
        reason=safety.ReasonCode.SAFETY_TEST, acknowledge=True,
        acknowledge_paper_arming=True, preflight=PREFLIGHT, arming_scope=SCOPE,
    )
    results = []
    barrier = threading.Barrier(2)

    def run(target):
        barrier.wait()
        try:
            value = armed_control.transition(target, expected_generation=2,
                reason=safety.ReasonCode.SAFETY_TEST, acknowledge=True)
            results.append(value.state.value)
        except safety.SafetyControlError as error:
            results.append(str(error))

    threads = [threading.Thread(target=run, args=(state,)) for state in (
        safety.PersistentState.DISABLED, safety.PersistentState.EMERGENCY_STOP)]
    for thread in threads: thread.start()
    for thread in threads: thread.join(timeout=2)
    assert sum(value in {"DISABLED", "EMERGENCY_STOP"} for value in results) == 1
    assert "STALE_GENERATION" in results


def test_two_clear_requests_have_one_success(control):
    control.transition(safety.PersistentState.EMERGENCY_STOP, expected_generation=1,
                       reason=safety.ReasonCode.SAFETY_TEST, acknowledge=True)
    results = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(control.transition, safety.PersistentState.DISABLED,
            expected_generation=2, reason=safety.ReasonCode.SAFETY_TEST, acknowledge=True) for _ in range(2)]
        for future in futures:
            try: results.append(future.result().state.value)
            except safety.SafetyControlError as error: results.append(str(error))
    assert results.count("DISABLED") == 1
    assert results.count("STALE_GENERATION") == 1


def test_inflight_atomic_stage_finishes_once_stop_then_next_stage_denied(tmp_path):
    control = safety.PaperProductionSafetyControl(tmp_path / "inflight", interlock_timeout_seconds=2,
                                                 acl_checker=lambda _path: True)
    control.initialize_disabled(acknowledge=True)
    control.transition(safety.PersistentState.ARMED, expected_generation=1,
                       reason=safety.ReasonCode.SAFETY_TEST, acknowledge=True,
                       acknowledge_paper_arming=True, preflight=PREFLIGHT, arming_scope=SCOPE)
    composition = safety.ProductionPaperMutationComposition(safety.PaperProductionMutationSafetyGate(control))
    target = safety.PaperProductionMutationTarget("PRODUCTION", "PAPER", "BTCUSDT", "candidate:1", 2)
    started = threading.Event()
    release = threading.Event()
    completions = []

    def transaction():
        started.set()
        assert release.wait(2)
        completions.append("committed")

    stage = threading.Thread(target=lambda: composition.run_one_atomic_stage(
        safety.MutationStage.ENTRY_EXECUTION, target, PREREQUISITES, transaction))
    stage.start()
    assert started.wait(1)
    stop_result = []

    def stop():
        stopped = control.transition(safety.PersistentState.EMERGENCY_STOP, expected_generation=2,
                                     reason=safety.ReasonCode.OPERATOR_EMERGENCY_STOP, acknowledge=True)
        stop_result.append(stopped.state)

    stopper = threading.Thread(target=stop)
    stopper.start()
    time.sleep(0.03)
    assert stopper.is_alive()
    release.set()
    stage.join(timeout=2)
    stopper.join(timeout=2)
    assert completions == ["committed"]
    assert stop_result == [safety.PersistentState.EMERGENCY_STOP]
    assert control.read_authoritative().state is safety.PersistentState.EMERGENCY_STOP
    with pytest.raises(safety.SafetyControlError, match="MUTATION_DENIED_EMERGENCY_STOP"):
        composition.run_one_atomic_stage(safety.MutationStage.CLOSE_EXECUTION,
            safety.PaperProductionMutationTarget("PRODUCTION", "PAPER", "BTCUSDT", "candidate:1", 3),
            PREREQUISITES, lambda: completions.append("unexpected"))
    assert completions == ["committed"]


@pytest.mark.parametrize("case", range(1536))
def test_1536_case_authorization_fail_closed_matrix(armed_control, case):
    """1536 independently collected items prove conjunction and scope behavior."""
    stage = tuple(safety.MutationStage)[case % 4]
    scenario = (case // 4) % 12
    environment = "PRODUCTION"
    mode = "PAPER"
    symbol = "BTCUSDT"
    generation = 2
    commands = 0
    positions = 0
    candidate = f"candidate:{case}"
    prereq = [True] * 5
    expected_pass = scenario == 0
    if scenario == 1: environment = "STAGING"
    elif scenario == 2: mode = "LIVE"
    elif scenario == 3: symbol = "ETHUSDT"
    elif scenario == 4: generation = 1
    elif scenario == 5: prereq[0] = False
    elif scenario == 6: prereq[1] = False
    elif scenario == 7: prereq[2] = False
    elif scenario == 8: prereq[3] = False
    elif scenario == 9: prereq[4] = False
    elif scenario == 10:
        commands = 1
        expected_pass = stage is not safety.MutationStage.COMMAND_INGESTION
    elif scenario == 11:
        positions = 1
        expected_pass = stage in {safety.MutationStage.EXIT_EVALUATION_MUTATION, safety.MutationStage.CLOSE_EXECUTION}
    gate = safety.PaperProductionMutationSafetyGate(armed_control)
    mutation_target = safety.PaperProductionMutationTarget(
        environment, mode, symbol, candidate, generation, commands, positions)
    if expected_pass:
        with gate.authorize_mutation(stage, mutation_target, safety.MutationPrerequisites(*prereq)) as authorization:
            assert authorization.one_atomic_stage_only
            assert authorization.stage is stage
            assert authorization.generation == 2
    else:
        with pytest.raises(safety.SafetyControlError):
            with gate.authorize_mutation(stage, mutation_target, safety.MutationPrerequisites(*prereq)):
                pytest.fail("fail-closed matrix body executed")
