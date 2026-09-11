"""Content-aware validation for durable parameter-sweep artifacts."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Callable

import yaml

from .artifact_writer import DEFAULT_ARTIFACT_WRITER


COMPLETED_ARTIFACTS = (
    "RUN_CONFIG.yaml", "RUN_MANIFEST.json", "PREFLIGHT.json", "SEARCH_PLAN.json", "DATASET_MANIFEST.json",
    "DATASET_SNAPSHOT.json", "CHECKPOINT.json",
    "RESULTS.csv", "RESULTS.jsonl", "RESULTS.json", "TOP_CONFIGS.json",
    "ACCEPTED_CONFIGS.jsonl", "REJECTED_CONFIGS.jsonl", "FINALIST_TRADES.jsonl",
    "REJECTED_CONFIGS.json", "ARTIFACT_SIZES.json", "REPORT.md", "STATUS.json",
    "OPPORTUNITY_FUNNEL.json", "PARAMETER_REGISTRY.json",
)

TERMINAL_ARTIFACTS = {
    "COMPLETED": COMPLETED_ARTIFACTS,
    "FAILED_BEFORE_EVALUATION": (
        "RUN_CONFIG.yaml", "PREFLIGHT.json", "SEARCH_PLAN.json", "DATASET_MANIFEST.json", "DATASET_SNAPSHOT.json",
        "CHECKPOINT.json", "STATUS.json", "REPORT.md",
    ),
    "FAILED_DURING_EVALUATION": (
        "RUN_CONFIG.yaml", "PREFLIGHT.json", "SEARCH_PLAN.json", "DATASET_MANIFEST.json", "DATASET_SNAPSHOT.json",
        "CHECKPOINT.json", "STATUS.json", "RESULTS.csv", "RESULTS.jsonl",
        "REPORT.md",
    ),
    "CANCELLED": (
        "RUN_CONFIG.yaml", "PREFLIGHT.json", "SEARCH_PLAN.json", "DATASET_MANIFEST.json", "DATASET_SNAPSHOT.json",
        "CHECKPOINT.json", "STATUS.json", "RESULTS.csv", "RESULTS.jsonl",
    ),
    "INTERRUPTED_RESUMABLE": (
        "RUN_CONFIG.yaml", "PREFLIGHT.json", "SEARCH_PLAN.json", "DATASET_MANIFEST.json", "DATASET_SNAPSHOT.json",
        "CHECKPOINT.json", "STATUS.json", "RESULTS.csv", "RESULTS.jsonl",
    ),
}


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_artifacts(
    run_directory: Path, *, expected_run_id: str,
    expected_dataset_fingerprint: str, expected_config_hash: str,
    expected_count: int, terminal_state: str = "COMPLETED",
    on_file_checked: Callable[[str, bool, str | None], None] | None = None,
) -> dict[str, Any]:
    try:
        required_artifacts = TERMINAL_ARTIFACTS[terminal_state]
    except KeyError:
        raise ValueError(f"unknown terminal artifact contract: {terminal_state}") from None
    statuses: dict[str, dict[str, Any]] = {}
    for name in required_artifacts:
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
        manifest = _json(run_directory / "DATASET_MANIFEST.json")
        snapshot = _json(run_directory / "DATASET_SNAPSHOT.json")
        run_config = yaml.safe_load((run_directory / "RUN_CONFIG.yaml").read_text(encoding="utf-8"))
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
                manifest.get("dataset_fingerprint") == expected_dataset_fingerprint,
            )),
            "dataset_manifest_hash": (
                checkpoint.get("dataset_manifest_hash") == manifest.get("manifest_hash")
                and preflight.get("DATASET_MANIFEST_HASH") == manifest.get("manifest_hash")
                and search_plan.get("DATASET_MANIFEST_HASH") == manifest.get("manifest_hash")
                and run_config.get("dataset_manifest_hash") == manifest.get("manifest_hash")
            ),
            "dataset_snapshot_count": len(snapshot) == int(manifest.get("dataset_row_count", -1)),
            "config_hash": all((
                checkpoint.get("config_hash") == expected_config_hash,
                preflight.get("CONFIG_HASH") == expected_config_hash,
                search_plan.get("CONFIG_HASH") == expected_config_hash,
                run_config.get("baseline_config_hash") == expected_config_hash,
            )),
            "checkpoint_result_count": (
                int(checkpoint.get("last_durable_result_index", -2)) + 1 == expected_count
            ),
        }
        if terminal_state == "COMPLETED":
            json_results = _json(run_directory / "RESULTS.json")
            jsonl_results = [
                json.loads(line) for line in (run_directory / "RESULTS.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            with (run_directory / "RESULTS.csv").open(newline="", encoding="utf-8") as handle:
                csv_results = list(csv.DictReader(handle))
            checks["result_count"] = (
                len(json_results) == expected_count
                and len(jsonl_results) == expected_count
                and len(csv_results) == expected_count
            )
            identities = [(row.get("run_id"), row.get("result_index", row.get("config_index")), row.get("config_hash", row.get("config_id"))) for row in jsonl_results]
            checks["result_identity_unique"] = len(identities) == len(set(identities))
            checks["artifact_schema_v2"] = all(row.get("artifact_schema_version") == 2 for row in jsonl_results)
            checks["inline_market_path_zero"] = all("market_path_1m" not in line for line in (run_directory / "RESULTS.jsonl").read_text(encoding="utf-8").splitlines())
            checks["checkpoint_evaluated_equals_durable"] = (
                int(checkpoint.get("evaluated_count", -1))
                == int(checkpoint.get("durable_result_count", -2))
                == len(jsonl_results)
            )
        elif terminal_state == "FAILED_BEFORE_EVALUATION":
            status = _json(run_directory / "STATUS.json")
            checks["failed_before_evaluation_state"] = (
                status.get("state") == "FAILED"
                and status.get("phase") == "REPLAY_VALIDATION"
                and status.get("current_config_index") is None
                and int(status.get("completed_configs", -1)) == 0
            )
    except (OSError, TypeError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        checks["cross_artifact_parse"] = False
        checks["cross_artifact_error"] = str(exc)
    passed = all(item["passed"] for item in statuses.values()) and all(
        value for key, value in checks.items() if not key.endswith("_error")
    )
    payload = {
        "run_id": expected_run_id,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "terminal_state": terminal_state,
        "required_files": list(required_artifacts),
        "file_statuses": statuses,
        "result_count_expected": expected_count,
        "result_count_actual": (
            len(json_results) if "json_results" in locals() else expected_count
        ),
        "hash_fingerprint_checks": checks,
        "integrity_status": "PASS" if passed else "FAIL",
    }
    DEFAULT_ARTIFACT_WRITER.atomic_json(
        run_directory / "INTEGRITY.json", payload, operation="integrity_replace",
    )
    return payload
