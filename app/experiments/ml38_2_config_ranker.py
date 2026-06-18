from __future__ import annotations

from typing import Any


ML38_2_CONFIG_RANKER_NAME = "ml38_2_config_ranker"
ML38_2_CONFIG_RANKER_VERSION = "ml38_2"
FAILED_CANDIDATE_STATUSES = {"FAILED", "ERROR"}
FAILED_CANDIDATE_SCORE = -1_000_000.0

def is_rankable_candidate_status(status: str | None) -> bool:
    return str(status or "").upper() not in FAILED_CANDIDATE_STATUSES


class ML382ConfigRanker:
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

        score_components = {
            "walk_forward_pf_bonus": 3.0 if walk_forward_pf > 1.0 else 0.0,
            "walk_forward_total_r_bonus": 2.0 if walk_forward_total_r > 0.0 else 0.0,
            "accuracy_vs_baseline_bonus": 1.5 if accuracy > baseline else 0.0,
            "profit_aware_gate_bonus": 1.0 if "profit_aware_gate" in passed_gates else 0.0,
            "walk_forward_gate_bonus": 1.0 if "walk_forward_gate" in passed_gates else 0.0,
            "anti_collapse_bonus": anti_collapse_bonus,
            "confidence_profitability_bonus": confidence_profitability_bonus,
            "confidence_profitability_score_bonus": min(max(confidence_profitability_score, -3.0), 3.0) * 0.25,
            "collapse_penalty": -3.0 if collapse_detected else 0.0,
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
            "baseline_edge_gate_penalty": -2.0 if "baseline_edge_gate" in failed_gates else 0.0,
            "walk_forward_gate_penalty": -3.0 if "walk_forward_gate" in failed_gates else 0.0,
        }
        if excluded_from_best_selection:
            score_components["failed_candidate_penalty"] = FAILED_CANDIDATE_SCORE
            score = FAILED_CANDIDATE_SCORE
        else:
            score = round(sum(score_components.values()), 6)

        rejection_reasons: list[str] = []
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
        if "baseline_edge_gate" in failed_gates:
            rejection_reasons.append("baseline_edge_gate_failed")
        if "walk_forward_gate" in failed_gates:
            rejection_reasons.append("walk_forward_gate_failed")
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
