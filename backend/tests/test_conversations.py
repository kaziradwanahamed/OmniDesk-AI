"""Conversation CRUD and project-scoping tests."""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from tests.helpers import create_project, csrf_headers, register_user


async def test_conversation_crud_and_scoping(client: AsyncClient) -> None:
    await register_user(client)
    pid = await create_project(client)
    h = csrf_headers(client)

    created = await client.post(
        f"/api/v1/projects/{pid}/conversations", headers=h, json={"title": "Design"}
    )
    assert created.status_code == 201
    cid = created.json()["id"]
    assert created.json()["project_id"] == pid
    assert created.json()["title"] == "Design"

    listed = await client.get(f"/api/v1/projects/{pid}/conversations")
    assert listed.status_code == 200
    assert any(c["id"] == cid for c in listed.json())

    assert (await client.get(f"/api/v1/conversations/{cid}")).status_code == 200

    renamed = await client.patch(
        f"/api/v1/conversations/{cid}", headers=h, json={"title": "Renamed"}
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Renamed"

    assert (
        await client.delete(f"/api/v1/conversations/{cid}", headers=h)
    ).status_code == 204
    assert (await client.get(f"/api/v1/conversations/{cid}")).status_code == 404


async def test_list_conversations_requires_auth(client: AsyncClient) -> None:
    assert (
        await client.get(f"/api/v1/projects/{uuid.uuid4()}/conversations")
    ).status_code == 401
