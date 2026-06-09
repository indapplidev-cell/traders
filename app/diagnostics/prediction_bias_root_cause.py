from __future__ import annotations

from typing import Any

from app.training.metrics import INDEX_TO_LABEL, LABEL_TO_INDEX


class PredictionBiasRootCause:
    LABELS = ("UP", "DOWN", "FLAT")

    def build_report(
        self,
        model_version: str,
        label_version: str,
        split_payloads: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        split_reports = {name: self._analyze_split(**payload) for name, payload in split_payloads.items()}
        warnings = sorted({warning for report in split_reports.values() for warning in report["warnings"]})

        train_report = split_reports.get("train", {})
        test_report = split_reports.get("test", {})
        if self._likely_training_bias(train_report):
            warnings.append("likely_training_bias")
        if self._likely_label_bias(split_reports):
            warnings.append("likely_label_bias")

        report = {
            "model_version": model_version,
            "label_version": label_version,
            "splits": split_reports,
            "warnings": sorted(set(warnings)),
        }
        report["all_models_long_only_candidate"] = (
            int(test_report.get("predicted_signal_counts", {}).get("SHORT", 0)) == 0
            and int(test_report.get("predicted_signal_counts", {}).get("LONG", 0)) > 0
        )
        return report

    def _analyze_split(self, split_name: str, rows: list[Any], predictions: list[dict[str, Any]]) -> dict[str, Any]:
        actual_counts = {label: 0 for label in self.LABELS}
        predicted_counts = {label: 0 for label in self.LABELS}
        confusion_matrix = [[0, 0, 0] for _ in self.LABELS]
        margins: list[float] = []
        up_down_diffs: list[float] = []
        avg_prob_up = 0.0
        avg_prob_down = 0.0
        avg_prob_flat = 0.0

        for row, prediction in zip(rows, predictions):
            actual_label = row.direction_label
            predicted_label = prediction["predicted_label"]
            actual_counts[actual_label] += 1
            predicted_counts[predicted_label] += 1
            confusion_matrix[LABEL_TO_INDEX[actual_label]][LABEL_TO_INDEX[predicted_label]] += 1
            prob_up = float(prediction["prob_up"])
            prob_down = float(prediction["prob_down"])
            prob_flat = float(prediction["prob_flat"])
            avg_prob_up += prob_up
            avg_prob_down += prob_down
            avg_prob_flat += prob_flat
            ordered = sorted((prob_up, prob_down, prob_flat), reverse=True)
            margins.append(ordered[0] - ordered[1])
            up_down_diffs.append(abs(prob_up - prob_down))

        row_count = len(rows)
        if row_count:
            avg_prob_up /= row_count
            avg_prob_down /= row_count
            avg_prob_flat /= row_count

        actual_ratios = self._ratios(actual_counts, row_count)
        predicted_ratios = self._ratios(predicted_counts, row_count)
        predicted_signal_counts = {
            "LONG": predicted_counts["UP"],
            "SHORT": predicted_counts["DOWN"],
            "FLAT": predicted_counts["FLAT"],
        }
        precision_by_class = {label: self._precision(confusion_matrix, label) for label in self.LABELS}
        recall_by_class = {label: self._recall(confusion_matrix, label) for label in self.LABELS}
        warnings = self._warnings_for_split(
            actual_counts=actual_counts,
            actual_ratios=actual_ratios,
            predicted_counts=predicted_counts,
            predicted_ratios=predicted_ratios,
            recall_by_class=recall_by_class,
            avg_abs_up_down_diff=(sum(up_down_diffs) / row_count) if row_count else 0.0,
            margin_q90=self._quantile(margins, 0.90),
        )

        return {
            "split_name": split_name,
            "rows": row_count,
            "actual_counts": actual_counts,
            "actual_ratios": actual_ratios,
            "predicted_counts": predicted_counts,
            "predicted_ratios": predicted_ratios,
            "predicted_signal_counts": predicted_signal_counts,
            "avg_prob_up": avg_prob_up,
            "avg_prob_down": avg_prob_down,
            "avg_prob_flat": avg_prob_flat,
            "avg_abs_up_down_diff": (sum(up_down_diffs) / row_count) if row_count else 0.0,
            "avg_margin": (sum(margins) / row_count) if row_count else 0.0,
            "margin_q50": self._quantile(margins, 0.50),
            "margin_q90": self._quantile(margins, 0.90),
            "confusion_matrix": confusion_matrix,
            "precision_by_class": precision_by_class,
            "recall_by_class": recall_by_class,
            "warnings": warnings,
        }

    @staticmethod
    def _ratios(counts: dict[str, int], total_rows: int) -> dict[str, float]:
        if total_rows == 0:
            return {label: 0.0 for label in counts}
        return {label: counts[label] / total_rows for label in counts}

    @staticmethod
    def _precision(confusion_matrix: list[list[int]], label: str) -> float:
        class_index = LABEL_TO_INDEX[label]
        true_positive = confusion_matrix[class_index][class_index]
        predicted_positive = sum(row[class_index] for row in confusion_matrix)
        if predicted_positive == 0:
            return 0.0
        return true_positive / predicted_positive

    @staticmethod
    def _recall(confusion_matrix: list[list[int]], label: str) -> float:
        class_index = LABEL_TO_INDEX[label]
        true_positive = confusion_matrix[class_index][class_index]
        actual_positive = sum(confusion_matrix[class_index])
        if actual_positive == 0:
            return 0.0
        return true_positive / actual_positive

    def _warnings_for_split(
        self,
        actual_counts: dict[str, int],
        actual_ratios: dict[str, float],
        predicted_counts: dict[str, int],
        predicted_ratios: dict[str, float],
        recall_by_class: dict[str, float],
        avg_abs_up_down_diff: float,
        margin_q90: float,
    ) -> list[str]:
        warnings: list[str] = []
        labels_balanced = actual_ratios["UP"] < 0.60 and actual_ratios["DOWN"] < 0.60 and actual_ratios["FLAT"] < 0.50
        if predicted_ratios["UP"] >= 0.80 and labels_balanced:
            warnings.append("predicts_up_but_labels_balanced")
        if predicted_counts["DOWN"] == 0:
            warnings.append("predicts_no_down")
        if actual_counts["DOWN"] > 0 and recall_by_class["DOWN"] == 0.0:
            warnings.append("down_recall_zero")
        if actual_counts["FLAT"] > 0 and recall_by_class["FLAT"] == 0.0:
            warnings.append("flat_recall_zero")
        if avg_abs_up_down_diff < 0.10 or margin_q90 < 0.15:
            warnings.append("low_probability_separation")
        return warnings

    @staticmethod
    def _likely_training_bias(train_report: dict[str, Any]) -> bool:
        warnings = set(train_report.get("warnings", []))
        predicted_ratios = train_report.get("predicted_ratios", {})
        actual_ratios = train_report.get("actual_ratios", {})
        labels_balanced = (
            actual_ratios.get("UP", 0.0) < 0.60
            and actual_ratios.get("DOWN", 0.0) < 0.60
            and actual_ratios.get("FLAT", 0.0) < 0.50
        )
        return labels_balanced and (
            "predicts_up_but_labels_balanced" in warnings
            or predicted_ratios.get("UP", 0.0) >= 0.80
            or predicted_ratios.get("DOWN", 0.0) >= 0.80
        )

    @staticmethod
    def _likely_label_bias(split_reports: dict[str, dict[str, Any]]) -> bool:
        for report in split_reports.values():
            actual = report.get("actual_ratios", {})
            actual_counts = report.get("actual_counts", {})
            if actual.get("UP", 0.0) >= 0.60 or actual.get("DOWN", 0.0) >= 0.60 or actual.get("FLAT", 0.0) >= 0.50:
                return True
            if any(actual_counts.get(label, 0) == 0 for label in ("UP", "DOWN", "FLAT")):
                return True
        return False

    @staticmethod
    def _quantile(values: list[float], quantile: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        index = int(round((len(ordered) - 1) * quantile))
        return ordered[index]
