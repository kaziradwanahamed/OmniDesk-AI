"""Phase 9 — project file upload, extraction, chunking, dedup, pin/rename,
delete (with disk cleanup), upload security, and IDOR (404) coverage."""

from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.services import file_service
from tests.helpers import create_project, csrf_headers, register_user


def minimal_pdf(text: str) -> bytes:
    """A byte-correct single-page PDF whose text layer extracts to ``text``."""
    content = (f"BT /F1 24 Tf 72 700 Td ({text}) Tj ET").encode()
    bodies = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R"
        b"/Resources<</Font<</F1 5 0 R>>>>>>",
        b"<</Length " + str(len(content)).encode() + b">>stream\n" + content + b"\nendstream",
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(bodies, 1):
        offsets.append(len(out))
        out += str(i).encode() + b" 0 obj" + body + b"\nendobj\n"
    xref_pos = len(out)
    n = len(bodies) + 1
    out += b"xref\n0 " + str(n).encode() + b"\n0000000000 65535 f \n"
    for off in offsets:
        out += ("%010d 00000 n \n" % off).encode()
    out += (
        b"trailer\n<</Root 1 0 R/Size " + str(n).encode() + b">>\nstartxref\n"
        + str(xref_pos).encode() + b"\n%%EOF"
    )
    return bytes(out)


async def _upload(client, pid, filename, content, content_type):
    return await client.post(
        f"/api/v1/projects/{pid}/files",
        headers=csrf_headers(client),
        files={"file": (filename, content, content_type)},
    )


# --------------------------------- happy path --------------------------------


async def test_upload_text_extracts_and_chunks(client, upload_root):
    await register_user(client)
    pid = await create_project(client)
    body = ("# Spec\n" + "The retrieval keyword is ziggurat. " * 50).encode()
    r = await _upload(client, pid, "spec.md", body, "text/markdown")
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["filename"] == "spec.md"
    assert data["extension"] == ".md"
    assert data["extraction_status"] == "extracted"
    assert data["chunk_count"] >= 1
    assert data["pinned"] is False
    assert data["deduplicated"] is False
    # One file actually written to disk (under a UUID key, not the user name).
    files_on_disk = list(upload_root.iterdir())
    assert len(files_on_disk) == 1
    assert files_on_disk[0].name != "spec.md"

    # Chunk inspection endpoint returns stored excerpts.
    rc = await client.get(
        f"/api/v1/projects/{pid}/files/{data['id']}/chunks",
        headers=csrf_headers(client),
    )
    assert rc.status_code == 200
    chunks = rc.json()
    assert len(chunks) == data["chunk_count"]
    assert chunks[0]["token_est"] > 0
    assert "ziggurat" in chunks[0]["content"]


async def test_upload_large_text_produces_overlapping_chunks(client, upload_root):
    await register_user(client)
    pid = await create_project(client)
    # ~12k chars forces several chunks with overlap.
    body = ("alpha beta gamma delta epsilon " * 500).encode()
    r = await _upload(client, pid, "big.txt", body, "text/plain")
    assert r.status_code == 201
    fid = r.json()["id"]
    assert r.json()["chunk_count"] >= 2

    rc = await client.get(
        f"/api/v1/projects/{pid}/files/{fid}/chunks", headers=csrf_headers(client)
    )
    chunks = rc.json()
    # Consecutive chunks overlap: chunk[1] starts before chunk[0] ends.
    assert chunks[1]["char_start"] < chunks[0]["char_end"]
    # Line offsets are recorded for text files.
    assert chunks[0]["start_line"] is not None


async def test_upload_pdf_extracts_text(client, upload_root):
    await register_user(client)
    pid = await create_project(client)
    r = await _upload(
        client, pid, "paper.pdf", minimal_pdf("AlphaBravo retrieval keyword"),
        "application/pdf",
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["extraction_status"] == "extracted"
    assert data["chunk_count"] >= 1
    rc = await client.get(
        f"/api/v1/projects/{pid}/files/{data['id']}/chunks", headers=csrf_headers(client)
    )
    chunks = rc.json()
    assert "keyword" in chunks[0]["content"]
    assert chunks[0]["page_start"] == 1  # page offsets for PDFs


async def test_empty_file_handled_gracefully(client, upload_root):
    await register_user(client)
    pid = await create_project(client)
    r = await _upload(client, pid, "empty.txt", b"", "text/plain")
    assert r.status_code == 201
    assert r.json()["extraction_status"] == "empty"
    assert r.json()["chunk_count"] == 0


# ------------------------------ dedup / pin / delete -------------------------


async def test_sha256_dedup_per_project(client, upload_root):
    await register_user(client)
    pid = await create_project(client)
    body = b"identical bytes for dedup test"
    r1 = await _upload(client, pid, "a.txt", body, "text/plain")
    r2 = await _upload(client, pid, "b.txt", body, "text/plain")
    assert r1.status_code == 201 and r2.status_code == 201
    assert r2.json()["deduplicated"] is True
    assert r1.json()["id"] == r2.json()["id"]
    # Only one row and one disk file despite two uploads.
    lst = await client.get(f"/api/v1/projects/{pid}/files", headers=csrf_headers(client))
    assert len(lst.json()) == 1
    assert len(list(upload_root.iterdir())) == 1


async def test_pin_and_rename(client, upload_root):
    await register_user(client)
    pid = await create_project(client)
    fid = (await _upload(client, pid, "doc.md", b"hello world", "text/markdown")).json()["id"]
    r = await client.patch(
        f"/api/v1/projects/{pid}/files/{fid}",
        headers=csrf_headers(client),
        json={"pinned": True, "filename": "renamed.md"},
    )
    assert r.status_code == 200
    assert r.json()["pinned"] is True
    assert r.json()["filename"] == "renamed.md"


async def test_delete_removes_db_row_and_disk_file(client, upload_root):
    await register_user(client)
    pid = await create_project(client)
    fid = (await _upload(client, pid, "gone.txt", b"to be deleted", "text/plain")).json()["id"]
    assert len(list(upload_root.iterdir())) == 1

    d = await client.delete(
        f"/api/v1/projects/{pid}/files/{fid}", headers=csrf_headers(client)
    )
    assert d.status_code == 204
    # DB row gone (404) and disk cleaned up.
    g = await client.get(
        f"/api/v1/projects/{pid}/files/{fid}", headers=csrf_headers(client)
    )
    assert g.status_code == 404
    assert len(list(upload_root.iterdir())) == 0


# ------------------------------- upload security -----------------------------


async def test_reject_disallowed_extension(client, upload_root):
    await register_user(client)
    pid = await create_project(client)
    r = await _upload(client, pid, "evil.exe", b"MZ\x00binary", "application/octet-stream")
    assert r.status_code == 400
    assert "Unsupported file type" in r.json()["detail"]


async def test_reject_disallowed_mime(client, upload_root):
    await register_user(client)
    pid = await create_project(client)
    r = await _upload(client, pid, "pic.md", b"# looks like md", "image/png")
    assert r.status_code == 400
    assert "content type" in r.json()["detail"].lower()


async def test_reject_non_utf8_text(client, upload_root):
    await register_user(client)
    pid = await create_project(client)
    r = await _upload(client, pid, "bad.txt", b"\xff\xfe\x00\x01rubbish", "text/plain")
    assert r.status_code == 400
    assert "UTF-8" in r.json()["detail"]


async def test_reject_fake_pdf(client, upload_root):
    await register_user(client)
    pid = await create_project(client)
    r = await _upload(client, pid, "fake.pdf", b"not really a pdf", "application/pdf")
    assert r.status_code == 400


async def test_reject_oversize(client, upload_root, monkeypatch):
    await register_user(client)
    pid = await create_project(client)
    monkeypatch.setattr(get_settings(), "max_upload_bytes", 50)
    r = await _upload(client, pid, "big.txt", b"x" * 500, "text/plain")
    assert r.status_code == 413
    assert "too large" in r.json()["detail"].lower()


async def test_path_traversal_filename_is_contained(client, upload_root):
    await register_user(client)
    pid = await create_project(client)
    r = await _upload(
        client, pid, "../../../../etc/passwd.md", b"root:x:0:0", "text/markdown"
    )
    assert r.status_code == 201
    # Display name sanitized to a basename; nothing written outside the root.
    assert r.json()["filename"] == "passwd.md"
    on_disk = list(upload_root.rglob("*"))
    assert all(upload_root.resolve() in p.resolve().parents for p in on_disk)
    assert not any(p.name == "passwd.md" for p in on_disk)  # stored under a UUID key


def test_sanitize_filename_unit():
    assert file_service.sanitize_filename("../../etc/passwd") == "passwd"
    assert file_service.sanitize_filename("a/b/c.txt") == "c.txt"
    assert file_service.sanitize_filename("  ") == "upload"
    assert file_service.sanitize_filename("x\x00y.md") == "xy.md"


# ----------------------------------- IDOR 404 --------------------------------


async def test_idor_file_endpoints_return_404(make_client, upload_root):
    owner = await make_client()
    attacker = await make_client()
    await register_user(owner)
    await register_user(attacker)
    pid = await create_project(owner)
    fid = (await _upload(owner, pid, "secret.md", b"top secret", "text/markdown")).json()["id"]

    # List + upload on someone else's project → 404 (project ownership).
    assert (await attacker.get(
        f"/api/v1/projects/{pid}/files", headers=csrf_headers(attacker)
    )).status_code == 404
    assert (await _upload(attacker, pid, "x.md", b"hi", "text/markdown")).status_code == 404

    # Get / patch / delete a specific file → 404 (attachment ownership).
    assert (await attacker.get(
        f"/api/v1/projects/{pid}/files/{fid}", headers=csrf_headers(attacker)
    )).status_code == 404
    assert (await attacker.patch(
        f"/api/v1/projects/{pid}/files/{fid}",
        headers=csrf_headers(attacker),
        json={"pinned": True},
    )).status_code == 404
    assert (await attacker.delete(
        f"/api/v1/projects/{pid}/files/{fid}", headers=csrf_headers(attacker)
    )).status_code == 404

    # The owner's file is untouched.
    assert (await owner.get(
        f"/api/v1/projects/{pid}/files/{fid}", headers=csrf_headers(owner)
    )).json()["pinned"] is False
