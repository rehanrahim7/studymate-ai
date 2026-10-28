"""CORS configuration tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_cors_allows_known_origins(client: TestClient) -> None:
    for origin in [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]:
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert response.status_code in (200, 204)
        assert response.headers.get("access-control-allow-origin") == origin

        get_response = client.get("/api/v1/health", headers={"Origin": origin})
        assert get_response.headers.get("access-control-allow-origin") == origin


def test_cors_blocks_unknown_origin(client: TestClient) -> None:
    origin = "http://evil.example.com"
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") != origin

    get_response = client.get("/api/v1/health", headers={"Origin": origin})
    assert get_response.headers.get("access-control-allow-origin") != origin
