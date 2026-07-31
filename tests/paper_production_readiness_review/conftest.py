from __future__ import annotations

import pytest

from app.engine_paper.production_readiness import (
    EXPECTED_SCHEMA_BASE,
    EXPECTED_SCHEMA_HEAD,
    PaperProductionMigrationRehearsalResult,
    PaperProductionRuntimeReadinessReviewRequest,
)


@pytest.fixture
def accepted_rehearsal() -> PaperProductionMigrationRehearsalResult:
    return PaperProductionMigrationRehearsalResult(
        passed=True,
        start_revision=EXPECTED_SCHEMA_BASE,
        final_revision=EXPECTED_SCHEMA_HEAD,
        duration_ms=1,
        maximum_lock_wait_ms=0,
        unexpected_destructive_ddl=0,
        compatibility_checks_passed=True,
        paper_smoke_passed=True,
        open_connections_before_cleanup=0,
        idle_transactions_before_cleanup=0,
        lock_waits_before_cleanup=0,
        container_removed=True,
        artifacts_cleaned=True,
    )


@pytest.fixture
def valid_request(accepted_rehearsal):
    return PaperProductionRuntimeReadinessReviewRequest(
        server_branch="feature/engine-platform",
        server_head="0988984b9d37ab22e811ba106ae19c068d374438",
        server_tree="d423e5ce44c19245ed8161a9e0505c4090103057",
        server_clean=True,
        all_evidence_hashes_match=True,
        security_evidence_hash_match=True,
        credential_revalidation_performed=False,
        protected_binding_access_count=0,
        production_mutation_count=0,
        production_runner_invocation_count=0,
        production_paper_graph_read_count=0,
        migration_rehearsal=accepted_rehearsal,
    )
