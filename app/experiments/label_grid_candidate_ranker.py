from __future__ import annotations

from typing import Any


LABEL_GRID_CANDIDATE_RANKER_NAME = "label_grid_candidate_ranker"
LABEL_GRID_CANDIDATE_RANKER_VERSION = "ml28"


class LabelGridCandidateRanker:
    """Rank label-grid candidates using quality and robustness signals."""

    def rank(
        self,
        candidates: list[object],
    ) -> dict[str, Any]:
        normalized = [self._normalize_candidate(candidate) for candidate in candidates]
        scored = [self._build_ranked_candidate(candidate) for candidate in normalized]
        scored.sort(
            key=lambda item: (
                -float(item["score"]),
                item["candidate_status"] != "CANDIDATE_ACCEPTED_FOR_RESEARCH",
                item["config_id"],
            )
        )

        for index, item in enumerate(scored, start=1):
            item["rank"] = index

        accepted_count = sum(
            int(item["candidate_status"] == "CANDIDATE_ACCEPTED_FOR_RESEARCH")
            for item in scored
        )
        rejected_count = sum(
            int(item["candidate_status"] == "CANDIDATE_REJECTED")
            for item in scored
        )

        best_candidate = scored[0] if scored else None
        experiment_status = "FAILED"
        if scored:
            experiment_status = "COMPLETED_WITH_ACCEPTED_CANDIDATE"
            if accepted_count == 0:
                experiment_status = "COMPLETED_NO_ACCEPTED_CANDIDATE"

        return {
            "ranker_name": LABEL_GRID_CANDIDATE_RANKER_NAME,
            "ranker_version": LABEL_GRID_CANDIDATE_RANKER_VERSION,
            "experiment_status": experiment_status,
            "accepted_candidate_count": accepted_count,
            "rejected_candidate_count": rejected_count,
            "best_candidate": dict(best_candidate) if best_candidate is not None else None,
            "ranking": scored,
        }

    def _build_ranked_candidate(self, candidate: dict[str, Any]) -> dict[str, Any]:
        accuracy_edge = self._safe_float(candidate.get("accuracy_edge"))
        collapse_penalty = 2.0 if bool(candidate.get("collapse_detected", False)) else 0.0
        profit_factor = self._safe_float(candidate.get("profit_factor"))
        profit_total_r = self._safe_float(candidate.get("profit_total_r"))
        walk_forward_total_r = self._safe_float(candidate.get("walk_forward_global_total_r"))
        walk_forward_profit_factor = self._safe_float(
            candidate.get("walk_forward_profit_factor")
        )
        gap_severity = str(
            candidate.get("gap_severity_for_training")
            or candidate.get("gap_severity")
            or "UNKNOWN"
        )
        gap_penalty = self._gap_penalty(gap_severity)
        gate_fail_penalty = 0.35 * len(candidate.get("failed_gates", []))

        score = (
            accuracy_edge * 100.0
            + max(profit_factor - 1.0, -1.0) * 2.0
            + max(walk_forward_profit_factor - 1.0, -1.0) * 2.0
            + (profit_total_r * 0.02)
            + (walk_forward_total_r * 0.02)
            - collapse_penalty
            - gap_penalty
            - gate_fail_penalty
        )

        key_strengths: list[str] = []
        key_risks: list[str] = []

        if accuracy_edge > 0.0:
            key_strengths.append(f"accuracy_edge={accuracy_edge:.4f}")
        if profit_factor > 1.0:
            key_strengths.append(f"profit_factor={profit_factor:.3f}")
        if walk_forward_profit_factor > 1.0:
            key_strengths.append(
                f"walk_forward_profit_factor={walk_forward_profit_factor:.3f}"
            )
        if profit_total_r > 0.0:
            key_strengths.append(f"profit_total_r={profit_total_r:.2f}")
        if walk_forward_total_r > 0.0:
            key_strengths.append(
                f"walk_forward_global_total_r={walk_forward_total_r:.2f}"
            )

        if bool(candidate.get("collapse_detected", False)):
            key_risks.append(f"collapse={candidate.get('collapse_type') or 'UNKNOWN'}")
        if candidate.get("failed_gates"):
            key_risks.append(
                "failed_gates=" + ",".join(str(item) for item in candidate["failed_gates"])
            )
        gap_severity = str(
            candidate.get("gap_severity_for_training")
            or candidate.get("gap_severity")
            or "UNKNOWN"
        )
        if gap_severity not in {"OK", "LOW"}:
            key_risks.append(f"gap_severity={gap_severity}")
        if not key_strengths:
            key_strengths.append("no_clear_strength")
        if not key_risks:
            key_risks.append("no_critical_risks_detected")

        return {
            "rank": 0,
            "config_id": str(candidate.get("config_id") or ""),
            "model_version": candidate.get("model_version"),
            "score": round(float(score), 6),
            "candidate_status": str(candidate.get("candidate_status") or "UNKNOWN"),
            "quality_status": str(candidate.get("quality_status") or "UNKNOWN"),
            "key_strengths": key_strengths,
            "key_risks": key_risks,
            "failed_gates": list(candidate.get("failed_gates", [])),
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
    def _gap_penalty(gap_severity: str) -> float:
        return {
            "OK": 0.0,
            "LOW": 0.2,
            "MEDIUM": 0.6,
            "HIGH": 1.2,
            "CRITICAL": 2.0,
        }.get(gap_severity, 0.8)

    @staticmethod
    def _safe_float(value: Any) -> float:
        if value is None:
            return 0.0
        return float(value)
