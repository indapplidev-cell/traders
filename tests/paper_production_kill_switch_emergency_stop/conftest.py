from __future__ import annotations

import pytest

from app.engine_safety.paper_production_control import (
    ArmReadinessPreflight,
    PaperProductionArmingScope,
    PaperProductionSafetyControl,
    PersistentState,
    ReasonCode,
)


@pytest.fixture
def passed_preflight() -> ArmReadinessPreflight:
    return ArmReadinessPreflight(True, True, True, True, True, True, True, True, True)


@pytest.fixture
def scope() -> PaperProductionArmingScope:
    return PaperProductionArmingScope(1, 1, ("BTCUSDT",))


@pytest.fixture
def control(tmp_path):
    value = PaperProductionSafetyControl(tmp_path / "control", acl_checker=lambda _path: True)
    value.initialize_disabled(acknowledge=True)
    return value


@pytest.fixture(scope="session")
def armed_control(tmp_path_factory):
    value = PaperProductionSafetyControl(
        tmp_path_factory.mktemp("armed") / "control", acl_checker=lambda _path: True
    )
    value.initialize_disabled(acknowledge=True)
    value.transition(
        PersistentState.ARMED,
        expected_generation=1,
        reason=ReasonCode.SAFETY_TEST,
        acknowledge=True,
        acknowledge_paper_arming=True,
        preflight=ArmReadinessPreflight(True, True, True, True, True, True, True, True, True),
        arming_scope=PaperProductionArmingScope(1, 1, ("BTCUSDT",)),
    )
    return value
