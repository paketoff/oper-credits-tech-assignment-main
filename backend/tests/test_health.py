"""The liveness probe answers before anything else exists."""

from fastapi.testclient import TestClient

from app.main import app

_client = TestClient(app)


def test_health_returns_ok():
    response = _client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
