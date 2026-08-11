from __future__ import annotations

import pytest

from app.engine_paper.production_composition import PaperProductionComposition
from app.engine_safety.paper_production_control import (
    ArmReadinessPreflight,
    MutationPrerequisites,
    MutationStage,
    PaperProductionArmingScope,
    PaperProductionMutationSafetyGate,
    PaperProductionMutationTarget,
    PaperProductionSafetyControl,
    PersistentState,
    ReasonCode,
    SafetyControlError,
)


def target(generation=1, mode="PAPER"):
    return PaperProductionMutationTarget(
        "PRODUCTION", mode, "BTCUSDT", "candidate-1", generation
    )


def prerequisites():
    return MutationPrerequisites(True, True, True, True, True)


@pytest.fixture
def control(tmp_path):
    value = PaperProductionSafetyControl(tmp_path / "control", acl_checker=lambda _path: True)
    value.initialize_disabled(acknowledge=True)
    return value


@pytest.mark.parametrize("stage", tuple(MutationStage))
@pytest.mark.parametrize("repeat", range(2))
def test_every_mutation_stage_denies_while_disabled(control, stage, repeat):
    assert repeat >= 0
    with pytest.raises(SafetyControlError, match="MUTATION_DENIED_DISABLED"):
        with PaperProductionMutationSafetyGate(control).authorize_mutation(stage, target(), prerequisites()):
            raise AssertionError("must not execute")


@pytest.mark.parametrize("stage", tuple(MutationStage))
@pytest.mark.parametrize("repeat", range(2))
def test_every_mutation_stage_denies_emergency_stop(control, stage, repeat):
    stopped = control.transition(PersistentState.EMERGENCY_STOP, expected_generation=1,
                                 reason=ReasonCode.OPERATOR_EMERGENCY_STOP, acknowledge=True)
    assert repeat >= 0
    with pytest.raises(SafetyControlError, match="MUTATION_DENIED_EMERGENCY_STOP"):
        with PaperProductionMutationSafetyGate(control).authorize_mutation(
            stage, target(stopped.generation), prerequisites()
        ):
            raise AssertionError("must not execute")


@pytest.mark.parametrize("stage", tuple(MutationStage))
@pytest.mark.parametrize("repeat", range(2))
def test_authoritative_control_is_reread_and_stale_armed_cache_cannot_authorize(control, stage, repeat):
    preflight = ArmReadinessPreflight(True, True, True, True, True, True, True, True, True)
    armed = control.transition(PersistentState.ARMED, expected_generation=1,
        reason=ReasonCode.SAFETY_TEST, acknowledge=True, acknowledge_paper_arming=True,
        preflight=preflight, arming_scope=PaperProductionArmingScope(1, 1, ("BTCUSDT",)))
    control.transition(PersistentState.EMERGENCY_STOP, expected_generation=armed.generation,
                       reason=ReasonCode.OPERATOR_EMERGENCY_STOP, acknowledge=True)
    assert repeat >= 0
    with pytest.raises(SafetyControlError, match="MUTATION_DENIED_EMERGENCY_STOP"):
        with PaperProductionMutationSafetyGate(control).authorize_mutation(
            stage, target(armed.generation), prerequisites()
        ):
            raise AssertionError("must not execute")


@pytest.mark.parametrize("stage", tuple(MutationStage))
@pytest.mark.parametrize("repeat", range(2))
def test_live_is_always_denied_even_when_control_is_armed(control, stage, repeat):
    preflight = ArmReadinessPreflight(True, True, True, True, True, True, True, True, True)
    armed = control.transition(PersistentState.ARMED, expected_generation=1,
        reason=ReasonCode.SAFETY_TEST, acknowledge=True, acknowledge_paper_arming=True,
        preflight=preflight, arming_scope=PaperProductionArmingScope(1, 1, ("BTCUSDT",)))
    assert repeat >= 0
    with pytest.raises(SafetyControlError, match="LIVE_OR_NON_PRODUCTION_TARGET_DENIED"):
        with PaperProductionMutationSafetyGate(control).authorize_mutation(
            stage, target(armed.generation, "LIVE"), prerequisites()
        ):
            raise AssertionError("must not execute")
