import copy
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
import yaml

from app.config.trade_parameters import load_trade_parameters
from traders_ml.parameter_sweep.finding_verifier import FindingVerifier,export_configuration,load_export,validate_result
from traders_ml.parameter_sweep.frozen_funnel import resolve_frozen_configuration
from traders_ml.parameter_sweep.result_search import ENGINE_VERSION
from traders_ml.parameter_sweep.search_history import HistoryProvider


@pytest.fixture
def setup(tmp_path,monkeypatch):
    frozen=json.loads(Path('tests/research/fixtures/result_search_applicability.json').read_text())['cost']['frozen']
    dataset='a'*64
    monkeypatch.setattr(HistoryProvider,'load',lambda p:({'fingerprint':dataset},[{'kind':'PERSISTED_BOUNDARY','frozen':frozen}]))
    request=SimpleNamespace(initial_capital=100,data_mode='HISTORICAL_VERIFIED',target_config_count=1,
        scope='SINGLE_SYMBOL',symbols=('BTCUSDT',),baseline_hash='b'*64)
    config=resolve_frozen_configuration(frozen,{}).resolved_config_hash
    def trade(identity,net):
        return {'identity':identity,'symbol':'BTCUSDT','entry_boundary':100,'exit_boundary':200,
            'exit_observed_closed_ms':260,'exit_cause':'TAKE_PROFIT' if net>0 else 'STOP_LOSS',
            'gross_pnl':str(net+2),'entry_fee':'1','exit_fee':'1','net_pnl':str(net),
            'trace':[{'event':'CAUSAL_ADMISSION','decision_boundary':100,'dataset_fingerprint':dataset,'configuration_fingerprint':config}]}
    result={'engine':ENGINE_VERSION,'dataset_fingerprint':dataset,'configuration_fingerprint':config,
        'quality':'HISTORICAL_VERIFIED','execution_assumptions':None,'result':'SIMULATED','blockers':[],
        'open_positions':[],'closed_trades':[trade('winning',5),trade('losing',-8)],'net_pnl':'-3'}
    verifier=FindingVerifier(tmp_path,tmp_path/'dataset',request,replay=lambda overrides:copy.deepcopy(result))
    record={'number':0,'proposal':{},'result':result}
    return verifier,record,frozen


def test_export_loader_exact_hash_and_frozen_values(setup,tmp_path):
    verifier,record,frozen=setup
    path=tmp_path/'candidate.yaml'
    path.write_text(yaml.safe_dump(export_configuration(frozen,{'geometry.minimum_planned_rr':1.2})))
    loaded=load_export(path,frozen)
    assert loaded==resolve_frozen_configuration(frozen,{'geometry.minimum_planned_rr':1.2})
    native=load_trade_parameters(path)
    assert native.resolve_scalping_v2_parameter_set(frozen_source_authority_hash=frozen['resolved_config_hash']).resolved_config_hash==loaded.resolved_config_hash
    assert native.resolve_scalping_v2_parameter_set().resolved_config_hash!=loaded.resolved_config_hash


def test_one_win_exports_while_period_loss_remains_visible(setup):
    verifier,record,_=setup
    assert verifier.accept(record)
    entry=verifier.published()[0]
    assert entry['net_pnl']=='-3' and entry['wins']==entry['losses']==1
    assert 'period net PnL -3' in (verifier.directory/'REPORT.md').read_text()
    assert len((verifier.directory/'WINNING_TRADES.jsonl').read_text().splitlines())==1


def test_crash_before_publication_replays_persisted_candidate(setup):
    verifier,record,_=setup
    original=verifier.replay
    verifier.replay=lambda p:(_ for _ in ()).throw(RuntimeError('crash'))
    with pytest.raises(RuntimeError,match='crash'):verifier.accept(record)
    assert list(verifier.directory.glob('candidate_*.json')) and not verifier.published()
    verifier.replay=original
    assert verifier.accept(record) and len(verifier.published())==1


def test_invalid_evidence_and_replay_mismatch_never_publish(setup):
    verifier,record,_=setup
    bad=copy.deepcopy(record);bad['result']['closed_trades'][0]['net_pnl']='99'
    assert not verifier.accept(bad) and not verifier.published()
    verifier.replay=lambda p:copy.deepcopy(record['result'])|{'events':['different']}
    with pytest.raises(ValueError,match='REPLAY_RESULT_MISMATCH'):verifier.accept(record)
    assert not verifier.published()


def test_cancel_preserves_candidate_and_previously_published_result(setup):
    verifier,record,_=setup
    verifier.should_stop=lambda:True
    assert not verifier.accept(record) and not verifier.published()
    assert list(verifier.directory.glob('candidate_*.json'))
    verifier.should_stop=lambda:False
    assert verifier.accept(record)
    verifier.should_stop=lambda:True
    assert verifier.accept(record) and len(verifier.report())==1


def test_numeric_configuration_duplicate_is_not_second_finding(setup):
    verifier,record,frozen=setup
    verifier.request.target_config_count=2
    assert not verifier.accept(record)
    second=copy.deepcopy(record)
    second['proposal']={'signal.strategy_minimum_score':56}
    key=resolve_frozen_configuration(frozen,second['proposal']).resolved_config_hash
    second['result']['configuration_fingerprint']=key
    for trade in second['result']['closed_trades']:trade['trace'][0]['configuration_fingerprint']=key
    assert not verifier.accept(second) and len(verifier.published())==1


def test_target_two_requires_two_distinct_trade_paths(setup):
    verifier,record,frozen=setup
    verifier.request.target_config_count=2
    assert not verifier.accept(record)
    second=copy.deepcopy(record)
    second['proposal']={'signal.strategy_minimum_score':56}
    key=resolve_frozen_configuration(frozen,second['proposal']).resolved_config_hash
    second['result']['configuration_fingerprint']=key
    for trade in second['result']['closed_trades']:
        trade['trace'][0]['configuration_fingerprint']=key
        trade['exit_boundary']+=100
        trade['exit_observed_closed_ms']+=100
    verifier.replay=lambda p:copy.deepcopy(second['result'])
    assert verifier.accept(second) and len(verifier.published())==2


def test_future_admission_and_changed_published_yaml_rejected(setup):
    verifier,record,_=setup
    bad=copy.deepcopy(record)
    bad['result']['closed_trades'][0]['trace'][0]['decision_boundary']=101
    assert not verifier.accept(bad)
    assert verifier.accept(record)
    path=next(verifier.directory.glob('candidate_*.yaml'))
    path.write_text(path.read_text()+'\n# changed\n')
    with pytest.raises(ValueError,match='CHECKSUM'):verifier.published()


def test_storage_budget_prevents_publishing(setup):
    from traders_ml.parameter_sweep.result_search import ResearchStorageBudgetExceeded
    verifier,record,_=setup
    verifier.request.storage_budget_bytes=4096
    with pytest.raises(ResearchStorageBudgetExceeded):verifier.accept(record)
    assert not verifier.published()
