"""Security/hardening tests for existing Phase 1 endpoints and middleware."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.middleware.cors import CORSMiddleware

from app.main import create_app


def test_cors_middleware_configured() -> None:
    app = create_app()
    assert any(m.cls is CORSMiddleware for m in app.user_middleware)


async def test_unhandled_exception_is_generic_and_non_leaking() -> None:
    app = create_app()

    async def boom() -> None:
        # A secret-shaped detail that must never reach the client.
        raise RuntimeError("super-secret postgres://user:pw@db:5432/omnidesk")

    app.add_api_route("/_boom", boom, methods=["GET"])

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/_boom")

    assert resp.status_code == 500
    assert resp.json() == {"detail": "Internal Server Error"}
    body = resp.text
    assert "super-secret" not in body
    assert "postgres://" not in body
    assert "Traceback" not in body


async def test_ready_returns_503_without_leaking_when_db_down(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.api.health as health

    class FakeEngine:
        def connect(self):
            raise RuntimeError(
                "postgres://omnidesk:supersecret@db:5432/omnidesk down"
            )

    monkeypatch.setattr(health, "engine", FakeEngine())

    resp = await client.get("/ready")
    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "not_ready"
    assert data["database"] == "unavailable"
    text = resp.text
    assert "supersecret" not in text
    assert "postgres://" not in text
