from __future__ import annotations

from typing import Any

import torch

from app.diagnostics.entry_path_quality_filter import EntryPathQualityFilter
from app.diagnostics.trap_invalidation_feature_impact_audit import TrapInvalidationFeatureImpactAudit
from app.training.metrics import TrainingMetrics
from app.training.probability_calibration import softmax_with_temperature
from app.training.two_stage_thresholds import DEFAULT_OPPORTUNITY_THRESHOLD_CANDIDATES
from app.training.two_stage_thresholds import select_opportunity_threshold


class Evaluator:
    def __init__(
        self,
        metrics: TrainingMetrics | None = None,
        trap_invalidation_feature_impact_audit: TrapInvalidationFeatureImpactAudit | None = None,
        entry_path_quality_filter: EntryPathQualityFilter | None = None,
    ) -> None:
        self._metrics = metrics or TrainingMetrics()
        self._trap_invalidation_feature_impact_audit = (
            trap_invalidation_feature_impact_audit or TrapInvalidationFeatureImpactAudit()
        )
        self._entry_path_quality_filter = entry_path_quality_filter or EntryPathQualityFilter()

    def evaluate(
        self,
        model: torch.nn.Module,
        dataset: dict[str, torch.Tensor],
        direction_temperature: float = 1.0,
        opportunity_probability_threshold: float = 0.5,
        setup_quality_min_threshold: float | None = None,
        setup_quality_decision_mask_enabled: bool = False,
        setup_quality_decision_mask_min_threshold: float | None = None,
        entry_path_quality_filter_enabled: bool = False,
        entry_path_quality_min_threshold: float | None = None,
        stop_pressure_max_risk_score: float | None = None,
        opportunity_threshold_sweep_enabled: bool = False,
        opportunity_threshold_candidates: tuple[float, ...] = DEFAULT_OPPORTUNITY_THRESHOLD_CANDIDATES,
        opportunity_min_precision: float = 0.25,
        opportunity_min_recall: float = 0.50,
        opportunity_max_predicted_trade_rate: float = 0.15,
        opportunity_max_predicted_to_actual_trade_rate_ratio: float = 3.0,
        opportunity_max_false_positive_rate: float = 0.25,
        training_objective: str = "direction_global",
    ) -> dict[str, Any]:
        if dataset["features"].shape[0] == 0:
            return {
                "accuracy": 0.0,
                "precision_up": 0.0,
                "precision_down": 0.0,
                "confusion_matrix": [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
                "brier_score": 0.0,
                "tp_before_sl_accuracy": None,
                "average_expected_move_error": 0.0,
                "rows": 0,
                "direction_temperature": float(direction_temperature),
                "direction_evaluation_rows": 0,
                "opportunity_probability_threshold": float(opportunity_probability_threshold),
                "setup_quality_min_threshold": setup_quality_min_threshold,
                "setup_quality_decision_mask_enabled": bool(setup_quality_decision_mask_enabled),
                "setup_quality_decision_mask_min_threshold": setup_quality_decision_mask_min_threshold,
                "setup_quality_masked_row_count": 0,
                "setup_quality_forced_no_trade_count": 0,
                "setup_quality_mask_false_positive_removed_count": 0,
                "setup_quality_mask_trade_prediction_removed_count": 0,
                "raw_predicted_trade_rate": 0.0,
                "masked_predicted_trade_rate": 0.0,
                "raw_opportunity_precision": 0.0,
                "raw_opportunity_recall": 0.0,
                "raw_opportunity_f1": 0.0,
                "setup_quality_bucket_metrics": {},
                "setup_quality_bucket_metrics_raw": {},
                "setup_quality_bucket_metrics_after_mask": {},
                "setup_quality_distribution": {},
                "setup_quality_filter_summary": {},
                "entry_path_quality_filter_enabled": bool(entry_path_quality_filter_enabled),
                "entry_path_quality_min_threshold": entry_path_quality_min_threshold,
                "stop_pressure_max_risk_score": stop_pressure_max_risk_score,
                "entry_path_quality_masked_row_count": 0,
                "entry_path_quality_forced_no_trade_count": 0,
                "entry_path_quality_mask_trade_prediction_removed_count": 0,
                "entry_path_quality_mask_false_positive_removed_count": 0,
                "entry_path_quality_filter_summary": {},
                "entry_path_quality_filter_diagnostics": {},
            }

        opportunity_target_tensor = dataset.get("opportunity_target")
        if opportunity_target_tensor is None:
            opportunity_target_tensor = torch.ones_like(
                dataset["direction_target"],
                dtype=torch.float32,
            )
        else:
            opportunity_target_tensor = opportunity_target_tensor.to(dtype=torch.float32)
        setup_quality_score_tensor = dataset.get("setup_quality_score")
        if setup_quality_score_tensor is None:
            setup_quality_score_tensor = torch.zeros_like(
                dataset["direction_target"],
                dtype=torch.float32,
            )
        else:
            setup_quality_score_tensor = setup_quality_score_tensor.to(dtype=torch.float32)

        model.eval()
        with torch.no_grad():
            raw_outputs = model(dataset["features"])
            outputs = self._normalize_outputs(raw_outputs, dataset["features"])
            direction_probabilities_tensor = softmax_with_temperature(
                outputs["direction_logits"],
                temperature=direction_temperature,
            )
            tp_probabilities_tensor = torch.sigmoid(outputs["tp_sl_logits"])
            opportunity_probabilities_tensor = torch.sigmoid(outputs["opportunity_logit"])
            opportunity_target_tensor = opportunity_target_tensor.to(
                device=direction_probabilities_tensor.device,
                dtype=torch.float32,
            )
            direction_mask = None
            if training_objective in {"opportunity_first", "trade_two_stage"}:
                direction_mask = (opportunity_target_tensor > 0).cpu().tolist()

        feature_columns = list(dataset.get("feature_columns") or [])
        raw_feature_values_tensor = dataset.get("raw_feature_values")
        raw_feature_values = (
            raw_feature_values_tensor.cpu().tolist()
            if hasattr(raw_feature_values_tensor, "cpu")
            else list(raw_feature_values_tensor or [])
        )
        def _to_float_list(value: Any) -> list[float]:
            if value is None:
                return []
            if hasattr(value, "cpu"):
                value = value.cpu().tolist()
            return [float(item) for item in list(value)]

        move_target_tensor = dataset.get("move_target")
        risk_target_tensor = dataset.get("risk_target")
        move_targets = _to_float_list(move_target_tensor)
        risk_targets = _to_float_list(risk_target_tensor)
        setup_quality_scores = setup_quality_score_tensor.cpu().tolist()
        entry_path_quality_payload = self._entry_path_quality_filter.score_rows(
            feature_names=feature_columns,
            feature_rows=raw_feature_values,
            setup_quality_scores=setup_quality_scores,
            expected_move_atr=[float(value) for value in move_targets],
            invalidation_distance_atr=[float(value) for value in risk_targets],
        )

        metrics = self._metrics.compute(
            direction_probabilities=direction_probabilities_tensor.cpu().tolist(),
            direction_targets=dataset["direction_target"].cpu().tolist(),
            tp_sl_probabilities=tp_probabilities_tensor.cpu().tolist(),
            tp_sl_targets=self._decode_optional_boolean_targets(dataset["tp_sl_target"], dataset["tp_sl_mask"]),
            expected_move_predictions=outputs["expected_move_atr"].cpu().tolist(),
            expected_move_targets=dataset["move_target"].cpu().tolist(),
            direction_mask=direction_mask,
            opportunity_probabilities=opportunity_probabilities_tensor.cpu().tolist(),
            opportunity_targets=[int(value) for value in opportunity_target_tensor.cpu().tolist()],
            opportunity_probability_threshold=float(opportunity_probability_threshold),
            setup_quality_scores=setup_quality_scores,
            setup_quality_min_threshold=setup_quality_min_threshold,
            setup_quality_decision_mask_enabled=setup_quality_decision_mask_enabled,
            setup_quality_decision_mask_min_threshold=setup_quality_decision_mask_min_threshold,
            entry_path_quality_filter_enabled=entry_path_quality_filter_enabled,
            entry_path_quality_scores=list(entry_path_quality_payload.get("entry_path_quality_scores", [])),
            stop_pressure_risk_scores=list(entry_path_quality_payload.get("stop_pressure_risk_scores", [])),
            entry_path_quality_min_threshold=entry_path_quality_min_threshold,
            stop_pressure_max_risk_score=stop_pressure_max_risk_score,
            training_objective=training_objective,
        )
        metrics["entry_path_quality_filter_diagnostics"] = entry_path_quality_payload
        if training_objective == "trade_two_stage":
            metrics["trap_invalidation_feature_impact_audit"] = (
                self._trap_invalidation_feature_impact_audit.analyze(
                    feature_names=feature_columns,
                    feature_rows=raw_feature_values,
                    opportunity_probabilities=opportunity_probabilities_tensor.cpu().tolist(),
                    opportunity_targets=[int(value) for value in opportunity_target_tensor.cpu().tolist()],
                    direction_targets=[int(value) for value in dataset["direction_target"].cpu().tolist()],
                    direction_probabilities=direction_probabilities_tensor.cpu().tolist(),
                    setup_quality_scores=setup_quality_score_tensor.cpu().tolist(),
                    opportunity_probability_threshold=float(opportunity_probability_threshold),
                    setup_quality_decision_mask_enabled=bool(setup_quality_decision_mask_enabled),
                    setup_quality_decision_mask_min_threshold=setup_quality_decision_mask_min_threshold,
                )
            )
        metrics["rows"] = int(dataset["features"].shape[0])
        metrics["direction_temperature"] = float(direction_temperature)
        metrics["training_objective"] = training_objective
        metrics["opportunity_probability_mean"] = float(opportunity_probabilities_tensor.mean().detach().item())
        metrics["no_trade_probability_mean"] = float((1.0 - opportunity_probabilities_tensor).mean().detach().item())
        if training_objective == "trade_two_stage" and opportunity_threshold_sweep_enabled:
            threshold_selection = select_opportunity_threshold(
                opportunity_probabilities_tensor.cpu().tolist(),
                [int(value) for value in opportunity_target_tensor.cpu().tolist()],
                candidates=tuple(float(item) for item in opportunity_threshold_candidates),
                min_precision=float(opportunity_min_precision),
                min_recall=float(opportunity_min_recall),
                max_predicted_trade_rate=float(opportunity_max_predicted_trade_rate),
                max_predicted_to_actual_trade_rate_ratio=float(
                    opportunity_max_predicted_to_actual_trade_rate_ratio
                ),
                max_false_positive_rate=float(opportunity_max_false_positive_rate),
            )
            metrics["opportunity_threshold_sweep"] = threshold_selection.to_dict()

        conditioned_direction_probabilities = direction_probabilities_tensor
        if training_objective == "opportunity_first" and direction_mask and any(direction_mask):
            conditioned_direction_probabilities = direction_probabilities_tensor[opportunity_target_tensor > 0]

        direction_probability_mean = conditioned_direction_probabilities.mean(dim=0)
        metrics["direction_probabilities_conditioned_on_opportunity_mean"] = {
            "UP": float(direction_probability_mean[0].detach().item()),
            "DOWN": float(direction_probability_mean[1].detach().item()),
            "FLAT": float(direction_probability_mean[2].detach().item()),
        }
        if training_objective == "trade_two_stage":
            trade_mask_tensor = opportunity_target_tensor > 0
            if torch.any(trade_mask_tensor):
                trade_direction_probs = direction_probabilities_tensor[trade_mask_tensor][:, :2]
                trade_direction_probs = trade_direction_probs / trade_direction_probs.sum(dim=1, keepdim=True).clamp_min(1e-8)
                trade_direction_mean = trade_direction_probs.mean(dim=0)
                metrics["direction_probabilities_conditioned_on_trade_mean"] = {
                    "UP": float(trade_direction_mean[0].detach().item()),
                    "DOWN": float(trade_direction_mean[1].detach().item()),
                }
            else:
                metrics["direction_probabilities_conditioned_on_trade_mean"] = {"UP": 0.0, "DOWN": 0.0}
        return metrics

    @staticmethod
    def _decode_optional_boolean_targets(tp_targets: torch.Tensor, tp_mask: torch.Tensor) -> list[bool | None]:
        decoded: list[bool | None] = []
        for value, mask in zip(tp_targets.cpu().tolist(), tp_mask.cpu().tolist()):
            if mask <= 0:
                decoded.append(None)
            else:
                decoded.append(value >= 0.5)
        return decoded

    @staticmethod
    def _normalize_outputs(
        outputs: Any,
        features: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        if isinstance(outputs, dict):
            payload = dict(outputs)
            row_count = int(features.shape[0])
            payload.setdefault("tp_sl_logits", torch.zeros((row_count,), dtype=features.dtype, device=features.device))
            payload.setdefault("expected_move_atr", torch.zeros((row_count,), dtype=features.dtype, device=features.device))
            payload.setdefault("risk_score", torch.zeros((row_count,), dtype=features.dtype, device=features.device))
            payload.setdefault("opportunity_logit", torch.zeros((row_count,), dtype=features.dtype, device=features.device))
            return payload
        logits = outputs
        row_count = int(features.shape[0])
        zero = torch.zeros((row_count,), dtype=features.dtype, device=features.device)
        return {
            "direction_logits": logits,
            "tp_sl_logits": zero,
            "expected_move_atr": zero,
            "risk_score": zero,
            "opportunity_logit": zero,
        }
