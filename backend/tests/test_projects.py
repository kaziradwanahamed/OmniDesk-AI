"""Project & project-instructions CRUD persistence tests."""

from __future__ import annotations

from httpx import AsyncClient

from tests.helpers import csrf_headers, register_user


async def test_project_and_instructions_crud(client: AsyncClient) -> None:
    await register_user(client)
    h = csrf_headers(client)

    created = await client.post(
        "/api/v1/projects",
        headers=h,
        json={"name": "SentinelGate AI", "description": "security gateway", "status": "active"},
    )
    assert created.status_code == 201
    pid = created.json()["id"]
    assert created.json()["name"] == "SentinelGate AI"

    listed = await client.get("/api/v1/projects")
    assert listed.status_code == 200
    assert any(p["id"] == pid for p in listed.json())

    got = await client.get(f"/api/v1/projects/{pid}")
    assert got.status_code == 200
    assert got.json()["description"] == "security gateway"

    updated = await client.patch(
        f"/api/v1/projects/{pid}",
        headers=h,
        json={"name": "SentinelGate v2", "status": "paused"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "SentinelGate v2"
    assert updated.json()["status"] == "paused"

    # No instructions yet.
    none_yet = await client.get(f"/api/v1/projects/{pid}/instructions")
    assert none_yet.status_code == 200
    assert none_yet.json() is None

    v1 = await client.put(
        f"/api/v1/projects/{pid}/instructions",
        headers=h,
        json={"content": "Use FastAPI.", "response_style": "concise"},
    )
    assert v1.status_code == 200
    assert v1.json()["version"] == 1
    assert v1.json()["is_active"] is True

    v2 = await client.put(
        f"/api/v1/projects/{pid}/instructions",
        headers=h,
        json={"content": "Use FastAPI and Redis."},
    )
    assert v2.status_code == 200
    assert v2.json()["version"] == 2

    active = await client.get(f"/api/v1/projects/{pid}/instructions")
    assert active.json()["version"] == 2
    assert active.json()["content"] == "Use FastAPI and Redis."

    deleted = await client.delete(f"/api/v1/projects/{pid}", headers=h)
    assert deleted.status_code == 204
    assert (await client.get(f"/api/v1/projects/{pid}")).status_code == 404


async def test_create_project_requires_csrf(client: AsyncClient) -> None:
    await register_user(client)
    # Authenticated but missing the X-CSRF-Token header.
    resp = await client.post("/api/v1/projects", json={"name": "No CSRF"})
    assert resp.status_code == 403


async def test_list_projects_requires_auth(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/projects")).status_code == 401
