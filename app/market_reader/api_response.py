from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.market_reader.cli_preview import build_market_reader_preview_payload


BOOK_L1_API_SERVICE_NAME = "BOOK_L1_MARKET_READER"
BOOK_L1_API_CONTRACT_VERSION = "book_l1_api_response_v1"


class BookL1ApiResponseStatus(str, Enum):
    OK = "ok"
    ERROR = "error"


@dataclass(frozen=True)
class BookL1ApiRequest:
    """Запрос для безопасного BOOK-L1 API preview.

    Это не торговый запрос. Здесь нет direction, order side, quantity,
    leverage, risk profile или любых execution-полей.
    """

    symbol: str
    interval: str
    limit: int = 300
    min_candles: int = 50

    def __post_init__(self) -> None:
        if not self.symbol or not self.symbol.strip():
            raise ValueError("symbol must not be empty")
        if not self.interval or not self.interval.strip():
            raise ValueError("interval must not be empty")
        if self.limit <= 0:
            raise ValueError("limit must be positive")
        if self.min_candles <= 0:
            raise ValueError("min_candles must be positive")
        if self.limit < self.min_candles:
            raise ValueError("limit must be greater than or equal to min_candles")

        object.__setattr__(self, "symbol", self.symbol.strip().upper())
        object.__setattr__(self, "interval", self.interval.strip())

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "limit": self.limit,
            "min_candles": self.min_candles,
        }


@dataclass(frozen=True)
class BookL1ApiSafetyBlock:
    """Fail-closed safety block for BOOK-L1 API preview response."""

    api_preview_only: bool = True
    trade_signal: str = "NOT_EVALUATED"
    safe_for_runtime_trading: bool = False
    orders_enabled: bool = False
    live_trading_connected: bool = False
    traders_core_connected: bool = False
    approved_for_live_trading: bool = False
    approved_for_auto_activation: bool = False
    model_training_executed: bool = False
    binance_download_executed: bool = False

    def __post_init__(self) -> None:
        if self.api_preview_only is not True:
            raise ValueError("BOOK-L1 API response must remain preview-only")
        if self.trade_signal != "NOT_EVALUATED":
            raise ValueError("BOOK-L1 API response must not expose trading signals")
        if self.safe_for_runtime_trading is not False:
            raise ValueError("BOOK-L1 API response must not approve runtime trading")
        if self.orders_enabled is not False:
            raise ValueError("BOOK-L1 API response must not enable orders")
        if self.live_trading_connected is not False:
            raise ValueError("BOOK-L1 API response must not connect live trading")
        if self.traders_core_connected is not False:
            raise ValueError("BOOK-L1 API response must not connect traders-core")
        if self.approved_for_live_trading is not False:
            raise ValueError("BOOK-L1 API response must not approve live trading")
        if self.approved_for_auto_activation is not False:
            raise ValueError("BOOK-L1 API response must not approve auto activation")
        if self.model_training_executed is not False:
            raise ValueError("BOOK-L1 API response must not execute model training")
        if self.binance_download_executed is not False:
            raise ValueError("BOOK-L1 API response must not download Binance candles")

    def to_dict(self) -> dict[str, object]:
        return {
            "api_preview_only": self.api_preview_only,
            "trade_signal": self.trade_signal,
            "safe_for_runtime_trading": self.safe_for_runtime_trading,
            "orders_enabled": self.orders_enabled,
            "live_trading_connected": self.live_trading_connected,
            "traders_core_connected": self.traders_core_connected,
            "approved_for_live_trading": self.approved_for_live_trading,
            "approved_for_auto_activation": self.approved_for_auto_activation,
            "model_training_executed": self.model_training_executed,
            "binance_download_executed": self.binance_download_executed,
        }


@dataclass(frozen=True)
class BookL1ApiResponse:
    """Stable service/API response contract for BOOK-L1 Market Reader."""

    status: BookL1ApiResponseStatus
    request: BookL1ApiRequest
    preview: dict[str, Any] | None
    safety: BookL1ApiSafetyBlock = field(default_factory=BookL1ApiSafetyBlock)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
    service: str = BOOK_L1_API_SERVICE_NAME
    contract_version: str = BOOK_L1_API_CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "warnings", tuple(self.warnings))
        object.__setattr__(self, "errors", tuple(self.errors))

        if self.service != BOOK_L1_API_SERVICE_NAME:
            raise ValueError("unexpected BOOK-L1 API service name")

        if self.contract_version != BOOK_L1_API_CONTRACT_VERSION:
            raise ValueError("unexpected BOOK-L1 API contract version")

        if self.status == BookL1ApiResponseStatus.OK and self.preview is None:
            raise ValueError("ok BOOK-L1 API response must include preview payload")

        if self.status == BookL1ApiResponseStatus.OK and self.errors:
            raise ValueError("ok BOOK-L1 API response must not include errors")

        if self.status == BookL1ApiResponseStatus.ERROR and not self.errors:
            raise ValueError("error BOOK-L1 API response must include errors")

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "service": self.service,
            "contract_version": self.contract_version,
            "request": self.request.to_dict(),
            "preview": self.preview,
            "safety": self.safety.to_dict(),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


def validate_book_l1_preview_safety(preview: dict[str, Any] | None) -> tuple[str, ...]:
    """Return safety-contract errors for a preview payload.

    Пустой tuple означает, что payload безопасен для API preview.
    """

    errors: list[str] = []

    if preview is None:
        return ("preview payload is missing",)

    analysis = preview.get("analysis")
    if not isinstance(analysis, dict):
        return ("preview.analysis must be a dict",)

    if analysis.get("trade_signal") != "NOT_EVALUATED":
        errors.append("preview.analysis.trade_signal must be NOT_EVALUATED")

    if analysis.get("safe_for_runtime_trading") is not False:
        errors.append("preview.analysis.safe_for_runtime_trading must be false")

    if "market_regime" not in analysis:
        errors.append("preview.analysis.market_regime is missing")

    if "directional_bias" not in analysis:
        errors.append("preview.analysis.directional_bias is missing")

    if "confidence" not in analysis:
        errors.append("preview.analysis.confidence is missing")
    else:
        try:
            confidence = float(analysis["confidence"])
        except (TypeError, ValueError):
            errors.append("preview.analysis.confidence must be numeric")
        else:
            if not 0.0 <= confidence <= 1.0:
                errors.append("preview.analysis.confidence must be between 0.0 and 1.0")

    if "trend_strength" not in analysis:
        errors.append("preview.analysis.trend_strength is missing")

    if not isinstance(analysis.get("reason_codes"), list):
        errors.append("preview.analysis.reason_codes must be a list")

    return tuple(errors)


class BookL1ApiResponseBuilder:
    """Build fail-closed BOOK-L1 API response payloads from stored candles."""

    def build(
        self,
        *,
        request: BookL1ApiRequest,
        candle_repository: Any,
        reader: Any | None = None,
    ) -> BookL1ApiResponse:
        preview = build_market_reader_preview_payload(
            symbol=request.symbol,
            interval=request.interval,
            limit=request.limit,
            min_candles=request.min_candles,
            candle_repository=candle_repository,
            reader=reader,
        )

        errors = validate_book_l1_preview_safety(preview)

        if errors:
            return BookL1ApiResponse(
                status=BookL1ApiResponseStatus.ERROR,
                request=request,
                preview=preview,
                errors=errors,
            )

        return BookL1ApiResponse(
            status=BookL1ApiResponseStatus.OK,
            request=request,
            preview=preview,
        )


def build_book_l1_api_response_payload(
    *,
    symbol: str,
    interval: str,
    candle_repository: Any,
    limit: int = 300,
    min_candles: int = 50,
    reader: Any | None = None,
) -> dict[str, object]:
    """Build JSON-serializable BOOK-L1 API preview payload."""

    request = BookL1ApiRequest(
        symbol=symbol,
        interval=interval,
        limit=limit,
        min_candles=min_candles,
    )

    response = BookL1ApiResponseBuilder().build(
        request=request,
        candle_repository=candle_repository,
        reader=reader,
    )

    return response.to_dict()
