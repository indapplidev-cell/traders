ML38.10.26.1 - per-symbol staging self-copy / summary path fix

What was fixed:
- wrapper no longer deletes the source directory when `source == destination`;
- staged `feature_regime_experiment_summary.json` is validated before multi-symbol analysis;
- minimal stdout keeps path metadata: `output_dir`, `summary_json_path`, `summary_markdown_path`;
- heavy stdout payload suppression is preserved;
- runtime counts were not changed.

Checks:
- `py_compile`
- targeted `pytest`
- full `pytest`

Codex did not run runtime or cleanup commands.
