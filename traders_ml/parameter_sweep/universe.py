"""Read-only adapter to the authoritative Scalping trading universe."""

from __future__ import annotations

from app.trading_universe.domain import PREPARED_NEXT_TRADING_UNIVERSE, resolve_universe

ALL_SYMBOLS_ID = "ALL"


def resolve_parameter_sweep_universe() -> tuple[str, tuple[str, ...]]:
    """Return the existing v2 authority; Parameter Sweep owns no symbol list."""
    universe = resolve_universe(PREPARED_NEXT_TRADING_UNIVERSE.version_id)
    return universe.version_id, universe.symbols


def validate_parameter_sweep_symbol(value: object) -> str:
    _universe_id, symbols = resolve_parameter_sweep_universe()
    if not isinstance(value, str) or not value.strip():
        raise ValueError("SYMBOL_REQUIRED")
    symbol = value.strip().upper()
    if symbol not in symbols:
        raise ValueError("SYMBOL_NOT_IN_ACTIVE_UNIVERSE")
    return symbol


def validate_parameter_sweep_selection(value: object) -> str:
    """Validate the GUI selector while keeping ALL a transport-level sentinel."""
    if isinstance(value, str) and value.strip().upper() == ALL_SYMBOLS_ID:
        return ALL_SYMBOLS_ID
    return validate_parameter_sweep_symbol(value)


__all__ = [
    "ALL_SYMBOLS_ID", "resolve_parameter_sweep_universe",
    "validate_parameter_sweep_selection", "validate_parameter_sweep_symbol",
]
