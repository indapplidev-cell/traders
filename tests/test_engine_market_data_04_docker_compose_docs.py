from pathlib import Path


def test_compose_has_service_restart_and_health_dependency():
    text = (Path(__file__).parents[1] / "docker-compose.yml").read_text()
    assert "market-data-sync:" in text and "restart: always" in text and "service_healthy" in text
