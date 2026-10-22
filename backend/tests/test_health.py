"""Health-check endpoint tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_service_status(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"
    assert body["llm"] in {"ready", "unreachable"}


def test_root_points_to_health(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["health"] == "/api/v1/health"


def test_unknown_route_returns_404(client: TestClient) -> None:
    assert client.get("/api/v1/does-not-exist").status_code == 404
