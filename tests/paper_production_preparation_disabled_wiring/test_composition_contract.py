from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace

import pytest

from app.engine_paper.production_approval import PaperProductionApprovalReadiness
from app.engine_paper.production_composition import (
    EXPECTED_SCHEMA_BASE,
    EXPECTED_SCHEMA_HEAD,
    MINIMUM_PITR_WINDOW_SECONDS,
    REQUIRED_SOURCE_EVIDENCE_HASHES,
    PaperProductionComposition,
    PaperProductionGateStatus,
    PaperProductionMutationDecision,
    PaperProductionPreparationGate,
    PaperProductionPreparationReadiness,
)
from app.engine_paper.production_market_data import PaperProductionMarketDataReadiness
from app.engine_safety.paper_production_control import PersistentState


@pytest.mark.parametrize("repeat", range(160))
def test_current_production_snapshot_is_expected_successful_fail_closed_proof(current_request, repeat):
    snapshot = PaperProductionComposition.evaluate(current_request)
    by_gate = {item.gate: item for item in snapshot.findings}
    assert repeat >= 0
    assert snapshot.preparation_readiness is PaperProductionPreparationReadiness.READY_FOR_CONTROLLED_PRODUCTION_PREPARATION
    assert snapshot.mutation_authorization.decision is PaperProductionMutationDecision.DENIED_FAIL_CLOSED
    assert snapshot.mutation_authorization.denial_reasons == (
        "SCHEMA_0008", "PITR_BELOW_24H", "PAPER_RUNTIME_DISABLED", "CONTROL_STATE_DISABLED"
    )
    assert snapshot.production_mutations == snapshot.paper_table_reads == 0
    assert snapshot.reconciliation_precondition == "PAPER_SCHEMA_NOT_DEPLOYED"
    assert by_gate[PaperProductionPreparationGate.MARKET_DATA].status is PaperProductionGateStatus.PASS
    assert by_gate[PaperProductionPreparationGate.APPROVAL_BOUNDARY].status is PaperProductionGateStatus.PASS
    assert by_gate[PaperProductionPreparationGate.WAL].status is PaperProductionGateStatus.PASS
    assert by_gate[PaperProductionPreparationGate.LIVE_DENIAL].status is PaperProductionGateStatus.PASS


@pytest.mark.parametrize("repeat", range(120))
def test_isolated_future_ready_dry_run_can_issue_only_one_stage_authorization(future_request, repeat):
    snapshot = PaperProductionComposition.evaluate(future_request)
    assert repeat >= 0
    assert snapshot.mutation_authorization.decision is PaperProductionMutationDecision.AUTHORIZED_ONE_ATOMIC_STAGE
    assert snapshot.mutation_authorization.authorized_stage_count == 1
    assert snapshot.mutation_authorization.denial_reasons == ()
    assert snapshot.production_mutations == 0


SCHEMA_CASES = (
    (EXPECTED_SCHEMA_BASE, PaperProductionGateStatus.FAIL, "SCHEMA_0008"),
    ("0009_paper_trading_persistence_foundation", PaperProductionGateStatus.FAIL, "SCHEMA_PARTIAL_FAIL_CLOSED"),
    ("0010_paper_final_approval_and_order_transition_event_vocabulary", PaperProductionGateStatus.FAIL, "SCHEMA_PARTIAL_FAIL_CLOSED"),
    (EXPECTED_SCHEMA_HEAD, PaperProductionGateStatus.PASS, "SCHEMA_0011"),
    ("0012_unknown", PaperProductionGateStatus.FAIL, "SCHEMA_UNEXPECTED_COMPATIBILITY_REVIEW_REQUIRED"),
    ("garbage", PaperProductionGateStatus.FAIL, "SCHEMA_UNEXPECTED_COMPATIBILITY_REVIEW_REQUIRED"),
)


@pytest.mark.parametrize("revision,status,code", SCHEMA_CASES)
@pytest.mark.parametrize("repeat", range(24))
def test_schema_gate_is_exact_lineage_fail_closed(current_request, revision, status, code, repeat):
    snapshot = PaperProductionComposition.evaluate(replace(current_request, schema_revision=revision))
    finding = next(item for item in snapshot.findings if item.gate is PaperProductionPreparationGate.SCHEMA)
    assert repeat >= 0
    assert (finding.status, finding.code) == (status, code)


@pytest.mark.parametrize("seconds,passed", ((0, False), (22_272, False), (86_399, False), (86_400, True), (90_000, True)))
@pytest.mark.parametrize("repeat", range(24))
def test_pitr_gate_has_exact_24_hour_threshold(current_request, seconds, passed, repeat):
    snapshot = PaperProductionComposition.evaluate(replace(current_request, pitr_window_seconds=seconds))
    finding = next(item for item in snapshot.findings if item.gate is PaperProductionPreparationGate.PITR)
    assert repeat >= 0
    assert (finding.status is PaperProductionGateStatus.PASS) is passed
    assert MINIMUM_PITR_WINDOW_SECONDS == 86_400


@pytest.mark.parametrize("health,failures,chain,passed", (
    (True, 0, True, True), (False, 0, True, False), (True, 1, True, False),
    (True, 0, False, False), (False, 1, False, False),
))
@pytest.mark.parametrize("repeat", range(24))
def test_wal_gate_is_three_way_conjunction(current_request, health, failures, chain, passed, repeat):
    snapshot = PaperProductionComposition.evaluate(replace(
        current_request, wal_archive_health_pass=health,
        wal_unresolved_failures=failures, pitr_chain_valid=chain,
    ))
    finding = next(item for item in snapshot.findings if item.gate is PaperProductionPreparationGate.WAL)
    assert repeat >= 0
    assert (finding.status is PaperProductionGateStatus.PASS) is passed


@pytest.mark.parametrize("readiness,passed", tuple(
    (value, value is PaperProductionMarketDataReadiness.READY)
    for value in PaperProductionMarketDataReadiness
))
@pytest.mark.parametrize("repeat", range(32))
def test_market_data_boundary_gate_preserves_adapter_readiness(current_request, readiness, passed, repeat):
    snapshot = PaperProductionComposition.evaluate(replace(current_request, market_data_readiness=readiness))
    finding = next(item for item in snapshot.findings if item.gate is PaperProductionPreparationGate.MARKET_DATA)
    assert repeat >= 0
    assert (finding.status is PaperProductionGateStatus.PASS) is passed


@pytest.mark.parametrize("readiness,passed", tuple(
    (value, value in {PaperProductionApprovalReadiness.READY,
                      PaperProductionApprovalReadiness.HEALTHY_NO_ELIGIBLE_APPROVAL})
    for value in PaperProductionApprovalReadiness
))
@pytest.mark.parametrize("repeat", range(32))
def test_no_eligible_approval_is_healthy_boundary_but_zero_mutation(current_request, readiness, passed, repeat):
    snapshot = PaperProductionComposition.evaluate(replace(current_request, approval_boundary_readiness=readiness))
    finding = next(item for item in snapshot.findings if item.gate is PaperProductionPreparationGate.APPROVAL_BOUNDARY)
    assert repeat >= 0
    assert (finding.status is PaperProductionGateStatus.PASS) is passed
    assert snapshot.production_mutations == 0


BASELINE_SECURITY_MUTATIONS = (
    ("server_branch", "wrong"), ("server_head", "0" * 40),
    ("server_tree", "0" * 40), ("server_clean", False),
    ("source_evidence_hashes", (("WRONG", "0" * 64),)),
    ("protected_binding_open_count", 1), ("protected_binding_read_count", 1),
    ("protected_binding_hash_count", 1), ("protected_binding_fingerprint_count", 1),
    ("secret_derived_output_count", 1), ("production_mutation_count", 1),
    ("production_paper_table_read_count", 1),
)


@pytest.mark.parametrize("field,value", BASELINE_SECURITY_MUTATIONS)
@pytest.mark.parametrize("repeat", range(16))
def test_any_baseline_security_or_production_mutation_violation_is_safe_failure(current_request, field, value, repeat):
    result = PaperProductionComposition.evaluate(replace(current_request, **{field: value}))
    assert repeat >= 0
    assert result.preparation_readiness is PaperProductionPreparationReadiness.SAFE_FAILURE
    assert result.mutation_authorization.decision is PaperProductionMutationDecision.DENIED_FAIL_CLOSED


@pytest.mark.parametrize("repeat", range(96))
def test_snapshot_is_immutable_bounded_deterministic_and_secret_free(current_request, repeat):
    snapshot = PaperProductionComposition.evaluate(current_request)
    rendered = snapshot.safe_json()
    assert repeat >= 0
    assert rendered == snapshot.safe_json()
    assert len(rendered) < 16_384
    assert "://" not in rendered
    assert "password" not in rendered.casefold()
    assert json.loads(rendered)["production_mutations"] == 0
    with pytest.raises(FrozenInstanceError):
        snapshot.production_mutations = 1


@pytest.mark.parametrize("name,digest", tuple(REQUIRED_SOURCE_EVIDENCE_HASHES.items()))
@pytest.mark.parametrize("repeat", range(32))
def test_required_source_evidence_hashes_are_exact_immutable_contract(name, digest, repeat):
    assert repeat >= 0
    assert name == name.upper()
    assert len(digest) == 64 and digest == digest.lower()
    assert set(digest) <= set("0123456789abcdef")
    with pytest.raises(TypeError):
        REQUIRED_SOURCE_EVIDENCE_HASHES[name] = "0" * 64

