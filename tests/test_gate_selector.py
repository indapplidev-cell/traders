from app.validation.gate_selector import GateSelector


def test_gate_selector_uses_validation_rules_only() -> None:
    selector = GateSelector()
    gate_results = [
        {
            "gate_type": "max_prob",
            "threshold": 0.4,
            "signal_count": 20,
            "profit_factor": 3.0,
            "total_r": 10.0,
            "expectancy_r": 0.5,
            "long_count": 20,
            "short_count": 0,
            "max_drawdown_r": 1.0,
        },
        {
            "gate_type": "directional_edge",
            "threshold": 0.05,
            "signal_count": 35,
            "profit_factor": 1.5,
            "total_r": 4.0,
            "expectancy_r": 0.1,
            "long_count": 18,
            "short_count": 2,
            "max_drawdown_r": 2.0,
        },
    ]

    result = selector.select(gate_results)

    assert result["selected_gate"]["gate_type"] == "directional_edge"
    assert result["selected_gate"]["threshold"] == 0.05


def test_gate_selector_returns_null_when_no_validation_gate_passed() -> None:
    selector = GateSelector()

    result = selector.select(
        [
            {
                "gate_type": "max_prob",
                "threshold": 0.4,
                "signal_count": 10,
                "profit_factor": 1.2,
                "total_r": 2.0,
                "expectancy_r": 0.2,
                "long_count": 10,
                "short_count": 0,
                "max_drawdown_r": 1.0,
            }
        ]
    )

    assert result["selected_gate"] is None
    assert result["reject_reason"] == "no_validation_gate_passed"
