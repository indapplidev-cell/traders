from __future__ import annotations

import argparse
import csv
from pathlib import Path
import xml.etree.ElementTree as ET


ENVIRONMENT_CLASSES = {
    "tests.paper_account_baseline_persistence_schema_extension.test_postgres_0012",
    "tests.paper_approval_remediation.test_migration_0010",
    "tests.paper_close_causal_cursor_remediation.test_postgres_cursor_and_migration",
    "tests.paper_command_ingestion_retry.test_postgres_ingestion_service",
    "tests.paper_controlled_runtime_canary.test_postgres_canary",
    "tests.paper_controlled_runtime_dry_run.test_postgres_readonly",
    "tests.paper_controlled_runtime_sequence_canary.test_postgres_sequence",
    "tests.paper_controlled_worker_retry.test_postgres_concurrency",
    "tests.paper_controlled_worker_retry.test_postgres_full_lifecycle",
    "tests.paper_exit_evaluation_retry.test_postgres_service",
    "tests.paper_first_canary_correlation_readiness_remediation.test_postgres16_correlation",
    "tests.paper_operator_bounded_runtime_runner.test_postgres_runner",
    "tests.paper_order_execution_service.test_entry_cursor_retry_postgres",
    "tests.paper_order_execution_service.test_postgres_service_integration",
    "tests.paper_persistence.test_postgres_constraints",
    "tests.paper_production_preparation_backend_remediation.test_postgres16_cli_acceptance",
    "tests.paper_production_source_contract_remediation.test_postgres16_acceptance",
    "tests.paper_repository.test_atomic_lifecycle_and_concurrency",
    "tests.paper_repository.test_repository_contract",
}

DECOMMISSIONED_CLASSES = {
    "tests.engine_orchestrator.test_5m_runtime_parameterization_and_owner",
    "tests.engine_orchestrator.test_5m_shadow_full_funnel",
    "tests.engine_setup.test_causality_diagnostics_quality",
    "tests.engine_strategy.test_score_diagnostics",
    "tests.server_api.test_funnel_export",
    "tests.test_5m_scalping_geometry_quota_cost_remediation",
    "tests.test_5m_strategy_cap_forensic_replay",
    "tests.test_5m_strategy_cap_shadow_calibration",
    "tests.test_5m_strategy_target_actionability_shadow_calibration",
    "tests.test_engine_paper_01b_causal_context_propagation",
    "tests.test_engine_risk_01_decision_model",
    "tests.test_engine_risk_01_quality_gate",
    "tests.test_engine_risk_01_research_frequency_limits",
    "tests.test_scalping_performance_contract",
    "tests.test_scalping_risk_strategy_type_contract",
}

RESEARCH_CLASSES: set[str] = set()

LEGACY_CLASSES = {
    "tests.test_15m_first_class_domain_remediation",
    "tests.test_engine_orchestrator_01_cli",
    "tests.test_engine_orchestrator_01_config",
    "tests.test_engine_orchestrator_01_docker_compose_docs",
    "tests.test_engine_orchestrator_01_result_models",
}

OBSOLETE_CLASSES = {
    "tests.engine_orchestrator.test_failed_boundary_prompt_retry_integration",
    "tests.engine_orchestrator.test_freshness_retry_daemon",
    "tests.engine_orchestrator.test_freshness_retry_production_incidents",
    "tests.engine_orchestrator.test_freshness_retry_snapshot",
    "tests.engine_orchestrator.test_freshness_retry_store",
    "tests.engine_orchestrator.test_recovered_pair_health_integration",
    "tests.operator_control_production_deployment.test_eligible_approval_continuation",
    "tests.operator_control_production_deployment.test_multi_symbol_eligible_approval_ranking",
    "tests.operator_control_production_deployment.test_mutation_foundation_enablement",
    "tests.operator_control_production_deployment.test_runtime_and_binding",
    "tests.paper_controlled_runtime_canary.test_contract_matrix",
    "tests.paper_production_readiness_review.test_migration_and_static_policy",
    "tests.paper_readonly_deployment_postcondition_remediation.test_deployment_adapter",
    "tests.paper_readonly_reporting_api.test_api_contract",
    "tests.research.test_parameter_sweep_historical_replay",
    "tests.security_retry.test_compose_policy_matrix",
    "tests.test_continuous_budget_semantics",
    "tests.test_db_models",
    "tests.test_engine_market_data_01_contracts",
    "tests.test_engine_market_data_02_contracts",
    "tests.test_engine_market_data_03_contracts",
    "tests.test_engine_orchestrator_01_closed_window_detector",
    "tests.test_engine_orchestrator_01_daemon_once_mode",
    "tests.test_engine_orchestrator_01_dedupe",
    "tests.test_engine_orchestrator_01_result_store",
    "tests.test_market_data_dependency_contract",
}


def classify(classname: str, message: str) -> tuple[str, str, str, str, str]:
    if classname in ENVIRONMENT_CLASSES or "DATABASE_URL is required" in message or "TEST_PG_URL is required" in message:
        return (
            "ENVIRONMENT_REQUIRED", "current PAPER/PostgreSQL contract", "current",
            "isolated PostgreSQL 16", "scripts/run_active_production_gate.ps1 provisions a non-superuser database",
        )
    if classname in DECOMMISSIONED_CLASSES:
        return (
            "DECOMMISSIONED_FEATURE", "trade-5m-v1 / Scalping v1 runtime", "removed-v1",
            "none", "trade-5m-v2 Set #2 coverage in tests/scalping_v2_* and integration/paper_natural_execution_e2e",
        )
    if classname in RESEARCH_CLASSES:
        return (
            "ACTIVE_RESEARCH_GATE", "research diagnostics/calibration", "research-only",
            "research fixtures", "separate active_research suite; never gates production execution",
        )
    if classname in LEGACY_CLASSES:
        return (
            "LEGACY_HISTORICAL_COMPATIBILITY", "trade-15m-v1 or historical foundation contract", "legacy-15m/v1",
            "historical fixtures", "current historical-read coverage plus stopped-writer runtime certification",
        )
    if classname in OBSOLETE_CLASSES:
        return (
            "OBSOLETE_REPLACED_TEST", "frozen count/default/migration contract superseded by current architecture", "superseded",
            "none", "current Alembic-head, readiness, route-policy and projection certification suites",
        )
    if classname == "tests.test_market_data_image_security_contract":
        return (
            "REAL_REGRESSION", "active source credential scanner", "current",
            "none", "fixed scanner false-positive fixtures and production binding-name collision; rerun required",
        )
    return (
        "REAL_REGRESSION", "active production contract", "current", "none",
        "must pass active production gate after code/test-contract repair",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("junit", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--baseline-total", type=int, default=546)
    args = parser.parse_args()
    root = ET.parse(args.junit).getroot()
    rows: list[dict[str, str]] = []
    for case in root.iter("testcase"):
        outcome = case.find("failure")
        if outcome is None:
            outcome = case.find("error")
        if outcome is None:
            continue
        classname = case.attrib.get("classname", "")
        message = outcome.attrib.get("message", "")
        classification, feature, era, environment, replacement = classify(classname, message)
        rows.append({
            "test_path": classname.replace(".", "/") + ".py",
            "test_name": case.attrib.get("name", ""),
            "outcome": outcome.tag.upper(),
            "feature_profile_targeted": feature,
            "schema_runtime_era": era,
            "production_relevance": "BLOCKING" if classification in {"ACTIVE_PRODUCTION_GATE", "REAL_REGRESSION", "ENVIRONMENT_REQUIRED"} else "SEPARATE_SUITE",
            "environment_dependency": environment,
            "replacement_test_if_any": replacement,
            "classification": classification,
            "failure_fingerprint": " ".join(message.split())[:500],
        })
    if len(rows) > args.baseline_total:
        raise SystemExit(f"fresh non-pass count {len(rows)} exceeds declared baseline {args.baseline_total}")
    if len(rows) < args.baseline_total:
        rows.append({
            "test_path": "[prior-baseline-artifact-unavailable]",
            "test_name": "aggregate_collection_delta",
            "outcome": "BASELINE_DELTA",
            "feature_profile_targeted": "prior full-server aggregate only",
            "schema_runtime_era": "pre-task",
            "production_relevance": "SEPARATE_SUITE",
            "environment_dependency": "none",
            "replacement_test_if_any": f"fresh JUnit {args.junit.as_posix()} proves {len(rows)} reproducible non-pass entries",
            "classification": "OBSOLETE_REPLACED_TEST",
            "failure_fingerprint": "Original aggregate reported 546 non-pass but retained no nodeid inventory; current collection totals differ, so no test identity is fabricated.",
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["classification"]] = counts.get(row["classification"], 0) + 1
    print(f"TOTAL={len(rows)} " + " ".join(f"{key}={counts[key]}" for key in sorted(counts)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
