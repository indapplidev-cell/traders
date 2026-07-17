from __future__ import annotations

from app.engine_risk.risk_decision import RiskDecision


def risk_decision(**changes) -> RiskDecision:
    values = dict(
        risk_decision_id="risk:1", created_at_ms=1_700_000_000_001,
        source_strategy_decision_id="strategy:1", source_setup_id="setup:1",
        source_analysis_snapshot_id="analysis:1", symbol="BTCUSDT", timeframe="15m",
        closed_until_ms=1_700_000_000_000, risk_status="RISK_PRE_APPROVED_RESEARCH",
        risk_level="LOW", risk_score=90.0, risk_policy_version="risk-v1",
        source_decision_status="ALLOW_RESEARCH_TRADE_PLAN",
        source_strategy_type="BREAKOUT_CONTINUATION_RESEARCH",
        source_strategy_quality="GOOD", source_strategy_score=88.0,
        direction_hint="BULLISH", risk_reasons=[], risk_warnings=[],
        rejection_reasons=[], wait_reasons=[],
        risk_context={"confirmation_close": 100.0, "causal_support_level": 95.0,
                      "causal_target_level": 110.0, "volatility_buffer": 1.0},
        risk_pre_approved=True, requires_execution_review=True,
    )
    unsafe = {name: changes.pop(name) for name in list(changes)
              if name in {"is_trade_signal", "is_executable", "order_approved",
                          "execution_approved", "position_size_approved", "future_bars_used"}}
    values.update(changes)
    decision = RiskDecision(**values)
    for name, value in unsafe.items():
        object.__setattr__(decision, name, value)
    return decision


def routed(status: str) -> RiskDecision:
    mapping = {
        "WAIT": dict(risk_level="WAITING"), "REJECT": dict(risk_level="BLOCKED"),
        "NO_DECISION": dict(risk_level="UNKNOWN"), "ERROR": dict(risk_level="ERROR"),
    }
    return risk_decision(risk_status=status, risk_pre_approved=False,
                         requires_execution_review=False, **mapping[status])


def historical_row(**changes) -> dict:
    row = risk_decision().to_dict()
    row["closed_until_utc"] = "2023-11-14T22:13:20Z"
    row.update(changes)
    return row
