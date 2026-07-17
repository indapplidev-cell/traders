"""Errors raised while validating online analysis input."""


class OnlineAnalysisError(Exception):
    """Base error for the online analysis boundary."""


class InvalidMarketDataSnapshotError(OnlineAnalysisError, ValueError):
    """The market-data snapshot violates the closed-series contract."""
