from datetime import timedelta
from decimal import Decimal, getcontext
from app.engine_execution import ExecutionSide
from app.engine_position import PositionCloseEvent, PositionMarkEvent, PositionStatus
from tests.engine_position.conftest import NOW, make_open

def mark(p,price,id="m"):
 return PositionMarkEvent(id,p.position_id,NOW,"L",mark_price=price,source_window_close_ms=1700000000001,source_timeframe="15m")
def close(p,q,price,fee="0",id="c"):
 return PositionCloseEvent(id,p.position_id,NOW,"L",close_quantity=q,close_price=price,fee=fee)
def test_29_long_unrealized_profit():
 s,v,p=make_open(); assert v.apply_mark(p.position_id,mark(p,"110")).position.unrealized_pnl==Decimal("20")
def test_30_long_unrealized_loss():
 s,v,p=make_open(); assert v.apply_mark(p.position_id,mark(p,"90")).position.unrealized_pnl==Decimal("-20")
def test_31_short_unrealized_profit():
 s,v,p=make_open(ExecutionSide.SELL); assert v.apply_mark(p.position_id,mark(p,"90")).position.unrealized_pnl==Decimal("20")
def test_32_short_unrealized_loss():
 s,v,p=make_open(ExecutionSide.SELL); assert v.apply_mark(p.position_id,mark(p,"110")).position.unrealized_pnl==Decimal("-20")
def test_33_long_realized_profit():
 s,v,p=make_open(); assert v.close(p.position_id,close(p,"2","110")).position.gross_realized_pnl==Decimal("20")
def test_34_long_realized_loss():
 s,v,p=make_open(); assert v.close(p.position_id,close(p,"2","90")).position.gross_realized_pnl==Decimal("-20")
def test_35_short_realized_profit():
 s,v,p=make_open(ExecutionSide.SELL); assert v.close(p.position_id,close(p,"2","90")).position.gross_realized_pnl==Decimal("20")
def test_36_short_realized_loss():
 s,v,p=make_open(ExecutionSide.SELL); assert v.close(p.position_id,close(p,"2","110")).position.gross_realized_pnl==Decimal("-20")
def test_37_fees_reduce_net_realized():
 s,v,p=make_open(); x=v.close(p.position_id,close(p,"2","110","1.25")).position; assert x.net_realized_pnl==Decimal("18.75")
def test_38_partial_close_reduces_open_quantity():
 s,v,p=make_open(); x=v.partial_close(p.position_id,close(p,"0.75","110")).position; assert x.open_quantity==Decimal("1.25")
def test_39_over_close_is_blocked():
 s,v,p=make_open(); r=v.close(p.position_id,close(p,"3","110")); assert not r.applied and "INVALID_CLOSE_QUANTITY" in r.reason_codes
def test_40_closed_unrealized_is_zero():
 s,v,p=make_open(); assert v.close(p.position_id,close(p,"2","110")).position.unrealized_pnl==0
def test_41_decimal_precision_is_preserved():
 s,v,p=make_open(); x=v.partial_close(p.position_id,close(p,"0.123456789123456789","100.000000000000000001")).position; assert x.gross_realized_pnl==Decimal("0.000000000000000000123456789123456789")
def test_42_average_entry_is_stable_after_close():
 s,v,p=make_open(); assert v.partial_close(p.position_id,close(p,"1","130")).position.average_entry_price==Decimal("100")
