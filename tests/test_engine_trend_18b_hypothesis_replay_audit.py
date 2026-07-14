from scripts.engine_trend_18b_hypothesis_replay_audit import (
    DEFAULT_INPUT,
    canonicalize,
    read_json,
    review_row,
    run,
)


def diagnostics():
    return [read_json(path) for path in sorted((DEFAULT_INPUT / "json").glob("*.json"))]


def test_audit_deduplicates_replayed_market_periods() -> None:
    items = diagnostics()
    unique, aliases = canonicalize(items)
    assert len(items) == 60
    assert len(unique) == 45
    assert sum(len(values) - 1 for values in aliases.values()) == 15


def test_review_set_and_verdicts_are_explicit() -> None:
    unique, aliases = canonicalize(diagnostics())
    rows = [
        review_row(item, aliases)
        for item in unique
        if item["comparison"]["match_status"]
        in {"NEEDS_REVIEW", "QUESTIONABLE_UNKNOWN"}
    ]
    assert len(rows) == 22
    assert {row["verdict"] for row in rows} <= {
        "LABEL_ISSUE",
        "EXPECTED_CAUTION",
        "RULE_TOO_STRICT",
        "PRIORITY_ISSUE",
        "INSUFFICIENT_CONTEXT",
    }
    assert sum("TRAP_VS_RANGE" in row["review_groups"] for row in rows) == 2
    assert sum(row["verdict"] == "RULE_TOO_STRICT" for row in rows) == 0


def test_audit_writes_reproducible_artifacts(tmp_path) -> None:
    output = tmp_path / "review"
    report = tmp_path / "report.md"
    summary = run(DEFAULT_INPUT, output, report)
    assert summary["input_rows"] == 60
    assert summary["unique_periods"] == 45
    assert summary["unique_target_periods"] == 22
    assert summary["rule_changes_applied"] is False
    assert (output / "ENGINE_TREND_18B_REVIEW_MATRIX.csv").exists()
    assert (output / "ENGINE_TREND_18B_DOWN_CONFIRMATION_AUDIT.md").exists()
    assert report.exists()
