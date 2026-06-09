from __future__ import annotations

from typing import Any


class FoldLabelDiagnostics:
    LABELS = ("UP", "DOWN", "FLAT")

    def build_report(
        self,
        symbol: str,
        interval: str,
        feature_version: str,
        label_version: str,
        folds: list[dict[str, Any]],
    ) -> dict[str, Any]:
        fold_reports = [self._build_fold_report(fold) for fold in folds]
        warnings = sorted({warning for fold in fold_reports for warning in fold["warnings"]})
        return {
            "symbol": symbol,
            "interval": interval,
            "feature_version": feature_version,
            "label_version": label_version,
            "fold_count": len(fold_reports),
            "folds": fold_reports,
            "labels_are_balanced_by_fold": len(warnings) == 0,
            "warnings": warnings,
        }

    def _build_fold_report(self, fold: dict[str, Any]) -> dict[str, Any]:
        sections: dict[str, Any] = {}
        warnings: list[str] = []
        for split_name in ("train", "validation", "test"):
            rows = fold[f"{split_name}_rows_data"]
            counts = self._counts(rows)
            ratios = self._ratios(counts, len(rows))
            sections[split_name] = {
                "rows": len(rows),
                "counts": counts,
                "ratios": ratios,
            }
            warnings.extend(self._warnings_for_split(split_name, counts, ratios))

        return {
            "fold_index": fold["fold_index"],
            "train_start": fold["train_start"],
            "train_end": fold["train_end"],
            "validation_start": fold["validation_start"],
            "validation_end": fold["validation_end"],
            "test_start": fold["test_start"],
            "test_end": fold["test_end"],
            "train": sections["train"],
            "validation": sections["validation"],
            "test": sections["test"],
            "warnings": sorted(set(warnings)),
        }

    def _counts(self, rows: list[Any]) -> dict[str, int]:
        counts = {label: 0 for label in self.LABELS}
        for row in rows:
            counts[row.direction_label] += 1
        return counts

    @staticmethod
    def _ratios(counts: dict[str, int], total_rows: int) -> dict[str, float]:
        if total_rows == 0:
            return {label: 0.0 for label in counts}
        return {label: counts[label] / total_rows for label in counts}

    def _warnings_for_split(self, split_name: str, counts: dict[str, int], ratios: dict[str, float]) -> list[str]:
        warnings: list[str] = []
        prefix = split_name
        if ratios["UP"] >= 0.60:
            warnings.append(f"{prefix}_up_ratio_gte_0_60")
        if ratios["DOWN"] >= 0.60:
            warnings.append(f"{prefix}_down_ratio_gte_0_60")
        if ratios["FLAT"] >= 0.50:
            warnings.append("flat_ratio_gte_0_50")
        if any(counts[label] == 0 for label in self.LABELS):
            warnings.append("class_missing")
        return warnings
