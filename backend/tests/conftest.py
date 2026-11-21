"""Shared pytest fixtures: isolated test database + HTTP clients."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import models  # noqa: F401  (register all tables on Base.metadata)
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app

_DEV_URL = get_settings().database_url
_PREFIX, _, _DB_NAME = _DEV_URL.rpartition("/")
_TEST_DB = "omnidesk_test"
_TEST_URL = f"{_PREFIX}/{_TEST_DB}"
_ADMIN_URL = f"{_PREFIX}/postgres"

_db_ready = False


async def _ensure_test_db() -> None:
    """Create the test database (once) and ensure the schema exists."""
    global _db_ready
    if _db_ready:
        return
    admin = create_async_engine(_ADMIN_URL, isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :n"),
                {"n": _TEST_DB},
            )
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{_TEST_DB}"'))
    finally:
        await admin.dispose()

    engine = create_async_engine(_TEST_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    _db_ready = True


@pytest.fixture
async def test_engine():
    await _ensure_test_db()
    engine = create_async_engine(_TEST_URL)
    yield engine
    await engine.dispose()


@pytest.fixture
async def make_client(
    test_engine,
) -> AsyncGenerator[Callable[[], Awaitable[AsyncClient]], None]:
    sessionmaker = async_sessionmaker(test_engine, expire_on_commit=False)

    async def _override_get_db() -> AsyncGenerator:
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    created: list[AsyncClient] = []

    async def _make() -> AsyncClient:
        client = AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        )
        created.append(client)
        return client

    try:
        yield _make
    finally:
        for client in created:
            await client.aclose()
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
async def client(make_client) -> AsyncClient:
    return await make_client()
