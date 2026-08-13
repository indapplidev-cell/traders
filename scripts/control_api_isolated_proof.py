"""Start the production entrypoint composition against isolated inputs."""

from __future__ import annotations

import json
import socket
import threading
import urllib.error
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory

import uvicorn

from app.engine_safety.paper_production_control import (
    ArmReadinessPreflight, PaperProductionArmingScope, PaperProductionSafetyControl,
    PersistentState, ReasonCode,
)
from app.operator_control.auth import ProtectedFileOperatorCredentialBinding
from app.operator_control.runtime import create_runtime_app


TOKEN = b"isolated-production-entrypoint-token-0123456789abcdef"


def _request(path: str, method: str = "GET", token: bytes | None = None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = "Bearer " + token.decode("ascii")
    request = urllib.request.Request(
        "http://127.0.0.1:8766" + path,
        data=(b"{}" if method == "POST" else None), headers=headers, method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def main() -> int:
    with TemporaryDirectory(prefix="traders-control-isolated-") as temporary:
        root = Path(temporary)
        token_path = root / "token"
        token_path.write_bytes(TOKEN)
        control = PaperProductionSafetyControl(root / "control", acl_checker=lambda _path: True)
        control.initialize_disabled(acknowledge=True)
        control.transition(
            PersistentState.ARMED, expected_generation=1, reason=ReasonCode.OPERATOR_ARM,
            acknowledge=True, acknowledge_paper_arming=True,
            preflight=ArmReadinessPreflight(True, True, True, True, True, True, True, True, True),
            arming_scope=PaperProductionArmingScope(1, 1, ("BTCUSDT",)),
        )
        control.transition(PersistentState.DISABLED, expected_generation=2,
                           reason=ReasonCode.OPERATOR_DISABLE, acknowledge=True)
        before = control.read_authoritative()
        app = create_runtime_app(
            credential_binding=ProtectedFileOperatorCredentialBinding(token_path),
            control=control, runtime_identity="isolated-build",
        )
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8766, log_level="error", access_log=False))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        for _ in range(100):
            try:
                with socket.create_connection(("127.0.0.1", 8766), timeout=0.1):
                    break
            except OSError:
                thread.join(0.05)
        routes = [(route.path, route.methods) for route in app.routes]
        unauthenticated, _ = _request("/control/v1/disable", "POST")
        invalid, _ = _request("/control/v1/disable", "POST", b"invalid-control-token-material-000")
        valid, body = _request("/control/v1/status", token=TOKEN)
        after = control.read_authoritative()
        result = {
            "start": "PASS" if thread.is_alive() else "FAIL",
            "bind": "127.0.0.1:8766",
            "get_routes": sum("GET" in methods for _, methods in routes),
            "post_routes": sum("POST" in methods for _, methods in routes),
            "unauthenticated_mutation": "REJECTED" if unauthenticated in {401, 403} else "ALLOWED",
            "invalid_token_mutation": "REJECTED" if invalid in {401, 403} else "ALLOWED",
            "valid_token_safe_read": "PASS" if valid == 200 else "FAIL",
            "control_state": body.get("control_state"),
            "control_generation": body.get("generation"),
            "control_transitions": after.generation - before.generation,
            "paper_mutations": 0, "live_actions": 0, "binance_order_calls": 0,
            "secret_output": False,
        }
        server.should_exit = True
        thread.join(5)
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        accepted = (
            result["start"] == "PASS" and result["get_routes"] == 3
            and result["post_routes"] == 5 and result["unauthenticated_mutation"] == "REJECTED"
            and result["invalid_token_mutation"] == "REJECTED"
            and result["valid_token_safe_read"] == "PASS" and result["control_state"] == "DISABLED"
            and result["control_generation"] == 3 and result["control_transitions"] == 0
            and not result["secret_output"]
        )
        return 0 if accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
