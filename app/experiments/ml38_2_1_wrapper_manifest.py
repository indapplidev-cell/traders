from __future__ import annotations

from typing import Any


REUSE_REQUIRED_FEATURE_VERSION = "fv3_candle_ta_context"


def validate_reusable_symbol_summary(summary: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if str(summary.get("feature_version_used")) != REUSE_REQUIRED_FEATURE_VERSION:
        issues.append("feature_version_used_mismatch")
    if not bool(summary.get("candle_ta_context_features_attached", False)):
        issues.append("missing_candle_ta_context_features")
    if not bool(summary.get("real_feature_diagnostics_used", False)):
        issues.append("missing_real_feature_diagnostics")
    if not bool(summary.get("regime_features_attached", False)):
        issues.append("missing_regime_features")
    if str(summary.get("model_quality_validation_status")) != "COMPLETED":
        issues.append("model_quality_validation_not_completed")
    if not _as_list(summary.get("configs_ranked") or summary.get("ranking")):
        issues.append("missing_candidate_ranking")
    if not summary.get("best_candidate_config_id"):
        issues.append("missing_best_candidate_config_id")
    return {
        "reusable": not issues,
        "issues": issues,
    }


def build_ml38_2_1_wrapper_manifest(
    *,
    branch: str,
    archive_path: str,
    archive_stage_dir: str,
    manifest_path: str,
    script_path: str,
    source_mode: str,
    wrapper_completed_end_to_end: bool,
    symbols: list[str] | tuple[str, ...],
    symbols_completed: list[str] | tuple[str, ...],
    failed_symbols: list[str] | tuple[str, ...],
    run_results: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    multi_symbol_result: dict[str, Any] | None,
    included_files: list[str] | tuple[str, ...],
    stage_report_path: str | None = None,
    analysis_json_path: str | None = None,
    analysis_markdown_path: str | None = None,
) -> dict[str, Any]:
    payload = dict(multi_symbol_result or {})
    return {
        "stage": "ML38.2.1",
        "branch": branch,
        "feature_version": REUSE_REQUIRED_FEATURE_VERSION,
        "archive_path": archive_path,
        "archive_stage_dir": archive_stage_dir,
        "manifest_path": manifest_path,
        "script_path": script_path,
        "source_mode": source_mode,
        "wrapper_completed_end_to_end": wrapper_completed_end_to_end,
        "manual_archive_assembly_used": False,
        "fresh_grid_archive_created_by_wrapper": True,
        "symbols": list(symbols),
        "symbols_completed": list(symbols_completed),
        "failed_symbols": list(failed_symbols),
        "candidate_count": payload.get("candidate_count"),
        "accepted_candidate_count": payload.get("accepted_candidate_count"),
        "rejected_candidate_count": payload.get("rejected_candidate_count"),
        "schwager_robustness_summary": dict(
            payload.get("schwager_robustness_summary", {})
        ),
        "run_results": [dict(item) for item in run_results],
        "multi_symbol_result": payload,
        "included_files": list(included_files),
        "stage_report_path": stage_report_path,
        "analysis_json_path": analysis_json_path,
        "analysis_markdown_path": analysis_markdown_path,
    }


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return list(value)
    if isinstance(value, (tuple, set)):
        return list(value)
    return [value]
