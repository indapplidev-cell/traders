from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

import torch
import torch.nn.functional as F

from app.dataset.dataset_models import DatasetRow


LABELS = ("UP", "DOWN", "FLAT")


@dataclass(slots=True)
class DirectionHeadSplitDiagnostics:
    split_name: str
    rows: int
    top1_logit_gap_q50: float | None
    top1_logit_gap_q90: float | None
    target_logit_gap_q50: float | None
    target_logit_gap_q90: float | None
    positive_target_gap_ratio: float
    mean_abs_logit: float | None
    logit_std: float | None
    weak_logit_separation_detected: bool
    recommendations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "split_name": self.split_name,
            "rows": self.rows,
            "top1_logit_gap_q50": self.top1_logit_gap_q50,
            "top1_logit_gap_q90": self.top1_logit_gap_q90,
            "target_logit_gap_q50": self.target_logit_gap_q50,
            "target_logit_gap_q90": self.target_logit_gap_q90,
            "positive_target_gap_ratio": self.positive_target_gap_ratio,
            "mean_abs_logit": self.mean_abs_logit,
            "logit_std": self.logit_std,
            "weak_logit_separation_detected": self.weak_logit_separation_detected,
            "recommendations": list(self.recommendations),
        }


class DirectionHeadSeparationDiagnostics:
    """Диагностика разделения direction logits до softmax.

    Важно: это не quality gate и не acceptance shortcut.
    Это объясняет, почему collapse_gate падает: logits плохо расходятся.
    """

    def build_for_splits(
        self,
        model: torch.nn.Module,
        datasets: dict[str, dict[str, torch.Tensor]],
    ) -> dict[str, Any]:
        split_payloads = {}
        weak_splits = 0
        for split_name, dataset in datasets.items():
            payload = self.build_for_dataset(model=model, dataset=dataset, split_name=split_name).to_dict()
            split_payloads[split_name] = payload
            weak_splits += int(bool(payload.get("weak_logit_separation_detected", False)))

        return {
            "diagnostic_name": "direction_head_separation_diagnostics",
            "diagnostic_version": "ml38_8",
            "split_count": len(split_payloads),
            "weak_split_count": weak_splits,
            "weak_direction_head_detected": weak_splits > 0,
            "splits": split_payloads,
            "summary": {
                "test_top1_logit_gap_q50": split_payloads.get("test", {}).get("top1_logit_gap_q50"),
                "test_target_logit_gap_q50": split_payloads.get("test", {}).get("target_logit_gap_q50"),
                "test_positive_target_gap_ratio": split_payloads.get("test", {}).get("positive_target_gap_ratio"),
            },
        }

    def build_for_dataset(
        self,
        model: torch.nn.Module,
        dataset: dict[str, torch.Tensor],
        split_name: str,
    ) -> DirectionHeadSplitDiagnostics:
        features = dataset["features"]
        targets = dataset["direction_target"]

        if features.shape[0] == 0:
            return DirectionHeadSplitDiagnostics(
                split_name=split_name,
                rows=0,
                top1_logit_gap_q50=None,
                top1_logit_gap_q90=None,
                target_logit_gap_q50=None,
                target_logit_gap_q90=None,
                positive_target_gap_ratio=0.0,
                mean_abs_logit=None,
                logit_std=None,
                weak_logit_separation_detected=True,
                recommendations=["empty_split_no_direction_logit_diagnostics"],
            )

        model.eval()
        with torch.no_grad():
            outputs = model(features)
            logits = outputs["direction_logits"].detach()

        sorted_logits = torch.sort(logits, dim=1, descending=True).values
        top1_gap = sorted_logits[:, 0] - sorted_logits[:, 1]

        target_logits = logits.gather(1, targets.view(-1, 1)).squeeze(1)
        target_mask = F.one_hot(targets, num_classes=logits.shape[1]).bool()
        other_logits = logits.masked_fill(target_mask, float("-inf")).max(dim=1).values
        target_gap = target_logits - other_logits

        top1_q50 = self._quantile(top1_gap, 0.50)
        top1_q90 = self._quantile(top1_gap, 0.90)
        target_q50 = self._quantile(target_gap, 0.50)
        target_q90 = self._quantile(target_gap, 0.90)
        positive_ratio = float((target_gap > 0).float().mean().detach().item())
        mean_abs_logit = float(torch.mean(torch.abs(logits)).detach().item())
        logit_std = float(torch.std(logits).detach().item())

        weak = (
            top1_q50 is None
            or top1_q50 < 0.10
            or target_q50 is None
            or target_q50 < 0.00
            or positive_ratio < 0.42
        )
        recommendations = []
        if top1_q50 is not None and top1_q50 < 0.10:
            recommendations.append("increase_direction_logit_separation")
        if target_q50 is not None and target_q50 < 0.00:
            recommendations.append("target_class_logit_often_below_competing_class")
        if positive_ratio < 0.42:
            recommendations.append("direction_head_not_ranking_true_class_enough")

        return DirectionHeadSplitDiagnostics(
            split_name=split_name,
            rows=int(features.shape[0]),
            top1_logit_gap_q50=top1_q50,
            top1_logit_gap_q90=top1_q90,
            target_logit_gap_q50=target_q50,
            target_logit_gap_q90=target_q90,
            positive_target_gap_ratio=positive_ratio,
            mean_abs_logit=mean_abs_logit,
            logit_std=logit_std,
            weak_logit_separation_detected=weak,
            recommendations=recommendations,
        )

    @staticmethod
    def _quantile(values: torch.Tensor, fraction: float) -> float | None:
        if values.shape[0] == 0:
            return None
        return float(torch.quantile(values.float(), fraction).detach().item())


class LabelNoiseDiagnostics:
    """Диагностика noisy/ambiguous direction labels.

    Мы не удаляем строки и не смягчаем gates.
    Мы считаем веса для direction loss и сохраняем объяснение в metrics.json.
    """

    def build_by_split(self, split_rows: dict[str, list[DatasetRow]]) -> dict[str, Any]:
        split_payloads = {
            split_name: self.build(rows).to_dict()
            for split_name, rows in split_rows.items()
        }
        return {
            "diagnostic_name": "label_noise_diagnostics",
            "diagnostic_version": "ml38_8",
            "splits": split_payloads,
            "summary": {
                "train_noise_risk": split_payloads.get("train", {}).get("label_noise_risk"),
                "validation_noise_risk": split_payloads.get("validation", {}).get("label_noise_risk"),
                "test_noise_risk": split_payloads.get("test", {}).get("label_noise_risk"),
            },
        }

    def build(self, rows: list[DatasetRow]) -> "LabelNoiseDiagnosticsResult":
        if not rows:
            return LabelNoiseDiagnosticsResult(
                rows=0,
                direction_counts={label: 0 for label in LABELS},
                direction_ratios={label: 0.0 for label in LABELS},
                average_direction_sample_weight=0.0,
                low_weight_ratio=0.0,
                ambiguous_direction_ratio=0.0,
                noisy_flat_ratio=0.0,
                label_noise_risk="UNKNOWN",
                recommendations=["empty_rows_no_label_noise_diagnostics"],
            )

        weights = [direction_sample_weight_for_row(row) for row in rows]
        counts = Counter(row.direction_label for row in rows)
        total = len(rows)
        ratios = {label: counts.get(label, 0) / total for label in LABELS}
        low_weight_ratio = sum(int(weight < 0.65) for weight in weights) / total
        ambiguous_ratio = sum(int(self._is_ambiguous_direction(row)) for row in rows) / total
        noisy_flat_ratio = sum(int(self._is_noisy_flat(row)) for row in rows) / total

        risk = "LOW"
        recommendations = []
        if low_weight_ratio > 0.45 or ambiguous_ratio > 0.35:
            risk = "HIGH"
            recommendations.append("label_noise_high_consider_stronger_direction_sample_weighting")
        elif low_weight_ratio > 0.25 or ambiguous_ratio > 0.20:
            risk = "MEDIUM"
            recommendations.append("label_noise_medium_keep_weighted_direction_loss")

        if ratios.get("FLAT", 0.0) > 0.55:
            recommendations.append("flat_class_dominates_direction_labels")
        if min(ratios.values()) < 0.10:
            recommendations.append("one_direction_class_is_underrepresented")

        return LabelNoiseDiagnosticsResult(
            rows=total,
            direction_counts={label: counts.get(label, 0) for label in LABELS},
            direction_ratios=ratios,
            average_direction_sample_weight=sum(weights) / total,
            low_weight_ratio=low_weight_ratio,
            ambiguous_direction_ratio=ambiguous_ratio,
            noisy_flat_ratio=noisy_flat_ratio,
            label_noise_risk=risk,
            recommendations=recommendations,
        )

    @staticmethod
    def _is_ambiguous_direction(row: DatasetRow) -> bool:
        favorable = abs(float(row.max_favorable_move_atr))
        adverse = abs(float(row.max_adverse_move_atr))
        if row.direction_label == "FLAT":
            return abs(float(row.future_move_atr)) > 0.20
        return favorable - adverse < 0.20

    @staticmethod
    def _is_noisy_flat(row: DatasetRow) -> bool:
        if row.direction_label != "FLAT":
            return False
        return max(abs(float(row.max_favorable_move_atr)), abs(float(row.max_adverse_move_atr))) > 0.80


@dataclass(slots=True)
class LabelNoiseDiagnosticsResult:
    rows: int
    direction_counts: dict[str, int]
    direction_ratios: dict[str, float]
    average_direction_sample_weight: float
    low_weight_ratio: float
    ambiguous_direction_ratio: float
    noisy_flat_ratio: float
    label_noise_risk: str
    recommendations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows": self.rows,
            "direction_counts": dict(self.direction_counts),
            "direction_ratios": dict(self.direction_ratios),
            "average_direction_sample_weight": self.average_direction_sample_weight,
            "low_weight_ratio": self.low_weight_ratio,
            "ambiguous_direction_ratio": self.ambiguous_direction_ratio,
            "noisy_flat_ratio": self.noisy_flat_ratio,
            "label_noise_risk": self.label_noise_risk,
            "recommendations": list(self.recommendations),
        }


def direction_sample_weight_for_row(row: DatasetRow) -> float:
    """Вес строки для direction loss.

    ML38.9: flat/bias hardening.

    Логика:
    - стабильный FLAT усиливается, потому что quick-quality показал predicted FLAT=0;
    - noisy FLAT не удаляется, но получает меньший вес;
    - UP/DOWN не должны полностью доминировать над FLAT;
    - веса не являются gate и не принимают модель.
    """

    label = str(getattr(row, "direction_label", "FLAT")).upper()

    raw_future_move = getattr(row, "future_move_atr", 0.0)
    future_move = abs(float(raw_future_move or 0.0))

    raw_favorable = getattr(row, "max_favorable_move_atr", None)
    if raw_favorable is None:
        raw_favorable = future_move
    favorable = abs(float(raw_favorable or 0.0))

    raw_adverse = getattr(row, "max_adverse_move_atr", 0.0)
    adverse = abs(float(raw_adverse or 0.0))
    directional_edge = favorable - adverse

    if label == "DOWN":
        if directional_edge >= 0.80:
            return 1.45
        if directional_edge >= 0.45:
            return 1.25
        if directional_edge >= 0.20:
            return 0.85
        return 0.45

    if label == "UP":
        if directional_edge >= 0.80:
            return 1.05
        if directional_edge >= 0.45:
            return 0.95
        if directional_edge >= 0.20:
            return 0.70
        return 0.40

    # FLAT: стабильный flat теперь важнее, чем в ML38.8.
    max_excursion = max(favorable, adverse)
    if max_excursion <= 0.30 and future_move <= 0.20:
        return 1.45
    if max_excursion <= 0.50 and future_move <= 0.30:
        return 1.25
    if max_excursion <= 0.75:
        return 0.85
    return 0.45


def baseline_edge_sample_weight_for_row(
    row,
    *,
    base_weight: float | None = None,
    enabled: bool = True,
    directional_opportunity_boost: float = 1.20,
    clean_flat_boost: float = 1.15,
    noisy_flat_penalty: float = 0.85,
    min_weight: float = 0.20,
    max_weight: float = 4.00,
) -> float:
    """Baseline-edge-aware sample weight.

    The goal is not to blindly boost UP/DOWN. The goal is to make training care
    more about rows where the model can realistically beat a naive baseline:
    - clear UP/DOWN directional opportunity;
    - clean low-move FLAT rows;
    - less noisy ambiguous FLAT rows.
    """
    if base_weight is None:
        base_weight = direction_sample_weight_for_row(row)

    weight = float(base_weight)
    if not enabled:
        return _clamp_float(weight, min_weight, max_weight)

    label = str(getattr(row, "direction_label", "") or "").upper()
    future_move_atr = abs(_safe_float(getattr(row, "future_move_atr", 0.0), 0.0))
    max_favorable_move_atr = abs(
        _safe_float(getattr(row, "max_favorable_move_atr", future_move_atr), future_move_atr)
    )
    max_adverse_move_atr = abs(_safe_float(getattr(row, "max_adverse_move_atr", 0.0), 0.0))
    tp_before_sl = getattr(row, "tp_before_sl", None)

    if label in {"UP", "DOWN"}:
        if max_favorable_move_atr >= 0.50 or future_move_atr >= 0.50:
            weight *= directional_opportunity_boost
        if tp_before_sl is True:
            weight *= 1.05
        if max_adverse_move_atr > 0 and max_favorable_move_atr >= max_adverse_move_atr * 1.25:
            weight *= 1.05

    if label == "FLAT":
        if future_move_atr <= 0.25 and max_favorable_move_atr <= 0.35:
            weight *= clean_flat_boost
        elif future_move_atr >= 0.60 or max_favorable_move_atr >= 0.70:
            weight *= noisy_flat_penalty

    return _clamp_float(weight, min_weight, max_weight)


def _safe_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, float(value)))
