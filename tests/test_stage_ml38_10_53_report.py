from pathlib import Path


REPORT = Path("reports/stage_ml38_10_53_real_sidecar_generation_preflight_probe_report.md")


def test_stage_report_describes_probe_result_and_safety_boundary() -> None:
    text = REPORT.read_text(encoding="utf-8")
    required = [
        "ML38.10.53",
        "ML38.10.52",
        "design-only command design",
        "preflight probe only",
        "quick-quality was not run",
        "training/runtime was not run",
        "DB writes were not performed",
        "ml_labels/ml_predictions were not written",
        "real 6481 stream was not created",
        "NOT_READY_SIDEСAR_WIRING_NOT_CONFIRMED",
        "TEST_ONLY_BOUNDARY_RISK",
        "CONSISTENCY_VALIDATION_PARTIAL",
        "full 6481 cascade/outcome remains prohibited",
        "no production-like recompute",
        "no tradable edge",
    ]
    for marker in required:
        assert marker.lower() in text.lower(), marker


def test_stage_report_lists_files_and_checks() -> None:
    text = REPORT.read_text(encoding="utf-8")
    required = [
        "app/diagnostics/real_sidecar_generation_preflight_probe.py",
        "tests/test_ml38_10_53_real_sidecar_generation_preflight_probe.py",
        "tests/test_stage_ml38_10_53_report.py",
        "reports/stage_ml38_10_53_real_sidecar_generation_preflight_probe_report.md",
        "python -m py_compile",
        "targeted pytest",
        "git diff --check",
        "full pytest",
    ]
    for marker in required:
        assert marker.lower() in text.lower(), marker

