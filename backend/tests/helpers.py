"""Test helpers for auth flows."""

from __future__ import annotations

import uuid

from httpx import AsyncClient, Response


async def register_user(
    client: AsyncClient,
    email: str | None = None,
    password: str = "password123",
    display_name: str = "Test User",
) -> tuple[Response, str, str]:
    email = email or f"u_{uuid.uuid4().hex}@example.com"
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": display_name},
    )
    return resp, email, password


def csrf_headers(client: AsyncClient) -> dict[str, str]:
    token = client.cookies.get("csrf_token")
    return {"X-CSRF-Token": token} if token else {}
