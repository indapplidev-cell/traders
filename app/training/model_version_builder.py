from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import uuid4


DEFAULT_MODEL_VERSION_MAX_LENGTH = 100


def _slug(value: object, *, max_length: int) -> str:
    """Делает часть model_version безопасной для БД и файловой системы."""

    raw = str(value or "na").strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")
    if not slug:
        slug = "na"
    return slug[:max_length]


def build_unique_model_version(
    *,
    model_name: str,
    symbol: str,
    interval: str,
    horizon_candles: int,
    label_version: str,
    created_at: datetime | None = None,
    unique_suffix: str | None = None,
    max_length: int = DEFAULT_MODEL_VERSION_MAX_LENGTH,
) -> str:
    """
    Собирает уникальный model_version для параллельного обучения.

    Важно:
    - timestamp с microseconds сам по себе недостаточен;
    - параллельные BTC/ETH/SOL могут создать одинаковую версию;
    - поэтому добавляем symbol, interval, horizon, label_version и короткий uuid suffix;
    - длина должна помещаться в ml_model_versions.model_version String(100).
    """

    timestamp = (created_at or datetime.now(tz=timezone.utc)).strftime("%Y_%m_%d_%H%M%S_%f")
    suffix = _slug(unique_suffix or uuid4().hex[:10], max_length=16)

    prefix = _slug(f"ml_{model_name}_v1", max_length=32)
    symbol_part = _slug(symbol, max_length=12)
    interval_part = _slug(interval, max_length=8)
    horizon_part = f"h{int(horizon_candles)}"
    label_part = _slug(label_version, max_length=32)

    parts = [
        prefix,
        symbol_part,
        interval_part,
        horizon_part,
        label_part,
        timestamp,
        suffix,
    ]
    version = "_".join(parts)
    if len(version) <= max_length:
        return version

    # Если label_version слишком длинный, режем только label_part, сохраняя symbol/horizon/suffix.
    fixed_length = sum(len(part) for part in [prefix, symbol_part, interval_part, horizon_part, timestamp, suffix]) + 6
    available_label_length = max(8, max_length - fixed_length)
    label_part = _slug(label_version, max_length=available_label_length)
    version = "_".join([prefix, symbol_part, interval_part, horizon_part, label_part, timestamp, suffix])

    if len(version) <= max_length:
        return version

    # Последний fallback: сохраняем уникальность через symbol/horizon/timestamp/suffix.
    return "_".join([prefix, symbol_part, horizon_part, timestamp, suffix])[:max_length]
