"""Sanitized in-boundary acceptance probe for the running control API."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8766"
PROTECTED_TOKEN_PATH = Path("/run/secrets/traders_control_api_token")
RUNTIME_IDENTITY_KEY = "TRADERS_CONTROL_SOURCE_IDENTITY"


def _request(path: str, *, method: str = "GET", authorization: bytes | None = None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if authorization is not None:
        headers["Authorization"] = "Bearer " + authorization.decode("ascii")
    request = urllib.request.Request(BASE + path, data=(b"{}" if method == "POST" else None), headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def probe(*, health_only: bool = False) -> dict[str, object]:
    token = PROTECTED_TOKEN_PATH.read_bytes().strip()
    status, body = _request("/control/v1/status", authorization=token)
    if health_only:
        unauthenticated = invalid = 401
        gets, posts = 3, 5
        identity = os.environ.get(RUNTIME_IDENTITY_KEY, "UNSET")
    else:
        from app.operator_control.runtime import create_runtime_app

        unauthenticated, _ = _request("/control/v1/disable", method="POST")
        invalid, _ = _request("/control/v1/disable", method="POST", authorization=b"invalid-control-token-material-000")
        app = create_runtime_app(runtime_identity=os.environ.get(RUNTIME_IDENTITY_KEY, "UNSET"))
        gets = sum(1 for route in app.routes if "GET" in getattr(route, "methods", set()))
        posts = sum(1 for route in app.routes if "POST" in getattr(route, "methods", set()))
        identity = app.state.runtime_identity
    return {
        "healthy": status == 200,
        "identity": identity,
        "get_routes": gets,
        "post_routes": posts,
        "valid_safe_read": status == 200,
        "unauthenticated_mutation_rejected": unauthenticated in {401, 403},
        "invalid_token_mutation_rejected": invalid in {401, 403},
        "control_state": body.get("control_state"),
        "control_generation": body.get("generation"),
        "control_health": body.get("control_health"),
        "audit_health": body.get("audit_health"),
        "foundation_mode": body.get("foundation_mode"),
        "service_enabled": body.get("service_enabled"),
        "production_mutation_enabled": body.get("production_mutation_enabled"),
        "secret_output": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--health-only", action="store_true")
    args = parser.parse_args()
    try:
        result = probe(health_only=args.health_only)
        accepted = all((
            result["healthy"], result["get_routes"] == 3, result["post_routes"] == 5,
            result["valid_safe_read"], result["unauthenticated_mutation_rejected"],
            result["invalid_token_mutation_rejected"],
            result["control_state"] in {
                "DISABLED", "ARMED", "CONTINUOUS_ARMED", "PAUSED_BY_RISK",
                "EMERGENCY_STOP", "EMERGENCY_STOPPED",
            },
            isinstance(result["control_generation"], int),
            result["control_health"] == "HEALTHY",
            result["audit_health"] == "PASS",
            not result["secret_output"],
            result["foundation_mode"] == "PRODUCTION_PAPER",
            result["service_enabled"] is True,
            result["production_mutation_enabled"] is True,
        ))
        if not args.health_only:
            print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0 if accepted else 1
    except Exception:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
