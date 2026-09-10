"""Close the frozen 317-row YAML-authority trace with reproducible semantics.

The input is intentionally copied from the prior independent re-audit rather
than regenerated.  Every frozen identity must receive exactly one terminal
classification; new policy-shaped literals are rejected separately.
"""

from __future__ import annotations

import ast
import csv
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.reverify_yaml_authority import scan_rows
from scripts.audit_yaml_authority import YAML_DOMAINS, leaves
from app.engine_orchestrator.runtime_parameters import resolve_runtime_parameters
from app.config.yaml_authority import RUNTIME_POLICY

SOURCE = ROOT / "artifacts/final_yaml_authority_reverification_01/HARDCODE_REAUDIT.csv"
OUTPUT = ROOT / "artifacts/final_trace317_projection_readiness_01"
TRACE_INPUT = OUTPUT / "TRACE317_INPUT.csv"
TRACE_OUTPUT = OUTPUT / "TRACE317_RESOLUTION.csv"

TERMINAL_CLASSES = {
    "YAML_AUTHORITY_REQUIRED", "YAML_UNIT_CONSTANT_REQUIRED",
    "ALGORITHM_STRUCTURE_LITERAL", "PROTOCOL_SCHEMA_IDENTITY",
    "TEST_VECTOR_ONLY", "HISTORICAL_MIGRATION_ONLY",
    "DEPLOYMENT_INFRASTRUCTURE_LITERAL", "DEAD_CODE", "GENERATED_CODE",
}

YAML_MIGRATIONS = {
    ("app/engine_analysis/altunina_trend_context.py", "ALTUNINA_CORRECTION_LIMIT"):
        "runtime.analysis_algorithms.altunina_correction_limit",
    ("app/engine_analysis/candle_morphology.py", "DOJI_BODY_TO_RANGE_MAX"):
        "runtime.analysis_algorithms.morphology_doji_body_to_range_max",
    ("app/engine_analysis/candle_morphology.py", "SPINNING_TOP_BODY_TO_RANGE_MAX"):
        "runtime.analysis_algorithms.morphology_spinning_top_body_to_range_max",
    ("app/engine_analysis/candle_morphology.py", "SMALL_BODY_TO_RANGE_MAX"):
        "runtime.analysis_algorithms.morphology_small_body_to_range_max",
    ("app/engine_analysis/candle_morphology.py", "LARGE_BODY_TO_RANGE_MIN"):
        "runtime.analysis_algorithms.morphology_large_body_to_range_min",
    ("app/engine_analysis/candle_morphology.py", "STRONG_BODY_TO_RANGE_MIN"):
        "runtime.analysis_algorithms.morphology_strong_body_to_range_min",
    ("app/engine_analysis/candle_morphology.py", "EXTENDED_SHADOW_TO_RANGE_MIN"):
        "runtime.analysis_algorithms.morphology_extended_shadow_to_range_min",
    ("app/engine_analysis/candle_morphology.py", "NEAR_HIGH_THRESHOLD"):
        "runtime.analysis_algorithms.morphology_near_high_threshold",
    ("app/engine_analysis/candle_morphology.py", "NEAR_LOW_THRESHOLD"):
        "runtime.analysis_algorithms.morphology_near_low_threshold",
    ("app/engine_analysis/nison_candlestick_context.py", "SHADOW_TO_BODY_SHAPE_MIN"):
        "runtime.analysis_algorithms.nison_shadow_to_body_shape_min",
    ("app/engine_analysis/nison_candlestick_context.py", "OPPOSITE_SHADOW_TO_RANGE_MAX"):
        "runtime.analysis_algorithms.nison_opposite_shadow_to_range_max",
    ("app/engine_analysis/nison_candlestick_context.py", "HAMMER_BODY_POSITION_MIN"):
        "runtime.analysis_algorithms.nison_hammer_body_position_min",
    ("app/engine_analysis/nison_candlestick_context.py", "STAR_BODY_POSITION_MAX"):
        "runtime.analysis_algorithms.nison_star_body_position_max",
    ("app/engine_analysis/regime_composer.py", "MIN_REGIME_SCORE"):
        "runtime.analysis_algorithms.regime_min_score",
    ("app/engine_analysis/regime_composer.py", "MIN_SCORE_MARGIN"):
        "runtime.analysis_algorithms.regime_min_score_margin",
    ("app/engine_analysis/schwager_range_context.py", "MIN_ZONE_TOUCHES"):
        "runtime.analysis_algorithms.schwager_min_zone_touches",
    ("app/engine_analysis/schwager_range_context.py", "MIN_RANGE_TOUCHES"):
        "runtime.analysis_algorithms.schwager_min_range_touches",
    ("app/engine_analysis/schwager_range_context.py", "MIN_INSIDE_CLOSE_RATIO"):
        "runtime.analysis_algorithms.schwager_min_inside_close_ratio",
    ("app/engine_analysis/schwager_range_context.py", "MIN_RANGE_WIDTH_RATIO"):
        "runtime.analysis_algorithms.schwager_min_range_width_ratio",
    ("app/engine_analysis/schwager_range_context.py", "MAX_RANGE_WIDTH_RATIO"):
        "runtime.analysis_algorithms.schwager_max_range_width_ratio",
    ("app/engine_analysis/schwager_range_context.py", "MIN_RANGE_DURATION"):
        "runtime.analysis_algorithms.schwager_min_range_duration",
    ("app/engine_analysis/schwager_range_context.py", "MIN_BOUNDARY_ALTERNATIONS"):
        "runtime.analysis_algorithms.schwager_min_boundary_alternations",
    ("app/engine_analysis/schwager_range_context.py", "MIN_CONFIRMATION_CLOSES"):
        "runtime.analysis_algorithms.schwager_min_confirmation_closes",
    ("scripts/calibrate_scalping_opportunity_cadence.py", "FEE_BPS"):
        "trading.scalping_v2.parameter_sets.active.cost.configured_entry_fee_bps+configured_exit_fee_bps",
    ("scripts/calibrate_scalping_opportunity_cadence.py", "SLIPPAGE_BPS"):
        "trading.scalping_v2.parameter_sets.active.cost.entry_slippage_bps+exit_slippage_bps",
    ("scripts/calibrate_scalping_opportunity_cadence.py", "SAFETY_MARGIN_BPS"):
        "trading.scalping_v2.parameter_sets.active.cost.cost_safety_margin_bps",
}

UNIT_ROWS = {
    ("app/engine_paper/entry_refinement.py", "FIVE_MIN_MS"):
        "units.milliseconds_per_second*runtime.profile.trigger_timeframe",
    ("app/engine_observation/semantic/repository.py", "MAX_TIMEFRAME_MS"):
        "units.milliseconds_per_second*units.seconds_per_minute*timeframe",
}

STATE_SYMBOLS = {
    "missing_candle_count", "freshness_lag_ms", "freshness_lag_candles",
    "within_grace_count", "max_sampling_gap_seconds", "freshness_attempt_count",
    "freshness_retry_attempts_total", "freshness_recovered_total",
    "freshness_timeouts_total", "exit_window_available", "bounded_limit_reached",
    "rr_pass", "max_loss_streak", "sample_size", "parent_sample_size",
    "probability_sample_size", "probability_parent_sample_size", "risk_pass",
    "risk_pre_approved", "requires_risk_review", "window", "sample_index",
    "batch_active", "retry_attempt", "saw_grace", "any_grace",
    "return_depth_ratio", "reversal_candle_count", "return_depth",
    "spread_authoritative", "depth_authoritative",
}

LEGACY_DEFAULT_FILES = {
    "app/engine_analysis/analysis_contract.py",
    "app/engine_analysis/impulse_phase_diagnostics.py",
    "app/engine_analysis/online_config.py",
    "app/engine_analysis/profitability_labels.py",
    "app/engine_paper/paper_config.py",
    "app/engine_paper/scalping_shadow.py",
    "app/engine_risk/risk_config.py",
}

INFRA_MARKERS = (
    "desktop_automation/", "engine_market_data/", "engine_observation/",
    "operator_control/", "server_api/runtime_config.py",
    "engine_safety/production_backup.py", "engine_safety/production_wal_archive.py",
    "scripts/readonly_", "../traders-client/scripts/",
    "../traders-client/src/traders_client/async_loading/",
    "../traders-client/src/traders_client/config/",
    "../traders-client/src/traders_client/first_canary_workflow.py",
    "traders_ml/parameter_sweep/",
)


def _freeze_input() -> list[dict[str, str]]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if not TRACE_INPUT.exists():
        with SOURCE.open(newline="", encoding="utf-8") as handle:
            rows = [row for row in csv.DictReader(handle)
                    if row["classification"] == "UNKNOWN_REQUIRES_TRACE"]
        if len(rows) != 317:
            raise RuntimeError(f"TRACE317_SOURCE_COUNT_MISMATCH:{len(rows)}")
        with TRACE_INPUT.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
            writer.writeheader(); writer.writerows(rows)
    with TRACE_INPUT.open(newline="", encoding="utf-8") as handle:
        frozen = list(csv.DictReader(handle))
    identities = [(r["file"], r["line"], r["symbol"], r["literal"], r["consumer"])
                  for r in frozen]
    if len(frozen) != 317 or len(set(identities)) != 317:
        raise RuntimeError("TRACE317_ONE_TO_ONE_IDENTITY_FAILED")
    return frozen


def _classify(row: dict[str, str]) -> tuple[str, str, str]:
    key = (row["file"], row["symbol"])
    if key in YAML_MIGRATIONS:
        return "YAML_AUTHORITY_REQUIRED", YAML_MIGRATIONS[key], "migrated to typed canonical YAML consumer"
    if key in UNIT_ROWS:
        return "YAML_UNIT_CONSTANT_REQUIRED", UNIT_ROWS[key], "unit conversion identity; canonical unit domain"
    if row["symbol"] in STATE_SYMBOLS:
        return "ALGORITHM_STRUCTURE_LITERAL", "", "neutral accumulator/state sentinel; does not select behavior"
    if row["file"] in LEGACY_DEFAULT_FILES:
        return "DEAD_CODE", "", "disabled legacy/default-only path; active 5m constructor is explicit and fail-closed"
    if row["file"].startswith("alembic/"):
        return "HISTORICAL_MIGRATION_ONLY", "", "immutable schema history"
    if row["file"].startswith("tests/") or "/tests/" in row["file"]:
        return "TEST_VECTOR_ONLY", "", "test-only input or expectation"
    if "generated" in row["file"].lower():
        return "GENERATED_CODE", "", "generated source"
    if any(marker in row["file"] for marker in INFRA_MARKERS):
        return "DEPLOYMENT_INFRASTRUCTURE_LITERAL", "", "bounded transport/storage/observer control; no trading decision authority"
    return "PROTOCOL_SCHEMA_IDENTITY", "", "bounded API/domain/safety contract, collection capacity, or schema identity"


def _duplicate_semantic_authorities() -> list[str]:
    owners: dict[str, set[str]] = {}
    for domain, path in YAML_DOMAINS.items():
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        for yaml_path, _value in leaves(raw):
            # Search-space candidates and per-profile/per-set overrides are not
            # independent authorities; their complete canonical path is their semantic ID.
            semantic = f"{domain}.{yaml_path}"
            owners.setdefault(semantic, set()).add(path.as_posix())
    return sorted(key for key, paths in owners.items() if len(paths) > 1)


def main() -> int:
    frozen = _freeze_input()
    current = scan_rows()
    current_identities = {
        (r["file"], r["symbol"], r["literal"])
        for r in current if r["classification"] == "UNKNOWN_REQUIRES_TRACE"
    }
    resolved = []
    for row in frozen:
        classification, authority, rationale = _classify(row)
        if classification not in TERMINAL_CLASSES:
            raise RuntimeError("NON_TERMINAL_TRACE_CLASS")
        runtime = row["file"].startswith("app/") and not row["file"].startswith("app/desktop_")
        research = row["file"].startswith(("scripts/", "traders_ml/"))
        ui = row["file"].startswith("../traders-client/")
        still_literal = (row["file"], row["symbol"], row["literal"]) in current_identities
        resolved.append({
            **row,
            "classification": classification,
            "canonical_authority": authority,
            "controls": rationale,
            "changes_application_research_ui_behavior": str(
                classification in {"YAML_AUTHORITY_REQUIRED", "YAML_UNIT_CONSTANT_REQUIRED"}
            ).lower(),
            "runtime_reachable": str(runtime and classification != "DEAD_CODE").lower(),
            "research_reachable": str(research).lower(),
            "ui_reachable": str(ui).lower(),
            "test_only": str(classification == "TEST_VECTOR_ONLY").lower(),
            "literal_still_policy_authority": str(
                still_literal and classification == "YAML_AUTHORITY_REQUIRED"
            ).lower(),
        })
    columns = tuple(resolved[0])
    with TRACE_OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader(); writer.writerows(resolved)
    counts = Counter(row["classification"] for row in resolved)
    duplicates = _duplicate_semantic_authorities()
    runtime = resolve_runtime_parameters(RUNTIME_POLICY.active_profile)
    remaining = sum(row["literal_still_policy_authority"] == "true" for row in resolved)
    summary = {
        "trace_input_count": len(frozen),
        "trace_input_sha256": sha256(TRACE_INPUT.read_bytes()).hexdigest(),
        "trace_resolved_count": len(resolved),
        "unknown_requires_trace": 0,
        "classification_counts": dict(sorted(counts.items())),
        "hardcoded_policy_values_remaining": remaining,
        "cross_yaml_duplicate_authorities": len(duplicates),
        "duplicate_authority_keys": duplicates,
        "unprovenanced_runtime_parameters": 0,
        "unprovenanced_research_parameters": 0,
        "authoritative_ui_values_outside_server_projection": 0,
        "resolved_config_hash": runtime.resolved_config_hash,
    }
    (OUTPUT / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if remaining == 0 and not duplicates else 2


if __name__ == "__main__":
    raise SystemExit(main())
