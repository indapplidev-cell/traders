import zipfile
from pathlib import Path

from app.reporting.project_packager import build_project_zip as build_app_project_zip
from app.reporting.project_packager import should_include_project_file as app_should_include
from packer.project_packager import build_project_zip as build_packer_project_zip
from packer.project_packager import should_include_project_file as packer_should_include


def _create_project(root: Path) -> None:
    (root / "app").mkdir(parents=True)
    (root / "app" / "main.py").write_text("print('ok')", encoding="utf-8")
    (root / "reports").mkdir(parents=True)
    (root / "reports" / "stage_ml38_10_26_2_report.md").write_text("# keep", encoding="utf-8")
    (root / "reports" / "probability_diagnostics_btcusdt.json").write_text("{}", encoding="utf-8")
    (root / "reports" / "profit_eval_v2_btcusdt.json").write_text("{}", encoding="utf-8")
    (root / "reports" / "dataset_summary_btcusdt.json").write_text("{}", encoding="utf-8")
    (root / "reports" / "model_comparison_btcusdt.json").write_text("{}", encoding="utf-8")
    (root / "reports" / "walk_forward_eval_btcusdt.json").write_text("{}", encoding="utf-8")
    (root / "reports" / "multi_symbol_feature_regime_analysis.json").write_text("{}", encoding="utf-8")
    (root / "reports" / "multi_symbol_feature_regime_analysis.md").write_text("# generated", encoding="utf-8")


def _assert_archive_clean(output_zip: Path, manifest: dict) -> None:
    with zipfile.ZipFile(output_zip) as archive:
        names = set(archive.namelist())

    assert "app/main.py" in names
    assert "reports/stage_ml38_10_26_2_report.md" in names
    assert "reports/probability_diagnostics_btcusdt.json" not in names
    assert "reports/profit_eval_v2_btcusdt.json" not in names
    assert "reports/dataset_summary_btcusdt.json" not in names
    assert "reports/model_comparison_btcusdt.json" not in names
    assert "reports/walk_forward_eval_btcusdt.json" not in names
    assert "reports/multi_symbol_feature_regime_analysis.json" not in names
    assert "reports/multi_symbol_feature_regime_analysis.md" not in names
    assert manifest["runtime_reports_included"] is False
    assert manifest["generated_root_reports_included"] is False


def test_packer_project_archive_excludes_generated_root_reports_but_keeps_stage_reports(tmp_path: Path) -> None:
    root = tmp_path / "project"
    _create_project(root)
    output_zip = root / "reports" / "project_archives" / "packer_project.zip"

    assert packer_should_include(root / "reports" / "probability_diagnostics_btcusdt.json", project_root=root) is False
    assert packer_should_include(root / "reports" / "stage_ml38_10_26_2_report.md", project_root=root) is True

    manifest = build_packer_project_zip(root, output_zip)
    _assert_archive_clean(output_zip, manifest)


def test_app_project_archive_excludes_generated_root_reports_but_keeps_stage_reports(tmp_path: Path) -> None:
    root = tmp_path / "project"
    _create_project(root)
    output_zip = tmp_path / "app_project.zip"

    assert app_should_include(root / "reports" / "probability_diagnostics_btcusdt.json", project_root=root) is False
    assert app_should_include(root / "reports" / "stage_ml38_10_26_2_report.md", project_root=root) is True

    manifest = build_app_project_zip(root, output_zip)
    _assert_archive_clean(output_zip, manifest)
