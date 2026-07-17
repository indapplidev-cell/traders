import pytest

from app.engine_orchestrator.pipeline_result import PipelineResult, SafetyCounters


def test_result_vocab_and_zero_safety():
    result = PipelineResult("BTCUSDT", "15m", 1)
    assert not result.safety_counters.has_violation
    assert SafetyCounters(future_bars_used_count=1).has_violation
    with pytest.raises(ValueError):
        PipelineResult("BTCUSDT", "15m", 1, final_result="UNSUPPORTED")
