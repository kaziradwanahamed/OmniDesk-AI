"""Project memory (decisions & tasks) CRUD, activation invariant, and IDOR."""

from __future__ import annotations

from httpx import AsyncClient

from tests.helpers import create_project, csrf_headers, register_user


async def test_decision_crud(client: AsyncClient) -> None:
    await register_user(client)
    h = csrf_headers(client)
    pid = await create_project(client)

    created = await client.post(
        f"/api/v1/projects/{pid}/decisions",
        headers=h,
        json={"title": "Use FastAPI", "rationale": "Async + typed"},
    )
    assert created.status_code == 201
    d = created.json()
    assert d["title"] == "Use FastAPI"
    assert d["status"] == "active"
    did = d["id"]

    listed = await client.get(f"/api/v1/projects/{pid}/decisions")
    assert [x["id"] for x in listed.json()] == [did]

    patched = await client.patch(
        f"/api/v1/projects/{pid}/decisions/{did}",
        headers=h,
        json={"status": "superseded"},
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "superseded"

    deleted = await client.delete(
        f"/api/v1/projects/{pid}/decisions/{did}", headers=h
    )
    assert deleted.status_code == 204
    assert (await client.get(f"/api/v1/projects/{pid}/decisions")).json() == []


async def test_task_crud_and_single_active_invariant(client: AsyncClient) -> None:
    await register_user(client)
    h = csrf_headers(client)
    pid = await create_project(client)

    t1 = (
        await client.post(
            f"/api/v1/projects/{pid}/tasks",
            headers=h,
            json={"title": "Build context builder"},
        )
    ).json()
    t2 = (
        await client.post(
            f"/api/v1/projects/{pid}/tasks",
            headers=h,
            json={"title": "Wire frontend", "status": "todo"},
        )
    ).json()
    assert t1["is_active_task"] is False and t2["is_active_task"] is False

    # Activate t1, then t2 — only one may be active at a time.
    r1 = await client.patch(
        f"/api/v1/projects/{pid}/tasks/{t1['id']}/activate", headers=h
    )
    assert r1.status_code == 200 and r1.json()["is_active_task"] is True

    await client.patch(
        f"/api/v1/projects/{pid}/tasks/{t2['id']}/activate", headers=h
    )
    tasks = {t["id"]: t for t in (await client.get(f"/api/v1/projects/{pid}/tasks")).json()}
    assert tasks[t1["id"]]["is_active_task"] is False
    assert tasks[t2["id"]]["is_active_task"] is True


async def test_task_update_status(client: AsyncClient) -> None:
    await register_user(client)
    h = csrf_headers(client)
    pid = await create_project(client)
    t = (
        await client.post(
            f"/api/v1/projects/{pid}/tasks", headers=h, json={"title": "X"}
        )
    ).json()
    r = await client.patch(
        f"/api/v1/projects/{pid}/tasks/{t['id']}",
        headers=h,
        json={"status": "in_progress"},
    )
    assert r.status_code == 200 and r.json()["status"] == "in_progress"


async def test_memory_requires_csrf(client: AsyncClient) -> None:
    await register_user(client)
    pid = await create_project(client)
    r = await client.post(
        f"/api/v1/projects/{pid}/decisions", json={"title": "No CSRF"}
    )
    assert r.status_code == 403


async def test_memory_idor(make_client) -> None:
    a = await make_client()
    await register_user(a)
    pid_a = await create_project(a)
    did = (
        await a.post(
            f"/api/v1/projects/{pid_a}/decisions",
            headers=csrf_headers(a),
            json={"title": "A's decision"},
        )
    ).json()["id"]
    tid = (
        await a.post(
            f"/api/v1/projects/{pid_a}/tasks",
            headers=csrf_headers(a),
            json={"title": "A's task"},
        )
    ).json()["id"]

    b = await make_client()
    await register_user(b)
    hb = csrf_headers(b)

    # B cannot list, read, mutate, activate, or delete A's project memory.
    assert (await b.get(f"/api/v1/projects/{pid_a}/decisions")).status_code == 404
    assert (await b.get(f"/api/v1/projects/{pid_a}/tasks")).status_code == 404
    assert (
        await b.patch(
            f"/api/v1/projects/{pid_a}/decisions/{did}",
            headers=hb,
            json={"title": "hijack"},
        )
    ).status_code == 404
    assert (
        await b.patch(
            f"/api/v1/projects/{pid_a}/tasks/{tid}/activate", headers=hb
        )
    ).status_code == 404
    assert (
        await b.delete(
            f"/api/v1/projects/{pid_a}/tasks/{tid}", headers=hb
        )
    ).status_code == 404

    # A's decision is untouched.
    assert (
        await a.get(f"/api/v1/projects/{pid_a}/decisions")
    ).json()[0]["title"] == "A's decision"


async def test_cross_project_id_is_404(client: AsyncClient) -> None:
    """A decision id from another of the SAME user's projects is not reachable
    through a different project path."""
    await register_user(client)
    h = csrf_headers(client)
    p1 = await create_project(client, name="P1")
    p2 = await create_project(client, name="P2")
    did = (
        await client.post(
            f"/api/v1/projects/{p1}/decisions", headers=h, json={"title": "in p1"}
        )
    ).json()["id"]
    # Same owner, wrong project path -> 404 (scoped by project_id).
    r = await client.patch(
        f"/api/v1/projects/{p2}/decisions/{did}", headers=h, json={"title": "x"}
    )
    assert r.status_code == 404
