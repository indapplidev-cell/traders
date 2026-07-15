"""Exchange-neutral market symbol normalization."""

import re

_SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,30}$")


def normalize_market_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper() if isinstance(symbol, str) else ""
    if not _SYMBOL_RE.fullmatch(normalized):
        raise ValueError(f"Invalid market symbol: {symbol!r}")
    return normalized


class MarketSymbol(str):
    def __new__(cls, value: str) -> "MarketSymbol":
        return str.__new__(cls, normalize_market_symbol(value))
