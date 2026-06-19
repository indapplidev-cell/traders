from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from statistics import mean, median
import math
from typing import Any


def get_value(row: Any, *names: str) -> Any:
    if isinstance(row, Mapping):
        for name in names:
            if name in row:
                return row[name]
    for name in names:
        if hasattr(row, name):
            return getattr(row, name)
    return None


def get_mapping(row: Any, *names: str) -> dict[str, Any]:
    for name in names:
        value = get_value(row, name)
        if isinstance(value, Mapping):
            return {str(key): value[key] for key in value}
    if isinstance(row, Mapping):
        return {
            str(key): value
            for key, value in row.items()
            if isinstance(key, str) and _looks_like_feature_value(value)
        }
    return {}


def normalize_label(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().upper()
    if normalized in {"UP", "LONG", "BUY", "BULL", "1"}:
        return "UP"
    if normalized in {"DOWN", "SHORT", "SELL", "BEAR", "-1"}:
        return "DOWN"
    if normalized in {"FLAT", "NEUTRAL", "SIDEWAYS", "RANGE", "0"}:
        return "FLAT"
    return normalized or None


def safe_float(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(result) or math.isinf(result):
        return default
    return result


def label_from_row(row: Any) -> str | None:
    return normalize_label(
        get_value(
            row,
            "actual_direction",
            "actual_label",
            "direction_label",
            "label",
            "target_direction",
            "future_close_direction",
        )
    )


def predicted_label_from_row(row: Any) -> str | None:
    return normalize_label(
        get_value(
            row,
            "predicted_label",
            "prediction",
            "predicted",
            "selected_prediction",
            "y_pred",
        )
    )


def distribution(labels: Sequence[str]) -> dict[str, float]:
    counts = Counter(str(item).upper() for item in labels if item)
    total = sum(counts.values())
    payload: dict[str, float] = {}
    for label in ("UP", "DOWN", "FLAT"):
        count = counts.get(label, 0)
        payload[label] = 0.0 if total == 0 else round(count / total, 6)
    return payload


def distribution_counts(labels: Sequence[str]) -> dict[str, int]:
    counts = Counter(str(item).upper() for item in labels if item)
    return {label: int(counts.get(label, 0)) for label in ("UP", "DOWN", "FLAT")}


def majority_accuracy(labels: Sequence[str]) -> float | None:
    counts = distribution_counts(labels)
    total = sum(counts.values())
    if total == 0:
        return None
    return max(counts.values()) / total


def numeric_summary(values: Sequence[float]) -> dict[str, float | None]:
    clean = sorted(float(value) for value in values)
    if not clean:
        return {
            "mean": None,
            "median": None,
            "std": None,
            "q25": None,
            "q75": None,
        }
    avg = mean(clean)
    variance = sum((value - avg) ** 2 for value in clean) / len(clean)
    return {
        "mean": avg,
        "median": median(clean),
        "std": math.sqrt(variance),
        "q25": percentile(clean, 0.25),
        "q75": percentile(clean, 0.75),
    }


def percentile(values: Sequence[float], q: float) -> float | None:
    clean = sorted(float(value) for value in values)
    if not clean:
        return None
    if len(clean) == 1:
        return clean[0]
    q = min(max(q, 0.0), 1.0)
    index = (len(clean) - 1) * q
    lower = int(math.floor(index))
    upper = int(math.ceil(index))
    if lower == upper:
        return clean[lower]
    weight = index - lower
    return clean[lower] * (1.0 - weight) + clean[upper] * weight


def effect_size(first: Sequence[float], second: Sequence[float]) -> float | None:
    left = [float(value) for value in first]
    right = [float(value) for value in second]
    if len(left) < 2 or len(right) < 2:
        return None
    left_mean = mean(left)
    right_mean = mean(right)
    left_var = sum((value - left_mean) ** 2 for value in left) / len(left)
    right_var = sum((value - right_mean) ** 2 for value in right) / len(right)
    pooled = math.sqrt((left_var + right_var) / 2.0)
    if pooled <= 1e-12:
        return 0.0
    return abs(left_mean - right_mean) / pooled


def _looks_like_feature_value(value: Any) -> bool:
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return True
    return value is None
