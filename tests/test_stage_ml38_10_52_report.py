from pathlib import Path


REPORT = Path("reports/stage_ml38_10_52_real_sidecar_generation_command_design_report.md")


def test_stage_report_exists_and_describes_design_boundary() -> None:
    text = REPORT.read_text(encoding="utf-8")

    required = [
        "ML38.10.52",
        "ML38.10.50",
        "ML38.10.51",
        "design-only",
        "quick-quality was not run",
        "training/runtime was not run",
        "DB writes were not performed",
        "ml_labels and ml_predictions were not written",
        "real 6481 stream was not created",
        "FAIL_CLOSED",
        "lv36",
        "lv31",
        "fv4",
        "fv3",
        "full 6481 cascade/outcome remains prohibited",
        "no production-like recompute",
        "no tradable edge",
    ]
    for marker in required:
        assert marker.lower() in text.lower(), marker


def test_stage_report_lists_files_and_allowed_checks() -> None:
    text = REPORT.read_text(encoding="utf-8")
    lower_text = text.lower()

    assert "app/diagnostics/real_sidecar_generation_command_design.py" in text
    assert "tests/test_ml38_10_52_real_sidecar_generation_command_design.py" in text
    assert "tests/test_stage_ml38_10_52_report.py" in text
    assert "python -m py_compile" in lower_text
    assert "targeted pytest" in lower_text
    assert "git diff --check" in lower_text
    assert "full pytest" in lower_text
