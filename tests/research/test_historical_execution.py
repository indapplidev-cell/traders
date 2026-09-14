from types import SimpleNamespace
from decimal import Decimal
import pytest

from app.engine_market_data.candle import Candle
from traders_ml.parameter_sweep.historical_execution import HistoricalExecution


def candle(t, o=100, h=101, l=99, c=100):
    return Candle("BTCUSDT", "1m", t, t+59999, o,h,l,c,1,is_closed=True)


def execution(side="LONG", fee=0):
    e = HistoricalExecution(1000, SimpleNamespace(risk_per_trade_bps=20))
    e.open(identity="research:test",symbol="BTCUSDT",side=side,reference=100,
           stop=95 if side=="LONG" else 105,target=105 if side=="LONG" else 95,candle=candle(0),
           entry_fee_bps=fee,exit_fee_bps=fee,entry_slippage_bps=0,exit_slippage_bps=0)
    return e


@pytest.mark.parametrize("side,trigger,exit_price", [("LONG",candle(60000,100,106,99,105),106),
                                                   ("SHORT",candle(60000,100,101,94,95),94)])
def test_shared_exit_and_accounting_profitable(side,trigger,exit_price):
    e=execution(side)
    e.advance("BTCUSDT",trigger)
    assert not e.closed
    e.advance("BTCUSDT",candle(120000,exit_price,exit_price+1,exit_price-1,exit_price))
    trade=e.closed[0]
    assert Decimal(trade["net_pnl"])>0 and trade["exit_cause"]=="TAKE_PROFIT"
    assert e.balance==1000+Decimal(trade["net_pnl"])


def test_both_hits_stop_first_and_no_synthetic_tail_close():
    e=execution()
    e.advance("BTCUSDT",candle(60000,100,106,94,100))
    assert e.positions["BTCUSDT"].exit_cause=="STOP_LOSS"
    assert e.summary()["terminal"]=="INCOMPLETE_EXIT_TAIL" and not e.closed
    e.advance("BTCUSDT",candle(120000,94,95,93,94))
    assert Decimal(e.closed[0]["net_pnl"])<0


def test_positive_gross_negative_net_fees_once():
    e=execution(fee=100)
    e.advance("BTCUSDT",candle(60000,100,106,99,105))
    e.advance("BTCUSDT",candle(120000,101,102,100,101))
    t=e.closed[0]
    assert Decimal(t["gross_pnl"])>0>Decimal(t["net_pnl"])
    assert e.balance==1000+Decimal(t["net_pnl"])


def test_gap_and_duplicate_symbol_are_rejected():
    e=execution()
    with pytest.raises(ValueError,match="MARKET_DATA_GAP"):
        e.advance("BTCUSDT",candle(120000))
    assert not e.closed


def test_shadow_timeout_does_not_close_and_trials_are_isolated():
    e=execution(); other=execution()
    for t in range(60000,3660000,60000):
        e.advance("BTCUSDT",candle(t))
    assert not e.closed and e.positions and not other.closed
    assert other.positions["BTCUSDT"].cursor==60000


def test_shared_portfolio_gate_rejects_conflicts():
    e=execution()
    e.runtime=SimpleNamespace(parameter_set_id="set",risk_per_trade_bps=20,
        portfolio_max_concurrent_positions=1,portfolio_max_total_open_risk_bps=50,profile_id="trade-5m-v2")
    result=SimpleNamespace(symbol="BTCUSDT",trade_profile_id="trade-5m-v2",runtime_parameter_set_id="set",
        runtime_parameters_snapshot=e.runtime,closed_until_ms=60000,paper_payload={"paper_direction":"BULLISH"})
    assert e.portfolio_gate(result)["reason_code"]=="PORTFOLIO_REJECT_DUPLICATE_OR_OPPOSING_SYMBOL"
    result.symbol="ETHUSDT"
    assert e.portfolio_gate(result)["reason_code"]=="PORTFOLIO_REJECT_MAX_CONCURRENT_POSITIONS"
    e.runtime.portfolio_max_concurrent_positions=3
    e.runtime.portfolio_max_total_open_risk_bps=25
    assert e.portfolio_gate(result)["reason_code"]=="PORTFOLIO_REJECT_TOTAL_OPEN_RISK"


@pytest.mark.parametrize("side",["LONG","SHORT"])
def test_entry_price_and_fee_match_full_production_fill_simulator(side):
    from tests.paper_fill_simulator.conftest import make_command,make_request,make_candle,COMMAND_BOUNDARY_MS
    from app.engine_paper.fill_simulator import simulate_paper_fill
    from app.engine_safety.paper_domain import PaperSide
    from app.operator_control.production_executor import _foundation_policy
    e=HistoricalExecution(1000,SimpleNamespace(risk_per_trade_bps=20))
    p=e.open(identity="parity",symbol="BTCUSDT",side=side,reference=100,
        stop=95 if side=="LONG" else 105,target=105 if side=="LONG" else 95,
        candle=candle(COMMAND_BOUNDARY_MS),entry_fee_bps=10,exit_fee_bps=10,
        entry_slippage_bps=2,exit_slippage_bps=2)
    command=make_command(side=PaperSide(side),quantity=p.quantity)
    request=make_request(command=command,policy=_foundation_policy(),candles=(make_candle(open_price=Decimal(100)),))
    fill=simulate_paper_fill(request).fill
    assert fill is not None
    assert fill.price==p.entry and fill.fee_amount==p.entry_fee
