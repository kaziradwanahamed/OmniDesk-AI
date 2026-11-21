"""Phase 9 — project export (Markdown / JSON), content fidelity, and IDOR."""

from __future__ import annotations

import json

from tests.helpers import (
    create_conversation,
    create_project,
    csrf_headers,
    register_user,
)


async def _setup(client) -> str:
    await register_user(client)
    pid = await create_project(client, name="Export Project")
    await create_conversation(client, pid, title="Design chat")
    await client.post(
        f"/api/v1/projects/{pid}/files",
        headers=csrf_headers(client),
        files={"file": ("notes.md", b"# Architecture notes", "text/markdown")},
    )
    return pid


async def test_export_markdown(client, upload_root):
    pid = await _setup(client)
    r = await client.get(f"/api/v1/projects/{pid}/export", params={"format": "md"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/markdown")
    assert "attachment; filename=" in r.headers["content-disposition"]
    text = r.text
    assert "# Project Export: Export Project" in text
    assert "Design chat" in text
    assert "notes.md" in text


async def test_export_json(client, upload_root):
    pid = await _setup(client)
    r = await client.get(f"/api/v1/projects/{pid}/export", params={"format": "json"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    data = json.loads(r.text)
    assert data["project"]["name"] == "Export Project"
    assert data["files"][0]["filename"] == "notes.md"
    assert data["conversations"][0]["title"] == "Design chat"


async def test_export_invalid_format_rejected(client):
    await register_user(client)
    pid = await create_project(client)
    r = await client.get(f"/api/v1/projects/{pid}/export", params={"format": "pdf"})
    assert r.status_code in (400, 422)


async def test_export_idor_404(make_client, upload_root):
    owner = await make_client()
    attacker = await make_client()
    pid = await _setup(owner)
    await register_user(attacker)
    for fmt in ("md", "json"):
        r = await attacker.get(
            f"/api/v1/projects/{pid}/export", params={"format": fmt}
        )
        assert r.status_code == 404
