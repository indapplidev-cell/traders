"""Content-aware validation for durable parameter-sweep artifacts."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Callable

import yaml

from app.config.yaml_authority import ValidationSamplePolicy

from .artifact_writer import DEFAULT_ARTIFACT_WRITER
from .artifact_v2 import aggregate_result_semantics
from .research_protocol import canonical_hash, holdout_result_hash


COMPLETED_ARTIFACTS = (
    "RUN_CONFIG.yaml", "RUN_MANIFEST.json", "PREFLIGHT.json", "SEARCH_PLAN.json", "DATASET_MANIFEST.json",
    "DATASET_SNAPSHOT.json", "CHECKPOINT.json",
    "RESULTS.csv", "RESULTS.jsonl", "RESULTS.json", "TOP_CONFIGS.json",
    "ACCEPTED_CONFIGS.jsonl", "REJECTED_CONFIGS.jsonl", "FINALIST_TRADES.jsonl",
    "REJECTED_CONFIGS.json", "ARTIFACT_SIZES.json", "REPORT.md", "STATUS.json",
    "OPPORTUNITY_FUNNEL.json", "PARAMETER_REGISTRY.json",
    "WINNER_LOSER_DATASET.jsonl", "DATA_DRIVEN_SEARCH_RANGES.json",
    "RESEARCH_BLOCK_STATUS.json", "FINALIST_FREEZE.json",
    "HOLDOUT_RESULTS.jsonl",
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
    expected_symbol: str | None = None,
    validation_policy: ValidationSamplePolicy | None = None,
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
        resolved_validation_policy = validation_policy or ValidationSamplePolicy(
            minimum_validation_trades=run_config["VALIDATION_MINIMUM_TRADES"],
            minimum_independent_periods=run_config["MINIMUM_INDEPENDENT_PERIODS"],
            independent_period_unit=run_config["INDEPENDENT_PERIOD_UNIT"],
            provenance=run_config["VALIDATION_GATE_PROVENANCE"],
        )
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
        if expected_symbol is not None:
            checks["single_symbol_identity"] = all((
                checkpoint.get("symbol") == expected_symbol,
                preflight.get("SYMBOL") == expected_symbol,
                search_plan.get("symbol") == expected_symbol,
                run_config.get("symbol") == expected_symbol,
                manifest.get("symbol") == expected_symbol,
                manifest.get("symbols") == [expected_symbol],
                all(row.get("symbol") == expected_symbol for row in snapshot),
            ))
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
            if expected_symbol is not None:
                run_manifest = _json(run_directory / "RUN_MANIFEST.json")
                freeze = _json(run_directory / "FINALIST_FREEZE.json")
                checks["single_symbol_results"] = all(
                    row.get("symbol") == expected_symbol
                    and int(row.get("evaluated_symbol_count", 0)) == 1
                    for row in jsonl_results
                ) and run_manifest.get("symbol") == expected_symbol and freeze.get("symbol") == expected_symbol
            identities = [(row.get("run_id"), row.get("result_index", row.get("config_index")), row.get("config_hash", row.get("config_id"))) for row in jsonl_results]
            checks["result_identity_unique"] = len(identities) == len(set(identities))
            checks["artifact_schema_v2"] = all(row.get("artifact_schema_version") == 2 for row in jsonl_results)
            checks["inline_market_path_zero"] = all("market_path_1m" not in line for line in (run_directory / "RESULTS.jsonl").read_text(encoding="utf-8").splitlines())
            checks["checkpoint_evaluated_equals_durable"] = (
                int(checkpoint.get("evaluated_count", -1))
                == int(checkpoint.get("durable_result_count", -2))
                == len(jsonl_results)
            )
            status = _json(run_directory / "STATUS.json")
            accepted_rows = [
                json.loads(line) for line in (run_directory / "ACCEPTED_CONFIGS.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            rejected_rows = [
                json.loads(line) for line in (run_directory / "REJECTED_CONFIGS.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            semantics = aggregate_result_semantics(
                jsonl_results, error_count=int(checkpoint.get("failed_count", 0)),
                validation_policy=resolved_validation_policy,
            )
            checks["results_status_parity"] = all((
                status.get("evaluation_status_counts") == semantics["evaluation_status_counts"],
                status.get("performance_class_counts") == semantics["performance_class_counts"],
                int(status.get("accepted_configs", -1)) == semantics["accepted_configs"],
                int(status.get("rejected_configs", -1)) == semantics["rejected_configs"],
                int(status.get("error_configs", -1)) == semantics["error_configs"],
                status.get("canonical_validation") == semantics["canonical_validation"],
                checkpoint.get("canonical_validation") == semantics["canonical_validation"],
                status.get("validation_readiness") == semantics["validation_readiness"],
                checkpoint.get("validation_readiness") == semantics["validation_readiness"],
            ))
            checks["accepted_rejected_artifact_parity"] = (
                len(accepted_rows) == semantics["accepted_configs"]
                and len(rejected_rows) == len(jsonl_results) - semantics["accepted_configs"]
            )
            report = (run_directory / "REPORT.md").read_text(encoding="utf-8")
            policy_fields = resolved_validation_policy.artifact_fields()
            provenance_keys = (
                "VALIDATION_MINIMUM_TRADES", "VALIDATION_MINIMUM_TRADES_SOURCE",
                "MINIMUM_INDEPENDENT_PERIODS", "MINIMUM_INDEPENDENT_PERIODS_SOURCE",
                "INDEPENDENT_PERIOD_UNIT", "INDEPENDENT_PERIOD_UNIT_SOURCE",
                "VALIDATION_GATE_PROVENANCE",
            )
            checks["results_report_parity"] = all((
                f"EVALUATION_STATUS_COUNTS: `{json.dumps(semantics['evaluation_status_counts'], sort_keys=True)}`" in report,
                f"PERFORMANCE_CLASS_COUNTS: `{json.dumps(semantics['performance_class_counts'], sort_keys=True)}`" in report,
                f"CANONICAL_VALIDATION: `{json.dumps(semantics['canonical_validation'], sort_keys=True)}`" in report,
            ))
            resolved_seed = checkpoint.get("resolved_seed", checkpoint.get("seed"))
            run_manifest = _json(run_directory / "RUN_MANIFEST.json")
            checks["validation_gate_provenance"] = all(
                artifact.get(key) == policy_fields[key]
                for artifact in (run_config, status, checkpoint, run_manifest)
                for key in provenance_keys
            ) and all(
                f"{key} = {policy_fields[key]}" in report
                for key in provenance_keys[:-1]
            )
            opportunity_funnel = _json(run_directory / "OPPORTUNITY_FUNNEL.json")
            freeze = _json(run_directory / "FINALIST_FREEZE.json")
            holdout_results = [
                json.loads(line) for line in (run_directory / "HOLDOUT_RESULTS.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            winner_loser = [
                json.loads(line) for line in (run_directory / "WINNER_LOSER_DATASET.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            ranges = _json(run_directory / "DATA_DRIVEN_SEARCH_RANGES.json")
            freeze_hash = canonical_hash({
                key: value for key, value in freeze.items() if key != "freeze_hash"
            })
            frozen_ids = {
                str(item["finalist_id"]) for item in freeze.get("finalists", [])
            }
            results_by_id = {str(row["config_id"]): row for row in jsonl_results}
            holdout_ids = [str(item.get("finalist_id")) for item in holdout_results]
            checks["finalist_freeze_integrity"] = (
                freeze.get("freeze_hash") == freeze_hash
                and checkpoint.get("freeze_hash") == freeze_hash
                and freeze.get("dataset_fingerprint") == expected_dataset_fingerprint
                and int(freeze.get("finalist_count_selected", -1)) == len(frozen_ids)
            )
            checks["finalist_eligibility"] = all(
                results_by_id[str(item["finalist_id"])].get("performance_class") == "VALIDATION_CANDIDATE"
                and results_by_id[str(item["finalist_id"])].get("evaluation_status") == "ACCEPTED"
                and not results_by_id[str(item["finalist_id"])].get("insufficient_sample_gates")
                for item in freeze.get("finalists", [])
            )
            signatures = [str(item.get("behavioral_signature")) for item in freeze.get("finalists", [])]
            checks["behavioral_finalist_dedup"] = (
                len(signatures) == len(set(signatures))
                and all(
                    int(item.get("equivalence_count", 0)) == len(item.get("equivalent_config_ids", []))
                    and item.get("representative_config_id") == item.get("finalist_id")
                    for item in freeze.get("finalists", [])
                )
            )
            checks["holdout_frozen_finalists_only_once"] = (
                set(holdout_ids) <= frozen_ids
                and len(holdout_ids) == len(set(holdout_ids))
                and checkpoint.get("holdout_result_hash") == holdout_result_hash(holdout_results)
            )
            checks["zero_finalists_holdout_guard"] = (
                bool(frozen_ids)
                or (
                    freeze.get("reason") == "ZERO_ELIGIBLE_VALIDATION_FINALISTS"
                    and checkpoint.get("campaign_verdict") == "HOLDOUT_SKIPPED_ZERO_FINALISTS"
                    and checkpoint.get("holdout_opened") is False
                    and checkpoint.get("holdout_evaluated") is False
                    and int(checkpoint.get("holdout_evaluations", -1)) == 0
                    and int(checkpoint.get("holdout_rows_read", -1)) == 0
                    and int(checkpoint.get("holdout_metrics_computed", -1)) == 0
                    and not holdout_results
                )
            )
            history_values = (
                manifest.get("history_target_days"), checkpoint.get("history_target_days"),
                status.get("history_target_days"), run_config.get("history_target_days"),
                run_manifest.get("history_target_days"),
            )
            checks["history_depth_parity"] = (
                all(value == 30 for value in history_values)
                and all(
                    artifact.get("history_start") == manifest.get("history_start")
                    and artifact.get("history_end") == manifest.get("history_end")
                    and artifact.get("history_actual_days") == manifest.get("history_actual_days")
                    and artifact.get("history_depth_status") == manifest.get("history_depth_status")
                    for artifact in (checkpoint, status, run_config, run_manifest)
                )
            )
            checks["winner_loser_holdout_zero"] = all(
                row.get("split") in {"CALIBRATION", "VALIDATION"}
                and int(row.get("feature_timestamp", 1)) <= int(row.get("entry_decision_timestamp", 0))
                for row in winner_loser
            )
            checks["range_artifact_run_local"] = (
                ranges.get("mutates_yaml") is False
                and ranges.get("global_authority") is False
            )
            finalist_rows = [
                json.loads(line) for line in (run_directory / "FINALIST_TRADES.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            seed_values = (
                checkpoint.get("seed"), checkpoint.get("resolved_seed"),
                preflight.get("SEED"), preflight.get("RESOLVED_SEED"),
                search_plan.get("SEED"), search_plan.get("RESOLVED_SEED"),
                run_config.get("seed"), run_config.get("resolved_seed"),
                run_config.get("sampler_seed"), run_manifest.get("resolved_seed"),
                status.get("resolved_seed"),
            )
            checks["resolved_seed_parity"] = (
                resolved_seed is not None
                and all(value == resolved_seed for value in seed_values)
                and all(row.get("resolved_seed") == resolved_seed for row in jsonl_results)
                and all(row.get("resolved_seed") == resolved_seed for row in accepted_rows + rejected_rows + finalist_rows)
                and opportunity_funnel.get("RESOLVED_SEED") == resolved_seed
                and f"Requested/resolved/sampler seed: {resolved_seed}/{resolved_seed}/{resolved_seed}" in report
            )
            checks["opportunity_funnel_aggregation_parity"] = (
                opportunity_funnel.get("RUN_AGGREGATION") == semantics
            )
            finalist_validation: dict[str, list[dict[str, Any]]] = {}
            for trade in finalist_rows:
                if trade.get("split") == "validation":
                    finalist_validation.setdefault(str(trade["config_id"]), []).append(trade)
            results_by_id = {str(row["config_id"]): row for row in jsonl_results}
            checks["finalist_trades_coverage_parity"] = all(
                int(results_by_id[config_id]["trade_count"]) == len(trades)
                and int(results_by_id[config_id]["symbol_coverage"]) == len({str(t["symbol"]) for t in trades})
                and int(results_by_id[config_id]["setup_coverage"]) == len({str(t.get("setup_type") or "UNKNOWN") for t in trades})
                and int(results_by_id[config_id]["independent_period_count"]) == len({
                    datetime.fromtimestamp(int(t.get("opened_at_ms", t.get("boundary_ms"))) / 1000, timezone.utc).date().isoformat()
                    for t in trades
                })
                for config_id, trades in finalist_validation.items()
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
