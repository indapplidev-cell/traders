"""Read-only adapter to the authoritative Scalping trading universe."""

from __future__ import annotations

from app.trading_universe.domain import PREPARED_NEXT_TRADING_UNIVERSE, resolve_universe


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


__all__ = ["resolve_parameter_sweep_universe", "validate_parameter_sweep_symbol"]
