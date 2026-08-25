"""Count exact new shared-DB credential exposure without rendering a match."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.verify_shared_db_secret_binding import BINDING, binding_errors


EVIDENCE = ROOT.parent / "evidence_inbox"
CONTAINERS = (
    "traders-ml-market-data-sync-1",
    "traders-ml-online-orchestrator-5m-1",
    "traders-ml-online-orchestrator-1",
)


def _tracked_paths() -> tuple[Path, ...]:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    return tuple(
        ROOT / item.decode("utf-8")
        for item in result.stdout.split(b"\0")
        if item
    )


def _evidence_paths() -> tuple[Path, ...]:
    return tuple(path for path in EVIDENCE.rglob("*") if path.is_file())


def _matching_files(paths: tuple[Path, ...], secret: bytes) -> int:
    findings = 0
    for path in paths:
        try:
            if secret in path.read_bytes():
                findings += 1
        except OSError:
            findings += 1
    return findings


def _matching_logs(secret: bytes) -> int:
    findings = 0
    for container in CONTAINERS:
        result = subprocess.run(
            ["docker", "logs", "--since", "2h", container],
            check=False,
            capture_output=True,
        )
        if result.returncode or secret in result.stdout or secret in result.stderr:
            findings += 1
    return findings


def main() -> int:
    if binding_errors(BINDING):
        print("SCAN=NOT_RUN")
        print("ERROR_CODE=PROTECTED_BINDING_INVALID")
        print("SECRET_VALUE_OUTPUT=NO")
        print("SECRET_DERIVED_HASH_CREATED=NO")
        return 2
    secret = BINDING.read_bytes().strip()
    tracked = _matching_files(_tracked_paths(), secret)
    evidence = _matching_files(_evidence_paths(), secret)
    logs = _matching_logs(secret)
    total = tracked + evidence + logs
    print(f"TRACKED_SECRET_FINDINGS={tracked}")
    print(f"EVIDENCE_SECRET_FINDINGS={evidence}")
    print(f"TASK_LOG_SECRET_FINDINGS={logs}")
    print(f"NEW_SECRET_EXPOSURE_FINDINGS={total}")
    print("SECRET_VALUE_OUTPUT=NO")
    print("SECRET_DERIVED_HASH_CREATED=NO")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
