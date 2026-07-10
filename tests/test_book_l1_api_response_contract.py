from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from app.market_reader.api_response import (
    BOOK_L1_API_CONTRACT_VERSION,
    BOOK_L1_API_SERVICE_NAME,
    BookL1ApiRequest,
    BookL1ApiResponse,
    BookL1ApiResponseBuilder,
    BookL1ApiResponseStatus,
    BookL1ApiSafetyBlock,
    build_book_l1_api_response_payload,
    validate_book_l1_preview_safety,
)


def _make_candles(count: int = 80) -> list[SimpleNamespace]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles: list[SimpleNamespace] = []

    for index in range(count):
        base = 100.0 + (index * 0.2)
        candles.append(
            SimpleNamespace(
                open_time=start + timedelta(minutes=15 * index),
                open=base,
                high=base + 1.0,
                low=base - 1.0,
                close=base + 0.4,
                volume=1000.0 + index,
            )
        )

    return candles


class FakeCandleRepository:
    def __init__(self, candles: list[Any]) -> None:
        self.candles = list(candles)
        self.calls: list[dict[str, object]] = []

    def get_last_n(self, *, symbol: str, interval: str, limit: int) -> list[Any]:
        self.calls.append(
            {
                "symbol": symbol,
                "interval": interval,
                "limit": limit,
            }
        )
        return self.candles[-limit:]


def test_api_request_normalizes_symbol_and_validates_values() -> None:
    request = BookL1ApiRequest(
        symbol="btcusdt",
        interval="15m",
        limit=100,
        min_candles=50,
    )

    assert request.to_dict() == {
        "symbol": "BTCUSDT",
        "interval": "15m",
        "limit": 100,
        "min_candles": 50,
    }


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"symbol": "", "interval": "15m"}, "symbol must not be empty"),
        ({"symbol": "BTCUSDT", "interval": ""}, "interval must not be empty"),
        ({"symbol": "BTCUSDT", "interval": "15m", "limit": 0}, "limit must be positive"),
        (
            {"symbol": "BTCUSDT", "interval": "15m", "min_candles": 0},
            "min_candles must be positive",
        ),
        (
            {"symbol": "BTCUSDT", "interval": "15m", "limit": 10, "min_candles": 50},
            "limit must be greater than or equal to min_candles",
        ),
    ],
)
def test_api_request_rejects_invalid_values(kwargs: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        BookL1ApiRequest(**kwargs)


def test_safety_block_is_fail_closed_by_default() -> None:
    safety = BookL1ApiSafetyBlock()

    assert safety.to_dict() == {
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
    }


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"api_preview_only": False}, "preview-only"),
        ({"trade_signal": "LONG"}, "must not expose trading signals"),
        ({"safe_for_runtime_trading": True}, "must not approve runtime trading"),
        ({"orders_enabled": True}, "must not enable orders"),
        ({"live_trading_connected": True}, "must not connect live trading"),
        ({"traders_core_connected": True}, "must not connect traders-core"),
        ({"approved_for_live_trading": True}, "must not approve live trading"),
        ({"approved_for_auto_activation": True}, "must not approve auto activation"),
        ({"model_training_executed": True}, "must not execute model training"),
        ({"binance_download_executed": True}, "must not download Binance candles"),
    ],
)
def test_safety_block_rejects_unsafe_values(kwargs: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        BookL1ApiSafetyBlock(**kwargs)


def test_validate_preview_safety_accepts_safe_preview_payload() -> None:
    preview = {
        "analysis": {
            "market_regime": "FLAT",
            "directional_bias": "NEUTRAL",
            "confidence": 0.5,
            "trend_strength": "NONE",
            "reason_codes": [],
            "trade_signal": "NOT_EVALUATED",
            "safe_for_runtime_trading": False,
        }
    }

    assert validate_book_l1_preview_safety(preview) == ()


def test_validate_preview_safety_reports_unsafe_preview_payload() -> None:
    preview = {
        "analysis": {
            "market_regime": "UP",
            "directional_bias": "BULLISH",
            "confidence": 1.2,
            "trend_strength": "STRONG",
            "reason_codes": "not-a-list",
            "trade_signal": "LONG",
            "safe_for_runtime_trading": True,
        }
    }

    errors = validate_book_l1_preview_safety(preview)

    assert "preview.analysis.trade_signal must be NOT_EVALUATED" in errors
    assert "preview.analysis.safe_for_runtime_trading must be false" in errors
    assert "preview.analysis.confidence must be between 0.0 and 1.0" in errors
    assert "preview.analysis.reason_codes must be a list" in errors


def test_api_response_requires_preview_for_ok_status() -> None:
    request = BookL1ApiRequest(symbol="BTCUSDT", interval="15m")

    with pytest.raises(ValueError, match="ok BOOK-L1 API response must include preview payload"):
        BookL1ApiResponse(
            status=BookL1ApiResponseStatus.OK,
            request=request,
            preview=None,
        )


def test_api_response_requires_errors_for_error_status() -> None:
    request = BookL1ApiRequest(symbol="BTCUSDT", interval="15m")

    with pytest.raises(ValueError, match="error BOOK-L1 API response must include errors"):
        BookL1ApiResponse(
            status=BookL1ApiResponseStatus.ERROR,
            request=request,
            preview=None,
        )


def test_api_response_builder_wraps_market_reader_preview_payload() -> None:
    repository = FakeCandleRepository(_make_candles(90))
    request = BookL1ApiRequest(
        symbol="btcusdt",
        interval="15m",
        limit=80,
        min_candles=50,
    )

    response = BookL1ApiResponseBuilder().build(
        request=request,
        candle_repository=repository,
    )

    payload = response.to_dict()

    assert payload["status"] == "ok"
    assert payload["service"] == BOOK_L1_API_SERVICE_NAME
    assert payload["contract_version"] == BOOK_L1_API_CONTRACT_VERSION
    assert payload["request"] == {
        "symbol": "BTCUSDT",
        "interval": "15m",
        "limit": 80,
        "min_candles": 50,
    }

    preview = payload["preview"]
    assert isinstance(preview, dict)
    assert preview["symbol"] == "BTCUSDT"
    assert preview["interval"] == "15m"
    assert preview["requested_limit"] == 80
    assert preview["candle_count"] == 80

    analysis = preview["analysis"]
    assert analysis["trade_signal"] == "NOT_EVALUATED"
    assert analysis["safe_for_runtime_trading"] is False

    safety = payload["safety"]
    assert safety["api_preview_only"] is True
    assert safety["trade_signal"] == "NOT_EVALUATED"
    assert safety["safe_for_runtime_trading"] is False
    assert safety["orders_enabled"] is False
    assert safety["live_trading_connected"] is False
    assert safety["traders_core_connected"] is False
    assert safety["approved_for_live_trading"] is False
    assert safety["approved_for_auto_activation"] is False
    assert safety["model_training_executed"] is False
    assert safety["binance_download_executed"] is False

    assert payload["warnings"] == []
    assert payload["errors"] == []

    assert repository.calls == [
        {
            "symbol": "BTCUSDT",
            "interval": "15m",
            "limit": 80,
        }
    ]


def test_build_book_l1_api_response_payload_is_json_serializable() -> None:
    repository = FakeCandleRepository(_make_candles(90))

    payload = build_book_l1_api_response_payload(
        symbol="BTCUSDT",
        interval="15m",
        limit=80,
        min_candles=50,
        candle_repository=repository,
    )

    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)

    assert '"status": "ok"' in encoded
    assert '"service": "BOOK_L1_MARKET_READER"' in encoded
    assert '"trade_signal": "NOT_EVALUATED"' in encoded
    assert '"safe_for_runtime_trading": false' in encoded


def test_builder_returns_error_response_when_preview_contract_is_unsafe() -> None:
    request = BookL1ApiRequest(symbol="BTCUSDT", interval="15m")

    response = BookL1ApiResponse(
        status=BookL1ApiResponseStatus.ERROR,
        request=request,
        preview={
            "analysis": {
                "market_regime": "UP",
                "directional_bias": "BULLISH",
                "confidence": 0.75,
                "trend_strength": "STRONG",
                "reason_codes": [],
                "trade_signal": "LONG",
                "safe_for_runtime_trading": True,
            }
        },
        errors=(
            "preview.analysis.trade_signal must be NOT_EVALUATED",
            "preview.analysis.safe_for_runtime_trading must be false",
        ),
    )

    payload = response.to_dict()

    assert payload["status"] == "error"
    assert payload["errors"] == [
        "preview.analysis.trade_signal must be NOT_EVALUATED",
        "preview.analysis.safe_for_runtime_trading must be false",
    ]
    assert payload["safety"]["orders_enabled"] is False
