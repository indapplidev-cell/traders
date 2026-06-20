from __future__ import annotations

from typing import Any

from app.diagnostics.decision_policy_grid import apply_selected_decision_policy_metrics


ML38_2_CONFIG_RANKER_NAME = "ml38_2_config_ranker"
ML38_2_CONFIG_RANKER_VERSION = "ml38_2"
FAILED_CANDIDATE_STATUSES = {"FAILED", "ERROR"}
FAILED_CANDIDATE_SCORE = -1_000_000.0
TWO_STAGE_QUALITY_MIN_PRECISION = 0.30
TWO_STAGE_QUALITY_MIN_RECALL = 0.45
TWO_STAGE_QUALITY_MIN_F1 = 0.35
TWO_STAGE_QUALITY_MIN_PREDICTED_TRADE_RATE = 0.03
TWO_STAGE_QUALITY_MAX_PREDICTED_TRADE_RATE = 0.14
TWO_STAGE_QUALITY_MAX_TRADE_RATE_RATIO = 2.5
TWO_STAGE_QUALITY_MAX_FALSE_POSITIVE_RATE = 0.10
TWO_STAGE_QUALITY_MIN_DIRECTION_TRADE_ROWS = 20
ANTI_UNDERTRADING_MIN_RECALL = 0.35
ANTI_UNDERTRADING_MIN_F1 = 0.20
ANTI_UNDERTRADING_MIN_DIRECTION_TRADE_ROWS = 10

# Backward-compatible aliases for ML38.10.7 tests and old reports.
SETUP_QUALITY_FILTER_MIN_PRECISION = TWO_STAGE_QUALITY_MIN_PRECISION
SETUP_QUALITY_FILTER_MIN_RECALL = TWO_STAGE_QUALITY_MIN_RECALL
SETUP_QUALITY_FILTER_MAX_PREDICTED_TRADE_RATE = 0.15
SETUP_QUALITY_FILTER_MAX_TRADE_RATE_RATIO = TWO_STAGE_QUALITY_MAX_TRADE_RATE_RATIO
SETUP_QUALITY_FILTER_MAX_FALSE_POSITIVE_RATE = 0.12

def is_rankable_candidate_status(status: str | None) -> bool:
    return str(status or "").upper() not in FAILED_CANDIDATE_STATUSES


def evaluate_setup_quality_filter(
    *,
    opportunity_precision: Any,
    opportunity_recall: Any,
    predicted_trade_rate: Any,
    actual_trade_rate: Any,
    predicted_to_actual_trade_rate_ratio: Any,
    opportunity_false_positive_rate: Any,
) -> dict[str, Any]:
    required_metrics = (
        opportunity_precision,
        opportunity_recall,
        predicted_trade_rate,
        actual_trade_rate,
        predicted_to_actual_trade_rate_ratio,
        opportunity_false_positive_rate,
    )
    if any(value is None for value in required_metrics):
        return {"passed": False, "reason": "missing_two_stage_metrics"}

    actual_trade_rate_value = float(actual_trade_rate)
    if actual_trade_rate_value <= 0.0:
        return {"passed": False, "reason": "no_actual_trade_rows"}

    precision_value = float(opportunity_precision)
    recall_value = float(opportunity_recall)
    predicted_trade_rate_value = float(predicted_trade_rate)
    trade_rate_ratio_value = float(predicted_to_actual_trade_rate_ratio)
    false_positive_rate_value = float(opportunity_false_positive_rate)

    if precision_value < SETUP_QUALITY_FILTER_MIN_PRECISION:
        return {"passed": False, "reason": "precision_below_minimum"}
    if recall_value < SETUP_QUALITY_FILTER_MIN_RECALL:
        return {"passed": False, "reason": "recall_below_minimum"}
    if predicted_trade_rate_value > SETUP_QUALITY_FILTER_MAX_PREDICTED_TRADE_RATE:
        return {"passed": False, "reason": "predicted_trade_rate_too_high"}
    if trade_rate_ratio_value > SETUP_QUALITY_FILTER_MAX_TRADE_RATE_RATIO:
        return {"passed": False, "reason": "predicted_to_actual_trade_rate_ratio_too_high"}
    if false_positive_rate_value > SETUP_QUALITY_FILTER_MAX_FALSE_POSITIVE_RATE:
        return {"passed": False, "reason": "opportunity_false_positive_rate_too_high"}

    return {"passed": True, "reason": "passed"}


def evaluate_two_stage_quality_gate(
    *,
    opportunity_precision: Any,
    opportunity_recall: Any,
    opportunity_f1: Any,
    predicted_trade_rate: Any,
    actual_trade_rate: Any,
    predicted_to_actual_trade_rate_ratio: Any,
    opportunity_false_positive_rate: Any,
    direction_trade_rows: Any,
    missing_or_zero_false_positive_count: Any,
) -> dict[str, Any]:
    required_metrics = (
        opportunity_precision,
        opportunity_recall,
        opportunity_f1,
        predicted_trade_rate,
        actual_trade_rate,
        predicted_to_actual_trade_rate_ratio,
        opportunity_false_positive_rate,
    )
    if any(value is None for value in required_metrics):
        return {
            "passed": False,
            "reason": "missing_two_stage_metrics",
            "failed_reasons": ["missing_two_stage_metrics"],
        }

    actual_trade_rate_value = float(actual_trade_rate)
    if actual_trade_rate_value <= 0.0:
        return {
            "passed": False,
            "reason": "no_actual_trade_rows",
            "failed_reasons": ["no_actual_trade_rows"],
        }

    precision_value = float(opportunity_precision)
    recall_value = float(opportunity_recall)
    f1_value = float(opportunity_f1)
    predicted_trade_rate_value = float(predicted_trade_rate)
    trade_rate_ratio_value = float(predicted_to_actual_trade_rate_ratio)
    false_positive_rate_value = float(opportunity_false_positive_rate)
    direction_rows_value = int(direction_trade_rows or 0)
    missing_fp_value = int(missing_or_zero_false_positive_count or 0)

    failed_reasons: list[str] = []
    if precision_value < TWO_STAGE_QUALITY_MIN_PRECISION:
        failed_reasons.append("precision_below_minimum")
    if recall_value < TWO_STAGE_QUALITY_MIN_RECALL:
        failed_reasons.append("recall_below_minimum")
    if f1_value < TWO_STAGE_QUALITY_MIN_F1:
        failed_reasons.append("f1_below_minimum")
    if predicted_trade_rate_value < TWO_STAGE_QUALITY_MIN_PREDICTED_TRADE_RATE:
        failed_reasons.append("predicted_trade_rate_too_low")
    if predicted_trade_rate_value > TWO_STAGE_QUALITY_MAX_PREDICTED_TRADE_RATE:
        failed_reasons.append("predicted_trade_rate_too_high")
    if trade_rate_ratio_value > TWO_STAGE_QUALITY_MAX_TRADE_RATE_RATIO:
        failed_reasons.append("predicted_to_actual_trade_rate_ratio_too_high")
    if false_positive_rate_value > TWO_STAGE_QUALITY_MAX_FALSE_POSITIVE_RATE:
        failed_reasons.append("opportunity_false_positive_rate_too_high")
    if missing_fp_value > 0:
        failed_reasons.append("missing_or_zero_false_positive_count_above_zero")
    if direction_rows_value < TWO_STAGE_QUALITY_MIN_DIRECTION_TRADE_ROWS:
        failed_reasons.append("direction_trade_rows_too_low")

    return {
        "passed": not failed_reasons,
        "reason": "passed" if not failed_reasons else failed_reasons[0],
        "failed_reasons": failed_reasons,
        "minimums": {
            "precision": TWO_STAGE_QUALITY_MIN_PRECISION,
            "recall": TWO_STAGE_QUALITY_MIN_RECALL,
            "f1": TWO_STAGE_QUALITY_MIN_F1,
            "predicted_trade_rate": TWO_STAGE_QUALITY_MIN_PREDICTED_TRADE_RATE,
            "direction_trade_rows": TWO_STAGE_QUALITY_MIN_DIRECTION_TRADE_ROWS,
        },
        "maximums": {
            "predicted_trade_rate": TWO_STAGE_QUALITY_MAX_PREDICTED_TRADE_RATE,
            "predicted_to_actual_trade_rate_ratio": TWO_STAGE_QUALITY_MAX_TRADE_RATE_RATIO,
            "opportunity_false_positive_rate": TWO_STAGE_QUALITY_MAX_FALSE_POSITIVE_RATE,
            "missing_or_zero_false_positive_count": 0,
        },
    }


def evaluate_anti_undertrading_gate(
    *,
    opportunity_recall: Any,
    opportunity_f1: Any,
    predicted_trade_rate: Any,
    direction_trade_rows: Any,
) -> dict[str, Any]:
    recall_value = float(opportunity_recall or 0.0)
    f1_value = float(opportunity_f1 or 0.0)
    predicted_trade_rate_value = float(predicted_trade_rate or 0.0)
    direction_rows_value = int(direction_trade_rows or 0)

    failed_reasons: list[str] = []
    if predicted_trade_rate_value < TWO_STAGE_QUALITY_MIN_PREDICTED_TRADE_RATE:
        failed_reasons.append("predicted_trade_rate_too_low")
    if recall_value < ANTI_UNDERTRADING_MIN_RECALL:
        failed_reasons.append("recall_too_low")
    if f1_value < ANTI_UNDERTRADING_MIN_F1:
        failed_reasons.append("f1_too_low")
    if direction_rows_value < ANTI_UNDERTRADING_MIN_DIRECTION_TRADE_ROWS:
        failed_reasons.append("direction_trade_rows_too_low")

    return {
        "passed": not failed_reasons,
        "reason": "passed" if not failed_reasons else failed_reasons[0],
        "failed_reasons": failed_reasons,
    }


class ML382ConfigRanker:
    def _baseline_edge_score_component(self, candidate: dict) -> tuple[float, dict[str, float], list[str]]:
        edge = candidate.get("baseline_edge")
        components: dict[str, float] = {}
        reasons: list[str] = []

        if edge is None:
            components["baseline_edge_unknown_penalty"] = -1.0
            reasons.append("baseline_edge_unknown")
            return -1.0, components, reasons

        edge = float(edge)
        if edge < 0:
            components["baseline_edge_negative_penalty"] = -3.0
            reasons.append("baseline_edge_gate_failed")
            return -3.0, components, reasons

        if edge == 0:
            components["baseline_edge_zero_penalty"] = -1.5
            reasons.append("baseline_edge_gate_failed")
            return -1.5, components, reasons

        if edge >= 0.03:
            components["baseline_edge_strong_bonus"] = 3.0
            return 3.0, components, reasons

        if edge >= 0.015:
            components["baseline_edge_medium_bonus"] = 1.5
            return 1.5, components, reasons

        components["baseline_edge_weak_bonus"] = 0.5
        return 0.5, components, reasons

    def _collapse_severity_score_component(self, candidate: dict) -> tuple[float, dict[str, float], list[str]]:
        severity = str(candidate.get("collapse_severity") or "UNKNOWN").upper()
        components: dict[str, float] = {}
        reasons: list[str] = []

        if severity == "CRITICAL":
            components["critical_collapse_penalty"] = -5.0
            reasons.append("collapse_gate_failed")
            return -5.0, components, reasons

        if severity == "WATCH":
            components["collapse_watch_penalty"] = -1.5
            reasons.append("collapse_severity=WATCH")
            return -1.5, components, reasons

        if severity == "OK":
            components["collapse_ok_bonus"] = 1.0
            return 1.0, components, reasons

        components["collapse_unknown_penalty"] = -1.0
        reasons.append("collapse_severity_unknown")
        return -1.0, components, reasons

    def rank(self, candidates: list[object]) -> dict[str, Any]:
        normalized = [self._normalize_candidate(candidate) for candidate in candidates]
        ranked = [self._ranked_row(candidate) for candidate in normalized]
        ranked.sort(
            key=lambda item: (
                bool(item.get("excluded_from_best_selection", False)),
                -float(item["score"]),
                item["candidate_status"] != "ACCEPTED",
                item["config_id"],
            )
        )
        for index, item in enumerate(ranked, start=1):
            item["rank"] = index

        eligible = [
            item
            for item in ranked
            if not bool(item.get("excluded_from_best_selection", False))
        ]
        best = eligible[0] if eligible else None

        accepted_count = sum(int(item["candidate_status"] == "ACCEPTED") for item in ranked)
        rejected_count = sum(int(item["candidate_status"] == "REJECTED") for item in ranked)
        failed_count = sum(int(item["candidate_status"] == "FAILED") for item in ranked)

        return {
            "ranker_name": ML38_2_CONFIG_RANKER_NAME,
            "ranker_version": ML38_2_CONFIG_RANKER_VERSION,
            "ranking": ranked,
            "best_candidate": None if best is None else dict(best),
            "best_candidate_config_id": None if best is None else best["config_id"],
            "best_candidate_score": None if best is None else best["score"],
            "accepted_candidate_count": accepted_count,
            "rejected_candidate_count": rejected_count,
            "failed_candidate_count": failed_count,
            "model_accepted": accepted_count > 0,
            "reasons_why_best_still_rejected": [] if best is None else list(best["rejection_reasons"]),
        }

    def _ranked_row(self, candidate: dict[str, Any]) -> dict[str, Any]:
        candidate = dict(candidate)
        apply_selected_decision_policy_metrics(candidate)
        failed_gates = [str(item) for item in candidate.get("failed_gates", [])]
        passed_gates = [str(item) for item in candidate.get("passed_gates", [])]
        candidate_status = str(candidate.get("candidate_status") or "UNKNOWN").upper()
        excluded_from_best_selection = not is_rankable_candidate_status(candidate_status)
        walk_forward_pf = self._safe_float(candidate.get("walk_forward_profit_factor"))
        walk_forward_total_r = self._safe_float(candidate.get("walk_forward_total_r"))
        accuracy = self._safe_float(candidate.get("model_accuracy"))
        baseline = self._safe_float(candidate.get("baseline_accuracy"))
        collapse_detected = bool(candidate.get("collapse_detected", False))
        bias = dict(candidate.get("flat_bias_diagnostics", {}))
        collapse_summary = dict(candidate.get("collapse_tuning_summary", {}))
        anti_collapse_diagnostics = dict(candidate.get("anti_collapse_diagnostics", {}))
        anti_collapse_score = self._safe_float(
            candidate.get("anti_collapse_score")
            if candidate.get("anti_collapse_score") is not None
            else anti_collapse_diagnostics.get("anti_collapse_score")
        )
        anti_collapse_status = str(
            candidate.get("anti_collapse_status")
            or anti_collapse_diagnostics.get("anti_collapse_status")
            or "UNKNOWN"
        )
        anti_collapse_bonus = 0.0
        if anti_collapse_score >= 4.0:
            anti_collapse_bonus = 1.5
        elif anti_collapse_score >= 2.0:
            anti_collapse_bonus = 0.75

        confidence_profitability_diagnostics = dict(
            candidate.get("confidence_profitability_diagnostics", {})
        )
        confidence_profitability_score = self._safe_float(
            candidate.get("confidence_profitability_score")
            if candidate.get("confidence_profitability_score") is not None
            else confidence_profitability_diagnostics.get("confidence_profitability_score")
        )
        confidence_profitability_status = str(
            candidate.get("confidence_profitability_status")
            or confidence_profitability_diagnostics.get("confidence_profitability_status")
            or "UNKNOWN"
        ).upper()
        confidence_profitability_bonus = 0.0
        if confidence_profitability_status == "GOOD":
            confidence_profitability_bonus = 2.0
        elif confidence_profitability_status == "WATCH":
            confidence_profitability_bonus = 0.75
        elif confidence_profitability_status == "WEAK":
            confidence_profitability_bonus = -1.0
        calibrated_decision = dict(candidate.get("calibrated_decision_diagnostics", {}))
        calibrated_ratios = dict(calibrated_decision.get("calibrated_predicted_ratios", {}))
        raw_ratios = dict(calibrated_decision.get("raw_predicted_ratios", {}))
        calibrated_flat = float(calibrated_ratios.get("FLAT", 0.0))
        calibrated_up = float(calibrated_ratios.get("UP", 0.0))
        calibrated_down = float(calibrated_ratios.get("DOWN", 0.0))
        bounded_selection = dict(candidate.get("bounded_calibrated_decision_selection", {}))
        decision_source = str(candidate.get("prediction_decision_source") or "")
        decision_policy_payload = dict(candidate.get("decision_policy_grid_diagnostics", {}))
        selected_policy = dict(decision_policy_payload.get("selected_policy", {}))
        selected_policy_id = decision_policy_payload.get("selected_policy_id")
        selected_policy_edge = selected_policy.get("baseline_edge")
        selected_policy_safe = selected_policy.get("distribution_safe")
        training_objective = str(
            candidate.get("training_objective")
            or dict(candidate.get("label_config", {})).get("training_objective")
            or ""
        )
        two_stage_trade_diagnostics = dict(candidate.get("two_stage_trade_diagnostics", {}))
        precision_control_gates = dict(two_stage_trade_diagnostics.get("precision_control_gates", {}))
        opportunity_precision = self._safe_float(candidate.get("opportunity_precision"))
        opportunity_recall = self._safe_float(candidate.get("opportunity_recall"))
        opportunity_f1 = self._safe_float(candidate.get("opportunity_f1"))
        opportunity_false_positive_rate = self._safe_float(candidate.get("opportunity_false_positive_rate"))
        predicted_trade_rate = self._safe_float(candidate.get("predicted_trade_rate"))
        actual_trade_rate = self._safe_float(candidate.get("actual_trade_rate"))
        predicted_to_actual_trade_rate_ratio = self._safe_float(
            candidate.get("predicted_to_actual_trade_rate_ratio")
        )
        direction_accuracy_on_trade_rows = self._safe_float(
            dict(two_stage_trade_diagnostics).get("direction_accuracy_on_trade_rows")
            if two_stage_trade_diagnostics
            else candidate.get("direction_accuracy_on_trade_rows")
        )
        setup_quality_min_threshold = (
            candidate.get("setup_quality_min_threshold")
            if candidate.get("setup_quality_min_threshold") is not None
            else two_stage_trade_diagnostics.get("setup_quality_min_threshold")
        )
        setup_quality_decision_mask_summary = dict(
            candidate.get("setup_quality_decision_mask_summary")
            or two_stage_trade_diagnostics.get("setup_quality_decision_mask_summary", {})
        )
        setup_quality_bucket_metrics = dict(
            candidate.get("setup_quality_bucket_metrics")
            or two_stage_trade_diagnostics.get("setup_quality_bucket_metrics", {})
        )
        setup_quality_bucket_metrics_raw = dict(
            candidate.get("setup_quality_bucket_metrics_raw")
            or two_stage_trade_diagnostics.get("setup_quality_bucket_metrics_raw", {})
        )
        setup_quality_bucket_metrics_after_mask = dict(
            candidate.get("setup_quality_bucket_metrics_after_mask")
            or two_stage_trade_diagnostics.get("setup_quality_bucket_metrics_after_mask", {})
            or setup_quality_bucket_metrics
        )
        setup_quality_filter_summary = dict(
            candidate.get("setup_quality_filter_summary")
            or two_stage_trade_diagnostics.get("setup_quality_filter_summary", {})
        )
        setup_quality_filter = evaluate_setup_quality_filter(
            opportunity_precision=(
                candidate.get("opportunity_precision")
                if candidate.get("opportunity_precision") is not None
                else two_stage_trade_diagnostics.get("opportunity_precision")
            ),
            opportunity_recall=(
                candidate.get("opportunity_recall")
                if candidate.get("opportunity_recall") is not None
                else two_stage_trade_diagnostics.get("opportunity_recall")
            ),
            predicted_trade_rate=(
                candidate.get("predicted_trade_rate")
                if candidate.get("predicted_trade_rate") is not None
                else two_stage_trade_diagnostics.get("predicted_trade_rate")
            ),
            actual_trade_rate=(
                candidate.get("actual_trade_rate")
                if candidate.get("actual_trade_rate") is not None
                else two_stage_trade_diagnostics.get("actual_trade_rate")
            ),
            predicted_to_actual_trade_rate_ratio=(
                candidate.get("predicted_to_actual_trade_rate_ratio")
                if candidate.get("predicted_to_actual_trade_rate_ratio") is not None
                else two_stage_trade_diagnostics.get("predicted_to_actual_trade_rate_ratio")
            ),
            opportunity_false_positive_rate=(
                candidate.get("opportunity_false_positive_rate")
                if candidate.get("opportunity_false_positive_rate") is not None
                else two_stage_trade_diagnostics.get("opportunity_false_positive_rate")
            ),
        )
        two_stage_quality_gate = {
            "passed": False,
            "reason": "not_trade_two_stage",
            "failed_reasons": ["not_trade_two_stage"],
        }
        anti_undertrading_gate = {
            "passed": False,
            "reason": "not_trade_two_stage",
            "failed_reasons": ["not_trade_two_stage"],
        }
        missing_or_zero_false_positives = 0
        undertrading_risk_detected = False
        bounded_calibration_bonus = 0.0
        bounded_calibration_fallback_penalty = 0.0
        if bounded_selection:
            if decision_source == "calibrated_decision_layer":
                bounded_calibration_bonus = 0.5
            elif decision_source.startswith("raw_argmax_fallback"):
                bounded_calibration_fallback_penalty = -0.25

        score_components = {
            "walk_forward_pf_bonus": 3.0 if walk_forward_pf > 1.0 else 0.0,
            "walk_forward_total_r_bonus": 2.0 if walk_forward_total_r > 0.0 else 0.0,
            "accuracy_vs_baseline_bonus": 1.5 if accuracy > baseline else 0.0,
            "profit_aware_gate_bonus": 1.0 if "profit_aware_gate" in passed_gates else 0.0,
            "walk_forward_gate_bonus": 1.0 if "walk_forward_gate" in passed_gates else 0.0,
            "anti_collapse_bonus": anti_collapse_bonus,
            "confidence_profitability_bonus": confidence_profitability_bonus,
            "confidence_profitability_score_bonus": min(max(confidence_profitability_score, -3.0), 3.0) * 0.25,
            "flat_bias_penalty": -2.0
            if str(bias.get("symbol_bias_severity")) in {"HIGH", "CRITICAL"}
            else 0.0,
            "down_blindness_penalty": -2.0
            if bool(bias.get("down_blindness_detected", False))
            else 0.0,
            "up_bias_penalty": -2.0
            if bool(bias.get("up_bias_detected", False))
            else 0.0,
            "flat_underprediction_penalty": -2.0
            if bool(bias.get("flat_underprediction_detected", False))
            else 0.0,
            "up_dominance_penalty": -3.0
            if bool(bias.get("up_dominance_detected", False))
            else 0.0,
            "bias_gate_penalty": -2.0 if "bias_gate" in failed_gates else 0.0,
            "walk_forward_gate_penalty": -3.0 if "walk_forward_gate" in failed_gates else 0.0,
            "bounded_calibration_bonus": bounded_calibration_bonus,
            "bounded_calibration_fallback_penalty": bounded_calibration_fallback_penalty,
        }
        if selected_policy_id:
            score_components["decision_policy_grid_bonus"] = 0.75
        else:
            score_components["decision_policy_grid_bonus"] = 0.0

        if selected_policy_safe is True:
            score_components["decision_policy_distribution_bonus"] = 1.0
        else:
            score_components["decision_policy_distribution_bonus"] = 0.0

        try:
            edge = float(selected_policy_edge)
        except (TypeError, ValueError):
            edge = None

        if edge is not None and edge > 0.0:
            score_components["decision_policy_baseline_edge_bonus"] = min(3.0, edge * 50.0)
        else:
            score_components["decision_policy_baseline_edge_bonus"] = 0.0
        if training_objective == "trade_two_stage":
            missing_or_zero_bucket = dict(
                setup_quality_bucket_metrics_after_mask.get("missing_or_zero", {})
            )
            missing_or_zero_false_positives = int(
                missing_or_zero_bucket.get("false_positive_count", 0) or 0
            )
            low_quality_false_positive_count = sum(
                int(dict(setup_quality_bucket_metrics_after_mask.get(bucket_name, {})).get("false_positive_count", 0) or 0)
                for bucket_name in ("low_0_00_0_40", "mid_0_40_0_60")
            )
            raw_predicted_trade_rate = self._safe_float(candidate.get("raw_predicted_trade_rate"))
            masked_predicted_trade_rate = self._safe_float(
                candidate.get("masked_predicted_trade_rate")
                if candidate.get("masked_predicted_trade_rate") is not None
                else predicted_trade_rate
            )
            forced_no_trade_count = self._safe_float(
                setup_quality_decision_mask_summary.get("forced_no_trade_count")
            )
            predicted_trade_removed_ratio = 0.0
            if raw_predicted_trade_rate > 0.0:
                predicted_trade_removed_ratio = max(
                    0.0,
                    (raw_predicted_trade_rate - masked_predicted_trade_rate) / raw_predicted_trade_rate,
                )
            direction_trade_rows = int(
                candidate.get("direction_trade_rows")
                or two_stage_trade_diagnostics.get("direction_trade_rows")
                or 0
            )
            two_stage_quality_gate = evaluate_two_stage_quality_gate(
                opportunity_precision=opportunity_precision,
                opportunity_recall=opportunity_recall,
                opportunity_f1=opportunity_f1,
                predicted_trade_rate=predicted_trade_rate,
                actual_trade_rate=actual_trade_rate,
                predicted_to_actual_trade_rate_ratio=predicted_to_actual_trade_rate_ratio,
                opportunity_false_positive_rate=opportunity_false_positive_rate,
                direction_trade_rows=direction_trade_rows,
                missing_or_zero_false_positive_count=missing_or_zero_false_positives,
            )
            anti_undertrading_gate = evaluate_anti_undertrading_gate(
                opportunity_recall=opportunity_recall,
                opportunity_f1=opportunity_f1,
                predicted_trade_rate=predicted_trade_rate,
                direction_trade_rows=direction_trade_rows,
            )
            undertrading_risk_detected = not bool(anti_undertrading_gate.get("passed"))
            score_components["opportunity_f1_bonus"] = min(3.0, opportunity_f1 * 6.0)
            score_components["opportunity_precision_bonus"] = min(2.5, opportunity_precision * 5.0)
            score_components["direction_accuracy_trade_rows_bonus"] = min(
                1.0,
                max(0.0, direction_accuracy_on_trade_rows - 0.45) * 4.0,
            )
            score_components["setup_quality_filter_bonus"] = 0.5 if bool(setup_quality_filter.get("passed")) else 0.0
            score_components["setup_quality_missing_fp_zero_bonus"] = (
                1.0 if missing_or_zero_false_positives == 0 else -2.0
            )
            score_components["setup_quality_precision_gate_bonus"] = (
                0.75 if opportunity_precision >= 0.30 else 0.0
            )
            score_components["setup_quality_trade_rate_bonus"] = (
                0.50 if predicted_trade_rate <= 0.13 else 0.0
            )
            score_components["setup_quality_low_bucket_fp_penalty"] = -min(
                2.0,
                low_quality_false_positive_count * 0.5,
            )
            score_components["trade_rate_ratio_penalty"] = -max(
                0.0,
                predicted_to_actual_trade_rate_ratio - 2.5,
            )
            score_components["opportunity_false_positive_penalty"] = -max(
                0.0,
                opportunity_false_positive_rate - SETUP_QUALITY_FILTER_MAX_FALSE_POSITIVE_RATE,
            ) * 10.0
            score_components["predicted_trade_rate_ceiling_penalty"] = -max(
                0.0,
                predicted_trade_rate - SETUP_QUALITY_FILTER_MAX_PREDICTED_TRADE_RATE,
            ) * 20.0
            score_components["setup_quality_over_masking_penalty"] = (
                -1.5
                if forced_no_trade_count > 0 and predicted_trade_removed_ratio > 0.35 and opportunity_recall < 0.45
                else 0.0
            )
            score_components["two_stage_quality_gate_bonus"] = (
                3.0 if bool(two_stage_quality_gate.get("passed")) else -1.5
            )
            score_components["anti_undertrading_gate_bonus"] = (
                1.25 if bool(anti_undertrading_gate.get("passed")) else -3.0
            )
            score_components["opportunity_f1_quality_bonus"] = min(2.0, opportunity_f1 * 5.0)
            score_components["balanced_trade_rate_bonus"] = (
                1.0 if 0.06 <= predicted_trade_rate <= 0.14 else 0.0
            )
            score_components["undertrading_predicted_trade_rate_penalty"] = (
                -4.0 if predicted_trade_rate < TWO_STAGE_QUALITY_MIN_PREDICTED_TRADE_RATE else 0.0
            )
            score_components["undertrading_recall_penalty"] = (
                -4.0 if opportunity_recall < ANTI_UNDERTRADING_MIN_RECALL else 0.0
            )
            score_components["undertrading_f1_penalty"] = (
                -3.0 if opportunity_f1 < ANTI_UNDERTRADING_MIN_F1 else 0.0
            )
            score_components["undertrading_direction_rows_penalty"] = (
                -2.0 if direction_trade_rows < ANTI_UNDERTRADING_MIN_DIRECTION_TRADE_ROWS else 0.0
            )
            score_components["precision_trap_penalty"] = (
                -6.0
                if opportunity_precision >= 0.80
                and (opportunity_recall < 0.10 or predicted_trade_rate < 0.01)
                else 0.0
            )
        rejection_reasons: list[str] = []
        baseline_score, baseline_components, baseline_reasons = self._baseline_edge_score_component(candidate)
        collapse_score, collapse_components, collapse_reasons = self._collapse_severity_score_component(candidate)
        score_components.update(baseline_components)
        score_components.update(collapse_components)
        if not excluded_from_best_selection and calibrated_decision.get("enabled"):
            score_components["calibrated_decision_enabled_bonus"] = 0.5
            if 0.10 <= calibrated_flat <= 0.45:
                score_components["calibrated_flat_coverage_bonus"] = 1.0
            elif calibrated_flat < 0.05:
                score_components["calibrated_flat_underprediction_penalty"] = -2.0
            elif calibrated_flat > 0.60:
                score_components["calibrated_flat_overprediction_penalty"] = -2.0

            if calibrated_up <= 0.75:
                score_components["calibrated_up_dominance_reduction_bonus"] = 1.0
            else:
                score_components["calibrated_up_dominance_penalty"] = -2.0

            if calibrated_down >= 0.15:
                score_components["calibrated_down_coverage_bonus"] = 1.0
            else:
                score_components["calibrated_down_blindness_penalty"] = -2.0
        if excluded_from_best_selection:
            score_components["failed_candidate_penalty"] = FAILED_CANDIDATE_SCORE
            score = FAILED_CANDIDATE_SCORE
        else:
            score = round(sum(score_components.values()), 6)

        for reason in baseline_reasons:
            if reason not in rejection_reasons:
                rejection_reasons.append(reason)
        if "baseline_edge_gate_failed" in baseline_reasons and "baseline_edge_gate" not in failed_gates:
            failed_gates.append("baseline_edge_gate")

        for reason in collapse_reasons:
            if reason not in rejection_reasons:
                rejection_reasons.append(reason)
        if "collapse_gate_failed" in collapse_reasons and "collapse_gate" not in failed_gates:
            failed_gates.append("collapse_gate")

        if collapse_detected:
            rejection_reasons.append(
                f"collapse_type={collapse_summary.get('collapse_type') or candidate.get('collapse_type') or 'unknown'}"
            )
        if bool(bias.get("flat_bias_detected", False)):
            rejection_reasons.append("flat_bias_detected")
        if bool(bias.get("down_blindness_detected", False)):
            rejection_reasons.append("down_blindness_detected")
        if bool(bias.get("flat_underprediction_detected", False)):
            rejection_reasons.append("flat_underprediction_detected")
        if bool(bias.get("up_bias_detected", False)):
            rejection_reasons.append("up_bias_detected")
        if bool(bias.get("up_dominance_detected", False)):
            rejection_reasons.append("up_dominance_detected")
        for reason in bias.get("bias_rejection_reasons", []):
            if str(reason) not in rejection_reasons:
                rejection_reasons.append(str(reason))
        if "bias_gate" in failed_gates:
            rejection_reasons.append("bias_gate_failed")
        if "baseline_edge_gate" in failed_gates and "baseline_edge_gate_failed" not in rejection_reasons:
            rejection_reasons.append("baseline_edge_gate_failed")
        if "collapse_gate" in failed_gates and "collapse_gate_failed" not in rejection_reasons:
            rejection_reasons.append("collapse_gate_failed")
        if "walk_forward_gate" in failed_gates:
            rejection_reasons.append("walk_forward_gate_failed")
        if training_objective == "trade_two_stage":
            if bool(two_stage_quality_gate.get("passed")):
                if "two_stage_quality_gate_passed_but_candidate_still_rejected" not in rejection_reasons:
                    rejection_reasons.append("two_stage_quality_gate_passed_but_candidate_still_rejected")
            else:
                for reason in two_stage_quality_gate.get("failed_reasons", []):
                    formatted = f"two_stage_quality_gate_failed:{reason}"
                    if formatted not in rejection_reasons:
                        rejection_reasons.append(formatted)
            if not bool(anti_undertrading_gate.get("passed")):
                for reason in anti_undertrading_gate.get("failed_reasons", []):
                    formatted = f"anti_undertrading_gate_failed:{reason}"
                    if formatted not in rejection_reasons:
                        rejection_reasons.append(formatted)
        if candidate.get("candidate_status") == "REJECTED" and not rejection_reasons:
            rejection_reasons.extend(f"failed_gate={gate}" for gate in failed_gates)
        if candidate.get("candidate_status") != "REJECTED":
            rejection_reasons = []

        return {
            "rank": 0,
            "config_id": str(candidate.get("config_id") or ""),
            "candidate_id": str(candidate.get("candidate_id") or candidate.get("config_id") or ""),
            "candidate_status": candidate_status,
            "score": score,
            "excluded_from_best_selection": excluded_from_best_selection,
            "score_components": score_components,
            "anti_collapse_diagnostics": anti_collapse_diagnostics,
            "anti_collapse_score": anti_collapse_score,
            "anti_collapse_status": anti_collapse_status,
            "confidence_profitability_diagnostics": confidence_profitability_diagnostics,
            "confidence_profitability_score": confidence_profitability_score,
            "confidence_profitability_status": confidence_profitability_status,
            "calibrated_decision_diagnostics": calibrated_decision,
            "bounded_calibrated_decision_selection": bounded_selection,
            "decision_policy_grid_diagnostics": decision_policy_payload,
            "decision_policy_selected_policy_id": selected_policy_id,
            "prediction_root_cause_audit": dict(candidate.get("prediction_root_cause_audit", {})),
            "book_driven_forensic_audit": dict(candidate.get("book_driven_forensic_audit", {})),
            "schwager_slice_robustness": dict(candidate.get("schwager_slice_robustness", {})),
            "schwager_robustness_decision_board": dict(
                candidate.get("schwager_robustness_decision_board", {})
            ),
            "calibrated_predicted_ratios": calibrated_ratios,
            "raw_predicted_ratios": raw_ratios,
            "prediction_decision_source": decision_source,
            "training_objective": training_objective,
            "failed_gates": failed_gates,
            "passed_gates": passed_gates,
            "collapse_type": collapse_summary.get("collapse_type") or candidate.get("collapse_type"),
            "flat_bias_detected": bool(bias.get("flat_bias_detected", False)),
            "down_blindness_detected": bool(bias.get("down_blindness_detected", False)),
            "flat_underprediction_detected": bool(bias.get("flat_underprediction_detected", False)),
            "up_bias_detected": bool(bias.get("up_bias_detected", False)),
            "up_dominance_detected": bool(bias.get("up_dominance_detected", False)),
            "bias_gate_failed": bool(bias.get("bias_gate_failed", False)),
            "bias_rejection_reasons": list(bias.get("bias_rejection_reasons", [])),
            "symbol_bias_severity": bias.get("symbol_bias_severity"),
            "walk_forward_profit_factor": walk_forward_pf,
            "walk_forward_total_r": walk_forward_total_r,
            "accuracy": accuracy,
            "baseline_accuracy": baseline,
            "baseline_edge": candidate.get("baseline_edge"),
            "baseline_edge_status": candidate.get("baseline_edge_status"),
            "collapse_severity": candidate.get("collapse_severity"),
            "opportunity_probability_threshold": candidate.get("opportunity_probability_threshold"),
            "setup_quality_min_threshold": setup_quality_min_threshold,
            "selected_opportunity_threshold": candidate.get("selected_opportunity_threshold"),
            "opportunity_threshold_selection": dict(candidate.get("opportunity_threshold_selection", {})),
            "opportunity_threshold_sweep": dict(candidate.get("opportunity_threshold_sweep", {})),
            "setup_quality_filter_passed": bool(setup_quality_filter.get("passed", False)),
            "setup_quality_filter_reason": setup_quality_filter.get("reason"),
            "two_stage_quality_gate": two_stage_quality_gate,
            "two_stage_quality_gate_passed": bool(two_stage_quality_gate.get("passed", False)),
            "anti_undertrading_gate": anti_undertrading_gate,
            "anti_undertrading_gate_passed": bool(anti_undertrading_gate.get("passed", False)),
            "undertrading_risk_detected": bool(undertrading_risk_detected),
            "missing_or_zero_false_positive_count": int(missing_or_zero_false_positives),
            "setup_quality_bucket_metrics": setup_quality_bucket_metrics,
            "setup_quality_bucket_metrics_raw": setup_quality_bucket_metrics_raw,
            "setup_quality_bucket_metrics_after_mask": setup_quality_bucket_metrics_after_mask,
            "setup_quality_filter_summary": setup_quality_filter_summary,
            "setup_quality_decision_mask_summary": setup_quality_decision_mask_summary,
            "predicted_to_actual_trade_rate_ratio": predicted_to_actual_trade_rate_ratio,
            "predicted_trade_rate": predicted_trade_rate,
            "actual_trade_rate": actual_trade_rate,
            "opportunity_precision": opportunity_precision,
            "opportunity_recall": opportunity_recall,
            "opportunity_f1": opportunity_f1,
            "raw_predicted_trade_rate": candidate.get("raw_predicted_trade_rate"),
            "masked_predicted_trade_rate": candidate.get("masked_predicted_trade_rate"),
            "raw_opportunity_precision": candidate.get("raw_opportunity_precision"),
            "raw_opportunity_recall": candidate.get("raw_opportunity_recall"),
            "raw_opportunity_f1": candidate.get("raw_opportunity_f1"),
            "opportunity_false_positive_rate": opportunity_false_positive_rate,
            "two_stage_trade_diagnostics": two_stage_trade_diagnostics,
            "precision_control_passed": bool(two_stage_trade_diagnostics.get("precision_control_passed", False)),
            "opportunity_precision_gate": {
                "passed": "opportunity_precision_below_gate" not in two_stage_trade_diagnostics.get("warnings", []),
                "minimum": precision_control_gates.get("min_precision"),
                "actual": opportunity_precision,
            },
            "opportunity_recall_gate": {
                "passed": "opportunity_recall_below_gate" not in two_stage_trade_diagnostics.get("warnings", []),
                "minimum": precision_control_gates.get("min_recall"),
                "actual": opportunity_recall,
            },
            "predicted_trade_rate_gate": {
                "passed": "predicted_trade_rate_above_gate" not in two_stage_trade_diagnostics.get("warnings", []),
                "maximum": precision_control_gates.get("max_predicted_trade_rate"),
                "actual": predicted_trade_rate,
            },
            "trade_rate_ratio_gate": {
                "passed": "predicted_to_actual_trade_rate_ratio_above_gate"
                not in two_stage_trade_diagnostics.get("warnings", []),
                "maximum": precision_control_gates.get("max_predicted_to_actual_trade_rate_ratio"),
                "actual": predicted_to_actual_trade_rate_ratio,
            },
            "opportunity_false_positive_gate": {
                "passed": "opportunity_false_positive_rate_above_gate"
                not in two_stage_trade_diagnostics.get("warnings", []),
                "maximum": precision_control_gates.get("max_false_positive_rate"),
                "actual": opportunity_false_positive_rate,
            },
            "rejection_reasons": rejection_reasons,
        }

    @staticmethod
    def _normalize_candidate(candidate: object) -> dict[str, Any]:
        if isinstance(candidate, dict):
            return dict(candidate)
        to_dict = getattr(candidate, "to_dict", None)
        if callable(to_dict):
            return dict(to_dict())
        raise TypeError("candidate must be a dict or provide to_dict()")

    @staticmethod
    def _safe_float(value: Any) -> float:
        if value is None:
            return 0.0
        return float(value)
