from __future__ import annotations

from app.engine_execution import (
    DisabledLiveExecutionGateway, DryRunExecutionGateway, ExecutionIntentBuilder,
    PaperExecutionGateway,
)
from app.engine_paper import PaperRunner
from app.engine_risk.risk_decision import RiskDecision


def intent(payload, mode):
    return ExecutionIntentBuilder().build(
        payload["strategy_decision"], payload["risk_decision"], payload["setup_context"],
        mode, payload["source_window"],
    )


def test_dry_run_acknowledges_locally(approved_payload, monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("unexpected transport call")
    monkeypatch.setattr("socket.socket.connect", fail)
    acknowledgement = DryRunExecutionGateway().submit(intent(approved_payload, "DRY_RUN"))
    assert acknowledgement.status.value == "ACKNOWLEDGED"
    assert acknowledgement.external_order_id is None


def test_gateway_preserves_duplicate_semantics(approved_payload):
    from app.engine_execution import InMemoryIdempotencyRegistry
    registry = InMemoryIdempotencyRegistry()
    builder = ExecutionIntentBuilder(registry=registry)
    args = (approved_payload["strategy_decision"], approved_payload["risk_decision"],
            approved_payload["setup_context"], "DRY_RUN", approved_payload["source_window"])
    builder.build(*args)
    duplicate = builder.build(*args)
    acknowledgement = DryRunExecutionGateway().submit(duplicate)
    assert acknowledgement.status.value == "DUPLICATE"
    assert acknowledgement.reason_codes == ("DUPLICATE_EXECUTION_INTENT",)


def test_paper_gateway_delegates_only_to_engine_paper(approved_payload, monkeypatch):
    risk = RiskDecision(
        risk_decision_id="risk:1", created_at_ms=1, source_strategy_decision_id="strategy:1",
        source_setup_id="setup:1", source_analysis_snapshot_id="analysis:1", symbol="BTCUSDT",
        timeframe="15m", closed_until_ms=1_700_000_000_000,
        risk_status="RISK_PRE_APPROVED_RESEARCH", risk_level="LOW", risk_score=90,
        risk_policy_version="risk-v1", source_decision_status="ALLOW_RESEARCH_TRADE_PLAN",
        source_strategy_type="BREAKOUT_CONTINUATION_RESEARCH", source_strategy_quality="GOOD",
        source_strategy_score=90, direction_hint="BULLISH",
        risk_context={"confirmation_close": 100, "causal_support_level": 95,
                      "causal_target_level": 112.5, "volatility_buffer": 1},
        risk_pre_approved=True, requires_execution_review=True,
    )
    runner = PaperRunner()
    calls = []
    original = runner.process_risk_decision
    monkeypatch.setattr(runner, "process_risk_decision", lambda source: (calls.append(source), original(source))[1])
    acknowledgement = PaperExecutionGateway(runner, {"risk:1": risk}).submit(intent(approved_payload, "PAPER"))
    assert calls == [risk]
    assert acknowledgement.status.value == "ACKNOWLEDGED"
    assert acknowledgement.metadata["paper_plan_id"]
    assert acknowledgement.metadata["intent_values"] == {
        "quantity": "0.25", "reference_price": "100.10",
        "stop_price": "95.00", "target_price": "112.50",
    }
    assert acknowledgement.external_order_id is None


def test_paper_gateway_does_not_run_same_ready_intent_twice(approved_payload, monkeypatch):
    risk = _paper_risk_decision()
    runner = PaperRunner()
    original = runner.process_risk_decision
    calls = []
    monkeypatch.setattr(runner, "process_risk_decision",
                        lambda source: (calls.append(source), original(source))[1])
    gateway = PaperExecutionGateway(runner, {"risk:1": risk})
    ready = intent(approved_payload, "PAPER")
    first = gateway.submit(ready)
    second = gateway.submit(ready)
    assert first.status.value == "ACKNOWLEDGED"
    assert second.status.value == "DUPLICATE"
    assert calls == [risk]


def test_paper_gateway_does_not_run_rejected_or_disabled_intent(payload_copy, monkeypatch):
    risk = _paper_risk_decision()
    runner = PaperRunner()
    calls = []
    monkeypatch.setattr(runner, "process_risk_decision", lambda source: calls.append(source))
    gateway = PaperExecutionGateway(runner, {"risk:1": risk})
    rejected_payload = payload_copy()
    rejected_payload["setup_context"]["quantity"] = "0"
    rejected = intent(rejected_payload, "PAPER")
    disabled = intent(payload_copy(), "LIVE")
    assert gateway.submit(rejected).status.value == "REJECTED"
    assert gateway.submit(disabled).status.value == "REJECTED"
    assert calls == []


def test_paper_runner_exception_becomes_safe_rejection(approved_payload, monkeypatch):
    risk = _paper_risk_decision()
    runner = PaperRunner()
    monkeypatch.setattr(runner, "process_risk_decision",
                        lambda source: (_ for _ in ()).throw(RuntimeError("paper failure")))
    acknowledgement = PaperExecutionGateway(runner, {"risk:1": risk}).submit(
        intent(approved_payload, "PAPER"))
    assert acknowledgement.status.value == "REJECTED"
    assert acknowledgement.reason_codes == ("CONTRACT_MISMATCH",)
    assert acknowledgement.external_order_id is None
    assert "RuntimeError" in acknowledgement.warnings[0]


def test_disabled_live_gateway_always_rejects(approved_payload):
    live_intent = intent(approved_payload, "LIVE")
    acknowledgement = DisabledLiveExecutionGateway().submit(live_intent)
    assert acknowledgement.status.value == "DISABLED"
    assert acknowledgement.reason_codes == ("LIVE_EXECUTION_DISABLED",)


def _paper_risk_decision() -> RiskDecision:
    return RiskDecision(
        risk_decision_id="risk:1", created_at_ms=1, source_strategy_decision_id="strategy:1",
        source_setup_id="setup:1", source_analysis_snapshot_id="analysis:1", symbol="BTCUSDT",
        timeframe="15m", closed_until_ms=1_700_000_000_000,
        risk_status="RISK_PRE_APPROVED_RESEARCH", risk_level="LOW", risk_score=90,
        risk_policy_version="risk-v1", source_decision_status="ALLOW_RESEARCH_TRADE_PLAN",
        source_strategy_type="BREAKOUT_CONTINUATION_RESEARCH", source_strategy_quality="GOOD",
        source_strategy_score=90, direction_hint="BULLISH",
        risk_context={"confirmation_close": 100, "causal_support_level": 95,
                      "causal_target_level": 112.5, "volatility_buffer": 1},
        risk_pre_approved=True, requires_execution_review=True,
    )
