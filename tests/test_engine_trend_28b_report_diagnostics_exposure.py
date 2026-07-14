from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from app.market_reader.engine_trend.offline_report_diagnostics import (
    attach_contextual_diagnostics,
)
from app.market_reader.engine_trend.data_source_boundary import (
    CandleDataRequest,
    build_candle_data_batch,
    run_engine_trend_from_batch,
)
from scripts.engine_trend_18_hypothesis_replay import build_diagnostic


ROOT = Path(__file__).resolve().parents[1]
REPLAY = ROOT / "reports" / "engine_trend" / "hypothesis_replay" / "json"


def _load(name: str) -> dict[str, object]:
    return json.loads((REPLAY / name).read_text(encoding="utf-8"))


def test_unknown_replay_artifact_gets_diagnostics_without_decision_changes() -> None:
    source = _load("btc_15m_expected_unknown_or_mixed_001.json")
    source["setup_eligibility"] = {"eligible": False, "reason": "source_contract"}
    before = deepcopy(source)

    exposed = attach_contextual_diagnostics(source)
    diagnostics = exposed.pop("contextual_diagnostics")

    assert exposed == before
    assert source == before
    assert diagnostics["source_regime"] == "UNKNOWN"
    assert diagnostics["action"] == "NO_ACTION"
    assert {"WAIT_FOR_CONFIRMATION", "NO_ACTION"} <= set(
        diagnostics["diagnostic_tags"]
    )
    assert exposed["composer"]["regime"] == "UNKNOWN"
    assert exposed["comparison"]["new_regime"] == "UNKNOWN"
    assert exposed["setup_eligibility"] == before["setup_eligibility"]
    assert exposed["safety"]["trade_signal"] == "NOT_EVALUATED"
    assert diagnostics["safety"]["trade_signal_created"] is False
    assert diagnostics["artifact_contract"]["trade_signal_created"] is False


def test_flat_replay_artifact_stays_flat_with_confirmed_range_context() -> None:
    source = _load("sol_15m_expected_flat_001.json")
    exposed = attach_contextual_diagnostics(source)
    diagnostics = exposed["contextual_diagnostics"]

    assert source["composer"]["regime"] == "FLAT"
    assert exposed["composer"]["regime"] == "FLAT"
    assert exposed["comparison"] == source["comparison"]
    assert "CONFIRMED_RANGE_CONTEXT" in diagnostics["diagnostic_tags"]
    assert diagnostics["contextual_state"] == "CONTEXT_ONLY"
    assert diagnostics["action"] == "NO_ACTION"


def test_historical_missing_fields_are_not_observable_not_false() -> None:
    source = _load("btc_15m_expected_unknown_or_mixed_001.json")
    diagnostics = attach_contextual_diagnostics(source)["contextual_diagnostics"]

    assert diagnostics["observability"]["price_position"] == "not_observable"
    assert diagnostics["observability"]["zones"] == "observable"
    assert diagnostics["observability"]["zone_proximity"] == "not_observable"
    assert diagnostics["observability"]["indicators"] == "not_observable"
    assert diagnostics["observability"]["multi_timeframe"] == "not_observable"
    assert diagnostics["price_position"]["last_close"] is None
    assert "NEAR_SUPPORT" not in diagnostics["diagnostic_tags"]
    assert "NEAR_RESISTANCE" not in diagnostics["diagnostic_tags"]


def test_candle_backed_replay_makes_price_and_zone_diagnostics_observable() -> None:
    source = _load("btc_15m_expected_unknown_or_mixed_001.json")
    candles = (
        {"high": 103500.0, "low": 102000.0, "close": 103500.0},
    )
    diagnostics = attach_contextual_diagnostics(source, candles=candles)[
        "contextual_diagnostics"
    ]

    assert diagnostics["observability"]["price_position"] == "observable"
    assert diagnostics["observability"]["zones"] == "observable"
    assert diagnostics["observability"]["zone_proximity"] == "observable"
    assert diagnostics["price_position"]["last_close"] == 103500.0
    assert "NEAR_RESISTANCE" in diagnostics["diagnostic_tags"]
    assert "BREAKOUT_NOT_CONFIRMED" in diagnostics["diagnostic_tags"]
    assert diagnostics["action"] == "NO_ACTION"


def test_replay_generator_attaches_diagnostics_after_finalized_engine_result() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
    for index in range(96):
        close = 100.0 + ((index % 8) - 4) * 0.15
        rows.append(
            {
                "timestamp": (start + timedelta(minutes=15 * index)).isoformat(),
                "open": close - 0.05,
                "high": close + 0.25,
                "low": close - 0.25,
                "close": close,
                "volume": 10.0,
            }
        )
    request = CandleDataRequest("TESTUSDT", "15m", 96)
    boundary = run_engine_trend_from_batch(
        build_candle_data_batch(request, rows, min_candle_count=96)
    )
    finalized = boundary.engine_output.composer_output.result
    window = {
        "source_stage": "TEST",
        "old": {
            "engine_market_regime": finalized.market_regime.value,
            "confidence": finalized.confidence,
        },
        "window_id": "generated_offline_replay",
        "symbol": "TESTUSDT",
        "interval": "15m",
        "period_start": rows[0]["timestamp"],
        "period_end": rows[-1]["timestamp"],
        "window_length": 96,
        "reference_label": "RECENT_BASELINE",
        "selection_reason": "test",
    }

    artifact = build_diagnostic(window, boundary)

    assert "contextual_diagnostics" in artifact
    assert artifact["composer"]["regime"] == finalized.market_regime.value
    assert artifact["composer"]["confidence"] == finalized.confidence
    assert artifact["safety"] == finalized.safety.to_dict()
    assert artifact["contextual_diagnostics"]["source_regime"] == finalized.market_regime.value
    assert artifact["contextual_diagnostics"]["safety"]["setup_created"] is False
    assert artifact["contextual_diagnostics"]["safety"]["trade_signal_created"] is False
