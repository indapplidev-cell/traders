"""GET-only, no-echo inspection of the production Control status."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

URL = "http://127.0.0.1:8766/control/v1/status"
PROTECTED_TOKEN_PATH = ROOT / ".control-api.token"
ALLOWED_FIELDS = (
    "control_state",
    "generation",
    "control_health",
    "audit_health",
    "foundation_mode",
    "service_enabled",
    "production_mutation_enabled",
)


def inspect() -> dict[str, object]:
    token = PROTECTED_TOKEN_PATH.read_bytes().strip()
    request = urllib.request.Request(
        URL,
        headers={"Authorization": "Bearer " + token.decode("ascii")},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read())
            if response.status != 200 or not isinstance(payload, dict):
                raise RuntimeError("CONTROL_STATUS_REJECTED")
    except Exception:
        raise RuntimeError("CONTROL_STATUS_REJECTED") from None
    return {key: payload.get(key) for key in ALLOWED_FIELDS}


def main() -> int:
    try:
        result = inspect()
    except (OSError, RuntimeError, UnicodeError, ValueError):
        print("CONTROL_STATUS=FAILED")
        print("ERROR_CLASS=NORMALIZED_CONTROL_STATUS_FAILURE")
        print("SECRET_VALUE_OUTPUT=NO")
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    print("CONTROL_HTTP_METHOD=GET_ONLY")
    print("SECRET_VALUE_OUTPUT=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
