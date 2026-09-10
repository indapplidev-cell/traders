from __future__ import annotations

import pytest

from app.config.yaml_authority import RUNTIME_POLICY, RuntimePolicy
from scripts.check_yaml_authority import scan_text_for_policy_literals


@pytest.mark.parametrize(
    "source,reason",
    (
        ("MIN_RR = 1.5", "LITERAL_POLICY_ASSIGNMENT:MIN_RR"),
        ("TIMEOUT = 900", "LITERAL_POLICY_ASSIGNMENT:TIMEOUT"),
        ("value = config.get('x', 20)", "LITERAL_POLICY_FALLBACK:get"),
        ("value = getattr(cfg, 'x', 0.03)", "LITERAL_POLICY_FALLBACK:getattr"),
        (
            "parser.add_argument('--budget', default=5000)",
            "LITERAL_POLICY_FALLBACK:add_argument",
        ),
        ("DESKTOP_TIMEOUT = 12", "LITERAL_POLICY_ASSIGNMENT:DESKTOP_TIMEOUT"),
        ("RESEARCH_RISK = 0.1", "LITERAL_POLICY_ASSIGNMENT:RESEARCH_RISK"),
    ),
)
def test_adversarial_python_policy_literals_fail(source, reason):
    assert reason in scan_text_for_policy_literals(source)


def test_missing_required_runtime_yaml_key_fails():
    raw = RUNTIME_POLICY.model_dump(mode="python")
    del raw["analysis_algorithms"]["regime_min_score"]
    with pytest.raises(Exception):
        RuntimePolicy.model_validate(raw)


def test_5m_profile_cannot_fallback_to_15m():
    raw = RUNTIME_POLICY.model_dump(mode="python")
    raw["profiles"]["trade-5m-v2"]["trigger_timeframe"] = "15m"
    raw["profiles"]["trade-5m-v2"]["trade_mode"] = "SCALPING"
    with pytest.raises(Exception, match="cannot fall back to 15m"):
        RuntimePolicy.model_validate(raw)
