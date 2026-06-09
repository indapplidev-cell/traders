import json

from app.gates.gate_policy_prediction_contract import (
    GatePolicyPredictionPayloadContract,
)


def test_gate_policy_prediction_contract_defines_required_fields() -> None:
    contract = GatePolicyPredictionPayloadContract()

    assert contract.required_fields == (
        "regime",
        "direction",
        "confidence",
        "tp_before_sl_probability",
    )

    assert contract.is_required_field("regime") is True
    assert contract.is_required_field("direction") is True
    assert contract.is_required_field("confidence") is True
    assert contract.is_required_field("tp_before_sl_probability") is True
    assert contract.is_required_field("risk_score") is False


def test_gate_policy_prediction_contract_defines_optional_fields() -> None:
    contract = GatePolicyPredictionPayloadContract()

    expected_optional_fields = {
        "risk_score",
        "expected_move_atr",
        "model_total_r",
        "baseline_total_r",
        "model_profit_factor",
        "baseline_profit_factor",
        "sample_count",
    }

    assert set(contract.optional_fields) == expected_optional_fields

    for field_name in expected_optional_fields:
        assert contract.is_optional_field(field_name) is True
        assert contract.is_known_field(field_name) is True


def test_gate_policy_prediction_contract_resolves_aliases() -> None:
    contract = GatePolicyPredictionPayloadContract()

    assert contract.canonical_field_for_alias("market_regime") == "regime"
    assert contract.canonical_field_for_alias("predicted_direction") == "direction"
    assert contract.canonical_field_for_alias("model_confidence") == "confidence"
    assert (
        contract.canonical_field_for_alias("tp_before_sl_prob")
        == "tp_before_sl_probability"
    )
    assert contract.canonical_field_for_alias("model_risk_score") == "risk_score"
    assert contract.canonical_field_for_alias("expected_atr_move") == "expected_move_atr"
    assert contract.canonical_field_for_alias("ml_total_r") == "model_total_r"
    assert contract.canonical_field_for_alias("baseline_r") == "baseline_total_r"
    assert contract.canonical_field_for_alias("ml_profit_factor") == "model_profit_factor"
    assert contract.canonical_field_for_alias("samples") == "sample_count"


def test_gate_policy_prediction_contract_unknown_alias_returns_none() -> None:
    contract = GatePolicyPredictionPayloadContract()

    assert contract.canonical_field_for_alias("unknown_field") is None
    assert contract.canonical_field_for_alias("") is None


def test_gate_policy_prediction_contract_normalizes_direction_aliases() -> None:
    contract = GatePolicyPredictionPayloadContract()

    assert contract.normalize_direction_alias("UP") == "LONG"
    assert contract.normalize_direction_alias("BUY") == "LONG"
    assert contract.normalize_direction_alias("LONG") == "LONG"

    assert contract.normalize_direction_alias("DOWN") == "SHORT"
    assert contract.normalize_direction_alias("SELL") == "SHORT"
    assert contract.normalize_direction_alias("SHORT") == "SHORT"

    assert contract.normalize_direction_alias("FLAT") == "FLAT"
    assert contract.normalize_direction_alias("SIDEWAYS") == "FLAT"

    assert contract.normalize_direction_alias("NONE") == "NONE"
    assert contract.normalize_direction_alias("NO_TRADE") == "NONE"
    assert contract.normalize_direction_alias("bad") == "NONE"


def test_gate_policy_prediction_contract_defines_known_regimes() -> None:
    contract = GatePolicyPredictionPayloadContract()

    assert "trend_up" in contract.known_regime_values
    assert "trend_down" in contract.known_regime_values
    assert "breakout_setup" in contract.known_regime_values
    assert "range" in contract.known_regime_values
    assert "high_volatility" in contract.known_regime_values
    assert "low_volatility" in contract.known_regime_values
    assert "low_liquidity" in contract.known_regime_values
    assert "unknown" in contract.known_regime_values


def test_gate_policy_prediction_contract_to_dict_is_json_safe() -> None:
    contract = GatePolicyPredictionPayloadContract()

    payload = contract.to_dict()

    assert payload["required_fields"] == [
        "regime",
        "direction",
        "confidence",
        "tp_before_sl_probability",
    ]

    assert "risk_score" in payload["optional_fields"]
    assert payload["field_aliases"]["regime"] == [
        "regime",
        "market_regime",
        "detected_regime",
    ]
    assert payload["direction_aliases"]["BUY"] == "LONG"
    assert "trend_up" in payload["known_regime_values"]

    json.dumps(payload, ensure_ascii=False)
