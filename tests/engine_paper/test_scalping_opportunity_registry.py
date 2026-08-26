from app.engine_paper.scalping_opportunity_registry import ScalpingOpportunityRegistry


def test_repeat_observation_is_counted_but_not_readmitted_without_reentry_policy():
    registry = ScalpingOpportunityRegistry()
    identity = "opportunity:abc"
    assert registry.observe_and_claim(identity)
    assert not registry.observe_and_claim(identity)
    assert registry.observation_count(identity) == 2


def test_explicit_reentry_policy_can_readmit_the_same_causal_identity():
    registry = ScalpingOpportunityRegistry()
    identity = "opportunity:abc"
    assert registry.observe_and_claim(identity)
    assert registry.observe_and_claim(identity, reentry_enabled=True)
