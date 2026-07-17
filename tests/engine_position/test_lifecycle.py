from datetime import timedelta
from app.engine_position import *
from tests.engine_position.conftest import NOW, make_contract, make_open

def close(p,id="close",q="1",price="110",at=NOW):
    return PositionCloseEvent(id,p.position_id,at,"LOCAL_TEST",close_quantity=q,close_price=price,fee="0")
def test_18_pending_open_to_open():
    i,a=make_contract(); s=InMemoryPositionStore(); v=PositionLifecycleService(s); p=v.create_position(i,a,current_timestamp=NOW); e=PositionFillEvent("o",p.position_id,NOW,"LOCAL",fill_quantity="2",fill_price="100",fee="0",action="OPEN"); assert v.apply_fill(p.position_id,e).new_status is PositionStatus.OPEN
def test_19_open_to_partially_closed():
    s,v,p=make_open(); assert v.partial_close(p.position_id,close(p)).new_status is PositionStatus.PARTIALLY_CLOSED
def test_20_open_to_closed():
    s,v,p=make_open(); assert v.close(p.position_id,close(p,q="2")).new_status is PositionStatus.CLOSED
def test_21_partial_to_closed():
    s,v,p=make_open(); p=v.partial_close(p.position_id,close(p)).position; assert v.close(p.position_id,close(p,"c2","1",at=NOW+timedelta(seconds=1))).new_status is PositionStatus.CLOSED
def test_22_closed_to_open_blocked():
    s,v,p=make_open(); p=v.close(p.position_id,close(p,q="2")).position; e=PositionFillEvent("again",p.position_id,NOW,"L",fill_quantity="1",fill_price="1",fee="0",action="OPEN"); assert not v.apply_fill(p.position_id,e).applied
def test_23_cancelled_to_open_blocked():
    i,a=make_contract(); s=InMemoryPositionStore(); v=PositionLifecycleService(s); p=v.create_position(i,a,current_timestamp=NOW); p=v.cancel(p.position_id,PositionCancelEvent("x",p.position_id,NOW,"L")).position; e=PositionFillEvent("o",p.position_id,NOW,"L",fill_quantity="1",fill_price="100",fee="0",action="OPEN"); assert not v.apply_fill(p.position_id,e).applied
def test_24_rejected_to_open_blocked_by_terminal_contract():
    from dataclasses import replace
    from app.engine_position.lifecycle import reduce_event
    i,a=make_contract(); p=PositionLifecycleService(InMemoryPositionStore()).builder.build(i,a,current_timestamp=NOW)
    p=replace(p,status=PositionStatus.REJECTED)
    e=PositionFillEvent("o",p.position_id,NOW,"L",fill_quantity="1",fill_price="100",fee="0",action="OPEN")
    assert not reduce_event(p,e).applied
def test_25_duplicate_event_blocked():
    s,v,p=make_open(); e=close(p); assert v.partial_close(p.position_id,e).applied and not v.partial_close(p.position_id,e).applied
def test_26_wrong_position_id_blocked():
    s,v,p=make_open(); e=PositionMarkEvent("m","other",NOW,"L",mark_price="101",source_window_close_ms=1700000000001,source_timeframe="15m"); assert "POSITION_ID_MISMATCH" in v.apply_mark(p.position_id,e).reason_codes
def test_27_out_of_order_event_blocked():
    s,v,p=make_open(); e=PositionMarkEvent("m",p.position_id,NOW-timedelta(seconds=1),"L",mark_price="101",source_window_close_ms=1700000000001,source_timeframe="15m"); assert "OUT_OF_ORDER_POSITION_EVENT" in v.apply_mark(p.position_id,e).reason_codes
def test_28_post_terminal_event_blocked():
    s,v,p=make_open(); p=v.close(p.position_id,close(p,q="2")).position; assert not v.cancel(p.position_id,PositionCancelEvent("x",p.position_id,NOW,"L")).applied

def test_partial_open_fill_is_explicitly_unsupported():
    i,a=make_contract(); s=InMemoryPositionStore(); v=PositionLifecycleService(s); p=v.create_position(i,a,current_timestamp=NOW)
    e=PositionFillEvent("partial",p.position_id,NOW,"LOCAL",fill_quantity="1",fill_price="100",fee="0",action="OPEN")
    result=v.apply_fill(p.position_id,e)
    assert not result.applied and result.reason_codes == ("PARTIAL_OPEN_FILL_UNSUPPORTED",)
    assert result.position.initial_quantity==2 and result.position.open_quantity==2

def test_open_position_cannot_be_cancelled():
    s,v,p=make_open(); result=v.cancel(p.position_id,PositionCancelEvent("cancel-open",p.position_id,NOW,"LOCAL"))
    assert not result.applied and result.reason_codes == ("INVALID_POSITION_TRANSITION",)
    assert result.position.status is PositionStatus.OPEN
