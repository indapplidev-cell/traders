from pathlib import Path
from traders_ml.parameter_sweep.opportunity_registry import ResearchOpportunityRegistry


def test_registry_retains_production_rules_without_filesystem_io(monkeypatch,tmp_path):
    monkeypatch.setenv("TRADERS_SCALPING_OPPORTUNITY_REGISTRY_PATH",str(tmp_path/"production.json"))
    def forbidden(*args,**kwargs):
        raise AssertionError("research accessed production registry filesystem")
    monkeypatch.setattr(Path,"read_text",forbidden)
    monkeypatch.setattr(Path,"write_text",forbidden)
    a=ResearchOpportunityRegistry(); b=ResearchOpportunityRegistry()
    identity="opportunity:BTCUSDT:causal-test"
    assert a.claim(identity).admitted
    assert not a.claim(identity).admitted
    assert b.claim(identity).admitted
    a.bind_plan(identity,"test-plan")
    a.record_execution(identity,"test-position")
    assert a.claim(identity).prior_execution_position_id=="test-position"
    assert b.claim(identity).prior_execution_position_id is None
