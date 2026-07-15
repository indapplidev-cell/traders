"""Errors raised by the market-data boundary."""


class MarketDataError(Exception):
    """Base error for the package."""


class CandleValidationError(MarketDataError, ValueError):
    """A candle violates the normalized candle contract."""


class UnsupportedTimeframeError(MarketDataError, ValueError):
    """A timeframe is not supported by this stage."""


class PublicMarketDataError(MarketDataError):
    """A public exchange request could not be completed."""


class WebSocketDisconnectedError(MarketDataError):
    """The public websocket stream disconnected."""


class DuplicateCandleConflict(MarketDataError):
    """Two different closed candles have the same deterministic identity."""
