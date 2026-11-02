from __future__ import annotations

import pytest

from traders_ml.parameter_sweep.bull_run_expert_audit import (
    BullRunTradeEvaluation,
    ExpertAuditRequest,
    ModuleCalibration,
    _classify_regime,
    _indicators,
    _weighted,
    independent_entry_verdict,
    independent_exit_verdict,
)
from traders_ml.parameter_sweep.bull_run_weights import (
    EntryScoreWeights,
    ExitScoreWeights,
    ScoreThresholds,
)

BASE = 1_790_000_000_000


def rows(count: int = 80, *, step: int = 60_000, bullish: bool = True):
    result = []
    for index in range(count):
        drift = index * (0.08 if bullish else -0.08)
        open_price = 100 + drift
        close = open_price + (0.06 if bullish else -0.06)
        result.append({
            "symbol": "BTCUSDT", "open_time_ms": BASE + index * step,
            "close_time_ms": BASE + (index + 1) * step - 1,
            "open": open_price, "high": max(open_price, close) + 0.03,
            "low": min(open_price, close) - 0.03, "close": close,
            "volume": 100 + index,
        })
    return result


def test_expert_contracts_are_inactive_research_calibrations():
    request = ExpertAuditRequest(calibration_request_path="request.json", search_trials=100)
    assert request.minimum_net_profit_bps == 8
    calibration = ModuleCalibration(
        calibration_id="test", regime="ALL", entry_weights=EntryScoreWeights(),
        exit_weights=ExitScoreWeights(),
        thresholds=ScoreThresholds(entry=60, at_risk=45, exit=65, strong_reversal=80),
        minimum_net_profit_bps=8,
    )
    assert calibration.research_only is True


def test_indicator_calculation_uses_closed_prefix_only():
    source = rows()
    before = _indicators(source[:-1])
    changed = [dict(item) for item in source]
    changed[-1]["close"] = 1000
    after = _indicators(changed[:-1])
    assert before == after
    assert _indicators(source).ema9 != _indicators(changed).ema9


def test_entry_verdict_is_causal_and_has_complete_components():
    one = rows(step=60_000)
    five = rows(step=300_000)
    boundary = int(five[-1]["close_time_ms"]) + 1
    first = independent_entry_verdict("BTCUSDT", boundary, one, five)
    future_one = one + rows(1, step=60_000, bullish=False)
    future_one[-1]["open_time_ms"] = boundary
    future_one[-1]["close_time_ms"] = boundary + 59_999
    second = independent_entry_verdict("BTCUSDT", boundary, future_one, five)
    assert first == second
    assert set(first.entry_components) == set(EntryScoreWeights.model_fields)
    assert first.future_bars_used is False


def test_exit_verdict_has_complete_scores_and_no_future_use():
    one = rows(step=60_000)
    five = rows(step=300_000)
    boundary = int(five[-1]["close_time_ms"]) + 1
    verdict = independent_exit_verdict(
        "BTCUSDT", boundary, "IMPULSE_BREAKOUT", one, five, 100, 107
    )
    assert set(verdict.exit_components) == set(ExitScoreWeights.model_fields)
    assert verdict.future_bars_used is False


def test_rubric_weights_match_the_declared_percentage_contract():
    values = {name: 80.0 for name in EntryScoreWeights.model_fields}
    assert _weighted(values, EntryScoreWeights()) == pytest.approx(80)
    exit_values = {name: 65.0 for name in ExitScoreWeights.model_fields}
    assert _weighted(exit_values, ExitScoreWeights()) == pytest.approx(65)


def test_regime_classification_is_one_of_causal_public_regimes():
    source = rows()
    indicator = _indicators(source)
    assert _classify_regime(source, indicator) in {
        "IMPULSE_BREAKOUT", "BREAKOUT_RETEST", "LOCAL_LOW_RECOVERY"
    }


def test_trade_contract_enforces_exact_cost_ledger():
    common = {
        "event_id": "event", "symbol": "BTCUSDT", "regime": "LOCAL_LOW_RECOVERY",
        "event_entry_open_time_ms": BASE, "event_peak_open_time_ms": BASE + 300_000,
        "successful": True, "captured_excursion_ratio": 0.5, "actual_project_verdict": {},
        "independent_entry_verdict": None, "independent_exit_verdict": None,
        "discrepancy_codes": (), "failure_reason": None, "gross_pnl_bps": 40,
        "fees_bps": 20, "impact_bps": 8,
    }
    assert BullRunTradeEvaluation(**common, net_pnl_bps=12).net_pnl_bps == 12
    with pytest.raises(ValueError, match="gross - fees - impact"):
        BullRunTradeEvaluation(**common, net_pnl_bps=11)
