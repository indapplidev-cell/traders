"""Content-aware validation for durable parameter-sweep artifacts."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Callable

import yaml


REQUIRED_ARTIFACTS = (
    "RUN_CONFIG.yaml", "PREFLIGHT.json", "SEARCH_PLAN.json", "CHECKPOINT.json",
    "RESULTS.csv", "RESULTS.jsonl", "RESULTS.json", "TOP_CONFIGS.json",
    "REJECTED_CONFIGS.json", "REPORT.md",
)


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_artifacts(
    run_directory: Path, *, expected_run_id: str,
    expected_dataset_fingerprint: str, expected_config_hash: str,
    expected_count: int,
    on_file_checked: Callable[[str, bool, str | None], None] | None = None,
) -> dict[str, Any]:
    statuses: dict[str, dict[str, Any]] = {}
    for name in REQUIRED_ARTIFACTS:
        path = run_directory / name
        error: str | None = None
        try:
            if not path.is_file():
                raise ValueError("missing")
            if path.stat().st_size == 0:
                raise ValueError("empty")
            if path.suffix == ".json":
                _json(path)
            elif path.suffix == ".yaml":
                yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
            error = str(exc)
        passed = error is None
        statuses[name] = {"exists": path.is_file(), "passed": passed, "error": error}
        if on_file_checked:
            on_file_checked(name, passed, error)

    checks: dict[str, Any] = {}
    try:
        checkpoint = _json(run_directory / "CHECKPOINT.json")
        preflight = _json(run_directory / "PREFLIGHT.json")
        search_plan = _json(run_directory / "SEARCH_PLAN.json")
        run_config = yaml.safe_load((run_directory / "RUN_CONFIG.yaml").read_text(encoding="utf-8"))
        json_results = _json(run_directory / "RESULTS.json")
        jsonl_results = [
            json.loads(line) for line in (run_directory / "RESULTS.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        with (run_directory / "RESULTS.csv").open(newline="", encoding="utf-8") as handle:
            csv_results = list(csv.DictReader(handle))
        checks = {
            "run_id": all((
                checkpoint.get("run_id") == expected_run_id,
                preflight.get("RUN_ID") == expected_run_id,
                search_plan.get("RUN_ID") == expected_run_id,
                run_config.get("run_id") == expected_run_id,
            )),
            "dataset_fingerprint": all((
                checkpoint.get("dataset_fingerprint") == expected_dataset_fingerprint,
                preflight.get("DATASET_FINGERPRINT") == expected_dataset_fingerprint,
                search_plan.get("DATASET_FINGERPRINT") == expected_dataset_fingerprint,
                run_config.get("dataset_fingerprint") == expected_dataset_fingerprint,
            )),
            "config_hash": all((
                checkpoint.get("config_hash") == expected_config_hash,
                preflight.get("CONFIG_HASH") == expected_config_hash,
                search_plan.get("CONFIG_HASH") == expected_config_hash,
                run_config.get("baseline_config_hash") == expected_config_hash,
            )),
            "result_count": (
                int(checkpoint.get("last_durable_result_index", -2)) + 1 == expected_count
                and len(json_results) == expected_count
                and len(jsonl_results) == expected_count
                and len(csv_results) == expected_count
            ),
        }
    except (OSError, TypeError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        checks["cross_artifact_parse"] = False
        checks["cross_artifact_error"] = str(exc)
    passed = all(item["passed"] for item in statuses.values()) and all(
        value for key, value in checks.items() if not key.endswith("_error")
    )
    payload = {
        "run_id": expected_run_id,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "required_files": list(REQUIRED_ARTIFACTS),
        "file_statuses": statuses,
        "result_count_expected": expected_count,
        "result_count_actual": len(json_results) if "json_results" in locals() else None,
        "hash_fingerprint_checks": checks,
        "integrity_status": "PASS" if passed else "FAIL",
    }
    temporary = run_directory / "INTEGRITY.json.tmp"
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(run_directory / "INTEGRITY.json")
    return payload
