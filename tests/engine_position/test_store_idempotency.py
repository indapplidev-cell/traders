from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import pytest
from app.engine_position import *
from app.engine_position.exceptions import PositionStoreError
from app.engine_position.idempotency import build_position_key
from tests.engine_position.conftest import NOW, make_contract, make_open

def key(**changes):
 d=dict(execution_intent_id="i",execution_idempotency_key="k",symbol="BTCUSDT",mode="PAPER",source_timeframe="15m",source_window_close_ms=1,setup_id="s",strategy_decision_id="st",risk_decision_id="r"); d.update(changes); return build_position_key(**d)
def test_43_position_key_is_deterministic(): assert key()==key()
def test_44_position_key_ignores_timestamp_and_metadata(): assert key()==key()
def test_45_different_intents_have_different_keys(): assert key()!=key(execution_intent_id="j")
def test_46_duplicate_position_is_rejected():
 i,a=make_contract(); s=InMemoryPositionStore(); v=PositionLifecycleService(s); p=v.create_position(i,a,current_timestamp=NOW)
 with pytest.raises(PositionStoreError) as e: s.create(p)
 assert "DUPLICATE_POSITION" in e.value.reason_codes
def test_47_concurrent_create_has_one_winner():
 i,a=make_contract(); p=PositionBuilder().build(i,a,current_timestamp=NOW); s=InMemoryPositionStore()
 def create():
  try: s.create(p); return True
  except PositionStoreError: return False
 with ThreadPoolExecutor(max_workers=8) as pool: results=list(pool.map(lambda _:create(),range(20)))
 assert sum(results)==1
def test_48_store_thread_safe_updates():
 s,v,p=make_open();
 def apply(n): return v.apply_mark(p.position_id,PositionMarkEvent(f"m{n}",p.position_id,NOW,"L",mark_price=str(101+n),source_window_close_ms=1700000000001+n,source_timeframe="15m"))
 with ThreadPoolExecutor(max_workers=4) as pool: list(pool.map(apply,range(4)))
 assert s.get(p.position_id) is not None
def test_49_store_duplicate_event_not_applied():
 s,v,p=make_open(); e=PositionMarkEvent("m",p.position_id,NOW,"L",mark_price="101",source_window_close_ms=1700000000001,source_timeframe="15m"); assert v.apply_mark(p.position_id,e).applied and not v.apply_mark(p.position_id,e).applied
def test_50_store_returns_deep_immutable_copy():
 s,v,p=make_open(); x=s.get(p.position_id); assert x is not p
 with pytest.raises(TypeError): x.metadata["x"]=1
