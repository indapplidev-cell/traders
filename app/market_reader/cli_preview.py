from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from app.market_reader.candle_window import CandleWindow
from app.market_reader.market_reader import MarketReaderOrchestrator
from app.market_reader.schemas import MarketAnalysisResult


@dataclass(frozen=True)
class MarketReaderPreview:
    symbol: str
    interval: str
    requested_limit: int
    candle_count: int
    first_open_time: str | None
    last_open_time: str | None
    analysis: MarketAnalysisResult

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "requested_limit": self.requested_limit,
            "candle_count": self.candle_count,
            "first_open_time": self.first_open_time,
            "last_open_time": self.last_open_time,
            "analysis": self.analysis.to_dict(),
        }


class MarketReaderPreviewBuilder:
    def __init__(self, reader: Any | None = None, min_candles: int = 50) -> None:
        if min_candles <= 0:
            raise ValueError("min_candles must be positive")
        self._reader = reader or MarketReaderOrchestrator()
        self._min_candles = min_candles

    def build(
        self,
        *,
        symbol: str,
        interval: str,
        candles: Sequence[Any],
        requested_limit: int,
    ) -> MarketReaderPreview:
        if requested_limit <= 0:
            raise ValueError("requested_limit must be positive")

        window = CandleWindow.from_candles(
            symbol=symbol,
            interval=interval,
            candles=candles,
            min_size=self._min_candles,
        )
        analysis = self._reader.analyze(window)

        if not isinstance(analysis, MarketAnalysisResult):
            raise ValueError("MarketReader must return MarketAnalysisResult")

        return MarketReaderPreview(
            symbol=symbol,
            interval=interval,
            requested_limit=requested_limit,
            candle_count=window.size,
            first_open_time=window.first_open_time.isoformat(),
            last_open_time=window.last_open_time.isoformat(),
            analysis=analysis,
        )


def build_market_reader_preview_payload(
    *,
    symbol: str,
    interval: str,
    limit: int,
    candle_repository: Any,
    reader: Any | None = None,
    min_candles: int = 50,
) -> dict[str, object]:
    if limit <= 0:
        raise ValueError("limit must be positive")

    candles = candle_repository.get_last_n(
        symbol=symbol,
        interval=interval,
        limit=limit,
    )

    preview = MarketReaderPreviewBuilder(
        reader=reader,
        min_candles=min_candles,
    ).build(
        symbol=symbol,
        interval=interval,
        candles=candles,
        requested_limit=limit,
    )

    return preview.to_dict()
