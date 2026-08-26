"""Count active production DB credential occurrences without rendering values."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.production_db_security_remediation import _load_bindings


EVIDENCE = ROOT.parent / "evidence_inbox"
CONTAINERS = (
    "traders-ml-postgres-1",
    "traders-ml-market-data-sync-1",
    "traders-ml-online-orchestrator-1",
    "traders-ml-online-orchestrator-5m-1",
    "traders-readonly-api-readonly-api-1",
    "traders-operator-control-api-operator-control-api-1",
)


def _tracked() -> tuple[Path, ...]:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    return tuple(ROOT / item.decode("utf-8") for item in result.stdout.split(b"\0") if item)


def _files(paths: tuple[Path, ...], credentials: tuple[bytes, ...]) -> int:
    findings = 0
    for path in paths:
        try:
            payload = path.read_bytes()
        except OSError:
            findings += 1
            continue
        if any(secret in payload for secret in credentials):
            findings += 1
    return findings


def _logs(credentials: tuple[bytes, ...]) -> int:
    findings = 0
    for container in CONTAINERS:
        result = subprocess.run(
            ["docker", "logs", "--since", "2h", container],
            check=False,
            capture_output=True,
        )
        if result.returncode or any(
            secret in result.stdout or secret in result.stderr for secret in credentials
        ):
            findings += 1
    return findings


def main() -> int:
    try:
        _values, passwords, _exposed = _load_bindings()
        credentials = tuple(value.encode("utf-8") for value in passwords.values())
        tracked = _files(_tracked(), credentials)
        evidence_paths = tuple(path for path in EVIDENCE.rglob("*") if path.is_file())
        evidence = _files(evidence_paths, credentials)
        logs = _logs(credentials)
    except Exception:
        print("SCAN=FAILED")
        print("ERROR_CLASS=NORMALIZED_SECRET_SCAN_FAILURE")
        print("SECRET_VALUE_OUTPUT=NO")
        print("SECRET_DERIVED_HASH_CREATED=NO")
        return 2
    total = tracked + evidence + logs
    print(f"TRACKED_SECRET_FINDINGS={tracked}")
    print(f"EVIDENCE_SECRET_FINDINGS={evidence}")
    print(f"TASK_LOG_SECRET_FINDINGS={logs}")
    print(f"ACTIVE_SECRET_EXPOSURE_FINDINGS={total}")
    print("SECRET_VALUE_OUTPUT=NO")
    print("SECRET_DERIVED_HASH_CREATED=NO")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
