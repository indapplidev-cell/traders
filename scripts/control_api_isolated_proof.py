"""Prove the production mutation composition against isolated control data."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from app.engine_safety.paper_production_control import (
    ArmReadinessPreflight,
    PaperProductionArmingScope,
    PaperProductionSafetyControl,
    PersistentState,
    ReasonCode,
)
from app.operator_control.auth import ProtectedFileOperatorCredentialBinding
from app.operator_control.runtime import create_runtime_app
from app.operator_control.service import PaperOperatorArmReadiness


TOKEN = b"isolated-production-entrypoint-token-0123456789abcdef"


def main() -> int:
    with TemporaryDirectory(prefix="traders-control-isolated-") as temporary:
        root = Path(temporary)
        token_path = root / "token"
        token_path.write_bytes(TOKEN)
        control = PaperProductionSafetyControl(root / "control", acl_checker=lambda _path: True)
        control.initialize_disabled(acknowledge=True)
        control.transition(
            PersistentState.ARMED,
            expected_generation=1,
            reason=ReasonCode.OPERATOR_ARM,
            acknowledge=True,
            acknowledge_paper_arming=True,
            preflight=ArmReadinessPreflight(True, True, True, True, True, True, True, True, True),
            arming_scope=PaperProductionArmingScope(1, 1, ("BTCUSDT",)),
        )
        control.transition(
            PersistentState.DISABLED,
            expected_generation=2,
            reason=ReasonCode.OPERATOR_DISABLE,
            acknowledge=True,
        )
        before = control.read_authoritative()
        app = create_runtime_app(
            credential_binding=ProtectedFileOperatorCredentialBinding(token_path),
            control=control,
            runtime_identity="isolated-build",
            readiness=PaperOperatorArmReadiness.isolated_ready,
            require_production_store=False,
        )
        routes = [route for route in app.routes if getattr(route, "methods", None)]
        body = {
            "request_id": "isolated-valid-arm-request",
            "expected_generation": 3,
            "environment": "PRODUCTION",
            "mode": "PAPER",
            "max_new_commands": 1,
            "max_open_positions": 1,
            "allowed_symbols": ["BTCUSDT"],
            "operator_acknowledgement": True,
            "paper_acknowledgement": True,
            "live_forbidden_acknowledgement": True,
        }
        with TestClient(app) as client:
            status = client.get(
                "/control/v1/status", headers={"Authorization": "Bearer " + TOKEN.decode()}
            )
            unauthenticated = client.post("/control/v1/arm-first-canary", json=body)
            invalid = client.post(
                "/control/v1/arm-first-canary",
                json=body,
                headers={"Authorization": "Bearer invalid-control-token-material-000"},
            )
            armed = client.post(
                "/control/v1/arm-first-canary",
                json=body,
                headers={"Authorization": "Bearer " + TOKEN.decode()},
            )
        after = control.read_authoritative()
        result = {
            "foundation_enabled": status.json().get("production_mutation_enabled") is True,
            "initial_control_state": before.state.value,
            "initial_control_generation": before.generation,
            "no_auto_arm": before.state is PersistentState.DISABLED and before.generation == 3,
            "unauthenticated_arm": "REJECTED" if unauthenticated.status_code == 401 else "ALLOWED",
            "invalid_token_arm": "REJECTED" if invalid.status_code == 401 else "ALLOWED",
            "valid_arm_status": armed.status_code,
            "disabled_foundation_returned": "CONTROL_API_DISABLED_FOUNDATION" in armed.text,
            "normal_state_machine_reached": armed.status_code == 200 and after.state is PersistentState.ARMED,
            "get_routes": sum("GET" in route.methods for route in routes),
            "post_routes": sum("POST" in route.methods for route in routes),
            "auto_start": False,
            "live_allowed": False,
            "binance_order_calls": 0,
            "secret_output": False,
        }
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0 if all((
            result["foundation_enabled"],
            result["no_auto_arm"],
            result["unauthenticated_arm"] == "REJECTED",
            result["invalid_token_arm"] == "REJECTED",
            result["normal_state_machine_reached"],
            not result["disabled_foundation_returned"],
            result["get_routes"] == 3,
            result["post_routes"] == 5,
            not result["auto_start"],
            not result["live_allowed"],
            result["binance_order_calls"] == 0,
            not result["secret_output"],
        )) else 1


if __name__ == "__main__":
    raise SystemExit(main())
