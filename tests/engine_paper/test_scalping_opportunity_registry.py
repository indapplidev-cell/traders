import pytest

from app.engine_paper.scalping_opportunity_registry import ScalpingOpportunityRegistry


def test_repeat_boundary_cannot_readmit_same_opportunity_across_restart(tmp_path):
    path = tmp_path / "opportunities.json"
    identity = "opportunity:abc"
    first = ScalpingOpportunityRegistry(path).claim(identity)
    second = ScalpingOpportunityRegistry(path).claim(identity)
    assert first.admitted
    assert not second.admitted
    assert second.duplicate_block_reason == "CAUSAL_OPPORTUNITY_ALREADY_EXECUTED"
    assert second.observation_count == 2


def test_execution_and_structural_reset_provenance_are_durable(tmp_path):
    path = tmp_path / "opportunities.json"
    registry = ScalpingOpportunityRegistry(path)
    registry.claim("opportunity:parent")
    registry.record_execution("opportunity:parent", "position:1")
    assert registry.claim("opportunity:parent").prior_execution_position_id == "position:1"
    registry.structural_reset(
        "opportunity:parent", "opportunity:child",
        reason="STRUCTURE_INVALIDATED_AND_REFORMED", evidence="swing:101.25",
    )
    child = ScalpingOpportunityRegistry(path).claim("opportunity:child")
    assert child.admitted
    assert child.causal_parent_id == "opportunity:parent"
    assert child.reset_reason == "STRUCTURE_INVALIDATED_AND_REFORMED"
    assert child.reset_evidence == "swing:101.25"


def test_boundary_reentry_flag_is_rejected(tmp_path):
    registry = ScalpingOpportunityRegistry(tmp_path / "opportunities.json")
    with pytest.raises(ValueError, match="structural_reset"):
        registry.observe_and_claim("opportunity:abc", reentry_enabled=True)
