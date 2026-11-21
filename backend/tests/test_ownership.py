"""IDOR / ownership negative tests: User B cannot touch User A's resources."""

from __future__ import annotations

from tests.helpers import csrf_headers, register_user


async def test_user_b_cannot_access_user_a_project(make_client) -> None:
    # User A creates a project with instructions.
    a = await make_client()
    await register_user(a)
    ha = csrf_headers(a)
    created = await a.post(
        "/api/v1/projects", headers=ha, json={"name": "A private project"}
    )
    assert created.status_code == 201
    pid = created.json()["id"]
    await a.put(
        f"/api/v1/projects/{pid}/instructions",
        headers=ha,
        json={"content": "Only A should see this."},
    )

    # User B authenticates with a valid session + CSRF, but is not the owner.
    b = await make_client()
    await register_user(b)
    hb = csrf_headers(b)

    assert (await b.get(f"/api/v1/projects/{pid}")).status_code == 404
    assert (
        await b.patch(f"/api/v1/projects/{pid}", headers=hb, json={"name": "hijack"})
    ).status_code == 404
    assert (
        await b.delete(f"/api/v1/projects/{pid}", headers=hb)
    ).status_code == 404
    assert (
        await b.get(f"/api/v1/projects/{pid}/instructions")
    ).status_code == 404
    assert (
        await b.put(
            f"/api/v1/projects/{pid}/instructions",
            headers=hb,
            json={"content": "overwrite"},
        )
    ).status_code == 404

    # B's own project list never includes A's project.
    b_list = await b.get("/api/v1/projects")
    assert all(p["id"] != pid for p in b_list.json())

    # A still owns an intact, accessible project.
    assert (await a.get(f"/api/v1/projects/{pid}")).status_code == 200
