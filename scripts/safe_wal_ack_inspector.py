"""Allowlisted WAL ACK owner/heartbeat inspection without command-line output."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.production_backup import SAFE_ROOT


LOCK = SAFE_ROOT / "catalog" / "wal_ack_daemon.pid"
STATE = SAFE_ROOT / "catalog" / "wal_ack_daemon_state.json"


def _process_identity(pid: int) -> tuple[bool, bool]:
    script = (
        "$p=Get-CimInstance Win32_Process -Filter \"ProcessId=$env:ACK_PID\";"
        "if($null -eq $p){exit 3};"
        "[ordered]@{Id=[int]$p.ProcessId;Name=[string]$p.Name;"
        "CommandLine=[string]$p.CommandLine}|ConvertTo-Json -Compress"
    )
    result = subprocess.run(
        ["pwsh.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        env={**os.environ, "ACK_PID": str(pid)},
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        timeout=10,
    )
    if result.returncode:
        return False, False
    try:
        payload = json.loads(result.stdout)
        command = str(payload.get("CommandLine") or "")
        identity = (
            int(payload.get("Id")) == pid
            and "production_wal_archive_remediation.py" in command
            and "daemon" in command
        )
        return True, identity
    except (TypeError, ValueError, json.JSONDecodeError):
        return False, False


def inspect() -> dict[str, object]:
    try:
        pid = int(LOCK.read_text(encoding="ascii").strip())
        state = json.loads(STATE.read_text(encoding="utf-8"))
        updated = datetime.fromisoformat(str(state["updated_at"]).replace("Z", "+00:00"))
        age = max(0, int((datetime.now(timezone.utc) - updated.astimezone(timezone.utc)).total_seconds()))
        alive, identity = _process_identity(pid)
        state_pid_match = state.get("process_id") == pid
        return {
            "lock_present": True,
            "process_id": pid,
            "process_alive": alive,
            "process_identity_match": identity,
            "state_pid_match": state_pid_match,
            "state_status": state.get("status") if state.get("status") in {"RUNNING", "DEGRADED"} else "UNKNOWN",
            "heartbeat_age_seconds": age,
            "heartbeat_healthy": age <= 30 and state.get("status") == "RUNNING" and state.get("error_class") == "NONE",
            "export_backlog_count": state.get("export_backlog_count") if isinstance(state.get("export_backlog_count"), int) else -1,
            "pending_archive_status_count": state.get("pending_archive_status_count") if isinstance(state.get("pending_archive_status_count"), int) else -1,
            "error_class": "NONE",
        }
    except Exception:
        return {
            "lock_present": LOCK.is_file(),
            "process_alive": False,
            "process_identity_match": False,
            "state_pid_match": False,
            "heartbeat_healthy": False,
            "error_class": "SAFE_ACK_INSPECTION_FAILED",
        }


def main() -> int:
    result = inspect()
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    print("COMMAND_LINE_VALUE_OUTPUT=NO")
    print("SECRET_VALUE_OUTPUT=NO")
    return 0 if result.get("heartbeat_healthy") and result.get("process_identity_match") else 1


if __name__ == "__main__":
    raise SystemExit(main())
