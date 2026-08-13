"""Sanitized in-boundary acceptance probe for the running control API."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request

from app.operator_control.runtime import PROTECTED_TOKEN_PATH, RUNTIME_IDENTITY_KEY, create_runtime_app


BASE = "http://127.0.0.1:8766"


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


def probe() -> dict[str, object]:
    token = PROTECTED_TOKEN_PATH.read_bytes().strip()
    status, body = _request("/control/v1/status", authorization=token)
    unauthenticated, _ = _request("/control/v1/disable", method="POST")
    invalid, _ = _request("/control/v1/disable", method="POST", authorization=b"invalid-control-token-material-000")
    app = create_runtime_app(runtime_identity=os.environ.get(RUNTIME_IDENTITY_KEY, "UNSET"))
    gets = sum(1 for route in app.routes if "GET" in getattr(route, "methods", set()))
    posts = sum(1 for route in app.routes if "POST" in getattr(route, "methods", set()))
    return {
        "healthy": status == 200,
        "identity": app.state.runtime_identity,
        "get_routes": gets,
        "post_routes": posts,
        "valid_safe_read": status == 200,
        "unauthenticated_mutation_rejected": unauthenticated in {401, 403},
        "invalid_token_mutation_rejected": invalid in {401, 403},
        "control_state": body.get("control_state"),
        "control_generation": body.get("generation"),
        "secret_output": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--health-only", action="store_true")
    args = parser.parse_args()
    try:
        result = probe()
        accepted = all((
            result["healthy"], result["get_routes"] == 3, result["post_routes"] == 5,
            result["valid_safe_read"], result["unauthenticated_mutation_rejected"],
            result["invalid_token_mutation_rejected"], result["control_state"] == "DISABLED",
            result["control_generation"] == 3, not result["secret_output"],
        ))
        if not args.health_only:
            print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0 if accepted else 1
    except Exception:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
