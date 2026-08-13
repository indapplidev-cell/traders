"""Narrow production deployment adapter for the Operator Control API only."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = ROOT / "ops/production/operator-control-api/compose.yaml"
SERVICE = "operator-control-api"
IMAGE = "traders-operator-control-api:production-v1"
IDENTITY_LABEL = "org.opencontainers.image.revision"
BINDING_HELPER = ROOT / "scripts/control_api_protected_binding.py"
PROBE_SCRIPT = "/service/scripts/control_api_runtime_probe.py"
MARKER = ROOT / "artifacts/paper-production-preparation/operator-control-api.narrow.json"


class ControlApiDeploymentError(RuntimeError):
    """Fixed, non-secret deployment failure."""


@dataclass(frozen=True, slots=True)
class ControlApiRuntimeAcceptance:
    identity: str
    healthy: bool
    get_routes: int
    post_routes: int
    valid_safe_read: bool
    unauthenticated_mutation_rejected: bool
    invalid_token_mutation_rejected: bool
    control_state: str
    control_generation: int
    secret_output: bool

    def accepted_for(self, identity: str) -> bool:
        return (
            self.identity == identity
            and self.healthy
            and self.get_routes == 3
            and self.post_routes == 5
            and self.valid_safe_read
            and self.unauthenticated_mutation_rejected
            and self.invalid_token_mutation_rejected
            and self.control_state == "DISABLED"
            and self.control_generation == 3
            and not self.secret_output
        )


class OperatorControlDeploymentAdapter:
    def __init__(
        self,
        *,
        root: Path = ROOT,
        command_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
        identity_provider: Callable[[], str] | None = None,
    ) -> None:
        self._root = root.resolve()
        self._compose = self._root / "ops/production/operator-control-api/compose.yaml"
        self._binding_helper = self._root / "scripts/control_api_protected_binding.py"
        self._marker = self._root / "artifacts/paper-production-preparation/operator-control-api.narrow.json"
        self._run = command_runner
        self._identity_provider = identity_provider or self._git_identity

    def _git_identity(self) -> str:
        status = self._run(
            ["git", "-C", str(self._root), "status", "--porcelain=v1"],
            capture_output=True, text=True, encoding="utf-8", check=False, timeout=20,
        )
        if status.returncode or status.stdout.strip():
            raise ControlApiDeploymentError("CONTROL_API_SOURCE_NOT_COMMITTED_CLEAN")
        result = self._run(
            ["git", "-C", str(self._root), "rev-parse", "HEAD"],
            capture_output=True, text=True, encoding="utf-8", check=False, timeout=20,
        )
        identity = result.stdout.strip()
        if result.returncode or len(identity) != 40:
            raise ControlApiDeploymentError("CONTROL_API_RUNTIME_IDENTITY_UNAVAILABLE")
        return identity

    @staticmethod
    def _environment(identity: str) -> dict[str, str]:
        environment = dict(os.environ)
        environment["TRADERS_CONTROL_SOURCE_IDENTITY"] = identity
        return environment

    def _quiet(self, command: Sequence[str], *, identity: str, timeout: int, code: str) -> None:
        result = self._run(
            list(command), env=self._environment(identity), stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=timeout,
        )
        if result.returncode:
            raise ControlApiDeploymentError(code)

    def ensure_protected_binding(self, identity: str) -> None:
        self._quiet(
            [sys.executable, str(self._binding_helper)], identity=identity, timeout=30,
            code="CONTROL_API_PROTECTED_CREDENTIAL_BINDING_FAILED",
        )

    def deploy(self) -> ControlApiRuntimeAcceptance:
        identity = self._identity_provider()
        if not self._compose.is_file() or not self._binding_helper.is_file():
            raise ControlApiDeploymentError("CONTROL_API_DEPLOYMENT_ADAPTER_INCOMPLETE")
        self.ensure_protected_binding(identity)
        base = ["docker", "compose", "-f", str(self._compose)]
        self._quiet([*base, "build", SERVICE], identity=identity, timeout=600,
                    code="CONTROL_API_CURRENT_IMAGE_BUILD_FAILED")
        self._quiet(
            [*base, "up", "-d", "--no-deps", "--force-recreate", "--wait", "--wait-timeout", "120", SERVICE],
            identity=identity, timeout=180, code="CONTROL_API_NARROW_DEPLOYMENT_FAILED",
        )
        acceptance = self.probe(identity)
        if not acceptance.accepted_for(identity):
            raise ControlApiDeploymentError("CONTROL_API_RUNTIME_ACCEPTANCE_FAILED")
        self._publish_marker(acceptance)
        return acceptance

    def probe(self, expected_identity: str | None = None) -> ControlApiRuntimeAcceptance:
        identity = expected_identity or self._identity_provider()
        base = ["docker", "compose", "-f", str(self._compose)]
        image = self._run(
            ["docker", "image", "inspect", IMAGE, "--format", "{{ index .Config.Labels \"org.opencontainers.image.revision\" }}"],
            capture_output=True, text=True, encoding="utf-8", check=False, timeout=30,
        )
        if image.returncode or image.stdout.strip() != identity:
            raise ControlApiDeploymentError("CONTROL_API_RUNTIME_IDENTITY_MISMATCH")
        result = self._run(
            [*base, "exec", "-T", SERVICE, "python", PROBE_SCRIPT],
            env=self._environment(identity), stdin=subprocess.DEVNULL, capture_output=True,
            text=True, encoding="utf-8", check=False, timeout=30,
        )
        if result.returncode:
            raise ControlApiDeploymentError("CONTROL_API_RUNTIME_PROBE_FAILED")
        try:
            payload = json.loads(result.stdout)
            return ControlApiRuntimeAcceptance(**payload)
        except Exception:
            raise ControlApiDeploymentError("CONTROL_API_RUNTIME_PROBE_INVALID") from None

    def _publish_marker(self, acceptance: ControlApiRuntimeAcceptance) -> None:
        payload: Mapping[str, object] = {
            "deployment": "NARROW", "service": SERVICE, "schema": 1,
            "source_identity": acceptance.identity, "runtime_health": "PASS",
            "get_routes": acceptance.get_routes, "post_routes": acceptance.post_routes,
            "bind": "127.0.0.1:8766", "control_state": acceptance.control_state,
            "control_generation": acceptance.control_generation,
        }
        self._marker.parent.mkdir(parents=True, exist_ok=True)
        rendered = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
        temporary = self._marker.with_name(f".{self._marker.name}.tmp")
        temporary.write_text(rendered, encoding="utf-8")
        os.replace(temporary, self._marker)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="traders-operator-control-deploy")
    parser.add_argument("command", choices=("deploy", "probe"))
    args = parser.parse_args(argv)
    adapter = OperatorControlDeploymentAdapter()
    try:
        acceptance = adapter.deploy() if args.command == "deploy" else adapter.probe()
    except ControlApiDeploymentError as error:
        print(f"CONTROL_API_DEPLOYMENT=FAIL:{error}")
        return 1
    print("CONTROL_API_DEPLOYMENT=PASS")
    print(f"CONTROL_API_RUNTIME_IDENTITY={acceptance.identity}")
    print(f"CONTROL_API_ROUTES={acceptance.get_routes}_GET_{acceptance.post_routes}_POST")
    print(f"CONTROL_API_STATE={acceptance.control_state}_GENERATION_{acceptance.control_generation}")
    print("CONTROL_API_SECRET_OUTPUT=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
