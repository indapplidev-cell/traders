from app.gates.gate_policy_models import (
    GateDirection,
    GatePolicyDecision,
    GatePolicyInput,
)
from app.gates.gate_policy_service import GatePolicyService


def test_gate_policy_allows_good_long_signal() -> None:
    service = GatePolicyService()

    result = service.evaluate(
        GatePolicyInput(
            regime="trend_up",
            direction=GateDirection.LONG,
            confidence=0.72,
            tp_before_sl_probability=0.61,
            risk_score=0.30,
            model_total_r=12.0,
            baseline_total_r=5.0,
            model_profit_factor=1.35,
            baseline_profit_factor=1.05,
            sample_count=80,
        )
    )

    assert result.allowed is True
    assert result.decision == GatePolicyDecision.ALLOW_LONG
    assert result.direction == GateDirection.LONG
    assert result.reasons == ("signal_passed_gate_policy",)


def test_gate_policy_allows_good_short_signal() -> None:
    service = GatePolicyService()

    result = service.evaluate(
        GatePolicyInput(
            regime="trend_down",
            direction="DOWN",
            confidence=0.70,
            tp_before_sl_probability=0.59,
            risk_score=0.25,
            model_total_r=8.0,
            baseline_total_r=2.0,
            model_profit_factor=1.25,
            baseline_profit_factor=1.00,
            sample_count=60,
        )
    )

    assert result.allowed is True
    assert result.decision == GatePolicyDecision.ALLOW_SHORT
    assert result.direction == GateDirection.SHORT


def test_gate_policy_blocks_flat_signal() -> None:
    service = GatePolicyService()

    result = service.evaluate(
        GatePolicyInput(
            regime="trend_up",
            direction="FLAT",
            confidence=0.90,
            tp_before_sl_probability=0.80,
        )
    )

    assert result.allowed is False
    assert result.decision == GatePolicyDecision.BLOCK
    assert result.reasons == ("direction_is_not_tradeable",)


def test_gate_policy_blocks_bad_regime() -> None:
    service = GatePolicyService()

    result = service.evaluate(
        GatePolicyInput(
            regime="range",
            direction="LONG",
            confidence=0.90,
            tp_before_sl_probability=0.80,
        )
    )

    assert result.allowed is False
    assert result.decision == GatePolicyDecision.BAD_REGIME
    assert result.reasons == ("regime_is_not_trusted",)


def test_gate_policy_blocks_unknown_regime() -> None:
    service = GatePolicyService()

    result = service.evaluate(
        GatePolicyInput(
            regime="custom_unverified_regime",
            direction="LONG",
            confidence=0.90,
            tp_before_sl_probability=0.80,
        )
    )

    assert result.allowed is False
    assert result.decision == GatePolicyDecision.BAD_REGIME


def test_gate_policy_blocks_low_confidence() -> None:
    service = GatePolicyService()

    result = service.evaluate(
        GatePolicyInput(
            regime="trend_up",
            direction="LONG",
            confidence=0.59,
            tp_before_sl_probability=0.80,
        )
    )

    assert result.allowed is False
    assert result.decision == GatePolicyDecision.LOW_CONFIDENCE
    assert result.reasons == ("confidence_below_threshold",)


def test_gate_policy_blocks_low_tp_before_sl_probability() -> None:
    service = GatePolicyService()

    result = service.evaluate(
        GatePolicyInput(
            regime="trend_up",
            direction="LONG",
            confidence=0.80,
            tp_before_sl_probability=0.54,
        )
    )

    assert result.allowed is False
    assert result.decision == GatePolicyDecision.LOW_CONFIDENCE
    assert result.reasons == ("tp_before_sl_probability_below_threshold",)


def test_gate_policy_blocks_high_risk_score() -> None:
    service = GatePolicyService()

    result = service.evaluate(
        GatePolicyInput(
            regime="trend_up",
            direction="LONG",
            confidence=0.80,
            tp_before_sl_probability=0.70,
            risk_score=0.66,
        )
    )

    assert result.allowed is False
    assert result.decision == GatePolicyDecision.MODEL_UNTRUSTED
    assert result.reasons == ("risk_score_above_threshold",)


def test_gate_policy_blocks_low_sample_count() -> None:
    service = GatePolicyService()

    result = service.evaluate(
        GatePolicyInput(
            regime="trend_up",
            direction="LONG",
            confidence=0.80,
            tp_before_sl_probability=0.70,
            sample_count=29,
        )
    )

    assert result.allowed is False
    assert result.decision == GatePolicyDecision.MODEL_UNTRUSTED
    assert result.reasons == ("sample_count_below_threshold",)


def test_gate_policy_blocks_when_baseline_total_r_is_better() -> None:
    service = GatePolicyService()

    result = service.evaluate(
        GatePolicyInput(
            regime="trend_up",
            direction="LONG",
            confidence=0.80,
            tp_before_sl_probability=0.70,
            risk_score=0.20,
            model_total_r=5.0,
            baseline_total_r=6.0,
            sample_count=100,
        )
    )

    assert result.allowed is False
    assert result.decision == GatePolicyDecision.BASELINE_BETTER
    assert result.reasons == ("baseline_total_r_better_than_model",)


def test_gate_policy_blocks_when_baseline_profit_factor_is_better() -> None:
    service = GatePolicyService()

    result = service.evaluate(
        GatePolicyInput(
            regime="trend_up",
            direction="LONG",
            confidence=0.80,
            tp_before_sl_probability=0.70,
            risk_score=0.20,
            model_total_r=10.0,
            baseline_total_r=5.0,
            model_profit_factor=1.10,
            baseline_profit_factor=1.20,
            sample_count=100,
        )
    )

    assert result.allowed is False
    assert result.decision == GatePolicyDecision.BASELINE_BETTER
    assert result.reasons == ("baseline_profit_factor_better_than_model",)


def test_gate_policy_accepts_direction_aliases() -> None:
    service = GatePolicyService()

    long_result = service.evaluate(
        GatePolicyInput(
            regime="trend_up",
            direction="BUY",
            confidence=0.80,
            tp_before_sl_probability=0.70,
        )
    )

    short_result = service.evaluate(
        GatePolicyInput(
            regime="trend_down",
            direction="SELL",
            confidence=0.80,
            tp_before_sl_probability=0.70,
        )
    )

    assert long_result.decision == GatePolicyDecision.ALLOW_LONG
    assert short_result.decision == GatePolicyDecision.ALLOW_SHORT
