from __future__ import annotations

import json
import subprocess

import pytest

from app.operator_control.deployment import (
    ControlApiDeploymentError,
    OperatorControlDeploymentAdapter,
)


IDENTITY = "a" * 40


class Runner:
    def __init__(self, *, fail_on: str | None = None):
        self.calls = []
        self.fail_on = fail_on

    def __call__(self, command, **kwargs):
        self.calls.append((tuple(command), kwargs))
        joined = " ".join(command)
        if self.fail_on and self.fail_on in joined:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="")
        if "image inspect" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=IDENTITY + "\n", stderr="")
        if "control_api_runtime_probe.py" in joined:
            payload = {
                "identity": IDENTITY, "healthy": True, "get_routes": 3, "post_routes": 5,
                "valid_safe_read": True, "unauthenticated_mutation_rejected": True,
                "invalid_token_mutation_rejected": True, "control_state": "DISABLED",
                "control_generation": 3, "foundation_mode": "PRODUCTION_PAPER",
                "service_enabled": True, "production_mutation_enabled": True,
                "secret_output": False,
            }
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")


def root(tmp_path):
    compose = tmp_path / "ops/production/operator-control-api/compose.yaml"
    compose.parent.mkdir(parents=True)
    compose.write_text("services: {}\n", encoding="utf-8")
    helper = tmp_path / "scripts/control_api_protected_binding.py"
    helper.parent.mkdir()
    helper.write_text("pass\n", encoding="utf-8")
    return tmp_path


def test_adapter_builds_and_recreates_only_operator_control_then_accepts(tmp_path):
    runner = Runner()
    adapter = OperatorControlDeploymentAdapter(root=root(tmp_path), command_runner=runner, identity_provider=lambda: IDENTITY)
    acceptance = adapter.deploy()
    commands = [call[0] for call in runner.calls]
    assert acceptance.accepted_for(IDENTITY)
    assert any(command[-2:] == ("build", "operator-control-api") for command in commands)
    up = next(command for command in commands if "up" in command)
    assert "--no-deps" in up and "--force-recreate" in up and up[-1] == "operator-control-api"
    assert all("down" not in command for command in commands)
    assert all("readonly-api" not in command for command in commands)
    marker = json.loads((tmp_path / "artifacts/paper-production-preparation/operator-control-api.narrow.json").read_text())
    assert marker["bind"] == "127.0.0.1:8766"
    assert marker["get_routes"] == 3 and marker["post_routes"] == 5
    assert marker["foundation_mode"] == "PRODUCTION_PAPER"
    assert marker["production_mutation_enabled"] is True


def test_compose_publishes_only_literal_loopback_for_container_listener():
    compose = (OperatorControlDeploymentAdapter()._compose).read_text(encoding="utf-8")
    assert '"127.0.0.1:8766:8766"' in compose
    assert 'TRADERS_CONTROL_CONTAINER_LISTENER: "1"' in compose


@pytest.mark.parametrize("failure", ("build operator-control-api", "up -d"))
def test_adapter_fails_closed_before_acceptance_on_deterministic_failure(tmp_path, failure):
    adapter = OperatorControlDeploymentAdapter(root=root(tmp_path), command_runner=Runner(fail_on=failure), identity_provider=lambda: IDENTITY)
    with pytest.raises(ControlApiDeploymentError):
        adapter.deploy()
    assert not (tmp_path / "artifacts/paper-production-preparation/operator-control-api.narrow.json").exists()
