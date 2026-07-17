from __future__ import annotations

from app.engine_strategy.strategy_decision import StrategyDecision


def strategy_decision(**changes) -> StrategyDecision:
    values = dict(
        decision_id="strategy:1", created_at_ms=1_700_000_000_001,
        source_setup_id="setup:1", source_analysis_snapshot_id="analysis:1",
        symbol="BTCUSDT", timeframe="15m", closed_until_ms=1_700_000_000_000,
        decision_status="ALLOW_RESEARCH_TRADE_PLAN",
        strategy_type="BREAKOUT_CONTINUATION_RESEARCH", direction_hint="BULLISH",
        setup_status="SETUP_CANDIDATE", setup_type="BREAKOUT_CONTINUATION",
        setup_quality="GOOD", setup_quality_score=90.0,
        strategy_score=82.0, strategy_quality="ACCEPTABLE",
        decision_reasons=[], decision_warnings=[], rejection_reasons=[], wait_reasons=[],
        required_next_layer="engine_risk", requires_risk_review=True, context={},
    )
    values.update(changes)
    status = values["decision_status"]
    if status != "ALLOW_RESEARCH_TRADE_PLAN":
        values.setdefault("required_next_layer", None)
        values.setdefault("requires_risk_review", False)
        if "required_next_layer" not in changes:
            values["required_next_layer"] = None
        if "requires_risk_review" not in changes:
            values["requires_risk_review"] = False
    return StrategyDecision(**values)


def historical_input(**changes) -> dict:
    source = strategy_decision()
    row = {
        "record_id": source.decision_id, "symbol": source.symbol, "timeframe": source.timeframe,
        "closed_until_ms": source.closed_until_ms,
        "closed_until_utc": "2023-11-14T22:13:20Z",
        "source_setup_id": source.source_setup_id,
        "source_setup_status": source.setup_status, "source_setup_type": source.setup_type,
        "source_setup_quality": source.setup_quality,
        "source_setup_quality_score": source.setup_quality_score,
        "source_direction_hint": source.direction_hint,
        "decision_status": source.decision_status, "strategy_type": source.strategy_type,
        "strategy_quality": source.strategy_quality, "strategy_score": source.strategy_score,
        "decision_reasons": [], "decision_warnings": [], "rejection_reasons": [], "wait_reasons": [],
        "requires_risk_review": True, "risk_approved": False, "is_executable": False,
        "is_trade_signal": False, "future_bars_used": False,
    }
    row.update(changes)
    return row
