from app.engine_analysis.engine import run_engine_analysis_from_rows
from app.engine_paper.paper_runner import PaperRunner
from app.engine_risk.risk_runner import RiskRunner
from app.engine_setup.setup_detector import SetupDetector
from app.engine_strategy.strategy_runner import StrategyRunner
from tests.engine_setup_01_helpers import analysis_snapshot
from tests.engine_strategy_01_helpers import candidate


def _trend_rows():
    rows = []
    for index in range(96):
        price = 100.0 + index * 0.25
        rows.append({
            "timestamp": f"2026-01-01T{(index // 4) % 24:02d}:{(index % 4) * 15:02d}:00Z",
            "open": price, "high": price + 0.8, "low": price - 0.5,
            "close": price + 0.4, "volume": 1000 + index,
        })
    return rows


def test_analysis_exports_closed_window_reference_and_atr():
    payload = run_engine_analysis_from_rows("TESTUSDT", "15m", _trend_rows()).json_payload
    context = payload["analysis_context"]
    assert context["reference_close"] == _trend_rows()[-1]["close"]
    assert context["current_closed_candle_close"] == context["reference_close"]
    assert context["confirmation_close"] > 0
    assert context["atr_value"] > 0
    assert context["volatility_buffer"] == context["atr_value"]
    assert context["causal_boundary_only"] is True


def test_setup_adds_direction_specific_levels():
    source = analysis_snapshot(
        regime="UP", impulse_phase="IMPULSE_EXTENSION", entry_quality="GOOD",
        reason_codes=["BREAKOUT_HELD_WITH_FOLLOW_THROUGH"],
        analysis_context={"reference_close": 100.0, "confirmation_close": 100.0,
                          "causal_support_level": 95.0, "causal_resistance_level": 110.0,
                          "atr_value": 1.0},
    )
    setup = SetupDetector().detect(source)
    assert setup.context["causal_invalidation_level"] == 95.0
    assert setup.context["causal_target_level"] == 110.0
    assert setup.context["nearest_opposite_level"] == 110.0


def test_allowlisted_context_reaches_ready_paper_plan():
    setup = candidate(
        setup_quality="GOOD", quality_score=90.0,
        context={"confirmation_close": 100.0, "reference_close": 100.0,
                 "causal_support_level": 95.0, "causal_resistance_level": 110.0,
                 "causal_invalidation_level": 95.0, "causal_target_level": 110.0,
                 "nearest_opposite_level": 110.0, "atr_value": 1.0,
                 "outcome": "MUST_NOT_PROPAGATE"},
    )
    strategy = StrategyRunner().process_setup_candidate(setup)
    risk = RiskRunner().process_strategy_decision(strategy)
    paper = PaperRunner().process_risk_decision(risk)
    assert strategy.decision_status == "ALLOW_RESEARCH_TRADE_PLAN"
    assert risk.risk_status == "RISK_PRE_APPROVED_RESEARCH"
    assert risk.risk_context["reference_close"] == 100.0
    assert "outcome" not in strategy.context and "outcome" not in risk.risk_context
    assert paper.paper_status == "PAPER_PLAN_READY"
    assert paper.hypothetical_entry_reference == 100.0
    assert paper.hypothetical_invalidation_level == 95.0
    assert paper.hypothetical_stop_level == 94.0
    assert paper.hypothetical_target_level == 110.0
    assert paper.future_bars_used is False and paper.is_executable is False


def test_missing_causal_target_is_not_fabricated():
    setup = candidate(
        setup_quality="GOOD", quality_score=90.0,
        context={"reference_close": 100.0, "causal_support_level": 95.0,
                 "causal_invalidation_level": 95.0, "atr_value": 1.0},
    )
    paper = PaperRunner().process_risk_decision(
        RiskRunner().process_strategy_decision(StrategyRunner().process_setup_candidate(setup)))
    assert paper.paper_status == "NO_PLAN"
    assert paper.hypothetical_target_level is None


def test_invalidation_must_be_on_protective_side_of_entry():
    setup = candidate(
        setup_quality="GOOD", quality_score=90.0,
        context={"confirmation_close": 100.0, "causal_support_level": 101.0,
                 "causal_invalidation_level": 101.0, "causal_target_level": 110.0,
                 "atr_value": 2.0},
    )
    paper = PaperRunner().process_risk_decision(
        RiskRunner().process_strategy_decision(StrategyRunner().process_setup_candidate(setup)))
    assert paper.paper_status == "REJECT"
    assert "PAPER_REJECT_INVALID_LEVEL_GEOMETRY" in paper.plan_reasons
