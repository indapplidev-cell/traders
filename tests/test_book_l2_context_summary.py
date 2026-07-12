from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from app.market_interpreter import (
    L1TimelineConsumer,
    L1TimelineConsumerConfig,
    L2TimelineTableFormatter,
    MarketBriefConfig,
    SymbolBrief,
    build_market_brief,
    build_market_brief_lines,
    select_best_observation_candidates,
    select_skip_candidates,
)
from app.market_interpreter.context_summary import (
    FORBIDDEN_BRIEF_TERMS,
    market_brief_to_dict,
    validate_market_brief_safety,
)
from app.market_interpreter.l1_timeline_consumer import _validate_l2_result_contract


def test_market_brief_config_defaults() -> None:
    config = MarketBriefConfig()

    assert config.max_observation_candidates == 3
    assert config.max_skip_candidates == 5
    assert config.min_high_quality_score == 0.70
    assert config.min_medium_quality_score == 0.45


def test_select_best_observation_candidates_excludes_skip_candidate() -> None:
    candidates = select_best_observation_candidates((_brief("BTCUSDT", skip_candidate=True), _brief("ETHUSDT")))

    assert [candidate.symbol for candidate in candidates] == ["ETHUSDT"]


def test_select_best_observation_candidates_sorts_deterministically() -> None:
    candidates = select_best_observation_candidates(
        (
            _brief("BBB", score=0.82, rank=2),
            _brief("AAA", score=0.82, rank=2),
            _brief("CCC", score=0.90, rank=3),
            _brief("DDD", score=0.82, rank=1),
        ),
        config=MarketBriefConfig(max_observation_candidates=4),
    )

    assert [candidate.symbol for candidate in candidates] == ["CCC", "DDD", "AAA", "BBB"]


def test_select_skip_candidates_includes_skip_candidates() -> None:
    candidates = select_skip_candidates((_brief("BTCUSDT"), _brief("SOLUSDT", skip_candidate=True, bucket="UNSTABLE", grade="SKIP", score=0.18)))

    assert [candidate.symbol for candidate in candidates] == ["SOLUSDT"]


def test_select_skip_candidates_includes_flat_context() -> None:
    candidates = select_skip_candidates((_brief("BTCUSDT", bucket="FLAT_CONTEXT", grade="LOW", score=0.40),))

    assert [candidate.symbol for candidate in candidates] == ["BTCUSDT"]


def test_build_brief_state_clean_context_available() -> None:
    brief = build_market_brief((_brief("BTCUSDT", bucket="CLEAN_TREND", grade="HIGH", score=0.91),), overall_state="MIXED")

    assert brief.brief_state == "CLEAN_CONTEXT_AVAILABLE"


def test_build_brief_state_flat_heavy() -> None:
    brief = build_market_brief(
        (
            _brief("BTCUSDT", bucket="FLAT_CONTEXT", grade="LOW", score=0.40, skip_candidate=True),
            _brief("ETHUSDT", bucket="STABLE_FLAT", grade="LOW", score=0.39),
            _brief("SOLUSDT", bucket="TRANSITIONING", grade="LOW", score=0.37),
        ),
        overall_state="RANGING",
    )

    assert brief.brief_state == "FLAT_HEAVY_CONTEXT"
    assert any("FLAT_CONTEXT" in point for point in brief.key_points)


def test_build_brief_state_unstable_context() -> None:
    brief = build_market_brief(
        (
            _brief("BTCUSDT", bucket="UNSTABLE", grade="SKIP", skip_candidate=True, score=0.10),
            _brief("ETHUSDT", bucket="UNSTABLE", grade="SKIP", skip_candidate=True, score=0.11),
            _brief("SOLUSDT", bucket="STABLE_FLAT", grade="LOW", score=0.35),
        ),
        overall_state="MIXED",
    )

    assert brief.brief_state == "UNSTABLE_CONTEXT"


def test_build_brief_state_unknown_context() -> None:
    brief = build_market_brief((_brief("BTCUSDT", bucket="UNKNOWN", grade="SKIP", skip_candidate=True),), overall_state="UNKNOWN")

    assert brief.brief_state == "UNKNOWN_CONTEXT"


def test_build_brief_state_error_context_when_no_valid_rows() -> None:
    assert build_market_brief((), overall_state="ERROR").brief_state == "ERROR_CONTEXT"
    assert build_market_brief((_brief("ERR", bucket="ERROR", grade="ERROR"),), overall_state="ERROR").brief_state == "ERROR_CONTEXT"


def test_key_points_include_overall_observation_and_skip_candidates() -> None:
    brief = build_market_brief(
        (
            _brief("BTCUSDT", bucket="CLEAN_TREND", grade="HIGH", score=0.91, rank=1),
            _brief("SOLUSDT", bucket="UNSTABLE", grade="SKIP", skip_candidate=True, score=0.18),
        ),
        overall_state="MIXED",
    )
    text = "\n".join(brief.key_points)

    assert "Overall context is MIXED." in text
    assert "Best observation candidates: BTCUSDT." in text
    assert "Skip candidates: SOLUSDT." in text


def test_safety_note_is_present_and_observe_only() -> None:
    brief = build_market_brief((_brief("BTCUSDT"),), overall_state="MIXED")

    assert "Observe-only" in brief.safety_note
    assert "Runtime action is not approved" in brief.safety_note


def test_human_brief_text_does_not_contain_forbidden_trade_terms() -> None:
    brief = build_market_brief(
        (
            _brief("BTCUSDT", bucket="CLEAN_TREND", grade="HIGH"),
            _brief("SOLUSDT", bucket="UNSTABLE", grade="SKIP", skip_candidate=True),
        ),
        overall_state="MIXED",
    )
    human_text = "\n".join(
        (
            brief.brief_state,
            brief.safety_note,
            *brief.key_points,
            *(candidate.main_reason for candidate in brief.observation_candidates),
            *(candidate.main_reason for candidate in brief.skip_candidates),
        )
    ).upper()

    for term in FORBIDDEN_BRIEF_TERMS:
        assert term not in human_text


def test_market_brief_serializes_to_dict_and_json() -> None:
    brief = build_market_brief((_brief("BTCUSDT"),), overall_state="MIXED")
    payload = market_brief_to_dict(brief)

    assert payload["brief_state"] == "CLEAN_CONTEXT_AVAILABLE"
    assert json.loads(json.dumps(payload))["safety_note"] == brief.safety_note


def test_timeline_context_export_includes_market_brief(tmp_path: Path) -> None:
    output_dir = tmp_path / "book_l2"
    L1TimelineConsumer().run(
        L1TimelineConsumerConfig(input_path=_write_payload(tmp_path), export_json=True, output_dir=output_dir)
    )
    payload = json.loads((output_dir / "timeline_context.json").read_text(encoding="utf-8"))

    assert "market_brief" in payload["result"]
    assert "observation_candidates" in payload["result"]["market_brief"]
    assert "skip_candidates" in payload["result"]["market_brief"]
    assert "key_points" in payload["result"]["market_brief"]
    assert "safety_note" in payload["result"]["market_brief"]


def test_strict_validation_requires_market_brief(tmp_path: Path) -> None:
    result = L1TimelineConsumer().run(L1TimelineConsumerConfig(input_path=_write_payload(tmp_path)))
    broken = replace(result, market_brief=None)

    assert "market_brief is required" in _validate_l2_result_contract(broken)


def test_strict_validation_rejects_skip_observation_candidate() -> None:
    brief = build_market_brief((_brief("BTCUSDT"),), overall_state="MIXED")
    broken = replace(
        brief,
        observation_candidates=(_brief("SOLUSDT", skip_candidate=True, bucket="UNSTABLE", grade="SKIP"),),
    )

    assert any("observation candidate" in error for error in validate_market_brief_safety(broken))


def test_details_output_includes_main_reason(tmp_path: Path) -> None:
    result = L1TimelineConsumer().run(L1TimelineConsumerConfig(input_path=_write_payload(tmp_path)))
    output = L2TimelineTableFormatter().format(result, input_path=tmp_path / "timeline_preview.json", show_details=True)

    assert "Market brief details:" in output
    assert "main_reason:" in output


def test_terminal_formatter_includes_best_observation_candidates(tmp_path: Path) -> None:
    result = L1TimelineConsumer().run(L1TimelineConsumerConfig(input_path=_write_payload(tmp_path)))
    output = L2TimelineTableFormatter().format(result, input_path=tmp_path / "timeline_preview.json")

    assert "Best observation candidates:" in output
    assert "Skip candidates:" in output
    assert "Key points:" in output


def test_market_brief_lines_show_none_when_no_candidates() -> None:
    lines = build_market_brief_lines(build_market_brief((), overall_state="ERROR"))

    assert "- none" in lines


def test_observation_candidates_are_not_named_trade_candidates(tmp_path: Path) -> None:
    output_dir = tmp_path / "book_l2"
    L1TimelineConsumer().run(
        L1TimelineConsumerConfig(input_path=_write_payload(tmp_path), export_json=True, output_dir=output_dir)
    )
    payload_text = (output_dir / "timeline_context.json").read_text(encoding="utf-8")

    assert "observation_candidates" in payload_text
    assert "trade_candidates" not in payload_text
    assert "entry_candidates" not in payload_text
    assert "buy_candidates" not in payload_text


def test_book_l2_still_does_not_import_candle_reader_or_orchestrator() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in Path("app/market_interpreter").glob("*.py"))

    assert "CandleRepository" not in source
    assert "MarketReaderOrchestrator" not in source
    assert "MarketReaderConfig" not in source
    assert "CandleWindow" not in source


def _brief(
    symbol: str,
    *,
    bucket: str = "CLEAN_TREND",
    score: float = 0.82,
    grade: str = "HIGH",
    rank: int | None = 1,
    skip_candidate: bool = False,
) -> SymbolBrief:
    return SymbolBrief(
        symbol=symbol,
        bucket=bucket,
        context_quality_score=score,
        quality_grade=grade,
        context_rank=rank,
        skip_candidate=skip_candidate,
        main_reason="Context requires observation.",
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
                {
                    "symbol": "BTCUSDT",
                    "status": "OK",
                    "regimes": ["FLAT", "UP"],
                    "last_transition": "FLAT_TO_UP",
                    "stability": "CHANGING",
                    "current_confidence": 0.82,
                    "current_trend_strength": "MODERATE",
                },
                {
                    "symbol": "SOLUSDT",
                    "status": "OK",
                    "regimes": ["UNKNOWN", "UNKNOWN"],
                    "last_transition": "TO_UNKNOWN",
                    "stability": "UNSTABLE",
                    "current_confidence": 0.18,
                    "current_trend_strength": "UNKNOWN",
                },
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
