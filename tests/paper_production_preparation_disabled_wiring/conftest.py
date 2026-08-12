from __future__ import annotations

from dataclasses import replace

import pytest

from app.engine_paper.production_approval import (
    PaperProductionApprovalReadiness,
    PaperProductionApprovalSourceAdapter,
)
from app.engine_paper.production_composition import (
    EXPECTED_SERVER_BRANCH,
    EXPECTED_SERVER_HEAD,
    EXPECTED_SERVER_TREE,
    EXPECTED_SCHEMA_BASE,
    REQUIRED_SOURCE_EVIDENCE_HASHES,
    PaperProductionComposition,
    PaperProductionPreparationRequest,
)
from app.engine_paper.production_market_data import (
    PaperProductionMarketDataInputAdapter,
    PaperProductionMarketDataReadiness,
)
from app.engine_safety.paper_production_control import (
    PaperProductionMutationSafetyGate,
    PersistentState,
)


@pytest.fixture
def current_request() -> PaperProductionPreparationRequest:
    return PaperProductionPreparationRequest(
        server_branch=EXPECTED_SERVER_BRANCH,
        server_head=EXPECTED_SERVER_HEAD,
        server_tree=EXPECTED_SERVER_TREE,
        server_clean=True,
        source_evidence_hashes=tuple(REQUIRED_SOURCE_EVIDENCE_HASHES.items()),
        protected_binding_open_count=0,
        protected_binding_read_count=0,
        protected_binding_hash_count=0,
        protected_binding_fingerprint_count=0,
        secret_derived_output_count=0,
        production_mutation_count=0,
        production_paper_table_read_count=0,
        schema_revision=EXPECTED_SCHEMA_BASE,
        pitr_window_seconds=22_272,
        wal_archive_health_pass=True,
        wal_unresolved_failures=0,
        pitr_chain_valid=True,
        market_data_readiness=PaperProductionMarketDataReadiness.READY,
        approval_boundary_readiness=PaperProductionApprovalReadiness.HEALTHY_NO_ELIGIBLE_APPROVAL,
        eligible_approval_count=0,
        paper_principal_ready=False,
        runtime_config_ready=True,
        runtime_enabled=False,
        kill_switch_health_pass=True,
        kill_switch_state=PersistentState.DISABLED,
        live_enabled=False,
    )


@pytest.fixture
def future_request(current_request):
    return replace(
        current_request,
        schema_revision="0013_paper_first_canary_correlation",
        pitr_window_seconds=86_400,
        approval_boundary_readiness=PaperProductionApprovalReadiness.READY,
        eligible_approval_count=1,
        paper_principal_ready=True,
        runtime_enabled=True,
        kill_switch_state=PersistentState.ARMED,
    )


@pytest.fixture
def composition():
    return PaperProductionComposition(
        PaperProductionMarketDataInputAdapter(lambda: None),
        PaperProductionApprovalSourceAdapter(lambda: None),
        PaperProductionMutationSafetyGate(object()),
    )

