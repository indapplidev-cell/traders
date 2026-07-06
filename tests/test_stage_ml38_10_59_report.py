from pathlib import Path


REPORT = Path("reports/stage_ml38_10_59_post_fix_sidecar_fixture_validation_report.md")


def test_stage_report_contains_required_scope_and_decision() -> None:
    text = REPORT.read_text(encoding="utf-8")
    required = (
        "ML38.10.59",
        "synthetic/tmp_path only",
        "POST_FIX_FIXTURE_VALIDATION_PASSED_NO_REAL_RUN",
        "quick-quality/training/runtime were not run",
        "no real artifacts were mutated",
        "no new real sidecars or ZIP were created",
        "full 6481 cascade/outcome remains blocked",
        "not a production-like recompute",
        "not tradable edge",
    )
    for phrase in required:
        assert phrase in text


def test_stage_report_covers_contract_sections_and_safety() -> None:
    text = REPORT.read_text(encoding="utf-8")
    for heading in (
        "Why ML38.10.59 follows ML38.10.58",
        "Synthetic fixture export result",
        "Exact-byte integrity result",
        "LF-only line ending result",
        "Summary contract fields result",
        "Schema version result",
        "sidecar_runtime_truth result",
        "Archive status result",
        "Completion status result",
        "Legacy normalized-only fail-closed result",
        "Real artifact guardrail",
        "Tests run",
        "Safety prohibitions",
        "Final decision",
    ):
        assert heading in text
