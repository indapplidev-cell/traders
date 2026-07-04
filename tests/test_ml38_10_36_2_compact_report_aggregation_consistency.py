from __future__ import annotations

import json

from app.experiments.compact_archive_pruner import (
    compact_feature_regime_summary_payload,
)
from app.experiments.multi_symbol_feature_regime_analyzer import (
    MultiSymbolFeatureRegimeAnalyzer,
)
from app.experiments.multi_symbol_feature_regime_reporter import (
    MultiSymbolFeatureRegimeReporter,
)


def _compact_summary() -> dict:
    return {
        "schema_version": "ml38.10.36.2",
        "source": "feature_regime_experiment_summary",
        "candidate_count": 46,
        "evaluated_candidate_count": 46,
        "failed_candidate_count": 0,
        "accepted_candidate_count": 0,
        "rejected_candidate_count": 46,
        "feature_version_used": "fv4_book_setup_context",
        "real_feature_diagnostics_used": True,
        "real_feature_diagnostics_row_count": 6481,
        "effective_gap_count_for_training": 0,
        "gap_severity_for_training": "OK",
        "gap_training_safe": True,
        "regime_features_attached": True,
        "regime_feature_count": 8,
        "regime_specific_training_applied": True,
        "regime_label_builder_used_in_training_any": True,
        "regime_label_builder_status": {
            "regime_label_builder_used_in_training": True,
            "regime_specific_training_applied": True,
        },
        "candle_ta_context_features_attached": True,
        "candle_ta_context_feature_count": 54,
        "book_setup_context_features_attached": True,
        "book_setup_context_feature_count": 54,
    }


def _compacted_payload() -> dict:
    return {
        "status": "ok",
        "symbol": "SOLUSDT",
        "interval": "15m",
        "compact_report": True,
        "compact_summary": _compact_summary(),
        # Old verbose diagnostics are intentionally absent.
    }


def test_compact_summary_values_survive_multi_symbol_aggregation(tmp_path) -> None:
    summary_path = tmp_path / "feature_regime_experiment_summary.json"
    summary_path.write_text(json.dumps(_compacted_payload()), encoding="utf-8")

    payload = MultiSymbolFeatureRegimeAnalyzer().analyze([summary_path])
    symbol = payload["symbol_results"][0]

    assert symbol["gap_severity_for_training"] == "OK"
    assert symbol["effective_gap_count_for_training"] == 0
    assert symbol["gap_training_safe"] is True
    assert "gap_quality_gate" not in symbol["failed_gates"]
    assert symbol["regime_specific_training_applied"] is True
    assert symbol["regime_label_builder_used_in_training"] is True
    assert symbol["feature_version_used"] == "fv4_book_setup_context"
    assert symbol["real_feature_diagnostics_used"] is True
    assert symbol["real_feature_diagnostics_row_count"] == 6481
    assert symbol["candidate_count"] == 46
    assert payload["candidate_count"] == 46
    assert payload["all_gap_training_safe"] is True
    assert payload["all_real_feature_diagnostics_used"] is True
    assert payload["symbols_missing_regime_features"] == []

    audit = payload["aggregate_report_source_consistency"]
    assert audit["status"] == "CONSISTENT"
    assert audit["compact_summary_source_used"] == {"SOLUSDT": True}
    assert audit["missing_fields_after_fallback"] == {"SOLUSDT": []}
    assert audit["warnings"] == []
    assert audit["source_priority_used"]["SOLUSDT"]["candidate_count"] == (
        "compact_summary.candidate_count"
    )


def test_pruner_builds_bounded_canonical_compact_summary() -> None:
    legacy_payload = {
        "status": "ok",
        "symbol": "SOLUSDT",
        **_compact_summary(),
        "candidate_results": [{"config_id": f"cfg_{index}"} for index in range(10)],
        "rows": [{"large": "payload"}],
    }

    compacted = compact_feature_regime_summary_payload(legacy_payload)
    canonical = compacted["compact_summary"]

    assert canonical["schema_version"] == "ml38.10.36.2"
    assert canonical["candidate_count"] == 46
    assert canonical["gap_severity_for_training"] == "OK"
    assert canonical["effective_gap_count_for_training"] == 0
    assert canonical["feature_version_used"] == "fv4_book_setup_context"
    assert canonical["real_feature_diagnostics_used"] is True
    assert canonical["regime_specific_training_applied"] is True
    assert "rows" not in compacted


def test_nested_and_candidate_fallbacks_work_without_old_verbose_blocks() -> None:
    summary = {
        "symbol": "SOLUSDT",
        "candidate_summary": {
            "candidate_count": 46,
            "evaluated_candidate_count": 46,
            "failed_candidate_count": 0,
            "accepted_candidate_count": 0,
            "rejected_candidate_count": 46,
        },
        "gap_quality_summary": {
            "effective_gap_count_for_training": 0,
            "gap_severity_for_training": "OK",
        },
        "feature_quality_summary": {
            "feature_version_used": "fv4_book_setup_context",
            "row_count": 6481,
        },
        "regime_feature_summary": {
            "regime_feature_count": 8,
        },
        "regime_label_builder_status": {
            "regime_label_builder_used_in_training": True,
            "regime_specific_training_applied": True,
        },
    }

    result = MultiSymbolFeatureRegimeAnalyzer._symbol_result(summary)

    assert result["gap_severity_for_training"] == "OK"
    assert result["gap_training_safe"] is True
    assert result["real_feature_diagnostics_used"] is True
    assert result["regime_features_attached"] is True
    assert result["regime_specific_training_applied"] is True
    assert result["regime_label_builder_used_in_training"] is True
    assert result["aggregate_report_source_consistency"][
        "missing_fields_after_fallback"
    ] == []


def test_unknown_is_used_only_when_all_sources_are_absent() -> None:
    result = MultiSymbolFeatureRegimeAnalyzer._symbol_result({"symbol": "SOLUSDT"})

    assert result["gap_severity_for_training"] == "UNKNOWN"
    assert result["gap_training_safe"] is False
    assert "gap_quality_gate" in result["failed_gates"]
    audit = result["aggregate_report_source_consistency"]
    assert "gap_severity_for_training" in audit["missing_fields_after_fallback"]
    assert "missing_after_all_fallbacks:gap_severity_for_training" in audit["warnings"]


def test_ml38_10_36_1_candidate_sample_is_a_supported_legacy_fallback() -> None:
    summary = {
        "symbol": "SOLUSDT",
        "candidate_count": 46,
        "failed_candidate_count": 0,
        "accepted_candidate_count": 0,
        "rejected_candidate_count": 46,
        "candidate_results": {
            "_compact_pruned": True,
            "original_type": "list",
            "original_len": 46,
            "sample": [
                {
                    "config_id": "legacy_compact_candidate",
                    "candidate_status": "REJECTED",
                    "real_feature_diagnostics_used": True,
                    "real_feature_diagnostics_row_count": 6481,
                    "gap_severity_for_training": "OK",
                    "gap_training_safe": True,
                    "regime_features_attached": True,
                    "regime_feature_count": 8,
                    "regime_specific_training_applied": True,
                    "regime_label_builder_used_in_training": True,
                    "book_setup_context_features_attached": True,
                    "book_setup_context_feature_count": 54,
                    "fv4_feature_count": 230,
                    "failed_gates": {
                        "_compact_pruned": True,
                        "original_type": "list",
                        "original_len": 2,
                        "sample": ["profit_aware_gate", "bias_gate"],
                    },
                }
            ],
        },
    }

    result = MultiSymbolFeatureRegimeAnalyzer._symbol_result(summary)

    assert result["feature_version_used"] == "fv4_book_setup_context"
    assert result["effective_gap_count_for_training"] == 0
    assert result["gap_severity_for_training"] == "OK"
    assert "gap_quality_gate" not in result["failed_gates"]
    assert result["failed_gates"] == ["profit_aware_gate", "bias_gate"]
    assert result["aggregate_report_source_consistency"][
        "missing_fields_after_fallback"
    ] == []


def test_reporter_outputs_consistency_audit(tmp_path) -> None:
    summary_path = tmp_path / "feature_regime_experiment_summary.json"
    summary_path.write_text(json.dumps(_compacted_payload()), encoding="utf-8")
    payload = MultiSymbolFeatureRegimeAnalyzer().analyze([summary_path])
    reporter = MultiSymbolFeatureRegimeReporter()

    compact = reporter.compact_summary_to_dict(payload)
    markdown = reporter._markdown(payload)

    assert compact["aggregate_report_source_consistency"]["status"] == "CONSISTENT"
    assert "## Compact Report Source Consistency" in markdown
    assert "compact_summary_source_used" in markdown
