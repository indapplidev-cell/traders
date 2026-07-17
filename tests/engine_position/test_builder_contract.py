from dataclasses import replace
from decimal import Decimal
import pytest
from app.engine_execution import *
from app.engine_position import *
from app.engine_position.builder import build_position_from_execution
from app.engine_position.exceptions import PositionContractError
from tests.engine_position.conftest import NOW, make_contract

def reason(intent,ack,code):
    with pytest.raises(PositionContractError) as e: build_position_from_execution(intent,ack,current_timestamp=NOW)
    assert code in e.value.reason_codes

def test_01_acknowledged_paper_creates_position():
    i,a=make_contract(ExecutionMode.PAPER); assert build_position_from_execution(i,a,current_timestamp=NOW).mode is ExecutionMode.PAPER
def test_02_acknowledged_dry_run_creates_position():
    i,a=make_contract(); assert build_position_from_execution(i,a,current_timestamp=NOW).status is PositionStatus.PENDING_OPEN
def test_03_live_is_blocked_first():
    i,a=make_contract(ExecutionMode.LIVE,quantity=Decimal("0")); reason(i,None,"LIVE_POSITION_MANAGEMENT_DISABLED")
def test_04_intent_not_ready():
    i,a=make_contract(status=ExecutionIntentStatus.REJECTED); reason(i,a,"EXECUTION_INTENT_NOT_READY")
def test_05_ack_not_acknowledged():
    i,a=make_contract(); a=replace(a,status=ExecutionAcknowledgementStatus.REJECTED,accepted_at_utc=None); reason(i,a,"EXECUTION_ACK_NOT_ACKNOWLEDGED")
def test_06_intent_ack_id_mismatch():
    i,a=make_contract(); reason(i,replace(a,execution_intent_id="other"),"EXECUTION_CONTRACT_MISMATCH")
def test_07_idempotency_mismatch():
    i,a=make_contract(); reason(i,replace(a,idempotency_key="other"),"EXECUTION_CONTRACT_MISMATCH")
def test_08_mode_mismatch():
    i,a=make_contract(); reason(i,replace(a,mode=ExecutionMode.PAPER),"MODE_MISMATCH")
def test_09_symbol_mismatch():
    i,a=make_contract(); reason(i,replace(a,metadata={"symbol":"ETHUSDT"}),"SYMBOL_MISMATCH")
def test_10_buy_maps_long():
    i,a=make_contract(); assert build_position_from_execution(i,a,current_timestamp=NOW).side is PositionSide.LONG
def test_11_sell_maps_short():
    i,a=make_contract(side=ExecutionSide.SELL); assert build_position_from_execution(i,a,current_timestamp=NOW).side is PositionSide.SHORT
def test_12_non_positive_quantity():
    i,a=make_contract(quantity=Decimal("0")); reason(i,a,"INVALID_INITIAL_QUANTITY")
@pytest.mark.parametrize("bad",[Decimal("NaN"),Decimal("Infinity")],ids=["nan","infinity"])
def test_13_non_finite_entry_price(bad):
    i,a=make_contract(reference_price=bad); reason(i,a,"INVALID_ENTRY_PRICE")
def test_14_missing_source_window():
    i,a=make_contract(source_window_close_ms=0,source_timeframe=""); reason(i,a,"MISSING_SOURCE_WINDOW")
def test_15_unclosed_source_window():
    i,a=make_contract(metadata={"source_window_is_closed":False}); reason(i,a,"SOURCE_WINDOW_NOT_CLOSED")
def test_16_invalid_long_geometry():
    i,a=make_contract(stop_price=Decimal("101")); reason(i,a,"INVALID_STOP_PLACEMENT")
def test_17_invalid_short_geometry():
    i,a=make_contract(side=ExecutionSide.SELL,target_price=Decimal("120")); reason(i,a,"INVALID_TARGET_PLACEMENT")

def test_acknowledgement_id_ignores_volatile_fields():
    from datetime import timedelta
    i,a=make_contract()
    first=build_position_from_execution(i,a,current_timestamp=NOW)
    volatile=replace(a,accepted_at_utc=NOW+timedelta(seconds=5),warnings=("changed",),
                     reason_codes=("POSITION_READY",),metadata={"volatile":"changed"})
    second=build_position_from_execution(i,volatile,current_timestamp=NOW)
    assert first.execution_acknowledgement_id==second.execution_acknowledgement_id

def test_acknowledgement_id_changes_with_stable_identity():
    i,a=make_contract(); first=build_position_from_execution(i,a,current_timestamp=NOW)
    other_i,other_a=make_contract(execution_intent_id="intent:2",idempotency_key="execution:v1:key-2")
    second=build_position_from_execution(other_i,other_a,current_timestamp=NOW)
    assert first.execution_acknowledgement_id!=second.execution_acknowledgement_id
