from pathlib import Path

import clean_traders_ml


def test_stage_markdown_report_is_allowed_for_technical_commit() -> None:
    path = Path(
        "reports/stage_ml38_10_36_1_compact_archive_size_hardening_report.md"
    )

    assert clean_traders_ml._is_stage_markdown_report(path) is True
    assert clean_traders_ml._is_commit_allowed_path(path.as_posix()) is True


def test_runtime_json_report_is_not_stage_markdown_report() -> None:
    path = Path("reports/profit_eval_v2_ml_candle_mlp_v1_solusdt_15m_h12_x.json")

    assert clean_traders_ml._is_stage_markdown_report(path) is False
    assert clean_traders_ml._is_commit_allowed_path(path.as_posix()) is False


def test_runtime_zip_archive_is_not_stage_markdown_report() -> None:
    path = Path("reports/feature_regime_experiments/quick_quality_x.zip")

    assert clean_traders_ml._is_stage_markdown_report(path) is False
    assert clean_traders_ml._is_commit_allowed_path(path.as_posix()) is False


def test_cleaner_log_is_not_stage_markdown_report() -> None:
    path = Path("reports/cleaner_logs/clean_traders_ml_20260704_040728.log")

    assert clean_traders_ml._is_stage_markdown_report(path) is False
    assert clean_traders_ml._is_commit_allowed_path(path.as_posix()) is False


def test_technical_commit_classification_includes_only_stage_markdown_report() -> None:
    entries = [
        clean_traders_ml.StatusEntry(" ", "M", "run_fv3_cached_tuning.py"),
        clean_traders_ml.StatusEntry(
            "?", "?", "app/experiments/compact_archive_pruner.py"
        ),
        clean_traders_ml.StatusEntry(
            "?",
            "?",
            "reports/stage_ml38_10_36_1_compact_archive_size_hardening_report.md",
        ),
        clean_traders_ml.StatusEntry(
            "?",
            "?",
            "tests/test_ml38_10_36_1_compact_archive_size_hardening.py",
        ),
        clean_traders_ml.StatusEntry("?", "?", "reports/profit_eval_v2_runtime.json"),
    ]

    included, skipped, conflicts = clean_traders_ml._select_commit_entries(
        entries, include_deletions=False
    )

    assert {entry.path for entry in included} == {
        "run_fv3_cached_tuning.py",
        "app/experiments/compact_archive_pruner.py",
        "reports/stage_ml38_10_36_1_compact_archive_size_hardening_report.md",
        "tests/test_ml38_10_36_1_compact_archive_size_hardening.py",
    }
    assert [entry.path for entry in skipped] == ["reports/profit_eval_v2_runtime.json"]
    assert conflicts == []
