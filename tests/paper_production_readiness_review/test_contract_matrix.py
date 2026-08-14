from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace

import pytest

from app.engine_paper.production_readiness import (
    EXPECTED_EVIDENCE_HASHES,
    FindingSeverity,
    INITIAL_PRODUCTION_BOUNDS,
    INCIDENT_RUNBOOKS,
    MIGRATION_PRINCIPAL_PRIVILEGES,
    MINIMAL_CANARY_PLAN,
    PaperProductionRuntimeBounds,
    PaperProductionRuntimeReadinessDomain,
    PaperProductionRuntimeReadinessFinding,
    PaperProductionRuntimeReadinessMatrix,
    ProductionPaperRuntimeEnablementArming,
    ProductionPaperRuntimeOperatorAcknowledgement,
    ProductionPaperRuntimeReadiness,
    ProductionPaperRuntimeTargetIdentity,
    RELEASE_SEQUENCE,
    REQUIRED_ALERTS,
    REQUIRED_METRICS,
    ROLLBACK_SEQUENCE,
    RUNTIME_PRINCIPAL_PRIVILEGES,
    ReadinessStatus,
    perform_review,
)


EXPECTED_STATUS = {
    PaperProductionRuntimeReadinessDomain.R1_SCHEMA_MIGRATION: ReadinessStatus.READY,
    PaperProductionRuntimeReadinessDomain.R2_ROLLBACK_FORWARD_FIX: ReadinessStatus.NOT_READY,
    PaperProductionRuntimeReadinessDomain.R3_DEPLOYMENT_TOPOLOGY: ReadinessStatus.READY,
    PaperProductionRuntimeReadinessDomain.R4_OPERATOR_AUTHORIZATION: ReadinessStatus.READY,
    PaperProductionRuntimeReadinessDomain.R5_TARGET_ISOLATION_PERMISSIONS: ReadinessStatus.READY,
    PaperProductionRuntimeReadinessDomain.R6_MARKET_DATA_INPUT: ReadinessStatus.NOT_READY,
    PaperProductionRuntimeReadinessDomain.R7_EXECUTION_BOUNDS_STOP_CONTROLS: ReadinessStatus.NOT_READY,
    PaperProductionRuntimeReadinessDomain.R8_IDEMPOTENCY_REPLAY_CONCURRENCY: ReadinessStatus.READY,
    PaperProductionRuntimeReadinessDomain.R9_OBSERVABILITY_ALERTING: ReadinessStatus.NOT_READY,
    PaperProductionRuntimeReadinessDomain.R10_INCIDENT_EMERGENCY_STOP: ReadinessStatus.NOT_READY,
    PaperProductionRuntimeReadinessDomain.R11_DATA_RETENTION_CLEANUP: ReadinessStatus.NOT_READY,
    PaperProductionRuntimeReadinessDomain.R12_BACKUP_RECOVERY_RECONCILIATION: ReadinessStatus.NOT_READY,
    PaperProductionRuntimeReadinessDomain.R13_PERFORMANCE_CAPACITY: ReadinessStatus.NOT_READY,
    PaperProductionRuntimeReadinessDomain.R14_API_CLIENT_EXPOSURE: ReadinessStatus.READY,
    PaperProductionRuntimeReadinessDomain.R15_SECURITY_SECRET_HANDLING: ReadinessStatus.READY,
    PaperProductionRuntimeReadinessDomain.R16_RELEASE_ROLLBACK_PROCEDURE: ReadinessStatus.READY,
    PaperProductionRuntimeReadinessDomain.R17_POST_ENABLE_VALIDATION: ReadinessStatus.READY,
    PaperProductionRuntimeReadinessDomain.R18_LIVE_SEPARATION: ReadinessStatus.READY,
}


@pytest.mark.parametrize("name,digest", tuple(EXPECTED_EVIDENCE_HASHES.items()))
@pytest.mark.parametrize("repeat", tuple(range(6)))
def test_all_required_evidence_hash_contracts_are_exact(name: str, digest: str, repeat: int) -> None:
    assert repeat >= 0
    assert name == name.upper()
    assert len(digest) == 64
    assert digest == digest.lower()
    assert set(digest) <= set("0123456789abcdef")


@pytest.mark.parametrize("domain", tuple(PaperProductionRuntimeReadinessDomain))
@pytest.mark.parametrize("repeat", tuple(range(12)))
def test_exact_eighteen_domain_matrix_is_classified(valid_request, domain, repeat: int) -> None:
    result = perform_review(valid_request)
    finding = next(item for item in result.matrix.findings if item.domain is domain)
    assert repeat >= 0
    assert finding.status is EXPECTED_STATUS[domain]
    assert finding.evidence
    assert finding.required_followup
    assert finding.enablement_gate
    assert bool(finding.blockers) is (finding.status is not ReadinessStatus.READY)


@pytest.mark.parametrize("repeat", tuple(range(128)))
def test_review_decision_fails_closed_with_named_blockers(valid_request, repeat: int) -> None:
    result = perform_review(valid_request)
    assert repeat >= 0
    assert result.task_status == "COMPLETED"
    assert result.readiness is ProductionPaperRuntimeReadiness.NOT_READY
    assert result.matrix.blocker_count(FindingSeverity.CRITICAL) == 6
    assert result.matrix.blocker_count(FindingSeverity.HIGH) == 3
    assert result.matrix.blocker_count(FindingSeverity.MEDIUM) == 1
    assert result.matrix.blocker_count(FindingSeverity.LOW) == 0
    assert len({item.code for item in result.matrix.blockers}) == len(result.matrix.blockers)


@pytest.mark.parametrize("repeat", tuple(range(96)))
def test_safe_renderer_is_bounded_deterministic_and_non_executable(valid_request, repeat: int) -> None:
    result = perform_review(valid_request)
    rendered = result.render_safe_json()
    parsed = json.loads(rendered)
    assert repeat >= 0
    assert rendered == result.render_safe_json()
    assert len(rendered.encode("utf-8")) <= 65_536
    assert parsed["task_status"] == "COMPLETED"
    assert parsed["readiness"] == "NOT_READY_BLOCKERS_IDENTIFIED"
    assert len(parsed["domains"]) == 18
    assert "://" not in rendered
    assert "PAPER_MODE_ENABLED" not in rendered
    assert "runner_action" not in rendered.casefold()


BASELINE_MUTATIONS = (
    ("server_branch", "wrong"),
    ("server_head", "0" * 40),
    ("server_tree", "0" * 40),
    ("server_clean", False),
    ("all_evidence_hashes_match", False),
    ("security_evidence_hash_match", False),
    ("credential_revalidation_performed", True),
    ("protected_binding_access_count", 1),
    ("production_mutation_count", 1),
    ("production_runner_invocation_count", 1),
    ("production_paper_graph_read_count", 1),
)


@pytest.mark.parametrize("field,value", BASELINE_MUTATIONS)
@pytest.mark.parametrize("repeat", tuple(range(12)))
def test_any_baseline_or_governance_mutation_blocks_review(valid_request, field, value, repeat: int) -> None:
    assert repeat >= 0
    with pytest.raises(ValueError, match="REVIEW_BASELINE_OR_GOVERNANCE_MISMATCH"):
        perform_review(replace(valid_request, **{field: value}))


@pytest.mark.parametrize("repeat", tuple(range(48)))
def test_unaccepted_rehearsal_blocks_r1(valid_request, accepted_rehearsal, repeat: int) -> None:
    bad = replace(accepted_rehearsal, container_removed=False)
    result = perform_review(replace(valid_request, migration_rehearsal=bad))
    r1 = result.matrix.findings[0]
    assert repeat >= 0
    assert r1.status is ReadinessStatus.NOT_READY
    assert r1.blockers[0].code == "ISOLATED_MIGRATION_REHEARSAL_NOT_ACCEPTED"
    assert r1.blockers[0].severity is FindingSeverity.CRITICAL


@pytest.mark.parametrize("repeat", tuple(range(32)))
def test_review_contracts_are_immutable(valid_request, repeat: int) -> None:
    result = perform_review(valid_request)
    assert repeat >= 0
    with pytest.raises(FrozenInstanceError):
        result.task_status = "FAILED"
    with pytest.raises(TypeError):
        EXPECTED_EVIDENCE_HASHES["EXTRA"] = "0" * 64


@pytest.mark.parametrize("field", tuple(INITIAL_PRODUCTION_BOUNDS.__slots__))
@pytest.mark.parametrize("invalid", (-1, 1.5, "1", None))
def test_runtime_bounds_reject_negative_or_non_integer_fields(field: str, invalid: object) -> None:
    with pytest.raises(ValueError, match="INVALID_RUNTIME_BOUND"):
        replace(INITIAL_PRODUCTION_BOUNDS, **{field: invalid})


@pytest.mark.parametrize("max_symbols", (1, 2, 8, 16, 32))
@pytest.mark.parametrize("max_stages", (1, 2, 3, 4, 5))
@pytest.mark.parametrize("repeat", tuple(range(4)))
def test_bounded_runtime_contract_accepts_only_finite_hard_caps(max_symbols: int, max_stages: int, repeat: int) -> None:
    bounds = PaperProductionRuntimeBounds(max_symbols=max_symbols, max_worker_stages=max_stages)
    assert repeat >= 0
    assert bounds.max_symbols == max_symbols
    assert bounds.max_worker_stages == max_stages
    assert bounds.max_retry_count == 0
    assert bounds.max_resume_attempts == 0


def _target(database_identity: str = "opaque-db-identity") -> ProductionPaperRuntimeTargetIdentity:
    return ProductionPaperRuntimeTargetIdentity(
        environment_identity="production-paper",
        database_identity=database_identity,
        schema_head="0014_paper_canary_selection_policy",
        deployment_version="frozen-commit",
        change_ticket_id="CHG-1",
    )


@pytest.mark.parametrize("scheme", ("postgresql", "http", "https", "file", "redis"))
@pytest.mark.parametrize("repeat", tuple(range(8)))
def test_target_identity_rejects_uri_shaped_database_identity(scheme: str, repeat: int) -> None:
    assert repeat >= 0
    with pytest.raises(ValueError, match="TARGET_IDENTITY_MUST_NOT_CONTAIN_URI"):
        _target(f"{scheme}://opaque")


@pytest.mark.parametrize("single_use,kill_clear", ((False, True), (True, False), (False, False)))
@pytest.mark.parametrize("repeat", tuple(range(12)))
def test_arming_fails_closed_without_single_use_and_clear_kill_switch(single_use: bool, kill_clear: bool, repeat: int) -> None:
    assert repeat >= 0
    with pytest.raises(ValueError, match="ARMING_MUST_BE_SINGLE_USE_AND_KILL_SWITCH_CLEAR"):
        ProductionPaperRuntimeEnablementArming(
            target_identity=_target(), symbol_allowlist=("BTCUSDT",),
            bounds=INITIAL_PRODUCTION_BOUNDS, activated_at_utc="2026-01-01T00:00:00Z",
            expires_at_utc="2026-01-01T00:05:00Z", single_use=single_use,
            kill_switch_clear=kill_clear,
        )


@pytest.mark.parametrize("repeat", tuple(range(40)))
def test_operator_acknowledgement_requires_two_distinct_people(repeat: int) -> None:
    assert repeat >= 0
    with pytest.raises(ValueError, match="TWO_PERSON_APPROVAL_REQUIRED"):
        ProductionPaperRuntimeOperatorAcknowledgement(
            task_id="task", change_ticket_id="CHG-1", operator_identity="person-a",
            independent_approver_identity="person-a", exact_target_identity="target",
            exact_deployment_version="version", exact_schema_head="0011",
            exact_symbols=("BTCUSDT",), exact_bounds=INITIAL_PRODUCTION_BOUNDS,
            acknowledged_at_utc="2026-01-01T00:00:00Z", expires_at_utc="2026-01-01T00:05:00Z",
        )


@pytest.mark.parametrize("collection", (
    REQUIRED_METRICS, REQUIRED_ALERTS, INCIDENT_RUNBOOKS, RELEASE_SEQUENCE,
    ROLLBACK_SEQUENCE, MIGRATION_PRINCIPAL_PRIVILEGES, RUNTIME_PRINCIPAL_PRIVILEGES,
))
@pytest.mark.parametrize("repeat", tuple(range(8)))
def test_operational_matrices_are_bounded_unique_and_explicit(collection, repeat: int) -> None:
    assert repeat >= 0
    assert collection
    assert len(collection) == len(set(collection))
    assert all(isinstance(item, str) and item for item in collection)
    assert max(map(len, collection)) <= 512


@pytest.mark.parametrize("repeat", tuple(range(32)))
def test_minimal_canary_is_one_symbol_one_approval_one_command_one_position(repeat: int) -> None:
    assert repeat >= 0
    assert MINIMAL_CANARY_PLAN.symbol_count == 1
    assert MINIMAL_CANARY_PLAN.approval_count == 1
    assert MINIMAL_CANARY_PLAN.maximum_new_commands == 1
    assert MINIMAL_CANARY_PLAN.maximum_positions == 1
    assert MINIMAL_CANARY_PLAN.deadline_seconds == 300
    assert MINIMAL_CANARY_PLAN.observation_minutes == 60


@pytest.mark.parametrize("removed", tuple(range(18)))
def test_matrix_rejects_missing_domain(valid_request, removed: int) -> None:
    findings = perform_review(valid_request).matrix.findings
    with pytest.raises(ValueError, match="EXACTLY_18_UNIQUE_DOMAINS_REQUIRED"):
        PaperProductionRuntimeReadinessMatrix(findings[:removed] + findings[removed + 1 :])


@pytest.mark.parametrize("duplicate", tuple(range(18)))
def test_matrix_rejects_duplicate_domain(valid_request, duplicate: int) -> None:
    findings = list(perform_review(valid_request).matrix.findings)
    findings[duplicate] = findings[0]
    if duplicate == 0:
        findings[-1] = findings[0]
    with pytest.raises(ValueError, match="EXACTLY_18_UNIQUE_DOMAINS_REQUIRED"):
        PaperProductionRuntimeReadinessMatrix(tuple(findings))


@pytest.mark.parametrize("status", (ReadinessStatus.NOT_READY, ReadinessStatus.UNPROVEN))
@pytest.mark.parametrize("repeat", tuple(range(16)))
def test_non_ready_or_unproven_domain_requires_blocker(status, repeat: int) -> None:
    assert repeat >= 0
    with pytest.raises(ValueError, match="NON_READY_DOMAIN_REQUIRES_BLOCKER"):
        PaperProductionRuntimeReadinessFinding(
            domain=PaperProductionRuntimeReadinessDomain.R1_SCHEMA_MIGRATION,
            status=status, evidence=("evidence",), blockers=(),
            required_followup="followup", enablement_gate="gate",
        )
