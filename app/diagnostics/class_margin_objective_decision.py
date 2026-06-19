from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from collections.abc import Mapping


BLOCKING_DECISIONS = {
    "NEEDS_LABEL_REWORK",
    "NEEDS_FEATURE_CONTEXT_REWORK",
    "NEEDS_OPPORTUNITY_FIRST_REWORK",
}
READY_DECISION = "READY_FOR_MODEL_OBJECTIVE_REWORK"
REQUIRED_DIAGNOSTICS = (
    "schwager_robustness_decision_board.final_research_decision",
    "feature_label_separability_audit.global_separability_rating",
    "label_ambiguity_audit.label_noise_rating",
)


def evaluate_class_margin_objective_decision(candidate_payload: Mapping[str, Any]) -> dict[str, Any]:
    board = _as_dict(candidate_payload.get("schwager_robustness_decision_board"))
    feature_audit = _extract_feature_audit(candidate_payload)
    label_audit = _extract_label_audit(candidate_payload)

    final_decision = str(board.get("final_research_decision") or "").upper()
    feature_rating = str(feature_audit.get("global_separability_rating") or "").upper()
    label_noise = str(label_audit.get("label_noise_rating") or "").upper()

    missing_diagnostics: list[str] = []
    if not final_decision:
        missing_diagnostics.append(REQUIRED_DIAGNOSTICS[0])
    if not feature_rating:
        missing_diagnostics.append(REQUIRED_DIAGNOSTICS[1])
    if not label_noise:
        missing_diagnostics.append(REQUIRED_DIAGNOSTICS[2])

    allowed = False
    reason = "required_runtime_evidence_missing"
    explanation = (
        "Class-margin objective stays blocked because the latest runtime evidence "
        "does not contain the required decision-board/audit payload."
    )

    if final_decision in BLOCKING_DECISIONS:
        reason = f"blocked_by_decision_board:{final_decision.lower()}"
        explanation = (
            "Class-margin objective stays blocked because the latest decision board "
            f"explicitly requires `{final_decision}` first."
        )
    elif final_decision == READY_DECISION:
        allowed = True
        reason = "decision_board_ready_for_model_objective_rework"
        explanation = (
            "Latest decision board explicitly allows model-objective rework, so "
            "class-margin separation may be enabled."
        )
    elif feature_rating and label_noise and feature_rating != "WEAK" and label_noise != "HIGH_NOISE":
        allowed = True
        reason = "audits_support_class_margin_rework"
        explanation = (
            "Latest runtime audits show non-weak feature separability and label "
            "ambiguity below HIGH_NOISE, so class-margin separation may be enabled."
        )
    elif feature_rating or label_noise or final_decision:
        reason = "runtime_audits_do_not_support_class_margin_rework"
        explanation = (
            "Class-margin objective stays blocked because runtime audits do not yet "
            "show the separability/noise conditions required by ML38.10.3."
        )

    return {
        "diagnostic_name": "class_margin_objective_decision",
        "diagnostic_version": "ml38_10_3",
        "class_margin_objective_allowed": allowed,
        "reason": reason,
        "required_diagnostics": list(REQUIRED_DIAGNOSTICS),
        "missing_diagnostics": missing_diagnostics,
        "decision_board_final_research_decision": final_decision or None,
        "feature_separability_rating": feature_rating or None,
        "label_noise_rating": label_noise or None,
        "global_classifier_path_status": "CAN_REWORK" if allowed else "BLOCKED",
        "explanation": explanation,
        "evidence_source_path": candidate_payload.get("evidence_source_path"),
        "evidence_source_type": candidate_payload.get("evidence_source_type"),
        "report_available": bool(candidate_payload.get("report_available", True)),
    }


def load_latest_class_margin_runtime_evidence(
    reports_root: str | Path = Path("reports"),
) -> dict[str, Any]:
    root = Path(reports_root)
    if not root.exists():
        return evaluate_class_margin_objective_decision(
            {
                "report_available": False,
                "evidence_source_type": "missing_reports_root",
                "evidence_source_path": str(root),
            }
        )

    candidates: list[tuple[float, dict[str, Any]]] = []
    for pattern, report_type in (
        ("feature_regime_experiments/*/feature_regime_experiment_summary.json", "feature_regime_summary"),
        ("training_pipeline_runs/*/training_pipeline_report.json", "training_pipeline_report"),
        ("label_grid_experiments/*/label_grid_experiment_summary.json", "label_grid_summary"),
    ):
        for path in root.glob(pattern):
            payload = _read_json(path)
            if payload is None:
                continue
            candidate_payload = _candidate_payload_from_report_payload(
                payload=payload,
                report_type=report_type,
                source_path=path,
            )
            if not candidate_payload:
                continue
            candidates.append((path.stat().st_mtime, candidate_payload))

    if not candidates:
        return evaluate_class_margin_objective_decision(
            {
                "report_available": False,
                "evidence_source_type": "no_runtime_reports_with_decision_payload",
                "evidence_source_path": str(root),
            }
        )

    _timestamp, latest_candidate_payload = max(candidates, key=lambda item: item[0])
    return evaluate_class_margin_objective_decision(latest_candidate_payload)


def _candidate_payload_from_report_payload(
    *,
    payload: Mapping[str, Any],
    report_type: str,
    source_path: Path,
) -> dict[str, Any]:
    candidate = _as_dict(payload)
    if report_type in {"feature_regime_summary", "label_grid_summary"}:
        best_config_id = str(payload.get("best_candidate_config_id") or "")
        ranked = payload.get("configs_ranked") or payload.get("candidate_ranking") or payload.get("candidate_results") or []
        for item in ranked:
            item_payload = _as_dict(item)
            item_config_id = str(item_payload.get("config_id") or "")
            if best_config_id and item_config_id == best_config_id:
                candidate = item_payload
                break
            if item_payload.get("schwager_robustness_decision_board"):
                candidate = item_payload
                break

    extracted = {
        "schwager_robustness_decision_board": _as_dict(candidate.get("schwager_robustness_decision_board")),
        "feature_label_separability_audit": _extract_feature_audit(candidate),
        "label_ambiguity_audit": _extract_label_audit(candidate),
        "book_driven_forensic_audit": _as_dict(candidate.get("book_driven_forensic_audit")),
        "evidence_source_type": report_type,
        "evidence_source_path": str(source_path),
        "report_available": True,
    }
    if not any(extracted[key] for key in ("schwager_robustness_decision_board", "feature_label_separability_audit", "label_ambiguity_audit")):
        return {}
    return extracted


def _extract_feature_audit(payload: Mapping[str, Any]) -> dict[str, Any]:
    direct = _as_dict(payload.get("feature_label_separability_audit"))
    if direct:
        return direct
    forensic = _as_dict(payload.get("book_driven_forensic_audit"))
    return _as_dict(forensic.get("feature_label_separability_audit"))


def _extract_label_audit(payload: Mapping[str, Any]) -> dict[str, Any]:
    direct = _as_dict(payload.get("label_ambiguity_audit"))
    if direct:
        return direct
    forensic = _as_dict(payload.get("book_driven_forensic_audit"))
    return _as_dict(forensic.get("label_ambiguity_audit"))


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}
