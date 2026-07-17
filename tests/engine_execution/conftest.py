from __future__ import annotations

from copy import deepcopy

import pytest


@pytest.fixture
def approved_payload() -> dict:
    return {
        "strategy_decision": {
            "decision_id": "strategy:1", "source_setup_id": "setup:1",
            "symbol": "BTCUSDT", "timeframe": "15m", "closed_until_ms": 1_700_000_000_000,
            "decision_status": "APPROVED", "side": "BUY",
        },
        "risk_decision": {
            "risk_decision_id": "risk:1", "source_strategy_decision_id": "strategy:1",
            "source_setup_id": "setup:1", "symbol": "BTCUSDT", "timeframe": "15m",
            "closed_until_ms": 1_700_000_000_000, "risk_status": "RISK_APPROVED", "side": "BUY",
        },
        "setup_context": {
            "setup_id": "setup:1", "risk_decision_id": "risk:1", "symbol": "BTCUSDT",
            "side": "BUY", "order_type": "MARKET_INTENT", "quantity": "0.25",
            "reference_price": "100.10", "limit_price": None, "stop_price": "95.00",
            "target_price": "112.50", "time_in_force": None, "reduce_only": False,
            "metadata": {"source": "focused-test"},
        },
        "source_window": {
            "timeframe": "15m", "closed_until_ms": 1_700_000_000_000, "is_closed": True,
        },
    }


@pytest.fixture
def payload_copy(approved_payload):
    return lambda: deepcopy(approved_payload)
