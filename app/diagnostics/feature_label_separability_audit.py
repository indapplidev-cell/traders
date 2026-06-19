from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Sequence

from app.diagnostics._book_audit_utils import (
    distribution_counts,
    effect_size,
    get_mapping,
    label_from_row,
    numeric_summary,
    safe_float,
)


@dataclass(frozen=True)
class FeatureClassStats:
    feature_name: str
    row_count: int
    up_mean: float | None
    down_mean: float | None
    flat_mean: float | None
    up_median: float | None
    down_median: float | None
    flat_median: float | None
    up_down_effect_size: float | None
    up_flat_effect_size: float | None
    down_flat_effect_size: float | None
    max_abs_effect_size: float | None
    separability_rating: str


class FeatureLabelSeparabilityAudit:
    diagnostic_name = "feature_label_separability_audit"
    diagnostic_version = "ml38_9_7"

    def evaluate(
        self,
        rows: Sequence[Any],
        feature_names: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        if not rows:
            return self._empty_payload()

        extracted: list[tuple[str, dict[str, Any]]] = []
        discovered_names: set[str] = set()
        for row in rows:
            label = label_from_row(row)
            features = get_mapping(row, "features_json", "features", "feature_values")
            if label is None:
                continue
            extracted.append((label, features))
            discovered_names.update(features.keys())

        selected_names = [str(name) for name in (feature_names or sorted(discovered_names))]
        feature_summaries: list[dict[str, Any]] = []
        stats_objects: list[FeatureClassStats] = []
        valid_global_scores: list[float] = []

        for feature_name in selected_names:
            values_by_label: dict[str, list[float]] = {"UP": [], "DOWN": [], "FLAT": []}
            for label, features in extracted:
                value = safe_float(features.get(feature_name))
                if value is not None and label in values_by_label:
                    values_by_label[label].append(value)

            up_stats = numeric_summary(values_by_label["UP"])
            down_stats = numeric_summary(values_by_label["DOWN"])
            flat_stats = numeric_summary(values_by_label["FLAT"])
            up_down = effect_size(values_by_label["UP"], values_by_label["DOWN"])
            up_flat = effect_size(values_by_label["UP"], values_by_label["FLAT"])
            down_flat = effect_size(values_by_label["DOWN"], values_by_label["FLAT"])
            valid_effects = [item for item in (up_down, up_flat, down_flat) if item is not None]
            max_effect = max(valid_effects) if valid_effects else None
            if max_effect is not None:
                valid_global_scores.append(max_effect)

            stats = FeatureClassStats(
                feature_name=feature_name,
                row_count=sum(len(values) for values in values_by_label.values()),
                up_mean=up_stats["mean"],
                down_mean=down_stats["mean"],
                flat_mean=flat_stats["mean"],
                up_median=up_stats["median"],
                down_median=down_stats["median"],
                flat_median=flat_stats["median"],
                up_down_effect_size=up_down,
                up_flat_effect_size=up_flat,
                down_flat_effect_size=down_flat,
                max_abs_effect_size=max_effect,
                separability_rating=self._rating(max_effect),
            )
            stats_objects.append(stats)
            payload = asdict(stats)
            payload["up_std"] = up_stats["std"]
            payload["down_std"] = down_stats["std"]
            payload["flat_std"] = flat_stats["std"]
            payload["up_q25"] = up_stats["q25"]
            payload["down_q25"] = down_stats["q25"]
            payload["flat_q25"] = flat_stats["q25"]
            payload["up_q75"] = up_stats["q75"]
            payload["down_q75"] = down_stats["q75"]
            payload["flat_q75"] = flat_stats["q75"]
            feature_summaries.append(payload)

        global_score = None if not valid_global_scores else round(sum(valid_global_scores) / len(valid_global_scores), 6)
        global_rating = self._global_rating(global_score)
        top_features = sorted(
            feature_summaries,
            key=lambda item: float(item.get("max_abs_effect_size") or -1.0),
            reverse=True,
        )[:5]
        weak_features = [
            item["feature_name"]
            for item in feature_summaries
            if item.get("max_abs_effect_size") is None or float(item["max_abs_effect_size"]) < 0.35
        ]
        warnings: list[str] = []
        if global_rating == "WEAK":
            warnings.append("weak_global_feature_separation")
        if not any(
            (stat.up_down_effect_size or 0.0) >= 0.35
            for stat in stats_objects
        ):
            warnings.append("down_up_features_not_separable")
        if not any(
            max(
                stat.up_flat_effect_size or 0.0,
                stat.down_flat_effect_size or 0.0,
            ) >= 0.35
            for stat in stats_objects
        ):
            warnings.append("flat_features_not_separable")

        labels = [label for label, _features in extracted]
        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "row_count": len(extracted),
            "class_counts": distribution_counts(labels),
            "feature_count": len(feature_summaries),
            "features": feature_summaries,
            "top_separating_features": top_features,
            "weak_separation_features": weak_features,
            "global_separability_score": global_score,
            "global_separability_rating": global_rating,
            "warnings": warnings,
        }

    def _empty_payload(self) -> dict[str, Any]:
        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "row_count": 0,
            "class_counts": {"UP": 0, "DOWN": 0, "FLAT": 0},
            "feature_count": 0,
            "features": [],
            "top_separating_features": [],
            "weak_separation_features": [],
            "global_separability_score": None,
            "global_separability_rating": "UNAVAILABLE",
            "warnings": [],
        }

    @staticmethod
    def _rating(value: float | None) -> str:
        if value is None:
            return "UNAVAILABLE"
        if value >= 0.8:
            return "GOOD"
        if value >= 0.4:
            return "WATCH"
        return "WEAK"

    @classmethod
    def _global_rating(cls, value: float | None) -> str:
        return cls._rating(value)
