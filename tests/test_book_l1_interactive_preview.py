from __future__ import annotations

from typing import Any

from typer.testing import CliRunner

import app.cli.commands as commands_module
from app.cli.commands import cli
from app.market_reader.interactive_preview import format_book_l1_interactive_preview_report


def _payload() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "BOOK_L1_MARKET_READER",
        "contract_version": "book_l1_api_response_v1",
        "request": {
            "symbol": "BTCUSDT",
            "interval": "15m",
            "limit": 300,
            "min_candles": 50,
        },
        "preview": {
            "symbol": "BTCUSDT",
            "interval": "15m",
            "requested_limit": 300,
            "candle_count": 300,
            "first_open_time": "2026-06-12T17:15:00+00:00",
            "last_open_time": "2026-06-15T20:00:00+00:00",
            "analysis": {
                "symbol": "BTCUSDT",
                "interval": "15m",
                "market_regime": "FLAT",
                "directional_bias": "NEUTRAL",
                "confidence": 0.9406046268096556,
                "trend_strength": "NONE",
                "reason_codes": [
                    "MARKET_READER_ORCHESTRATED",
                    "MARKET_REGIME_COMPOSED",
                ],
                "trade_signal": "NOT_EVALUATED",
                "safe_for_runtime_trading": False,
            },
        },
        "safety": {
            "api_preview_only": True,
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


def test_format_book_l1_interactive_preview_report_outputs_human_tables() -> None:
    report = format_book_l1_interactive_preview_report(_payload())

    assert "BOOK-L1 Interactive Preview / Human Table Report" in report
    assert "Preview only. This report is not a trading signal" in report
    assert "Request" in report
    assert "| symbol      | BTCUSDT |" in report
    assert "Market Analysis" in report
    assert "| market_regime            | FLAT" in report
    assert "| confidence               | 0.9406 (94.06%)" in report
    assert "| trade_signal             | NOT_EVALUATED" in report
    assert "| safe_for_runtime_trading | false" in report
    assert "Safety" in report
    assert "| trade_signal                 | NOT_EVALUATED" in report
    assert "| safe_for_runtime_trading     | false" in report
    assert "| orders_enabled               | false" in report
    assert "Reason Codes" in report
    assert "MARKET_READER_ORCHESTRATED" in report
    assert "Warnings\n(no items)" in report
    assert "Errors\n(no items)" in report


def test_book_l1_interactive_preview_cli_prints_report(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class DummySessionContext:
        def __enter__(self) -> object:
            return object()

        def __exit__(self, *args: object) -> None:
            return None

    class DummyRepository:
        def __init__(self, session: object) -> None:
            captured["session"] = session

    def fake_build_report(**kwargs: Any) -> str:
        captured.update(kwargs)
        return "BOOK-L1 Interactive Preview / Human Table Report\nRequest\nMarket Analysis"

    monkeypatch.setattr(commands_module, "get_session", lambda: DummySessionContext())
    monkeypatch.setattr(commands_module, "CandleRepository", DummyRepository)

    import app.market_reader.interactive_preview as interactive_preview_module

    monkeypatch.setattr(
        interactive_preview_module,
        "build_book_l1_interactive_preview_report",
        fake_build_report,
    )

    result = CliRunner().invoke(
        cli,
        [
            "book-l1-interactive-preview",
            "--symbol",
            "ETHUSDT",
            "--interval",
            "1h",
            "--limit",
            "120",
            "--min-candles",
            "60",
        ],
    )

    assert result.exit_code == 0
    assert "BOOK-L1 Interactive Preview / Human Table Report" in result.stdout
    assert captured["symbol"] == "ETHUSDT"
    assert captured["interval"] == "1h"
    assert captured["limit"] == 120
    assert captured["min_candles"] == 60
    assert isinstance(captured["candle_repository"], DummyRepository)
