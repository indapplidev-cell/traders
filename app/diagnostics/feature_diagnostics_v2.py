from __future__ import annotations

from typing import Any

from app.features.feature_models import feature_names_for_version


class FeatureDiagnosticsV2:
    def build_report(
        self,
        symbol: str,
        interval: str,
        feature_version: str,
        label_version: str,
        feature_rows: list[Any],
        labels_by_open_time: dict[Any, Any],
    ) -> dict[str, Any]:
        feature_names = feature_names_for_version(feature_version)
        total_rows = len(feature_rows)
        stats: dict[str, Any] = {}
        features_with_zero_variance: list[str] = []
        features_with_too_many_nulls: list[str] = []
        low_up_down_separation_features: list[str] = []
        warnings: list[str] = []

        for feature_name in feature_names:
            feature_missing = any(feature_name not in row.features_json for row in feature_rows)
            values = [row.features_json.get(feature_name) for row in feature_rows]
            null_count = sum(value is None for value in values)
            non_null_values = [float(value) for value in values if value is not None]
            non_null_ratio = (len(non_null_values) / total_rows) if total_rows else 0.0
            mean = (sum(non_null_values) / len(non_null_values)) if non_null_values else None
            std = self._std(non_null_values)
            minimum = min(non_null_values) if non_null_values else None
            maximum = max(non_null_values) if non_null_values else None
            class_means = self._class_means(feature_rows, labels_by_open_time, feature_name)
            up_down_separation = self._up_down_separation(class_means)
            stats[feature_name] = {
                "null_count": null_count,
                "non_null_ratio": non_null_ratio,
                "mean": mean,
                "std": std,
                "min": minimum,
                "max": maximum,
                "class_means": class_means,
                "up_down_separation": up_down_separation,
            }
            if feature_missing:
                warnings.append(f"feature_missing:{feature_name}")
            if (1.0 - non_null_ratio) > 0.20:
                features_with_too_many_nulls.append(feature_name)
                warnings.append(f"feature_null_ratio_gt_0_20:{feature_name}")
            if len(non_null_values) > 0 and (std == 0.0):
                features_with_zero_variance.append(feature_name)
                warnings.append(f"feature_zero_variance:{feature_name}")
            if up_down_separation is not None and up_down_separation < 0.05:
                low_up_down_separation_features.append(feature_name)
                warnings.append(f"low_up_down_separation:{feature_name}")

        top_up_down_separation = sorted(
            [
                {
                    "feature_name": feature_name,
                    "up_down_separation": stat["up_down_separation"],
                    "class_means": stat["class_means"],
                }
                for feature_name, stat in stats.items()
                if stat["up_down_separation"] is not None
            ],
            key=lambda item: float(item["up_down_separation"]),
            reverse=True,
        )[:10]

        return {
            "symbol": symbol,
            "interval": interval,
            "feature_version": feature_version,
            "label_version": label_version,
            "total_rows": total_rows,
            "feature_count": len(feature_names),
            "feature_stats": stats,
            "top_up_down_separation_features": top_up_down_separation,
            "features_with_zero_variance": features_with_zero_variance,
            "features_with_too_many_nulls": features_with_too_many_nulls,
            "low_up_down_separation_features": low_up_down_separation_features,
            "warnings": sorted(set(warnings)),
        }

    @staticmethod
    def _std(values: list[float]) -> float | None:
        if not values:
            return None
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        return variance ** 0.5

    @staticmethod
    def _class_means(feature_rows: list[Any], labels_by_open_time: dict[Any, Any], feature_name: str) -> dict[str, float | None]:
        buckets = {"UP": [], "DOWN": [], "FLAT": []}
        for row in feature_rows:
            label_row = labels_by_open_time.get(row.candle_open_time)
            if label_row is None:
                continue
            value = row.features_json.get(feature_name)
            if value is None:
                continue
            buckets[label_row.direction_label].append(float(value))
        return {
            label: (sum(values) / len(values) if values else None)
            for label, values in buckets.items()
        }

    @staticmethod
    def _up_down_separation(class_means: dict[str, float | None]) -> float | None:
        up_mean = class_means.get("UP")
        down_mean = class_means.get("DOWN")
        if up_mean is None or down_mean is None:
            return None
        return abs(float(up_mean) - float(down_mean))
