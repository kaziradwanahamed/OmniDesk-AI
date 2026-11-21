"""IDOR / ownership negative tests for conversation and message endpoints."""

from __future__ import annotations

from tests.helpers import create_conversation, create_project, csrf_headers, register_user


async def test_user_b_cannot_access_user_a_conversation(make_client) -> None:
    a = await make_client()
    await register_user(a)
    pid = await create_project(a)
    cid = await create_conversation(a, pid, title="A private thread")
    ha = csrf_headers(a)
    await a.post(
        f"/api/v1/conversations/{cid}/messages", headers=ha, json={"content": "secret"}
    )

    b = await make_client()
    await register_user(b)
    hb = csrf_headers(b)

    assert (await b.get(f"/api/v1/conversations/{cid}")).status_code == 404
    assert (await b.get(f"/api/v1/conversations/{cid}/messages")).status_code == 404
    assert (
        await b.patch(f"/api/v1/conversations/{cid}", headers=hb, json={"title": "x"})
    ).status_code == 404
    assert (
        await b.delete(f"/api/v1/conversations/{cid}", headers=hb)
    ).status_code == 404
    assert (
        await b.post(
            f"/api/v1/conversations/{cid}/messages", headers=hb, json={"content": "x"}
        )
    ).status_code == 404
    # B cannot even list A's project conversations.
    assert (
        await b.get(f"/api/v1/projects/{pid}/conversations")
    ).status_code == 404

    # A's data is intact.
    assert (await a.get(f"/api/v1/conversations/{cid}")).status_code == 200
    assert len((await a.get(f"/api/v1/conversations/{cid}/messages")).json()) == 2
