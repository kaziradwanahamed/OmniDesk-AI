"""Phase 9 — Layer 5 retrieval: ts_rank_cd ranking, pinned/explicit inclusion,
token-budget trimming, "[File: name | Chunk N]" formatting, ContextBuilder
integration via context-preview, and strict cross-project isolation."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.services import file_service
from tests.helpers import (
    create_conversation,
    create_project,
    csrf_headers,
    register_user,
)


@pytest.fixture
async def session(test_engine):
    sm = async_sessionmaker(test_engine, expire_on_commit=False)
    async with sm() as s:
        yield s


async def _upload(client, pid, filename, content, content_type="text/markdown"):
    r = await client.post(
        f"/api/v1/projects/{pid}/files",
        headers=csrf_headers(client),
        files={"file": (filename, content, content_type)},
    )
    assert r.status_code == 201, r.text
    return r.json()


# --------------------------- ts_rank_cd ranking ------------------------------


async def test_ts_rank_retrieval_matches_query(client, session, upload_root):
    await register_user(client)
    pid = await create_project(client)
    await _upload(
        client, pid, "infra.md",
        ("kubernetes deployment scaling pods and autoscaling policies. " * 20).encode(),
    )
    await _upload(
        client, pid, "food.md",
        ("banana smoothie recipe with yoghurt and honey. " * 20).encode(),
    )

    result = await file_service.retrieve_excerpts(
        session, uuid.UUID(pid), "kubernetes autoscaling", [], token_budget=4000
    )
    assert result.text, "expected a lexical match"
    assert "[File: infra.md | Chunk 1]" in result.text
    assert "food.md" not in result.text  # no lexical overlap
    assert result.included[0].filename == "infra.md"
    assert result.included[0].matched is True
    assert result.included[0].rank is not None


# ------------------------------ pinned / explicit ----------------------------


async def test_pinned_file_included_without_query(client, session, upload_root):
    await register_user(client)
    pid = await create_project(client)
    f = await _upload(client, pid, "pinned.md", b"important architecture note", "text/markdown")
    await client.patch(
        f"/api/v1/projects/{pid}/files/{f['id']}",
        headers=csrf_headers(client),
        json={"pinned": True},
    )
    # Empty query → pinned files still injected.
    result = await file_service.retrieve_excerpts(
        session, uuid.UUID(pid), "", [], token_budget=4000
    )
    assert "[File: pinned.md | Chunk 1]" in result.text
    assert result.included[0].pinned is True
    assert result.included[0].matched is False


async def test_include_file_ids_explicit_pin(client, session, upload_root):
    await register_user(client)
    pid = await create_project(client)
    f = await _upload(client, pid, "manual.md", b"explicitly attached for this turn", "text/markdown")
    result = await file_service.retrieve_excerpts(
        session, uuid.UUID(pid), "", [uuid.UUID(f["id"])], token_budget=4000
    )
    assert "manual.md" in result.text
    assert result.included[0].pinned is True


# ------------------------------ token budgeting ------------------------------


async def test_budget_trims_excess_chunks(client, session, upload_root):
    await register_user(client)
    pid = await create_project(client)
    f = await _upload(
        client, pid, "huge.txt",
        ("lorem ipsum dolor sit amet " * 800).encode(),
        "text/plain",
    )
    assert f["chunk_count"] >= 3
    await client.patch(
        f"/api/v1/projects/{pid}/files/{f['id']}",
        headers=csrf_headers(client),
        json={"pinned": True},
    )
    # A tight budget fits only the first chunk; the rest are reported as dropped.
    result = await file_service.retrieve_excerpts(
        session, uuid.UUID(pid), "", [], token_budget=800
    )
    assert len(result.included) == 1
    assert len(result.dropped) >= 1
    assert file_service.estimate_tokens(result.text) <= 800


async def test_zero_budget_returns_empty(client, session, upload_root):
    await register_user(client)
    pid = await create_project(client)
    f = await _upload(client, pid, "x.md", b"content here", "text/markdown")
    await client.patch(
        f"/api/v1/projects/{pid}/files/{f['id']}",
        headers=csrf_headers(client),
        json={"pinned": True},
    )
    result = await file_service.retrieve_excerpts(
        session, uuid.UUID(pid), "content", [], token_budget=0
    )
    assert result.text == ""
    assert result.included == []


# --------------------------- cross-project isolation -------------------------


async def test_retrieval_never_leaks_other_projects(client, session, upload_root):
    await register_user(client)
    pid_a = await create_project(client, name="Project A")
    pid_b = await create_project(client, name="Project B")
    await _upload(client, pid_a, "a_zebra.md", ("zebra crossing stripes " * 20).encode())
    fb = await _upload(client, pid_b, "b_zebra.md", ("zebra crossing stripes " * 20).encode())

    # Query project A, even explicitly passing project B's file id.
    result = await file_service.retrieve_excerpts(
        session, uuid.UUID(pid_a), "zebra", [uuid.UUID(fb["id"])], token_budget=8000
    )
    assert "a_zebra.md" in result.text
    assert "b_zebra.md" not in result.text
    assert all(e.filename == "a_zebra.md" for e in result.included)


# ----------------------- ContextBuilder (L5) integration ---------------------


async def test_context_preview_shows_l5_excerpts(client, upload_root):
    await register_user(client)
    pid = await create_project(client)
    cid = await create_conversation(client, pid)
    f = await _upload(
        client, pid, "design.md",
        ("the gateway uses token-bucket rate limiting at the edge. " * 15).encode(),
    )
    await client.patch(
        f"/api/v1/projects/{pid}/files/{f['id']}",
        headers=csrf_headers(client),
        json={"pinned": True},
    )

    r = await client.get(f"/api/v1/conversations/{cid}/context-preview")
    assert r.status_code == 200
    body = r.json()
    # L5 surfaced in the inspector payload...
    assert body["file_excerpts"], "expected pinned file excerpts in L5"
    assert body["file_excerpts"][0]["filename"] == "design.md"
    assert body["file_excerpts"][0]["pinned"] is True
    # ...recorded in the audited layers + per-layer token estimates...
    assert any(layer.startswith("file_excerpts:") for layer in body["included_layers"])
    assert any(k.startswith("file_excerpts:") for k in body["layer_tokens"])
    # ...and composed into the system prompt with the labeled boundary.
    assert "[File: design.md | Chunk 1]" in body["system_prompt"]


async def test_context_preview_query_matches_excerpts(client, upload_root):
    await register_user(client)
    pid = await create_project(client)
    cid = await create_conversation(client, pid)
    await _upload(
        client, pid, "api.md",
        ("the websocket endpoint negotiates a heartbeat interval. " * 15).encode(),
    )
    # No pin; the draft query drives lexical retrieval.
    r = await client.get(
        f"/api/v1/conversations/{cid}/context-preview",
        params={"q": "websocket heartbeat"},
    )
    assert r.status_code == 200
    body = r.json()
    assert any(e["matched"] for e in body["file_excerpts"])
    assert "[File: api.md | Chunk 1]" in body["system_prompt"]
