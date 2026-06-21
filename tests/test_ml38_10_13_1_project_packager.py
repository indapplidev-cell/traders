import zipfile
from pathlib import Path

from app.reporting.project_packager import build_project_zip, should_include_project_file


def test_project_packager_excludes_artifacts_and_runtime_reports(tmp_path: Path) -> None:
    project_root = tmp_path / "traders-ml"
    (project_root / "app").mkdir(parents=True)
    (project_root / "app" / "main.py").write_text("print('ok')", encoding="utf-8")
    model_file = project_root / "artifacts" / "models" / "candidate" / "model.pt"
    model_file.parent.mkdir(parents=True)
    model_file.write_bytes(b"model")
    runtime_report = project_root / "reports" / "feature_regime_experiments" / "run" / "report.json"
    runtime_report.parent.mkdir(parents=True)
    runtime_report.write_text("{}", encoding="utf-8")

    output_zip = tmp_path / "project.zip"
    manifest = build_project_zip(project_root, output_zip)

    assert output_zip.exists()
    assert manifest["artifacts_included"] is False
    assert manifest["runtime_reports_included"] is False

    with zipfile.ZipFile(output_zip) as archive:
        names = set(archive.namelist())

    assert "app/main.py" in names
    assert "artifacts/models/candidate/model.pt" not in names
    assert "reports/feature_regime_experiments/run/report.json" not in names
    assert "project_archive_manifest.json" in names


def test_should_include_project_file_excludes_zip_and_cache(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    zip_file = root / "old.zip"
    cache_file = root / "__pycache__" / "x.pyc"
    source_file = root / "app" / "x.py"
    zip_file.write_bytes(b"zip")
    cache_file.parent.mkdir(parents=True)
    cache_file.write_bytes(b"cache")
    source_file.parent.mkdir(parents=True)
    source_file.write_text("x = 1", encoding="utf-8")

    assert should_include_project_file(zip_file, project_root=root) is False
    assert should_include_project_file(cache_file, project_root=root) is False
    assert should_include_project_file(source_file, project_root=root) is True
