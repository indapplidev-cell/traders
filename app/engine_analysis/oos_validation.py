"""Leakage-safe balanced validation for deterministic and manual regime labels."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable


class ValidationLabelSource(str, Enum):
    MANUAL = "MANUAL"
    DETERMINISTIC_PROXY = "DETERMINISTIC_PROXY"
    DESCRIPTIVE = "DESCRIPTIVE"


@dataclass(frozen=True)
class OOSValidationResult:
    status: str
    raw_count: int
    unique_count: int
    balanced_count: int
    train_count: int
    test_count: int
    manual_test_count: int
    metrics: dict[str, Any]
    test_rows: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "raw_count": self.raw_count,
            "unique_count": self.unique_count,
            "balanced_count": self.balanced_count,
            "train_count": self.train_count,
            "test_count": self.test_count,
            "manual_test_count": self.manual_test_count,
            "metrics": dict(self.metrics),
            "test_rows": list(self.test_rows),
        }


EXPECTED_TO_REGIME = {
    "EXPECTED_UP": "UP",
    "EXPECTED_DOWN": "DOWN",
    "EXPECTED_FLAT": "FLAT",
}


def _fingerprint(item: dict[str, Any]) -> str:
    window = item["window"]
    return "|".join(
        str(window[key])
        for key in ("symbol", "interval", "period_start", "period_end")
    )


def _label_source(item: dict[str, Any]) -> ValidationLabelSource:
    window = item["window"]
    if window.get("manual_label") in {"UP", "DOWN", "FLAT", "UNKNOWN"}:
        return ValidationLabelSource.MANUAL
    reason = str(window.get("selection_reason") or "").lower()
    return (
        ValidationLabelSource.DETERMINISTIC_PROXY
        if "deterministic" in reason
        else ValidationLabelSource.DESCRIPTIVE
    )


def deduplicate_validation_items(
    items: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        groups[_fingerprint(item)].append(item)
    return [
        sorted(
            group,
            key=lambda item: (
                _label_source(item) is not ValidationLabelSource.MANUAL,
                item.get("source_stage") != "ENGINE-ANALYSIS-15B",
                item["window"]["window_id"],
            ),
        )[0]
        for group in groups.values()
    ]


def _validation_row(item: dict[str, Any]) -> dict[str, Any] | None:
    window = item["window"]
    expected = (
        window.get("manual_label")
        if _label_source(item) is ValidationLabelSource.MANUAL
        else EXPECTED_TO_REGIME.get(window["reference_label"])
    )
    if expected not in {"UP", "DOWN", "FLAT"}:
        return None
    return {
        "window_id": window["window_id"],
        "fingerprint": _fingerprint(item),
        "symbol": window["symbol"],
        "period_start": window["period_start"],
        "expected_regime": expected,
        "predicted_regime": item["composer"]["regime"],
        "label_source": _label_source(item).value,
    }


def _balance_and_split(
    rows: list[dict[str, Any]], train_ratio: float
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_class[row["expected_regime"]].append(row)
    required = {"UP", "DOWN", "FLAT"}
    if set(by_class) != required:
        return [], [], 0
    per_class = min(len(by_class[label]) for label in required)
    train: list[dict[str, Any]] = []
    test: list[dict[str, Any]] = []
    for label in sorted(required):
        selected = sorted(by_class[label], key=lambda row: row["period_start"])[-per_class:]
        split = max(1, min(per_class - 1, int(per_class * train_ratio)))
        train.extend(selected[:split])
        test.extend(selected[split:])
    return train, test, per_class * 3


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    exact = sum(row["expected_regime"] == row["predicted_regime"] for row in rows)
    unknown = sum(row["predicted_regime"] == "UNKNOWN" for row in rows)
    opposite = sum(
        (row["expected_regime"], row["predicted_regime"])
        in {("UP", "DOWN"), ("DOWN", "UP")}
        for row in rows
    )
    confusion = Counter(
        f"{row['expected_regime']}->{row['predicted_regime']}" for row in rows
    )
    decided = len(rows) - unknown
    return {
        "exact_match_count": exact,
        "exact_match_rate": exact / len(rows) if rows else None,
        "unknown_count": unknown,
        "unknown_rate": unknown / len(rows) if rows else None,
        "opposite_direction_count": opposite,
        "decided_count": decided,
        "decided_accuracy": exact / decided if decided else None,
        "confusion": dict(confusion),
        "class_counts": dict(Counter(row["expected_regime"] for row in rows)),
    }


def run_balanced_oos_validation(
    items: list[dict[str, Any]], *, train_ratio: float = 0.67
) -> OOSValidationResult:
    if not 0.0 < train_ratio < 1.0:
        raise ValueError("train_ratio must be between zero and one")
    unique = deduplicate_validation_items(items)
    rows = [row for item in unique if (row := _validation_row(item)) is not None]
    train, test, balanced_count = _balance_and_split(rows, train_ratio)
    manual_test_count = sum(
        row["label_source"] == ValidationLabelSource.MANUAL.value for row in test
    )
    status = (
        "BLOCKED_UNBALANCED_CLASSES"
        if not test
        else "BLOCKED_MANUAL_LABELS"
        if manual_test_count != len(test)
        else "READY_FOR_ACCEPTANCE_DECISION"
    )
    return OOSValidationResult(
        status=status,
        raw_count=len(items),
        unique_count=len(unique),
        balanced_count=balanced_count,
        train_count=len(train),
        test_count=len(test),
        manual_test_count=manual_test_count,
        metrics=_metrics(test),
        test_rows=tuple(sorted(test, key=lambda row: row["period_start"])),
    )


def build_manual_annotation_template(
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    unique = deduplicate_validation_items(items)
    return {
        "contract_version": "engine_analysis_manual_regime_labels_v1",
        "allowed_labels": ["UP", "DOWN", "FLAT", "UNKNOWN"],
        "instructions": "Assign labels without viewing engine predictions.",
        "windows": [
            {
                "window_id": item["window"]["window_id"],
                "fingerprint": _fingerprint(item),
                "symbol": item["window"]["symbol"],
                "interval": item["window"]["interval"],
                "period_start": item["window"]["period_start"],
                "period_end": item["window"]["period_end"],
                "manual_label": None,
                "reviewer": None,
                "reviewed_at": None,
                "notes": None,
            }
            for item in sorted(unique, key=lambda value: value["window"]["period_start"])
        ],
    }
