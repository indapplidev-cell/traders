from types import SimpleNamespace

from app.engine_paper.paper_config import PaperConfig
from app.engine_paper.paper_runner import PaperRunner
from app.engine_paper.portfolio_gate import evaluate_paper_portfolio_gate
from tests.engine_paper_01_helpers import risk_decision


def _risk(target: float, *, opportunity: str = "opportunity:natural:15m"):
    return risk_decision(risk_context={
        "confirmation_close": 100.0,
        "causal_support_level": 99.5,
        "causal_invalidation_level": 99.5,
        "causal_target_level": target,
        "volatility_buffer": 0.5,
        "opportunity_id": opportunity,
        "causal_target_candidates": [{
            "price": target,
            "timeframe": "15m",
            "known_at_ms": 1_800_000_000_000,
            "source_detail": "schwager_resistance_zone",
        }],
    })


def test_15m_net_cost_gate_pass_reject_and_exact_boundary_are_deterministic():
    config = PaperConfig(minimum_planned_rr=0.01)
    exact = PaperRunner(config).process_risk_decision(_risk(100.28))
    below = PaperRunner(config).process_risk_decision(_risk(100.279))
    passed = PaperRunner(config).process_risk_decision(_risk(101.0))

    exact_gate = exact.paper_context["net_cost_gate"]
    assert exact_gate["total_estimated_cost_bps"] == 27.0
    assert round(exact_gate["net_expected_outcome_bps"], 8) == 1.0
    assert exact_gate["gate_decision"] == "PASS"
    assert below.paper_status == "REJECT"
    assert below.paper_context["net_cost_gate"]["gate_decision"] == "REJECT"
    assert "PAPER_REJECT_NET_COST_GATE" in below.rejection_reasons
    assert passed.paper_status == "PAPER_PLAN_READY"
    assert passed.paper_context["net_cost_gate"]["deterministic"] is True


def test_rejected_rr_keeps_complete_geometry_and_actual_level_provenance():
    rejected = PaperRunner().process_risk_decision(_risk(100.4))
    evidence = rejected.paper_context["canonical_domain_evaluation"]
    assert rejected.paper_status == "REJECT"
    assert rejected.hypothetical_entry_reference == 100.0
    assert rejected.hypothetical_stop_level == 99.0
    assert rejected.hypothetical_target_level == 100.4
    assert evidence["risk_distance"] == 1.0
    assert round(evidence["reward_distance"], 8) == 0.4
    assert round(evidence["raw_rr"], 8) == 0.4
    assert evidence["rr_threshold"] == 1.5
    assert evidence["rr_pass"] is False
    assert evidence["calculation_version"] == "paper-level-geometry-v2"
    assert evidence["stop_provenance"]["raw_source_value"] == 99.5
    assert evidence["stop_provenance"]["final_normalized_value"] == 99.0
    assert evidence["target_provenance"]["source_timeframe"] == "15m"
    assert evidence["target_provenance"]["source_signal_or_model_output"] == (
        "schwager_resistance_zone"
    )


class _Rows:
    def __init__(self, rows=()):
        self.rows = rows

    def execute(self, _statement):
        return self.rows


def _result(profile="trade-15m-v1", symbol="BTCUSDT"):
    return SimpleNamespace(trade_profile_id=profile, symbol=symbol)


def test_portfolio_gate_pass_and_canonical_limit_rejections():
    from datetime import datetime, timezone
    from decimal import Decimal

    now = datetime(2026, 8, 31, tzinfo=timezone.utc)
    passed = evaluate_paper_portfolio_gate(
        _Rows(), result=_result(), candidate_direction="BULLISH",
        account_equity=Decimal("100"), evaluation_time=now,
    )
    assert passed["decision"] == "PASS"
    assert passed["measured"]["candidate_risk_bps"] == "10.0"
    assert passed["limits"]["max_concurrent_positions"] == 3

    position = lambda symbol, side="LONG", risk="0.001": SimpleNamespace(
        symbol=symbol, side=side, remaining_quantity=Decimal("1"),
        average_entry_price=Decimal("100"), stop_price=Decimal("100") - Decimal(risk),
    )
    duplicate = evaluate_paper_portfolio_gate(
        _Rows(((position("BTCUSDT"), "trade-5m-v1"),)),
        result=_result(), candidate_direction="BULLISH",
        account_equity=Decimal("100"), evaluation_time=now,
    )
    assert duplicate["reason_code"] == "PORTFOLIO_REJECT_DUPLICATE_OR_OPPOSING_SYMBOL"

    too_many = evaluate_paper_portfolio_gate(
        _Rows(tuple((position(symbol), "trade-15m-v1") for symbol in (
            "ETHUSDT", "SOLUSDT", "BNBUSDT"
        ))), result=_result(), candidate_direction="BULLISH",
        account_equity=Decimal("100"), evaluation_time=now,
    )
    assert too_many["reason_code"] == "PORTFOLIO_REJECT_MAX_CONCURRENT_POSITIONS"

    risk = evaluate_paper_portfolio_gate(
        _Rows(((position("ETHUSDT", risk="0.5"), "trade-15m-v1"),)),
        result=_result(), candidate_direction="BEARISH",
        account_equity=Decimal("100"), evaluation_time=now,
    )
    assert risk["reason_code"] == "PORTFOLIO_REJECT_TOTAL_OPEN_RISK"
