from dataclasses import FrozenInstanceError
from decimal import Decimal
import pytest
from app.engine_position import *
from tests.engine_position.conftest import NOW, make_open

def test_51_position_round_trip():
 s,v,p=make_open(); assert Position.from_dict(p.to_dict())==p
def test_52_fill_event_round_trip():
 s,v,p=make_open(); e=PositionFillEvent("e",p.position_id,NOW,"L",fill_quantity="1",fill_price="2",fee="0",action="CLOSE"); assert PositionEvent.from_dict(e.to_dict())==e
def test_53_mark_close_cancel_event_round_trip():
 s,v,p=make_open(); events=[PositionMarkEvent("m",p.position_id,NOW,"L",mark_price="2",source_window_close_ms=2,source_timeframe="15m"),PositionCloseEvent("c",p.position_id,NOW,"L",close_quantity="1",close_price="2",fee="0"),PositionCancelEvent("x",p.position_id,NOW,"L")]; assert all(PositionEvent.from_dict(e.to_dict())==e for e in events)
def test_54_transition_result_round_trip():
 s,v,p=make_open(); e=PositionMarkEvent("m",p.position_id,NOW,"L",mark_price="101",source_window_close_ms=1700000000001,source_timeframe="15m"); r=v.apply_mark(p.position_id,e); assert PositionTransitionResult.from_dict(r.to_dict())==r
def test_55_canonical_json_is_stable():
 s,v,p=make_open(); assert p.canonical_json()==p.canonical_json()
def test_56_decimal_serializes_as_string_and_utc_as_z():
 s,v,p=make_open(); d=p.to_dict(); assert isinstance(d["initial_quantity"],str) and d["updated_at_utc"].endswith("Z")
def test_57_unknown_schema_is_rejected():
 s,v,p=make_open(); d=p.to_dict(); d["position_schema_version"]=2
 with pytest.raises(ValueError): Position.from_dict(d)
def test_58_models_and_nested_metadata_are_immutable():
 s,v,p=make_open()
 with pytest.raises(FrozenInstanceError): p.symbol="X"
 with pytest.raises(TypeError): p.metadata["x"]=1
