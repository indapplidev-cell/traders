from __future__ import annotations

from typing import Any

from app.diagnostics.directional_side_walk_forward_stability import (
    DirectionalSideWalkForwardStabilityAnalyzer,
)


def _candidate(warnings: Any) -> dict[str, Any]:
    return {
        "config_id": "synthetic_ml38_10_64",
        "walk_forward_profit_diagnostics": {
            "fold_count": 1,
            "fold_signal_summary": {
                "fold_count": 1,
                "folds_with_gate": 1,
                "total_resolved_signal_count": 20,
            },
            "fold_profit_summary": {
                "profitable_fold_count": 1,
                "profitable_fold_rate": 1.0,
            },
            "walk_forward_stability_warnings": warnings,
        },
    }


def _warning_samples(warnings: Any) -> list[str]:
    row = DirectionalSideWalkForwardStabilityAnalyzer()._candidate_row(
        _candidate(warnings)
    )
    samples = row["walk_forward_stability_warnings"]
    assert all(isinstance(item, str) for item in samples)
    return samples


def test_compact_pruned_nested_dict_reaches_candidate_row_without_typeerror() -> None:
    compact_warning = {
        "sample": {
            "warning": "low_directional_coverage",
            "details": {"fold": 1, "value": 0.12},
        },
        "omitted_count": 3,
    }

    samples = _warning_samples([compact_warning])

    assert samples[0] == (
        '{"omitted_count":3,"sample":{"details":{"fold":1,"value":0.12},'
        '"warning":"low_directional_coverage"}}'
    )


def test_duplicate_compact_dict_warnings_are_deduplicated_in_order() -> None:
    first = {"sample": {"warning": "first"}, "omitted_count": 2}
    second = {"reason": "second"}

    samples = _warning_samples([first, first.copy(), second, first])

    assert samples[:2] == [
        '{"omitted_count":2,"sample":{"warning":"first"}}',
        "second",
    ]
    assert samples.count(samples[0]) == 1


def test_existing_string_warning_behavior_is_preserved() -> None:
    samples = _warning_samples(["a", "b", "a"])

    assert samples[:2] == ["a", "b"]
    assert samples.count("a") == 1


def test_mixed_warning_payloads_are_hash_safe_strings() -> None:
    samples = _warning_samples(["a", {"reason": "b"}, ["c", {"d": 1}], None])

    assert samples[:4] == ["a", "b", '["c",{"d":1}]', "None"]
