"""Liveness contract tests."""

from fastapi.testclient import TestClient

from repomind.main import create_app


def test_health_is_available_without_credentials() -> None:
    """The API boots and reports liveness on the free path."""
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "repomind",
        "version": "0.1.0",
    }
