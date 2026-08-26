"""Bounded read-only 5m Strategy cap SHADOW calibration export."""

from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine_observation.strategy_cap_calibration import calibrate
from scripts.observe_5m_scalping_calibration import PARAMETER_SET, load_rows


TASK = "TRADERS_5M_STRATEGY_CAP_SHADOW_CALIBRATION_EXPERIMENT_01"
FORENSIC_PARAMETER_START_BOUNDARY = 1787658000000


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-boundary", type=int, default=FORENSIC_PARAMETER_START_BOUNDARY)
    parser.add_argument("--max-boundaries", type=int, default=2880)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if not 1 <= args.max_boundaries <= 2880:
        raise SystemExit("max-boundaries must be in 1..2880")
    loaded = load_rows(args.start_boundary, args.max_boundaries)
    homogeneous = [row for row in loaded if row.get("parameter_set_id") == PARAMETER_SET]
    report = calibrate(homogeneous)
    report["excluded_nonmatching_or_incomplete_rows"] = len(loaded) - len(homogeneous)
    if report["parameter_set_id"] != PARAMETER_SET:
        raise SystemExit("runtime parameter identity mismatch")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = args.output_dir / f"{TASK}_DATASET_V1"
    records_path = stem.with_suffix(".jsonl")
    records = report.pop("records")
    records_path.write_text("".join(
        json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
        for record in records
    ), encoding="utf-8", newline="\n")
    report["records_sha256"] = sha256(records_path.read_bytes()).hexdigest()
    report["record_count"] = len(records)
    summary_path = stem.with_name(stem.name + "_SUMMARY.json")
    summary_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8", newline="\n")
    print(json.dumps({
        "dataset": str(records_path.resolve()),
        "summary": str(summary_path.resolve()),
        "summary_sha256": sha256(summary_path.read_bytes()).hexdigest(),
        "evaluations": report["evaluations"],
        "setup_candidates": report["setup_candidates"],
        "not_evaluated_total": report["not_evaluated_total"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
