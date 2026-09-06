"""Authorize bounded PAPER-only rehydration without exposing fee values."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile


SCHEMA = "USER_AUTHORIZED_STUB_REHYDRATION_V1"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--valid-hours", type=int, default=168)
    parser.add_argument("--interval-seconds", type=int, default=900)
    parser.add_argument("--acknowledge-paper-only-stub", action="store_true")
    args = parser.parse_args()
    if not args.acknowledge_paper_only_stub:
        raise SystemExit("explicit PAPER-only stub acknowledgement is required")
    if not 1 <= args.valid_hours <= 168:
        raise SystemExit("valid-hours must be between 1 and 168")
    if not 60 <= args.interval_seconds <= 3600:
        raise SystemExit("interval-seconds must be between 60 and 3600")

    path = args.path.resolve(strict=True)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("snapshot_type") != "USER_AUTHORIZED_STUB":
        raise SystemExit("only an explicit USER_AUTHORIZED_STUB may be authorized")
    if payload.get("real_account_data") is not False:
        raise SystemExit("stub must explicitly declare real_account_data=false")
    symbols = payload.get("symbols")
    if not isinstance(symbols, dict) or len(symbols) != 10:
        raise SystemExit("stub must contain the exact ten-symbol policy")
    for row in symbols.values():
        if not isinstance(row, dict) or "maker_bps" not in row or "taker_bps" not in row:
            raise SystemExit("stub contains an incomplete commission row")

    now = datetime.now(timezone.utc)
    authorized_at = now.isoformat().replace("+00:00", "Z")
    valid_until = (now + timedelta(hours=args.valid_hours)).isoformat().replace(
        "+00:00", "Z"
    )
    authorization_id = "paper-stub-auth:" + sha256(
        f"{payload['snapshot_id']}|{args.task}|{authorized_at}".encode()
    ).hexdigest()[:24]
    payload["rehydration_authorization"] = {
        "schema": SCHEMA,
        "authorization_id": authorization_id,
        "authorized_at": authorized_at,
        "valid_until": valid_until,
        "interval_seconds": args.interval_seconds,
        "authorized_by_task": args.task,
        "paper_only": True,
        "live_allowed": False,
    }

    original_mode = path.stat().st_mode
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.chmod(temporary, original_mode)
    os.replace(temporary, path)
    print(json.dumps({
        "authorization_id": authorization_id,
        "authorized_at": authorized_at,
        "valid_until": valid_until,
        "interval_seconds": args.interval_seconds,
        "paper_only": True,
        "live_allowed": False,
        "fee_values_output": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
