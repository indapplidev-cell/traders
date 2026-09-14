import copy
import json
from pathlib import Path

from traders_ml.parameter_sweep.search_parameters import generate_space, SPECS
from traders_ml.parameter_sweep.search_history import HistoryProvider


def test_domains_use_only_search_partition_and_causal_snapshots(monkeypatch):
    fixture=json.loads(Path('tests/research/fixtures/result_search_applicability.json').read_text())
    frozen=fixture['cost']['frozen']
    row={'kind':'PERSISTED_BOUNDARY','closed_until_ms':100,'frozen':frozen,
         'risk':{'created_at_ms':100,'source_strategy_score':30},'geometry':None}
    future=copy.deepcopy(row)
    future['risk']={'created_at_ms':9999,'source_strategy_score':100}
    candle={'kind':'CANDLE','timeframe':'5m','open':100,'close':101,'high':102,'low':99}
    rows=[row,candle]
    manifest={'fingerprint':'a'*64,'intervals':{'search_start_ms':0,'search_end_ms':1000}}
    monkeypatch.setattr(HistoryProvider,'load',lambda p:(manifest,[{'kind':'FORBIDDEN_TAIL'}]))
    def partition(p,name):
        assert name=='search'
        return rows
    monkeypatch.setattr(HistoryProvider,'partition',partition)
    before=generate_space(Path('.'))
    rows.append(future)
    after=generate_space(Path('.'))
    assert before==after
    assert len({s.family for s in SPECS})==5
    assert all(frozen['parameters'][k] in v for k,v in before['domains'].items())
    assert all(isinstance(v,int) for v in before['domains']['signal.regime_lookback_candles'])
    assert not before['independent_data_used'] and not before['exit_tail_used']
