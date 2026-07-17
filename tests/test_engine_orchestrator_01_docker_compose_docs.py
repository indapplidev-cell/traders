from pathlib import Path


def test_compose_has_opt_in_separate_service():
    source = Path("docker-compose.yml").read_text(encoding="utf-8")
    assert "online-orchestrator:" in source
    assert 'profiles: ["orchestrator"]' in source
    assert "market-data-sync:" in source
