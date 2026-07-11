from __future__ import annotations

import json
from pathlib import Path

from app.market_interpreter import L1TimelineConsumer, L1TimelineConsumerConfig, L2TimelineTableFormatter
from app.market_interpreter.context_rules import (
    MarketContextState,
    SymbolBucket,
    SymbolBucketDecision,
    classify_overall_market_context,
    classify_symbol_bucket,
)


def test_classify_symbol_bucket_insufficient_data() -> None:
    decision = classify_symbol_bucket(_row(status="INSUFFICIENT_DATA"))

    assert decision.bucket == SymbolBucket.INSUFFICIENT_DATA
    assert "L1_INSUFFICIENT_DATA" in decision.reason_codes


def test_classify_symbol_bucket_error() -> None:
    decision = classify_symbol_bucket(_row(status="ERROR"))

    assert decision.bucket == SymbolBucket.ERROR
    assert "L1_ROW_ERROR" in decision.reason_codes


def test_classify_symbol_bucket_unknown_is_skip_candidate() -> None:
    decision = classify_symbol_bucket(_row(current_regime="UNKNOWN", stability="STABLE"))

    assert decision.bucket == SymbolBucket.UNKNOWN
    assert decision.skip_candidate is True
    assert "CURRENT_REGIME_UNKNOWN" in decision.reason_codes
    assert "SKIP_CANDIDATE_CONTEXT" in decision.reason_codes


def test_classify_symbol_bucket_stable_flat() -> None:
    decision = classify_symbol_bucket(_row(current_regime="FLAT", stability="STABLE", last_transition="NO_CHANGE"))

    assert decision.bucket == SymbolBucket.STABLE_FLAT
    assert decision.skip_candidate is False
    assert decision.reason_codes == ("STABLE_FLAT_CONTEXT",)


def test_classify_symbol_bucket_up_clean_trend() -> None:
    decision = classify_symbol_bucket(_row(current_regime="UP", confidence=0.74))

    assert decision.bucket == SymbolBucket.CLEAN_TREND
    assert decision.skip_candidate is False
    assert decision.reason_codes == ("CURRENT_TREND_CONTEXT", "CURRENT_UP_CONTEXT", "ACCEPTABLE_CONFIDENCE")


def test_classify_symbol_bucket_down_clean_trend() -> None:
    decision = classify_symbol_bucket(_row(current_regime="DOWN", confidence=0.74))

    assert decision.bucket == SymbolBucket.CLEAN_TREND
    assert decision.skip_candidate is False
    assert decision.reason_codes == ("CURRENT_TREND_CONTEXT", "CURRENT_DOWN_CONTEXT", "ACCEPTABLE_CONFIDENCE")


def test_classify_symbol_bucket_low_confidence_transition() -> None:
    decision = classify_symbol_bucket(_row(current_regime="UP", last_transition="FLAT_TO_UP", confidence=0.41))

    assert decision.bucket == SymbolBucket.TRANSITIONING
    assert decision.skip_candidate is False
    assert decision.reason_codes == ("RECENT_REGIME_TRANSITION",)


def test_classify_symbol_bucket_unstable_is_skip_candidate() -> None:
    decision = classify_symbol_bucket(_row(current_regime="FLAT", stability="UNSTABLE"))

    assert decision.bucket == SymbolBucket.UNSTABLE
    assert decision.skip_candidate is True
    assert "UNSTABLE_TIMELINE_CONTEXT" in decision.reason_codes
    assert "SKIP_CANDIDATE_CONTEXT" in decision.reason_codes


def test_skip_candidate_truth_table() -> None:
    skip_buckets = {
        classify_symbol_bucket(_row(current_regime="UNKNOWN")).bucket,
        classify_symbol_bucket(_row(stability="UNSTABLE")).bucket,
        classify_symbol_bucket(_row(status="INSUFFICIENT_DATA")).bucket,
        classify_symbol_bucket(_row(status="ERROR")).bucket,
    }
    keep_buckets = {
        classify_symbol_bucket(_row(current_regime="UP")).bucket,
        classify_symbol_bucket(_row(current_regime="FLAT", stability="STABLE")).bucket,
        classify_symbol_bucket(_row(current_regime="UP", last_transition="FLAT_TO_UP", confidence=0.2)).bucket,
    }

    assert skip_buckets == {
        SymbolBucket.UNKNOWN,
        SymbolBucket.UNSTABLE,
        SymbolBucket.INSUFFICIENT_DATA,
        SymbolBucket.ERROR,
    }
    assert keep_buckets == {SymbolBucket.CLEAN_TREND, SymbolBucket.STABLE_FLAT, SymbolBucket.TRANSITIONING}


def test_overall_context_majority_stable_flat_is_ranging() -> None:
    state = classify_overall_market_context((_decision("A", SymbolBucket.STABLE_FLAT), _decision("B", SymbolBucket.STABLE_FLAT), _decision("C", SymbolBucket.CLEAN_TREND)))

    assert state == MarketContextState.RANGING


def test_overall_context_majority_clean_trend_same_direction_is_trending() -> None:
    state = classify_overall_market_context(
        (
            _decision("BTCUSDT", SymbolBucket.CLEAN_TREND, regime="UP"),
            _decision("ETHUSDT", SymbolBucket.CLEAN_TREND, regime="UP"),
            _decision("SOLUSDT", SymbolBucket.STABLE_FLAT, regime="FLAT"),
        )
    )

    assert state == MarketContextState.TRENDING


def test_overall_context_conflicting_clean_trends_is_mixed() -> None:
    state = classify_overall_market_context(
        (
            _decision("BTCUSDT", SymbolBucket.CLEAN_TREND, regime="UP"),
            _decision("ETHUSDT", SymbolBucket.CLEAN_TREND, regime="DOWN"),
        )
    )

    assert state == MarketContextState.MIXED


def test_overall_context_majority_unstable_or_transitioning_is_unstable() -> None:
    state = classify_overall_market_context(
        (
            _decision("A", SymbolBucket.UNSTABLE),
            _decision("B", SymbolBucket.TRANSITIONING),
            _decision("C", SymbolBucket.STABLE_FLAT),
        )
    )

    assert state == MarketContextState.UNSTABLE


def test_overall_context_all_unknownish_is_unknown() -> None:
    state = classify_overall_market_context(
        (
            _decision("A", SymbolBucket.UNKNOWN),
            _decision("B", SymbolBucket.INSUFFICIENT_DATA),
            _decision("C", SymbolBucket.ERROR),
        )
    )

    assert state == MarketContextState.UNKNOWN


def test_terminal_formatter_includes_bucket_and_skip_columns(tmp_path: Path) -> None:
    result = L1TimelineConsumer().run(L1TimelineConsumerConfig(input_path=_write_payload(tmp_path)))
    output = L2TimelineTableFormatter().format(result, input_path=tmp_path / "timeline_preview.json")

    assert "Bucket" in output
    assert "Skip" in output
    assert "Quality" in output
    assert "Rank" in output
    assert "Overall state" in output
    assert "Safety" in output


def test_details_mode_includes_context_reason_codes(tmp_path: Path) -> None:
    result = L1TimelineConsumer().run(L1TimelineConsumerConfig(input_path=_write_payload(tmp_path)))
    output = L2TimelineTableFormatter().format(result, input_path=tmp_path / "timeline_preview.json", show_details=True)

    assert "context_reason_codes" in output
    assert "Quality reason codes" in output
    assert "ACCEPTABLE_CONFIDENCE" in output
    assert "SKIP_CANDIDATE_CONTEXT" in output


def test_json_export_includes_bucket_fields(tmp_path: Path) -> None:
    input_path = _write_payload(tmp_path)
    output_dir = tmp_path / "book_l2"

    L1TimelineConsumer().run(L1TimelineConsumerConfig(input_path=input_path, export_json=True, output_dir=output_dir))
    payload = json.loads((output_dir / "timeline_context.json").read_text(encoding="utf-8"))
    first_symbol = payload["result"]["symbols"][0]
    market_context = payload["result"]["market_context"]

    assert first_symbol["bucket"] == "CLEAN_TREND"
    assert first_symbol["skip_candidate"] is False
    assert "context_reason_codes" in first_symbol
    assert "context_quality_score" in first_symbol
    assert "context_quality_grade" in first_symbol
    assert "context_rank" in first_symbol
    assert "context_quality_reason_codes" in first_symbol
    assert market_context["overall_state"] == "MIXED"
    assert market_context["bucket_counts"]["CLEAN_TREND"] == 1
    assert market_context["skip_candidate_count"] == 1
    assert payload["result"]["summary"]["quality_summary"]["HIGH"] >= 1
    assert "top_ranked_symbols" in payload["result"]["summary"]


def test_json_export_includes_fail_closed_safety(tmp_path: Path) -> None:
    input_path = _write_payload(tmp_path)
    output_dir = tmp_path / "book_l2"

    L1TimelineConsumer().run(L1TimelineConsumerConfig(input_path=input_path, export_json=True, output_dir=output_dir))
    safety = json.loads((output_dir / "timeline_context.json").read_text(encoding="utf-8"))["safety"]

    assert safety["trade_signal"] == "NOT_EVALUATED"
    assert safety["safe_for_runtime_trading"] is False
    assert safety["orders_enabled"] is False
    assert safety["live_trading_connected"] is False
    assert safety["traders_core_connected"] is False
    assert safety["approved_for_live_trading"] is False
    assert safety["approved_for_auto_activation"] is False


def test_forbidden_imports_are_absent_in_market_interpreter() -> None:
    forbidden = (
        "CandleRepository",
        "MarketReaderOrchestrator",
        "app.market_reader.market_reader",
        "app.storage",
        "app.data",
        "binance",
        "ccxt",
    )
    import_lines: list[str] = []
    for path in Path("app/market_interpreter").glob("*.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                import_lines.append(stripped)
    sources = "\n".join(import_lines)

    for token in forbidden:
        assert token not in sources


def _row(
    *,
    symbol: str = "BTCUSDT",
    status: str = "OK",
    current_regime: str = "UP",
    stability: str = "CHANGING",
    last_transition: str = "NO_CHANGE",
    confidence: float = 0.8,
    regimes: tuple[str, ...] | None = None,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "status": status,
        "current_regime": current_regime,
        "stability": stability,
        "last_transition": last_transition,
        "confidence": confidence,
        "current_confidence": confidence,
        "regimes": regimes or (current_regime,),
    }


def _decision(symbol: str, bucket: SymbolBucket, *, regime: str = "FLAT") -> SymbolBucketDecision:
    return SymbolBucketDecision(
        symbol=symbol,
        bucket=bucket,
        regime=regime,
        stability="STABLE",
        last_transition="NO_CHANGE",
        confidence=0.8,
        skip_candidate=bucket in {SymbolBucket.UNKNOWN, SymbolBucket.UNSTABLE, SymbolBucket.INSUFFICIENT_DATA, SymbolBucket.ERROR},
    )


def _write_payload(tmp_path: Path) -> Path:
    path = tmp_path / "timeline_preview.json"
    payload = {
        "status": "ok",
        "service": "BOOK_L1_MARKET_READER",
        "report_type": "timeline_preview",
        "contract_version": "book_l1_json_export_v1",
        "request": {},
        "result": {
            "rows": [
                _row(symbol="BTCUSDT", current_regime="UP", confidence=0.74),
                _row(symbol="ETHUSDT", current_regime="UNKNOWN", stability="UNSTABLE", last_transition="TO_UNKNOWN", confidence=0.41),
                _row(symbol="SOLUSDT", current_regime="FLAT", stability="STABLE", confidence=0.88),
            ]
        },
        "summary": {},
        "safety": {
            "trade_signal": "NOT_EVALUATED",
            "safe_for_runtime_trading": False,
            "orders_enabled": False,
            "live_trading_connected": False,
            "traders_core_connected": False,
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "model_training_executed": False,
            "binance_download_executed": False,
        },
        "warnings": [],
        "errors": [],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
