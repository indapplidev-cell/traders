from pathlib import Path


def test_runtime_has_no_forbidden_module_imports():
    root = Path("app/engine_orchestrator")
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    for module in ("app.engine_" + "execution", "app.engine_" + "position", "app.engine_" + "exit"):
        assert module not in source
