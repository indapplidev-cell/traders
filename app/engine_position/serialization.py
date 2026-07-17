"""Deterministic, lossless serialization primitives."""
from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Any

position_schema_version = 1


def freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(v) for v in value)
    if isinstance(value, (set, frozenset)):
        return tuple(freeze(v) for v in sorted(value, key=repr))
    return value


def thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [thaw(v) for v in value]
    return value


def utc_iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include UTC offset")
    return parsed.astimezone(timezone.utc)


def decimal(value: Any, *, optional: bool = False) -> Decimal | None:
    if value is None and optional:
        return None
    if value is None or isinstance(value, bool) or isinstance(value, float):
        raise ValueError("Decimal values must be supplied without float")
    result = value if isinstance(value, Decimal) else Decimal(str(value))
    if not result.is_finite():
        raise ValueError("Decimal must be finite")
    return result


def json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("non-finite Decimal")
        return format(value, "f")
    if isinstance(value, datetime):
        return utc_iso(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(k): json_value(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_value(v) for v in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"unsupported serialization value: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(json_value(value), ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))


def require_schema(payload: Mapping[str, Any]) -> None:
    if int(payload.get("position_schema_version", 0)) != position_schema_version:
        raise ValueError("unsupported position schema version")
