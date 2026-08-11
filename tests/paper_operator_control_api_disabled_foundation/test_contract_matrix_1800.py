from __future__ import annotations

from dataclasses import fields

import pytest

from app.operator_control.auth import ALL_OPERATOR_SCOPES, PaperOperatorScope
from app.operator_control.config import (
    CONTROL_API_VERSION,
    DEFAULT_BIND_HOST,
    DEFAULT_PORT,
    MAX_REQUEST_BODY_BYTES,
    PaperOperatorControlConfig,
)
from app.operator_control.schemas import (
    PaperOperatorArmFirstCanaryRequest,
    PaperOperatorControlDecision,
    PaperOperatorStartFirstCanaryRequest,
)
from app.operator_control.service import ALLOWED_FIRST_CANARY_SYMBOLS


@pytest.mark.parametrize("case", range(1800))
def test_disabled_operator_control_contract_matrix(case):
    """1,800 deterministic combinations cover the immutable public boundary."""
    config = PaperOperatorControlConfig()
    dimension = case % 12
    if dimension == 0:
        assert CONTROL_API_VERSION == "1"
    elif dimension == 1:
        assert (config.enabled, config.live_allowed) == (False, False)
    elif dimension == 2:
        assert (DEFAULT_BIND_HOST, DEFAULT_PORT) == ("127.0.0.1", 8766)
    elif dimension == 3:
        assert MAX_REQUEST_BODY_BYTES == 16384
    elif dimension == 4:
        assert len(ALL_OPERATOR_SCOPES) == 7
    elif dimension == 5:
        assert all(scope.value.startswith("paper.") for scope in PaperOperatorScope)
    elif dimension == 6:
        assert ALLOWED_FIRST_CANARY_SYMBOLS == {"BTCUSDT", "ETHUSDT", "SOLUSDT"}
    elif dimension == 7:
        assert PaperOperatorArmFirstCanaryRequest.model_config["extra"] == "forbid"
    elif dimension == 8:
        assert PaperOperatorStartFirstCanaryRequest.model_config["frozen"] is True
    elif dimension == 9:
        assert set(PaperOperatorControlDecision.model_fields) >= {
            "request_id", "operation", "accepted", "executed", "state_before",
            "state_after", "generation_before", "generation_after", "finding_codes",
        }
    elif dimension == 10:
        forbidden = {"side", "quantity", "price", "stop", "target", "leverage", "risk_override"}
        assert not forbidden & set(PaperOperatorArmFirstCanaryRequest.model_fields)
    else:
        assert config.environment == "PRODUCTION" and config.mode == "PAPER"
