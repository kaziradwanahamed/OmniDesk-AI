"""Auth flow tests: register, login, logout, /me, and rejection cases."""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from tests.helpers import register_user


async def test_register_login_me_logout_flow(make_client) -> None:
    client = await make_client()
    resp, email, _ = await register_user(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == email
    assert "id" in body
    assert "access_token" in client.cookies
    assert "csrf_token" in client.cookies

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == email

    logout = await client.post("/api/v1/auth/logout")
    assert logout.status_code == 204

    me_after = await client.get("/api/v1/auth/me")
    assert me_after.status_code == 401


async def test_login_with_registered_credentials(make_client) -> None:
    c1 = await make_client()
    _, email, password = await register_user(c1)

    c2 = await make_client()
    resp = await c2.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == email
    assert (await c2.get("/api/v1/auth/me")).status_code == 200


async def test_duplicate_email_rejected(make_client) -> None:
    c1 = await make_client()
    _, email, _ = await register_user(c1)
    c2 = await make_client()
    resp, _, _ = await register_user(c2, email=email)
    assert resp.status_code == 409


async def test_login_wrong_password(make_client) -> None:
    c1 = await make_client()
    _, email, _ = await register_user(c1)
    c2 = await make_client()
    resp = await c2.post(
        "/api/v1/auth/login", json={"email": email, "password": "wrong-password-xyz"}
    )
    assert resp.status_code == 401


async def test_me_requires_authentication(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_register_password_too_short(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": f"x_{uuid.uuid4().hex}@example.com", "password": "short"},
    )
    assert resp.status_code == 422
