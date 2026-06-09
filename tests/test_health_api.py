from fastapi.testclient import TestClient

from app.api.main import app


def test_health_api() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "traders-ml",
        "version": "0.1.0",
    }
