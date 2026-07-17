from datetime import datetime, timezone
from decimal import Decimal
import pytest
from app.engine_execution import (ExecutionAcknowledgement, ExecutionAcknowledgementStatus,
    ExecutionIntent, ExecutionIntentStatus, ExecutionMode, ExecutionOrderType, ExecutionSide)
from app.engine_position import *

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)

def make_contract(mode=ExecutionMode.DRY_RUN, side=ExecutionSide.BUY, **changes):
    data=dict(execution_intent_id="intent:1",idempotency_key="execution:v1:key",created_at_utc=NOW,
      symbol="BTCUSDT",side=side,execution_mode=mode,order_type=ExecutionOrderType.MARKET_INTENT,
      quantity=Decimal("2"),reference_price=Decimal("100"),limit_price=None,
      stop_price=Decimal("90") if side is ExecutionSide.BUY else Decimal("110"),
      target_price=Decimal("120") if side is ExecutionSide.BUY else Decimal("80"),time_in_force=None,
      reduce_only=False,strategy_decision_id="strategy:1",risk_decision_id="risk:1",setup_id="setup:1",
      source_window_close_ms=1700000000000,source_timeframe="15m",status=ExecutionIntentStatus.READY,
      metadata={})
    data.update(changes); intent=ExecutionIntent(**data)
    ack=ExecutionAcknowledgement(intent.execution_intent_id,intent.idempotency_key,mode,
      ExecutionAcknowledgementStatus.ACKNOWLEDGED,NOW)
    return intent,ack

def make_open(side=ExecutionSide.BUY, mode=ExecutionMode.DRY_RUN):
    i,a=make_contract(mode,side); store=InMemoryPositionStore(); service=PositionLifecycleService(store)
    p=service.create_position(i,a,current_timestamp=NOW,synthetic_local_fill=(mode is ExecutionMode.DRY_RUN))
    if p.status is PositionStatus.PENDING_OPEN:
        e=PositionFillEvent("open",p.position_id,NOW,"LOCAL_TEST",fill_quantity="2",fill_price="100",fee="0",action="OPEN")
        p=service.apply_fill(p.position_id,e).position
    return store,service,p

@pytest.fixture
def contract():
    return make_contract()

@pytest.fixture
def open_position():
    return make_open()
