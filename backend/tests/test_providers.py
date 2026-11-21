"""Provider config endpoints: masked keys, encryption, test connection, IDOR."""

from __future__ import annotations

from httpx import AsyncClient

from tests.fakes import FakeOpenAI, auth_error, patch_client
from tests.helpers import csrf_headers, register_user


async def test_set_key_is_masked_and_never_returns_raw(client: AsyncClient) -> None:
    await register_user(client)
    h = csrf_headers(client)
    resp = await client.put(
        "/api/v1/providers/openai/key", headers=h, json={"api_key": "sk-SECRETKEY1234"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["configured"] is True
    assert body["key_hint"] == "1234"
    assert "api_key" not in body
    assert "sk-SECRETKEY1234" not in resp.text  # raw key never returned

    listed = await client.get("/api/v1/providers")
    openai_cfg = next(c for c in listed.json() if c["provider"] == "openai")
    assert openai_cfg["configured"] is True
    assert openai_cfg["key_hint"] == "1234"


async def test_delete_key(client: AsyncClient) -> None:
    await register_user(client)
    h = csrf_headers(client)
    await client.put(
        "/api/v1/providers/openai/key", headers=h, json={"api_key": "sk-abcd1234efgh"}
    )
    resp = await client.delete("/api/v1/providers/openai/key", headers=h)
    assert resp.status_code == 200
    assert resp.json()["configured"] is False
    assert resp.json()["key_hint"] is None


async def test_test_connection_lists_models(client: AsyncClient, monkeypatch) -> None:
    patch_client(monkeypatch, FakeOpenAI(models=["gpt-test", "gpt-test-mini"]))
    await register_user(client)
    h = csrf_headers(client)
    await client.put(
        "/api/v1/providers/openai/key", headers=h, json={"api_key": "sk-abcd1234efgh"}
    )
    resp = await client.post("/api/v1/providers/openai/test", headers=h)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert "gpt-test" in resp.json()["models"]


async def test_test_connection_invalid_key(client: AsyncClient, monkeypatch) -> None:
    patch_client(monkeypatch, FakeOpenAI(models_error=auth_error()))
    await register_user(client)
    h = csrf_headers(client)
    await client.put(
        "/api/v1/providers/openai/key", headers=h, json={"api_key": "sk-abcd1234efgh"}
    )
    resp = await client.post("/api/v1/providers/openai/test", headers=h)
    assert resp.status_code == 200
    assert resp.json()["ok"] is False
    assert resp.json()["category"] == "AUTH_INVALID_KEY"


async def test_set_enabled_models_dedupes(client: AsyncClient) -> None:
    await register_user(client)
    h = csrf_headers(client)
    await client.put(
        "/api/v1/providers/openai/key", headers=h, json={"api_key": "sk-abcd1234efgh"}
    )
    resp = await client.put(
        "/api/v1/providers/openai/models",
        headers=h,
        json={"enabled_models": ["gpt-test", "gpt-test", "gpt-test-mini"]},
    )
    assert resp.status_code == 200
    assert resp.json()["enabled_models"] == ["gpt-test", "gpt-test-mini"]


async def test_set_key_requires_csrf(client: AsyncClient) -> None:
    await register_user(client)
    resp = await client.put(
        "/api/v1/providers/openai/key", json={"api_key": "sk-abcd1234efgh"}
    )
    assert resp.status_code == 403


async def test_unsupported_provider_rejected(client: AsyncClient) -> None:
    await register_user(client)
    h = csrf_headers(client)
    resp = await client.put(
        "/api/v1/providers/cohere/key", headers=h, json={"api_key": "co-whatever-123"}
    )
    assert resp.status_code == 404


async def test_provider_config_idor(make_client) -> None:
    a = await make_client()
    await register_user(a)
    await a.put(
        "/api/v1/providers/openai/key",
        headers=csrf_headers(a),
        json={"api_key": "sk-AAAAAAAA1111"},
    )

    b = await make_client()
    await register_user(b)
    b_list = (await b.get("/api/v1/providers")).json()
    openai_b = next(c for c in b_list if c["provider"] == "openai")
    # B never sees A's configured key.
    assert openai_b["configured"] is False
    assert openai_b["key_hint"] is None

    a_list = (await a.get("/api/v1/providers")).json()
    assert next(c for c in a_list if c["provider"] == "openai")["configured"] is True
