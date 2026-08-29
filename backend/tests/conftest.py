"""Shared fixtures. The one file units A, B and D all need (T44).

**Environment before imports, and that ordering is load-bearing.** `Settings`
reads the environment when it is constructed and `core.database` builds its
engine at import time, so anything that imports `app.` before these variables
exist gets the production defaults — a database under `/data` that the test
process cannot write. Nothing below this block may be moved above it.

`JWT_SECRET` is set here rather than defaulted in `Settings` because AUTH-017
is explicit: a default secret in code is worse than no auth, since it looks
like auth. Tests supply their own.
"""

import os
import tempfile
from pathlib import Path

_TMP_DATA_DIR = Path(tempfile.mkdtemp(prefix="borrower-portal-tests-"))
os.environ.setdefault("DATA_DIR", str(_TMP_DATA_DIR))
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production-0123456789")
os.environ.setdefault("ENVIRONMENT", "development")

from collections.abc import AsyncIterator  # noqa: E402

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.database import Base, _engine, _session_factory, create_all  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Clear the per-IP auth limiter between tests.

    It is process-wide and in-memory by design (AUTH-041), which means it also
    persists across tests in the same file unless something clears it: several
    tests signing up from the same client would otherwise share one budget of
    ten attempts and start failing with 429 partway through the suite.
    """
    from app.domains.auth.dependencies import _auth_limiter

    _auth_limiter._attempts.clear()
    yield
    _auth_limiter._attempts.clear()


@pytest.fixture(scope="session")
def settings():
    """The settings the whole test session runs against."""
    return get_settings()


@pytest.fixture
async def engine():
    """The application engine, with its schema created.

    File-backed, not in-memory: `journal_mode=WAL` is a property of a database
    *file*, and an in-memory database reports `memory` however it is asked.
    Testing the pragmas against `:memory:` would assert something that can never
    be true.
    """
    await create_all()
    yield _engine


@pytest.fixture
async def session(engine) -> AsyncIterator[AsyncSession]:
    """One session, rolled back afterwards so tests do not leak rows into each other."""
    async with _session_factory() as active:
        yield active
        await active.rollback()


@pytest.fixture(autouse=True)
async def _isolate(engine):
    """Empty every table after each test.

    The API tests commit — they go through the real service, which owns the
    transaction boundary (CQ-091) — so a rollback-per-test would not undo them.
    Without this, one test's user is another test's duplicate email, and the
    suite passes or fails depending on the order pytest happens to collect in.
    """
    yield
    async with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            await connection.execute(table.delete())


@pytest.fixture
async def clean_database(engine):
    """Drop and recreate every table, for a test that needs an empty database."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    return engine


@pytest.fixture
def blob_dir(settings) -> Path:
    """The blob root, created. Beside the database, never inside it (ARC-010)."""
    settings.blob_dir.mkdir(parents=True, exist_ok=True)
    return settings.blob_dir


@pytest.fixture
def app(engine):
    """The FastAPI application.

    `get_session` is not overridden: the engine already points at the temporary
    DATA_DIR set above, so the application under test uses the same real
    dependency wiring it uses in production. An override here would mean the
    tests exercise a graph the deployed app never builds.
    """
    return fastapi_app


@pytest.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    """An async HTTP client speaking to the app in-process, with no network."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
