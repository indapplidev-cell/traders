from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import cli
from app.market_interpreter import (
    L1TimelineConsumer,
    L1TimelineConsumerConfig,
    L1TimelineSymbolContext,
    L2TimelineTableFormatter,
    build_l2_safety_state,
    classify_overall_market_context,
    classify_symbol_context,
)


def test_config_defaults() -> None:
    config = L1TimelineConsumerConfig()

    assert config.input_path == Path("reports/book_l1/timeline_preview.json")
    assert config.output_dir == Path("reports/book_l2")
    assert config.strict is False
    assert config.export_json is False


def test_build_l2_safety_state_returns_fail_closed_values() -> None:
    safety = build_l2_safety_state()

    assert safety.trade_signal == "NOT_EVALUATED"
    assert safety.safe_for_runtime_trading is False
    assert safety.orders_enabled is False
    assert safety.live_trading_connected is False
    assert safety.traders_core_connected is False
    assert safety.approved_for_live_trading is False
    assert safety.approved_for_auto_activation is False
    assert safety.model_training_executed is False
    assert safety.binance_download_executed is False


def test_classify_symbol_context() -> None:
    assert _classify(current_regime="FLAT", stability="STABLE") == "STABLE_FLAT"
    assert _classify(current_regime="UP", stability="STABLE") == "STABLE_UP"
    assert _classify(current_regime="DOWN", stability="STABLE") == "STABLE_DOWN"
    assert _classify(current_regime="UP", last_transition="FLAT_TO_UP") == "EMERGING_UP"
    assert _classify(current_regime="DOWN", last_transition="FLAT_TO_DOWN") == "EMERGING_DOWN"
    assert _classify(status="INSUFFICIENT_DATA") == "SKIP_INSUFFICIENT_DATA"
    assert _classify(status="ERROR") == "SKIP_ERROR"
    assert _classify(current_regime="UNKNOWN") == "UNKNOWN"
    assert _classify(current_regime="FLAT", stability="UNSTABLE") == "UNSTABLE"


def test_classify_overall_market_context() -> None:
    assert classify_overall_market_context(()).overall_context == "NO_VALID_SYMBOLS"
    assert classify_overall_market_context((_symbol("A", "FLAT"), _symbol("B", "FLAT"))).overall_context == "ALL_FLAT"
    assert classify_overall_market_context((_symbol("A", "UP"), _symbol("B", "UP"), _symbol("C", "FLAT"))).overall_context == "BROAD_UP"
    assert classify_overall_market_context((_symbol("A", "DOWN"), _symbol("B", "DOWN"), _symbol("C", "FLAT"))).overall_context == "BROAD_DOWN"
    assert classify_overall_market_context(
        (_symbol("A", "UP", stability="UNSTABLE"), _symbol("B", "FLAT", stability="UNSTABLE"), _symbol("C", "DOWN"))
    ).overall_context == "UNSTABLE"
    assert classify_overall_market_context((_symbol("A", "UP"), _symbol("B", "DOWN"), _symbol("C", "FLAT"))).overall_context == "MIXED"


def test_missing_input_file_returns_fail_and_error(tmp_path: Path) -> None:
    result = L1TimelineConsumer().run(L1TimelineConsumerConfig(input_path=tmp_path / "missing.json"))

    assert result.status == "FAIL"
    assert result.market_context.overall_context == "NO_VALID_SYMBOLS"
    assert "missing input file" in result.errors[0]


def test_invalid_json_returns_fail_and_error(tmp_path: Path) -> None:
    path = tmp_path / "timeline_preview.json"
    path.write_text("{not json", encoding="utf-8")

    result = L1TimelineConsumer().run(L1TimelineConsumerConfig(input_path=path))

    assert result.status == "FAIL"
    assert "invalid JSON" in result.errors[0]


def test_wrong_service_fails_in_strict_mode(tmp_path: Path) -> None:
    path = _write_payload(tmp_path, service="OTHER")

    result = L1TimelineConsumer().run(L1TimelineConsumerConfig(input_path=path, strict=True))

    assert result.status == "FAIL"
    assert any("service must be BOOK_L1_MARKET_READER" in error for error in result.errors)


def test_wrong_contract_version_fails_in_strict_mode(tmp_path: Path) -> None:
    path = _write_payload(tmp_path, contract_version="old")

    result = L1TimelineConsumer().run(L1TimelineConsumerConfig(input_path=path, strict=True))

    assert result.status == "FAIL"
    assert any("contract_version must be book_l1_json_export_v1" in error for error in result.errors)


def test_fail_open_safety_in_input_fails(tmp_path: Path) -> None:
    path = _write_payload(tmp_path, safety_overrides={"safe_for_runtime_trading": True})

    result = L1TimelineConsumer().run(L1TimelineConsumerConfig(input_path=path))

    assert result.status == "FAIL"
    assert any("safety.safe_for_runtime_trading must be false" in error for error in result.errors)


def test_valid_minimal_book_l1_timeline_json_returns_ok(tmp_path: Path) -> None:
    path = _write_payload(tmp_path)

    result = L1TimelineConsumer().run(L1TimelineConsumerConfig(input_path=path, strict=True))

    assert result.status == "OK"
    assert result.source_report_type == "timeline_preview"
    assert result.source_contract_version == "book_l1_json_export_v1"


def test_consumer_extracts_symbols_correctly(tmp_path: Path) -> None:
    path = _write_payload(tmp_path)

    result = L1TimelineConsumer().run(L1TimelineConsumerConfig(input_path=path))

    assert [symbol.symbol for symbol in result.symbols] == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    assert result.symbols[0].current_regime == "FLAT"
    assert result.symbols[1].context_label == "EMERGING_UP"
    assert result.symbols[2].context_label == "UNKNOWN"


def test_table_formatter_includes_required_columns_and_observe_only(tmp_path: Path) -> None:
    result = L1TimelineConsumer().run(L1TimelineConsumerConfig(input_path=_write_payload(tmp_path)))
    output = L2TimelineTableFormatter().format(result, input_path=tmp_path / "timeline_preview.json")

    assert "Symbol" in output
    assert "Current" in output
    assert "Stability" in output
    assert "Last Change" in output
    assert "L2 Context" in output
    assert "OBSERVE_ONLY" in output


def test_details_mode_includes_observe_reason(tmp_path: Path) -> None:
    result = L1TimelineConsumer().run(L1TimelineConsumerConfig(input_path=_write_payload(tmp_path)))
    output = L2TimelineTableFormatter().format(result, input_path=tmp_path / "timeline_preview.json", show_details=True)

    assert "Details:" in output
    assert "observe_reason:" in output


def test_export_json_writes_timeline_context(tmp_path: Path) -> None:
    input_path = _write_payload(tmp_path)
    output_dir = tmp_path / "book_l2"

    L1TimelineConsumer().run(L1TimelineConsumerConfig(input_path=input_path, export_json=True, output_dir=output_dir))

    assert (output_dir / "timeline_context.json").is_file()


def test_export_overwrites_same_file_on_repeated_runs(tmp_path: Path) -> None:
    input_path = _write_payload(tmp_path)
    output_dir = tmp_path / "book_l2"
    consumer = L1TimelineConsumer()

    consumer.run(L1TimelineConsumerConfig(input_path=input_path, export_json=True, output_dir=output_dir))
    export_path = output_dir / "timeline_context.json"
    export_path.write_text("old marker", encoding="utf-8")
    consumer.run(L1TimelineConsumerConfig(input_path=input_path, export_json=True, output_dir=output_dir))

    assert "old marker" not in export_path.read_text(encoding="utf-8")


def test_export_json_contains_book_l2_contract(tmp_path: Path) -> None:
    input_path = _write_payload(tmp_path)
    output_dir = tmp_path / "book_l2"

    L1TimelineConsumer().run(L1TimelineConsumerConfig(input_path=input_path, export_json=True, output_dir=output_dir))
    payload = json.loads((output_dir / "timeline_context.json").read_text(encoding="utf-8"))

    assert payload["service"] == "BOOK_L2_MARKET_INTERPRETER"
    assert payload["report_type"] == "timeline_context"
    assert payload["contract_version"] == "book_l2_json_export_v1"


def test_export_json_safety_is_fail_closed(tmp_path: Path) -> None:
    input_path = _write_payload(tmp_path)
    output_dir = tmp_path / "book_l2"

    L1TimelineConsumer().run(L1TimelineConsumerConfig(input_path=input_path, export_json=True, output_dir=output_dir))
    safety = json.loads((output_dir / "timeline_context.json").read_text(encoding="utf-8"))["safety"]

    assert safety["trade_signal"] == "NOT_EVALUATED"
    assert safety["safe_for_runtime_trading"] is False
    assert safety["orders_enabled"] is False
    assert safety["live_trading_connected"] is False


def test_cli_help_contains_book_l2_timeline_context() -> None:
    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "book-l2-timeline-context" in result.stdout


def test_no_trade_decision_words_in_terminal_formatter_output(tmp_path: Path) -> None:
    result = L1TimelineConsumer().run(L1TimelineConsumerConfig(input_path=_write_payload(tmp_path)))
    output = L2TimelineTableFormatter().format(result, input_path=tmp_path / "timeline_preview.json", show_details=True)

    for forbidden in ("LONG", "SHORT", "BUY", "SELL"):
        assert forbidden not in output.upper()


def test_no_l1_candle_or_orchestrator_import_in_book_l2_module() -> None:
    source = Path("app/market_interpreter/l1_timeline_consumer.py").read_text(encoding="utf-8")

    assert "CandleRepository" not in source
    assert "MarketReaderOrchestrator" not in source


def _classify(
    *,
    status: str = "OK",
    current_regime: str = "FLAT",
    stability: str = "CHANGING",
    last_transition: str = "NO_CHANGE",
) -> str:
    return classify_symbol_context(
        status=status,
        current_regime=current_regime,
        stability=stability,
        last_transition=last_transition,
    )


def _symbol(symbol: str, current_regime: str, *, stability: str = "STABLE") -> L1TimelineSymbolContext:
    return L1TimelineSymbolContext(
        symbol=symbol,
        status="OK",
        current_regime=current_regime,
        stability=stability,
        last_transition="NO_CHANGE",
        current_confidence=0.8,
        current_trend_strength="NONE",
        context_label="UNKNOWN",
        observe_reason="observe only",
    )


def _write_payload(
    tmp_path: Path,
    *,
    service: str = "BOOK_L1_MARKET_READER",
    contract_version: str = "book_l1_json_export_v1",
    safety_overrides: dict[str, object] | None = None,
) -> Path:
    path = tmp_path / "timeline_preview.json"
    payload = _minimal_payload(
        service=service,
        contract_version=contract_version,
        safety_overrides=safety_overrides or {},
    )
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _minimal_payload(
    *,
    service: str,
    contract_version: str,
    safety_overrides: dict[str, object],
) -> dict[str, object]:
    safety = {
        "trade_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": False,
        "orders_enabled": False,
        "live_trading_connected": False,
        "traders_core_connected": False,
        "approved_for_live_trading": False,
        "approved_for_auto_activation": False,
        "model_training_executed": False,
        "binance_download_executed": False,
    }
    safety.update(safety_overrides)
    rows = [
        {
            "symbol": "BTCUSDT",
            "status": "OK",
            "regimes": ["FLAT", "FLAT"],
            "last_transition": "NO_CHANGE",
            "stability": "STABLE",
            "current_confidence": 0.88,
            "current_trend_strength": "NONE",
        },
        {
            "symbol": "ETHUSDT",
            "status": "OK",
            "regimes": ["FLAT", "UP"],
            "last_transition": "FLAT_TO_UP",
            "stability": "CHANGING",
            "current_confidence": 0.71,
            "current_trend_strength": "MODERATE",
        },
        {
            "symbol": "SOLUSDT",
            "status": "OK",
            "regimes": ["UNKNOWN", "UNKNOWN"],
            "last_transition": "TO_UNKNOWN",
            "stability": "UNSTABLE",
            "current_confidence": 0.41,
            "current_trend_strength": "UNKNOWN",
        },
    ]
    return {
        "status": "ok",
        "service": service,
        "report_type": "timeline_preview",
        "contract_version": contract_version,
        "request": {},
        "result": {"rows": rows},
        "summary": {},
        "safety": safety,
        "warnings": [],
        "errors": [],
    }
