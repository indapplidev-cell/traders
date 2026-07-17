from pathlib import Path


def test_module_has_no_forbidden_engine_imports_or_invocations():
    root = Path("app/engine_observation")
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    for name in ("engine_execution", "engine_position", "engine_exit", "PipelineRunner", "AnalysisRunner",
                 "SetupRunner", "StrategyRunner", "RiskRunner", "PaperRunner"):
        assert name not in source
    assert "INSERT INTO" not in source.upper()
    assert "UPDATE online_pipeline" not in source
