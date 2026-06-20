from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from app.diagnostics._book_audit_utils import (
    distribution,
    get_mapping,
    get_value,
    label_from_row,
    majority_accuracy,
    predicted_label_from_row,
    safe_float,
)
from app.diagnostics.feature_label_separability_audit import FeatureLabelSeparabilityAudit
from app.diagnostics.label_ambiguity_audit import LabelAmbiguityAudit
from app.diagnostics.schwager_negative_result_analyzer import SchwagerNegativeResultAnalyzer
from app.diagnostics.setup_context_audit import SetupContextAudit


def build_schwager_slice_robustness(
    prediction_rows: Sequence[Any],
    *,
    label_mode: str | None = None,
) -> dict[str, Any]:
    rows = list(prediction_rows or [])
    payload = {
        "diagnostic_name": "schwager_slice_robustness",
        "diagnostic_version": "ml38_10_2",
        "row_count": len(rows),
        "edge_by_time_slice": _group_edge_payload(_time_slice_groups(rows)),
        "edge_by_regime": _group_edge_payload(_bucket_groups(rows, _regime_bucket)),
        "edge_by_setup_type": _group_edge_payload(_bucket_groups(rows, _setup_bucket)),
        "edge_by_label_mode": _group_edge_payload(
            _bucket_groups(rows, lambda row: _label_mode_bucket(row, label_mode=label_mode))
        ),
        "edge_by_opportunity_bucket": _group_edge_payload(_bucket_groups(rows, _opportunity_bucket)),
        "edge_by_volatility_bucket": _group_edge_payload(_bucket_groups(rows, _volatility_bucket)),
        "edge_by_support_resistance_context": _group_edge_payload(
            _bucket_groups(rows, _support_resistance_bucket)
        ),
    }
    payload["robustness_flags"] = _robustness_flags(payload)
    return payload


class SchwagerRobustnessDecisionBoard:
    diagnostic_name = "schwager_robustness_decision_board"
    diagnostic_version = "ml38_10_2"

    def evaluate(self, candidate_payload: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(candidate_payload)
        candidate_selection = _as_dict(payload.get("candidate_selection"))
        quality_gates = _as_dict(payload.get("quality_gates_summary"))
        probability_diagnostics = _as_dict(payload.get("probability_diagnostics"))
        book_audit = _as_dict(payload.get("book_driven_forensic_audit"))

        prediction_rows = _rows_from_payload(payload, probability_diagnostics)
        label_mode = str(
            _as_dict(payload.get("label_config")).get("label_mode")
            or payload.get("label_mode")
            or "unknown"
        )
        slice_robustness = _as_dict(payload.get("schwager_slice_robustness"))
        if not slice_robustness and prediction_rows:
            slice_robustness = build_schwager_slice_robustness(
                prediction_rows,
                label_mode=label_mode,
            )

        feature_audit = _extract_or_build_feature_audit(payload, book_audit, prediction_rows)
        label_audit = _extract_or_build_label_audit(payload, book_audit, prediction_rows)
        setup_audit = _extract_or_build_setup_audit(payload, book_audit, prediction_rows)
        opportunity_diagnostics = _extract_opportunity_diagnostics(payload)
        two_stage_trade_diagnostics = _extract_two_stage_trade_diagnostics(payload)
        two_stage_quality_status = _two_stage_quality_status(two_stage_trade_diagnostics)
        negative_result = _extract_or_build_negative_result(
            payload=payload,
            book_audit=book_audit,
            feature_audit=feature_audit,
            label_audit=label_audit,
            setup_audit=setup_audit,
        )

        candidate_status = str(
            payload.get("candidate_status")
            or candidate_selection.get("candidate_status")
            or "UNKNOWN"
        ).upper()
        failed_gates = _string_list(
            payload.get("failed_gates")
            or candidate_selection.get("failed_gates")
            or quality_gates.get("failed_gates")
        )
        baseline_edge = _safe_edge(payload)
        model_edge_status = _model_edge_status(baseline_edge)
        baseline_edge_status = str(
            payload.get("baseline_edge_status")
            or negative_result.get("baseline_edge_status")
            or model_edge_status
        ).upper()
        walk_forward_status = _walk_forward_status(payload)
        profit_status = _profit_status(payload)
        collapse_status = _collapse_status(payload)
        bias_status = _bias_status(payload)
        setup_edge_status = _setup_edge_status(setup_audit, opportunity_diagnostics)
        opportunity_status = _opportunity_status(opportunity_diagnostics)
        label_noise_status = str(
            label_audit.get("label_noise_rating")
            or "UNAVAILABLE"
        ).upper()
        feature_separability_status = str(
            feature_audit.get("global_separability_rating")
            or "UNAVAILABLE"
        ).upper()
        overfit_risk_status = _overfit_risk_status(slice_robustness)

        primary_failure = _primary_failure(
            negative_result=negative_result,
            two_stage_quality_status=two_stage_quality_status,
            label_noise_status=label_noise_status,
            feature_separability_status=feature_separability_status,
            setup_edge_status=setup_edge_status,
            opportunity_status=opportunity_status,
            collapse_status=collapse_status,
            model_edge_status=model_edge_status,
            walk_forward_status=walk_forward_status,
            profit_status=profit_status,
            bias_status=bias_status,
            overfit_risk_status=overfit_risk_status,
        )
        secondary_failures = _secondary_failures(
            primary_failure=primary_failure,
            two_stage_quality_status=two_stage_quality_status,
            failed_gates=failed_gates,
            model_edge_status=model_edge_status,
            walk_forward_status=walk_forward_status,
            profit_status=profit_status,
            collapse_status=collapse_status,
            bias_status=bias_status,
            setup_edge_status=setup_edge_status,
            opportunity_status=opportunity_status,
            label_noise_status=label_noise_status,
            feature_separability_status=feature_separability_status,
            overfit_risk_status=overfit_risk_status,
        )
        final_research_decision = _final_research_decision(
            candidate_status=candidate_status,
            primary_failure=primary_failure,
            model_edge_status=model_edge_status,
            walk_forward_status=walk_forward_status,
            profit_status=profit_status,
            collapse_status=collapse_status,
            overfit_risk_status=overfit_risk_status,
            bias_status=bias_status,
        )

        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "candidate_status": candidate_status,
            "failed_gates": failed_gates,
            "model_edge_status": model_edge_status,
            "baseline_edge_status": baseline_edge_status,
            "walk_forward_status": walk_forward_status,
            "profit_status": profit_status,
            "collapse_status": collapse_status,
            "bias_status": bias_status,
            "setup_edge_status": setup_edge_status,
            "opportunity_status": opportunity_status,
            "two_stage_quality_status": two_stage_quality_status,
            "two_stage_quality_gate_passed": bool(
                _as_dict(two_stage_trade_diagnostics.get("two_stage_quality_gate")).get("passed")
                or two_stage_trade_diagnostics.get("two_stage_quality_gate_passed")
            ),
            "anti_undertrading_gate_passed": bool(
                _as_dict(two_stage_trade_diagnostics.get("anti_undertrading_gate")).get("passed")
                or two_stage_trade_diagnostics.get("anti_undertrading_gate_passed")
            ),
            "label_noise_status": label_noise_status,
            "feature_separability_status": feature_separability_status,
            "overfit_risk_status": overfit_risk_status,
            "primary_failure": primary_failure,
            "secondary_failures": secondary_failures,
            "what_not_to_do_next": _what_not_to_do_next(
                primary_failure=primary_failure,
                negative_result=negative_result,
            ),
            "what_to_do_next": _what_to_do_next(
                primary_failure=primary_failure,
                final_research_decision=final_research_decision,
                negative_result=negative_result,
            ),
            "final_research_decision": final_research_decision,
            "slice_robustness_available": bool(slice_robustness),
            "slice_warning_flags": _string_list(slice_robustness.get("robustness_flags")),
            "root_cause_bucket": negative_result.get("root_cause_bucket"),
            "forensic_final_diagnosis": book_audit.get("final_diagnosis"),
            "next_action_recommendation": book_audit.get("next_action_recommendation")
            or negative_result.get("primary_recommendation"),
        }


def _extract_opportunity_diagnostics(payload: Mapping[str, Any]) -> dict[str, Any]:
    opportunity = _as_dict(payload.get("opportunity_diagnostics"))
    if opportunity and isinstance(opportunity.get("test"), Mapping):
        return dict(opportunity["test"])
    if opportunity:
        return opportunity
    probability_diagnostics = _as_dict(payload.get("probability_diagnostics"))
    nested = _as_dict(probability_diagnostics.get("opportunity_diagnostics"))
    if nested and isinstance(nested.get("test"), Mapping):
        return dict(nested["test"])
    return nested


def _extract_two_stage_trade_diagnostics(payload: Mapping[str, Any]) -> dict[str, Any]:
    diagnostics = _as_dict(payload.get("two_stage_trade_diagnostics"))
    if diagnostics:
        return diagnostics
    probability_diagnostics = _as_dict(payload.get("probability_diagnostics"))
    nested = _as_dict(probability_diagnostics.get("two_stage_trade_diagnostics"))
    if nested:
        return nested
    candidate_selection = _as_dict(payload.get("candidate_selection"))
    return _as_dict(candidate_selection.get("two_stage_trade_diagnostics"))


def _two_stage_quality_status(two_stage_trade_diagnostics: Mapping[str, Any]) -> str:
    if not two_stage_trade_diagnostics:
        return "UNAVAILABLE"
    quality_gate = _as_dict(two_stage_trade_diagnostics.get("two_stage_quality_gate"))
    anti_undertrading_gate = _as_dict(two_stage_trade_diagnostics.get("anti_undertrading_gate"))
    quality_passed = bool(
        two_stage_trade_diagnostics.get("two_stage_quality_gate_passed")
        or quality_gate.get("passed")
    )
    anti_undertrading_passed = bool(
        two_stage_trade_diagnostics.get("anti_undertrading_gate_passed")
        or anti_undertrading_gate.get("passed")
    )
    if quality_passed and anti_undertrading_passed:
        return "PASSED"
    if not anti_undertrading_passed:
        return "UNDERTRADING"
    return "WEAK"


def _extract_or_build_feature_audit(
    payload: Mapping[str, Any],
    book_audit: Mapping[str, Any],
    prediction_rows: Sequence[Any],
) -> dict[str, Any]:
    audit = _as_dict(payload.get("feature_label_separability_audit"))
    if audit:
        return audit
    audit = _as_dict(book_audit.get("feature_label_separability_audit"))
    if audit:
        return audit
    if prediction_rows:
        return FeatureLabelSeparabilityAudit().evaluate(prediction_rows)
    return {}


def _extract_or_build_label_audit(
    payload: Mapping[str, Any],
    book_audit: Mapping[str, Any],
    prediction_rows: Sequence[Any],
) -> dict[str, Any]:
    audit = _as_dict(payload.get("label_ambiguity_audit"))
    if audit:
        return audit
    audit = _as_dict(book_audit.get("label_ambiguity_audit"))
    if audit:
        return audit
    if prediction_rows:
        return LabelAmbiguityAudit().evaluate(prediction_rows)
    return {}


def _extract_or_build_setup_audit(
    payload: Mapping[str, Any],
    book_audit: Mapping[str, Any],
    prediction_rows: Sequence[Any],
) -> dict[str, Any]:
    audit = _as_dict(payload.get("setup_context_audit"))
    if audit:
        return audit
    audit = _as_dict(book_audit.get("setup_context_audit"))
    if audit:
        return audit
    if prediction_rows:
        return SetupContextAudit().evaluate(prediction_rows)
    return {}


def _extract_or_build_negative_result(
    *,
    payload: Mapping[str, Any],
    book_audit: Mapping[str, Any],
    feature_audit: Mapping[str, Any],
    label_audit: Mapping[str, Any],
    setup_audit: Mapping[str, Any],
) -> dict[str, Any]:
    negative = _as_dict(payload.get("schwager_negative_result_analyzer"))
    if negative:
        return negative
    negative = _as_dict(book_audit.get("schwager_negative_result_analyzer"))
    if negative:
        return negative
    analyzer_payload = dict(payload)
    analyzer_payload["feature_label_separability_audit"] = dict(feature_audit)
    analyzer_payload["label_ambiguity_audit"] = dict(label_audit)
    analyzer_payload["setup_context_audit"] = dict(setup_audit)
    return SchwagerNegativeResultAnalyzer().evaluate(analyzer_payload)


def _rows_from_payload(
    payload: Mapping[str, Any],
    probability_diagnostics: Mapping[str, Any],
) -> list[Any]:
    for key in ("selected_prediction_rows", "prediction_rows", "raw_prediction_rows"):
        value = payload.get(key)
        if isinstance(value, list):
            return list(value)
    for key in ("selected_prediction_rows", "raw_prediction_rows"):
        value = probability_diagnostics.get(key)
        if isinstance(value, list):
            return list(value)
    return []


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _string_list(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if item is not None]
    if value is None:
        return []
    return [str(value)]


def _safe_edge(payload: Mapping[str, Any]) -> float | None:
    return safe_float(
        payload.get("baseline_edge", payload.get("accuracy_edge"))
    )


def _model_edge_status(edge: float | None) -> str:
    if edge is None:
        return "UNKNOWN"
    if edge > 0.01:
        return "POSITIVE_EDGE"
    if edge > 0.0:
        return "WEAK_EDGE"
    return "NEGATIVE_EDGE"


def _walk_forward_status(payload: Mapping[str, Any]) -> str:
    explicit = str(
        payload.get("walk_forward_status")
        or _as_dict(payload.get("walk_forward_profit_diagnostics")).get("walk_forward_status")
        or ""
    ).upper()
    if explicit:
        return explicit
    profit_factor = safe_float(
        payload.get("walk_forward_profit_factor", payload.get("walk_forward_pf"))
    )
    if profit_factor is None:
        return "NEEDS_MORE_DATA"
    return "STABLE" if profit_factor >= 1.0 else "UNSTABLE"


def _profit_status(payload: Mapping[str, Any]) -> str:
    explicit = str(
        payload.get("profit_aware_status")
        or _as_dict(payload.get("profit_aware_diagnostics")).get("profit_aware_status")
        or ""
    ).upper()
    if explicit:
        return explicit
    profit_factor = safe_float(payload.get("profit_factor"))
    if profit_factor is None:
        return "NEEDS_MORE_DATA"
    return "PROFITABLE" if profit_factor >= 1.0 else "NOT_PROFITABLE"


def _collapse_status(payload: Mapping[str, Any]) -> str:
    severity = str(
        payload.get("collapse_severity")
        or _as_dict(payload.get("collapse_diagnostics_v2")).get("collapse_severity")
        or ""
    ).upper()
    return severity or "UNAVAILABLE"


def _bias_status(payload: Mapping[str, Any]) -> str:
    severity = str(
        payload.get("symbol_bias_severity")
        or _as_dict(payload.get("flat_bias_diagnostics")).get("symbol_bias_severity")
        or ""
    ).upper()
    return severity or "UNAVAILABLE"


def _setup_edge_status(
    setup_audit: Mapping[str, Any],
    opportunity_diagnostics: Mapping[str, Any],
) -> str:
    setup_gate = _as_dict(opportunity_diagnostics.get("setup_edge_gate"))
    if setup_gate:
        if bool(setup_gate.get("passed")):
            return "ROBUST_SETUP_EDGE"
        if safe_float(setup_gate.get("opportunity_first_touch_success_rate"), 0.0) > 0.0:
            return "SETUP_EDGE_ONLY"
    positive_groups = _string_list(setup_audit.get("groups_with_positive_edge"))
    negative_groups = _string_list(setup_audit.get("groups_with_negative_edge"))
    if positive_groups and negative_groups:
        return "SETUP_EDGE_ONLY"
    if positive_groups:
        return "ROBUST_SETUP_EDGE"
    if setup_audit:
        return "NO_SETUP_EDGE"
    return "UNAVAILABLE"


def _opportunity_status(opportunity_diagnostics: Mapping[str, Any]) -> str:
    if not opportunity_diagnostics:
        return "UNAVAILABLE"
    collapse_gate = _as_dict(opportunity_diagnostics.get("opportunity_collapse_gate"))
    setup_gate = _as_dict(opportunity_diagnostics.get("setup_edge_gate"))
    if bool(collapse_gate.get("passed")) and bool(setup_gate.get("passed")):
        return "GOOD"
    opportunity_rate = safe_float(opportunity_diagnostics.get("opportunity_rate"), 0.0) or 0.0
    if opportunity_rate <= 0.0:
        return "NO_OPPORTUNITY_EDGE"
    return "WEAK"


def _overfit_risk_status(slice_robustness: Mapping[str, Any]) -> str:
    flags = set(_string_list(slice_robustness.get("robustness_flags")))
    if not slice_robustness:
        return "UNAVAILABLE"
    if flags & {
        "single_positive_time_slice",
        "single_positive_regime",
        "single_positive_setup_type",
        "negative_edge_slice_detected",
    }:
        return "HIGH"
    if flags & {"collapsed_slice_detected", "low_sample_slice_detected"}:
        return "MEDIUM"
    return "LOW"


def _primary_failure(
    *,
    negative_result: Mapping[str, Any],
    two_stage_quality_status: str,
    label_noise_status: str,
    feature_separability_status: str,
    setup_edge_status: str,
    opportunity_status: str,
    collapse_status: str,
    model_edge_status: str,
    walk_forward_status: str,
    profit_status: str,
    bias_status: str,
    overfit_risk_status: str,
) -> str:
    root_bucket = str(negative_result.get("root_cause_bucket") or "").upper()
    if two_stage_quality_status == "UNDERTRADING":
        return "two_stage_undertrading"
    if two_stage_quality_status == "PASSED":
        if walk_forward_status == "UNSTABLE" or profit_status in {"NEGATIVE", "POOR", "NOT_PROFITABLE"}:
            return "two_stage_needs_profit_validation"
        if model_edge_status == "NEGATIVE_EDGE":
            return "two_stage_needs_profit_validation"
        if overfit_risk_status == "HIGH":
            return "overfit_risk_high"
        if bias_status in {"HIGH", "CRITICAL"}:
            return "symbol_bias_high"
        return "no_hard_failure_detected"
    if label_noise_status == "HIGH_NOISE" or root_bucket == "LABEL_AMBIGUITY_HIGH":
        return "label_noise_high"
    if feature_separability_status == "WEAK" or root_bucket == "FEATURE_SEPARABILITY_WEAK":
        return "feature_separability_weak"
    if root_bucket in {"SETUP_EDGE_ONLY", "BASELINE_STRONGER_THAN_MODEL"}:
        return "opportunity_first_needed"
    if setup_edge_status == "SETUP_EDGE_ONLY" or opportunity_status in {"WEAK", "NO_OPPORTUNITY_EDGE"}:
        return "opportunity_first_needed"
    if collapse_status == "CRITICAL" or root_bucket == "WEAK_RAW_CLASS_SEPARATION":
        return "collapse_not_fixed"
    if model_edge_status == "NEGATIVE_EDGE":
        return "negative_model_edge"
    if walk_forward_status == "UNSTABLE":
        return "walk_forward_unstable"
    if profit_status in {"NEGATIVE", "POOR", "NOT_PROFITABLE"}:
        return "profit_not_confirmed"
    if bias_status in {"HIGH", "CRITICAL"}:
        return "symbol_bias_high"
    if overfit_risk_status == "HIGH":
        return "overfit_risk_high"
    return "no_hard_failure_detected"


def _secondary_failures(
    *,
    primary_failure: str,
    two_stage_quality_status: str,
    failed_gates: Sequence[str],
    model_edge_status: str,
    walk_forward_status: str,
    profit_status: str,
    collapse_status: str,
    bias_status: str,
    setup_edge_status: str,
    opportunity_status: str,
    label_noise_status: str,
    feature_separability_status: str,
    overfit_risk_status: str,
) -> list[str]:
    failures: list[str] = list(dict.fromkeys(str(item) for item in failed_gates))
    for condition, name in (
        (model_edge_status == "NEGATIVE_EDGE", "negative_model_edge"),
        (walk_forward_status == "UNSTABLE", "walk_forward_unstable"),
        (profit_status in {"NEGATIVE", "POOR", "NOT_PROFITABLE"}, "profit_not_confirmed"),
        (collapse_status in {"WATCH", "CRITICAL"}, "collapse_or_bias_risk"),
        (bias_status in {"HIGH", "CRITICAL"}, "symbol_bias_high"),
        (setup_edge_status == "SETUP_EDGE_ONLY", "setup_edge_not_global"),
        (opportunity_status in {"WEAK", "NO_OPPORTUNITY_EDGE"}, "opportunity_contract_weak"),
        (label_noise_status == "HIGH_NOISE", "label_noise_high"),
        (feature_separability_status == "WEAK", "feature_separability_weak"),
        (overfit_risk_status == "HIGH", "overfit_risk_high"),
        (two_stage_quality_status == "UNDERTRADING", "two_stage_undertrading"),
    ):
        if condition:
            failures.append(name)
    return [item for item in dict.fromkeys(failures) if item != primary_failure]


def _final_research_decision(
    *,
    candidate_status: str,
    primary_failure: str,
    model_edge_status: str,
    walk_forward_status: str,
    profit_status: str,
    collapse_status: str,
    overfit_risk_status: str,
    bias_status: str,
) -> str:
    if primary_failure == "two_stage_needs_profit_validation":
        return "TWO_STAGE_PROMISING_REJECTED_BY_PROFIT"
    if primary_failure == "two_stage_undertrading":
        return "TWO_STAGE_REJECTED_UNDERTRADING"
    if primary_failure == "label_noise_high":
        return "NEEDS_LABEL_REWORK"
    if primary_failure == "feature_separability_weak":
        return "NEEDS_FEATURE_CONTEXT_REWORK"
    if primary_failure == "opportunity_first_needed":
        return "NEEDS_OPPORTUNITY_FIRST_REWORK"
    if primary_failure in {"collapse_not_fixed", "negative_model_edge"}:
        return "NEEDS_MODEL_OBJECTIVE_REWORK"
    if candidate_status == "REJECTED" or walk_forward_status == "UNSTABLE":
        return "DO_NOT_SCALE_RUNTIME"
    if profit_status in {"NEGATIVE", "POOR", "NOT_PROFITABLE"}:
        return "DO_NOT_SCALE_RUNTIME"
    if collapse_status in {"WATCH", "CRITICAL"} or bias_status in {"HIGH", "CRITICAL"}:
        return "DO_NOT_SCALE_RUNTIME"
    if model_edge_status != "POSITIVE_EDGE" or overfit_risk_status in {"HIGH", "MEDIUM"}:
        return "READY_FOR_MORE_QUICK_QUALITY_SYMBOLS"
    return "READY_FOR_SINGLE_SYMBOL_FULL_ONLY_IF_USER_APPROVES"


def _what_not_to_do_next(
    *,
    primary_failure: str,
    negative_result: Mapping[str, Any,],
) -> list[str]:
    actions = ["do_not_soften_gates"]
    if primary_failure == "two_stage_needs_profit_validation":
        actions.append("do_not_rework_labels_yet")
        actions.append("do_not_relax_two_stage_quality_gate")
    if primary_failure == "two_stage_undertrading":
        actions.append("do_not_rank_precision_without_recall")
    if str(negative_result.get("root_cause_bucket") or "").upper() == "POST_PROCESSING_NOT_ROOT_CAUSE":
        actions.append("do_not_add_more_decision_policies")
    if primary_failure != "no_hard_failure_detected":
        actions.append("do_not_run_full_grid")
        actions.append("do_not_scale_runtime")
    return list(dict.fromkeys(actions))


def _what_to_do_next(
    *,
    primary_failure: str,
    final_research_decision: str,
    negative_result: Mapping[str, Any],
) -> list[str]:
    mapping = {
        "label_noise_high": [
            "inspect_first_touch_labels",
            "review_label_ambiguity_rows",
            "audit_flat_subtypes",
        ],
        "feature_separability_weak": [
            "add_setup_context_features",
            "inspect_feature_separability_by_slice",
            "improve_support_resistance_context",
        ],
        "opportunity_first_needed": [
            "train_opportunity_first",
            "inspect_setup_edge_by_group",
            "review_no_trade_labels",
        ],
        "collapse_not_fixed": [
            "inspect_prediction_collapse_slices",
            "rework_direction_objective",
            "keep_decision_layer_secondary",
        ],
        "negative_model_edge": [
            "rework_direction_objective",
            "compare_against_rule_baselines",
            "run_more_quick_quality_symbols",
        ],
        "walk_forward_unstable": [
            "run_more_quick_quality_symbols",
            "inspect_time_slice_edge_stability",
        ],
        "profit_not_confirmed": [
            "inspect_profit_aware_breakdown",
            "inspect_walk_forward_breakdown",
        ],
        "symbol_bias_high": [
            "inspect_class_bias_by_symbol",
            "inspect_prediction_collapse_slices",
        ],
        "overfit_risk_high": [
            "run_more_quick_quality_symbols",
            "inspect_slice_robustness_before_any_full_runtime",
        ],
        "two_stage_needs_profit_validation": [
            "run_more_quick_quality_symbols",
            "inspect_profit_aware_breakdown",
            "inspect_walk_forward_breakdown",
        ],
        "two_stage_undertrading": [
            "tighten_anti_undertrading_ranking",
            "inspect_threshold_sweep_for_recall_collapse",
            "compare_balanced_lv19_against_precision_trap_candidate",
        ],
    }
    actions = list(mapping.get(primary_failure, []))
    recommendation = str(negative_result.get("primary_recommendation") or "").strip()
    if recommendation:
        actions.append(recommendation)
    if not actions and final_research_decision == "READY_FOR_MORE_QUICK_QUALITY_SYMBOLS":
        actions.append("run_more_quick_quality_symbols")
    if not actions and final_research_decision == "READY_FOR_SINGLE_SYMBOL_FULL_ONLY_IF_USER_APPROVES":
        actions.append("request_single_symbol_full_approval")
    return list(dict.fromkeys(actions))


def _time_slice_groups(rows: Sequence[Any]) -> dict[str, list[Any]]:
    if not rows:
        return {}
    explicit_groups = _bucket_groups(rows, lambda row: str(get_value(row, "split", "split_name", "dataset_split") or ""))
    explicit_groups = {name: values for name, values in explicit_groups.items() if name}
    if explicit_groups:
        return explicit_groups
    groups: dict[str, list[Any]] = {"early_window": [], "mid_window": [], "late_window": []}
    total = len(rows)
    for index, row in enumerate(rows):
        ratio = (index + 1) / total
        if ratio <= 1.0 / 3.0:
            groups["early_window"].append(row)
        elif ratio <= 2.0 / 3.0:
            groups["mid_window"].append(row)
        else:
            groups["late_window"].append(row)
    return {name: values for name, values in groups.items() if values}


def _bucket_groups(rows: Sequence[Any], resolver) -> dict[str, list[Any]]:
    groups: dict[str, list[Any]] = defaultdict(list)
    for row in rows:
        key = str(resolver(row) or "unknown")
        groups[key].append(row)
    return dict(groups)


def _group_edge_payload(groups: Mapping[str, Sequence[Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for name, rows in groups.items():
        payload[str(name)] = _edge_summary(rows)
    return payload


def _edge_summary(rows: Sequence[Any]) -> dict[str, Any]:
    actual_labels = [label_from_row(row) or "FLAT" for row in rows]
    predicted_labels = [predicted_label_from_row(row) for row in rows]
    normalized_predictions = [label for label in predicted_labels if label is not None]
    model_accuracy = None
    baseline_accuracy = majority_accuracy(actual_labels)
    baseline_edge = None
    collapse_detected = False
    predicted_distribution = {}
    if normalized_predictions and len(normalized_predictions) == len(actual_labels):
        matches = sum(int(left == right) for left, right in zip(actual_labels, normalized_predictions))
        model_accuracy = matches / len(actual_labels) if actual_labels else None
        if baseline_accuracy is not None and model_accuracy is not None:
            baseline_edge = round(model_accuracy - baseline_accuracy, 6)
        predicted_distribution = distribution(normalized_predictions)
        collapse_detected = max(predicted_distribution.values()) >= 0.85 if predicted_distribution else False
    return {
        "row_count": len(rows),
        "model_accuracy": None if model_accuracy is None else round(model_accuracy, 6),
        "baseline_accuracy": None if baseline_accuracy is None else round(baseline_accuracy, 6),
        "baseline_edge": baseline_edge,
        "edge_status": _model_edge_status(baseline_edge),
        "collapse_detected": collapse_detected,
        "predicted_distribution": predicted_distribution,
        "low_sample_size": len(rows) < 10,
    }


def _robustness_flags(slice_payload: Mapping[str, Any]) -> list[str]:
    flags: list[str] = []
    for dimension in (
        "edge_by_time_slice",
        "edge_by_regime",
        "edge_by_setup_type",
        "edge_by_label_mode",
        "edge_by_opportunity_bucket",
        "edge_by_volatility_bucket",
        "edge_by_support_resistance_context",
    ):
        groups = _as_dict(slice_payload.get(dimension))
        if not groups:
            continue
        positive = [
            name
            for name, stats in groups.items()
            if safe_float(_as_dict(stats).get("baseline_edge"), 0.0) > 0.0
        ]
        negative = [
            name
            for name, stats in groups.items()
            if safe_float(_as_dict(stats).get("baseline_edge"), 0.0) < 0.0
        ]
        if len(groups) > 1 and len(positive) == 1:
            flags.append(f"single_positive_{dimension.removeprefix('edge_by_')}")
        if negative:
            flags.append("negative_edge_slice_detected")
        if any(bool(_as_dict(stats).get("collapse_detected")) for stats in groups.values()):
            flags.append("collapsed_slice_detected")
        if any(bool(_as_dict(stats).get("low_sample_size")) for stats in groups.values()):
            flags.append("low_sample_slice_detected")
    return list(dict.fromkeys(flags))


def _regime_bucket(row: Any) -> str:
    features = get_mapping(row, "features_json", "features", "feature_values")
    for regime in (
        "trend_up",
        "trend_down",
        "range",
        "high_volatility",
        "low_volatility",
    ):
        value = safe_float(features.get(f"regime_{regime}"))
        if value is not None and value >= 0.5:
            return regime
    return str(get_value(row, "regime", "market_regime", "regime_label") or "unknown")


def _setup_bucket(row: Any) -> str:
    setup_type = get_value(row, "setup_type")
    if setup_type:
        return str(setup_type)
    features = get_mapping(row, "features_json", "features", "feature_values")
    hammer = safe_float(features.get("hammer_score"), 0.0) or 0.0
    star = safe_float(features.get("shooting_star_score"), 0.0) or 0.0
    engulfing = safe_float(features.get("engulfing_score"), 0.0) or 0.0
    breakout = safe_float(features.get("breakout_strength"), 0.0) or 0.0
    trend = abs(safe_float(features.get("trend_strength"), 0.0) or 0.0)
    doji = safe_float(features.get("doji_score"), 0.0) or 0.0
    if max(hammer, star, engulfing) >= 0.5:
        return "reversal_candidate"
    if breakout >= 0.4:
        return "breakout_candidate"
    if trend >= 0.6:
        return "trend_continuation"
    if doji >= 0.6 or trend <= 0.2:
        return "indecision_or_range"
    return "no_setup"


def _label_mode_bucket(row: Any, *, label_mode: str | None) -> str:
    value = get_value(row, "label_mode", "labeling_mode", "label_source")
    if value:
        return str(value)
    return str(label_mode or "unknown")


def _opportunity_bucket(row: Any) -> str:
    opportunity_label = get_value(row, "opportunity_label")
    if opportunity_label is not None:
        return "opportunity" if int(opportunity_label or 0) == 1 else "no_trade"
    opportunity_score = safe_float(get_value(row, "opportunity_score"))
    if opportunity_score is not None:
        if opportunity_score >= 0.7:
            return "high_opportunity"
        if opportunity_score >= 0.4:
            return "borderline_opportunity"
        return "low_opportunity"
    move = abs(safe_float(get_value(row, "future_move_atr", "max_favorable_move_atr"), 0.0) or 0.0)
    if move >= 1.0:
        return "high_opportunity"
    if move >= 0.5:
        return "borderline_opportunity"
    return "low_opportunity"


def _volatility_bucket(row: Any) -> str:
    features = get_mapping(row, "features_json", "features", "feature_values")
    atr = abs(safe_float(get_value(row, "atr_14"), None) or safe_float(features.get("atr_14"), 0.0) or 0.0)
    if safe_float(features.get("regime_high_volatility"), 0.0) >= 0.5:
        return "high_volatility"
    if safe_float(features.get("regime_low_volatility"), 0.0) >= 0.5:
        return "low_volatility"
    if atr >= 1.5:
        return "high_volatility"
    if atr >= 0.8:
        return "medium_volatility"
    return "low_volatility"


def _support_resistance_bucket(row: Any) -> str:
    features = get_mapping(row, "features_json", "features", "feature_values")
    near_support = bool(features.get("near_support")) or (safe_float(features.get("support_distance_atr"), 9.0) or 9.0) <= 0.35
    near_resistance = bool(features.get("near_resistance")) or (safe_float(features.get("resistance_distance_atr"), 9.0) or 9.0) <= 0.35
    if near_support and near_resistance:
        return "support_and_resistance"
    if near_support:
        return "near_support"
    if near_resistance:
        return "near_resistance"
    return "no_sr_context"
