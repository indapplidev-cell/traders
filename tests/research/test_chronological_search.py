from types import SimpleNamespace as NS
from decimal import Decimal
import pytest

from app.engine_market_data.candle import Candle
from traders_ml.parameter_sweep import chronological_search as engine


COSTS={"spread_bps":0,"depth_impact_bps":0,"entry_slippage_bps":0,
       "exit_slippage_bps":0,"entry_fee_bps":0,"exit_fee_bps":0}


class FixtureFunnel:
    """Synthetic admission fixture; production calculations remain unmodified."""
    def __init__(self,*args):
        runtime=NS(parameter_set_id="test",risk_per_trade_bps=20,
            portfolio_max_concurrent_positions=1,portfolio_max_total_open_risk_bps=50,profile_id="trade-5m-v2")
        self.runner=NS(runtime_parameters=runtime)
        self.resolved=NS(resolved_config_hash="synthetic-test",parameters=NS(
            risk=NS(max_new_commands_per_cycle=1),lifecycle=NS(entry_fill_window_seconds=60,maximum_price_drift_bps=10)))
        self.manifest={"fingerprint":"SYNTHETIC_TEST_ONLY","symbols":["BTCUSDT","ETHUSDT"],
            "intervals":{"search_start_ms":300000,"search_end_ms":600000,"exit_tail_end_ms":900000}}
        self.repositories={s:NS(rows={"1m":[Candle(s,"1m",t,t+59999,
            106 if t>=420000 else 100,107 if t>=360000 else 101,99,
            106 if t>=360000 else 100,1,is_closed=True) for t in range(300000,900000,60000)]})
            for s in self.manifest["symbols"]}

    def run(self,symbol,boundary):
        return NS(symbol=symbol,closed_until_ms=boundary,paper_status="PAPER_PLAN_READY",final_reason=None,
            error_code=None,trade_profile_id="trade-5m-v2",runtime_parameter_set_id="test",
            runtime_parameters_snapshot=self.runner.runtime_parameters,
            risk_payload={"risk_score":90},strategy_payload={"strategy_score":90},paper_payload={
                "paper_plan_id":"test:"+symbol,"created_at_ms":boundary+1000,"paper_direction":"BULLISH",
                "hypothetical_entry_reference":100,"hypothetical_stop_level":95,
                "hypothetical_target_level":105,"planned_rr":1,"paper_context":{}}),None,False


def test_full_chronology_selector_fills_and_repeated_trials(monkeypatch,tmp_path):
    monkeypatch.setattr(engine,"FrozenFunnel",FixtureFunnel)
    first=engine.simulate(tmp_path,{},1000,assumed_execution_costs=COSTS)
    assert first==engine.simulate(tmp_path,{},1000,assumed_execution_costs=COSTS)
    assert first["result"]=="SIMULATED" and first["quality"]=="ASSUMPTION_BASED"
    assert first["has_profitable_closed_trade"] and len(first["closed_trades"])==1
    assert first["rejections"]["SELECTOR_NOT_SELECTED"]==1
    assert first["closed_trades"][0]["symbol"]=="BTCUSDT"
    assert Decimal(first["balance"])==1000+Decimal(first["net_pnl"])


def test_admitted_path_without_execution_evidence_is_not_a_loss_or_success(monkeypatch,tmp_path):
    monkeypatch.setattr(engine,"FrozenFunnel",FixtureFunnel)
    result=engine.simulate(tmp_path,{},1000)
    assert result["result"]=="BLOCKED_DATA" and not result["closed_trades"]
    assert not result["has_profitable_closed_trade"]
    assert result["blockers"][0]["reason"]=="EXECUTION_QUANTITY_AND_EXIT_TIME_COST_EVIDENCE_REQUIRED"


def test_negative_or_incomplete_assumptions_rejected(monkeypatch,tmp_path):
    monkeypatch.setattr(engine,"FrozenFunnel",FixtureFunnel)
    with pytest.raises(ValueError,match="INVALID_EXPLICIT"):
        engine.simulate(tmp_path,{},1000,assumed_execution_costs=COSTS|{"spread_bps":-1})


def test_expired_command_does_not_require_execution_costs(monkeypatch,tmp_path):
    class Expired(FixtureFunnel):
        def __init__(self,*args):
            super().__init__(*args)
            self.resolved.parameters.lifecycle.entry_fill_window_seconds=30
    monkeypatch.setattr(engine,"FrozenFunnel",Expired)
    result=engine.simulate(tmp_path,{},1000)
    assert not result["blockers"] and not result["closed_trades"]
    assert result["rejections"]["COMMAND_EXPIRED_BEFORE_ELIGIBLE_CANDLE_CLOSE"]==1
