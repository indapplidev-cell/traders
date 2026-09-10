from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.request import urlopen


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765/api/v1/trading/funnel?trade_profile=trade-5m-v2")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with urlopen(args.url, timeout=60) as response:  # noqa: S310 - fixed/read-only local endpoint by default
        envelope = json.load(response)
    data = envelope["data"]
    current = data["current_cycle"]
    if not current["cycle_complete"] or current["symbols_seen"] != 10:
        raise SystemExit("fresh exact-10 completed cycle required")
    records = []
    for item in current["items"]:
        detail = item["downstream_detail"]
        identity = detail["row_identity"]
        record = {
            "profile": identity["profile"],
            "timeframe": identity["timeframe"],
            "cycle_boundary": identity["cycle_boundary_ms"],
            "symbol": identity["symbol"],
            "stage": item["downstream_current_stage"],
            "status": item["stage_status"],
            "reason": item["terminal_reason_code"],
            "source_run_id": identity["source_run_id"],
            "opportunity_id": identity["opportunity_id"],
            "candidate_id": identity["candidate_id"],
            "approval_id": identity["approval_id"],
            "plan_id": identity["plan_id"],
            "updated_at": item["updated_at_ms"],
        }
        required_parity = {
            "profile": data["trade_profile_id"],
            "timeframe": data["primary_timeframe"],
            "cycle_boundary_ms": current["boundary_close_ms"],
            "symbol": item["symbol"],
            "source_run_id": item["source_run_id"],
            "candidate_id": item["candidate_id"],
        }
        for key, expected in required_parity.items():
            if identity[key] != expected:
                raise SystemExit(f"identity parity failure for {item['symbol']} field {key}")
        records.append(record)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    print(f"ROW_DETAIL_EXPECTED_IDENTITY={len(records)} CYCLE={current['boundary_close_ms']} PARITY=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
