from __future__ import annotations

from dataclasses import dataclass


DEFAULT_OPPORTUNITY_THRESHOLD_CANDIDATES = (0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80)


@dataclass(frozen=True, slots=True)
class OpportunityThresholdMetrics:
    threshold: float
    row_count: int
    true_positive_count: int
    false_positive_count: int
    false_negative_count: int
    true_negative_count: int
    actual_trade_rate: float
    predicted_trade_rate: float
    predicted_to_actual_trade_rate_ratio: float
    accuracy: float
    precision: float
    recall: float
    f1: float
    false_positive_rate: float
    passed_precision_control: bool = False
    failed_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, float | int | bool | list[str]]:
        return {
            "threshold": self.threshold,
            "row_count": self.row_count,
            "true_positive_count": self.true_positive_count,
            "false_positive_count": self.false_positive_count,
            "false_negative_count": self.false_negative_count,
            "true_negative_count": self.true_negative_count,
            "actual_trade_rate": self.actual_trade_rate,
            "predicted_trade_rate": self.predicted_trade_rate,
            "predicted_to_actual_trade_rate_ratio": self.predicted_to_actual_trade_rate_ratio,
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "false_positive_rate": self.false_positive_rate,
            "passed_precision_control": self.passed_precision_control,
            "failed_reasons": list(self.failed_reasons),
        }


@dataclass(frozen=True, slots=True)
class OpportunityThresholdSelection:
    selected_threshold: float
    threshold_candidates: tuple[float, ...]
    passed_precision_control: bool
    failed_reasons: tuple[str, ...]
    selected_metrics: OpportunityThresholdMetrics
    candidate_metrics: tuple[OpportunityThresholdMetrics, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "selected_threshold": self.selected_threshold,
            "threshold_candidates": list(self.threshold_candidates),
            "passed_precision_control": self.passed_precision_control,
            "failed_reasons": list(self.failed_reasons),
            "selected_metrics": self.selected_metrics.to_dict(),
            "candidate_metrics": [item.to_dict() for item in self.candidate_metrics],
        }


def compute_opportunity_threshold_metrics(
    opportunity_probabilities: list[float] | None,
    opportunity_targets: list[int] | None,
    *,
    threshold: float,
) -> OpportunityThresholdMetrics:
    probabilities = list(opportunity_probabilities or [])
    targets = [int(value) for value in (opportunity_targets or [])]
    row_count = min(len(probabilities), len(targets))
    probabilities = probabilities[:row_count]
    targets = targets[:row_count]
    predicted_trade_flags = [int(probability >= threshold) for probability in probabilities]

    true_positive_count = 0
    false_positive_count = 0
    false_negative_count = 0
    true_negative_count = 0
    for predicted_trade, actual_trade in zip(predicted_trade_flags, targets):
        if actual_trade == 1 and predicted_trade == 1:
            true_positive_count += 1
        elif actual_trade == 0 and predicted_trade == 1:
            false_positive_count += 1
        elif actual_trade == 1 and predicted_trade == 0:
            false_negative_count += 1
        else:
            true_negative_count += 1

    predicted_trade_rate = (
        sum(predicted_trade_flags) / row_count
        if row_count > 0
        else 0.0
    )
    actual_trade_rate = (
        sum(targets) / row_count
        if row_count > 0
        else 0.0
    )
    if actual_trade_rate == 0.0:
        predicted_to_actual_trade_rate_ratio = 0.0 if predicted_trade_rate == 0.0 else 999.0
    else:
        predicted_to_actual_trade_rate_ratio = predicted_trade_rate / actual_trade_rate

    accuracy = (
        (true_positive_count + true_negative_count) / row_count
        if row_count > 0
        else 0.0
    )
    precision = (
        true_positive_count / (true_positive_count + false_positive_count)
        if (true_positive_count + false_positive_count) > 0
        else 0.0
    )
    recall = (
        true_positive_count / (true_positive_count + false_negative_count)
        if (true_positive_count + false_negative_count) > 0
        else 0.0
    )
    f1 = (
        2.0 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    false_positive_rate = (
        false_positive_count / (false_positive_count + true_negative_count)
        if (false_positive_count + true_negative_count) > 0
        else 0.0
    )
    return OpportunityThresholdMetrics(
        threshold=float(threshold),
        row_count=row_count,
        true_positive_count=true_positive_count,
        false_positive_count=false_positive_count,
        false_negative_count=false_negative_count,
        true_negative_count=true_negative_count,
        actual_trade_rate=actual_trade_rate,
        predicted_trade_rate=predicted_trade_rate,
        predicted_to_actual_trade_rate_ratio=predicted_to_actual_trade_rate_ratio,
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        f1=f1,
        false_positive_rate=false_positive_rate,
    )


def select_opportunity_threshold(
    opportunity_probabilities: list[float] | None,
    opportunity_targets: list[int] | None,
    *,
    candidates: tuple[float, ...] = DEFAULT_OPPORTUNITY_THRESHOLD_CANDIDATES,
    min_precision: float = 0.25,
    min_recall: float = 0.50,
    max_predicted_trade_rate: float = 0.15,
    max_predicted_to_actual_trade_rate_ratio: float = 3.0,
    max_false_positive_rate: float = 0.25,
) -> OpportunityThresholdSelection:
    normalized_candidates = tuple(float(item) for item in candidates) or DEFAULT_OPPORTUNITY_THRESHOLD_CANDIDATES
    candidate_metrics: list[OpportunityThresholdMetrics] = []
    for threshold in normalized_candidates:
        metrics = compute_opportunity_threshold_metrics(
            opportunity_probabilities,
            opportunity_targets,
            threshold=threshold,
        )
        failed_reasons: list[str] = []
        if metrics.precision < min_precision:
            failed_reasons.append("opportunity_precision_gate")
        if metrics.recall < min_recall:
            failed_reasons.append("opportunity_recall_gate")
        if metrics.predicted_trade_rate > max_predicted_trade_rate:
            failed_reasons.append("predicted_trade_rate_gate")
        if metrics.predicted_to_actual_trade_rate_ratio > max_predicted_to_actual_trade_rate_ratio:
            failed_reasons.append("trade_rate_ratio_gate")
        if metrics.false_positive_rate > max_false_positive_rate:
            failed_reasons.append("opportunity_false_positive_gate")
        candidate_metrics.append(
            OpportunityThresholdMetrics(
                threshold=metrics.threshold,
                row_count=metrics.row_count,
                true_positive_count=metrics.true_positive_count,
                false_positive_count=metrics.false_positive_count,
                false_negative_count=metrics.false_negative_count,
                true_negative_count=metrics.true_negative_count,
                actual_trade_rate=metrics.actual_trade_rate,
                predicted_trade_rate=metrics.predicted_trade_rate,
                predicted_to_actual_trade_rate_ratio=metrics.predicted_to_actual_trade_rate_ratio,
                accuracy=metrics.accuracy,
                precision=metrics.precision,
                recall=metrics.recall,
                f1=metrics.f1,
                false_positive_rate=metrics.false_positive_rate,
                passed_precision_control=not failed_reasons,
                failed_reasons=tuple(failed_reasons),
            )
        )

    def selection_score(metrics: OpportunityThresholdMetrics) -> float:
        ratio_penalty = max(0.0, metrics.predicted_to_actual_trade_rate_ratio - 1.0) * 0.20
        trade_rate_penalty = max(0.0, metrics.predicted_trade_rate - max_predicted_trade_rate) * 5.0
        false_positive_penalty = max(0.0, metrics.false_positive_rate - max_false_positive_rate) * 2.0
        return round(
            (metrics.f1 * 10.0)
            + (metrics.precision * 3.0)
            + (metrics.recall * 1.5)
            - ratio_penalty
            - trade_rate_penalty
            - false_positive_penalty,
            8,
        )

    passing_candidates = [item for item in candidate_metrics if item.passed_precision_control]
    selection_pool = passing_candidates or candidate_metrics
    selected_metrics = max(
        selection_pool,
        key=lambda item: (
            selection_score(item),
            item.precision,
            item.recall,
            -item.predicted_to_actual_trade_rate_ratio,
            -item.predicted_trade_rate,
            item.threshold,
        ),
    )
    return OpportunityThresholdSelection(
        selected_threshold=selected_metrics.threshold,
        threshold_candidates=normalized_candidates,
        passed_precision_control=selected_metrics.passed_precision_control,
        failed_reasons=selected_metrics.failed_reasons,
        selected_metrics=selected_metrics,
        candidate_metrics=tuple(candidate_metrics),
    )
