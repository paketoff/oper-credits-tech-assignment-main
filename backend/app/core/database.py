"""The SQLite connection and nothing else: engine, sessions, pragmas (ARC-039).

This module knows no table and imports no domain — ARC-012 applies to it like
any other `core` module. Table definitions live in each domain's `tables.py` and
import `Base` from here, which is the direction the arrow is allowed to point.

It is also not `core.storage`. That owns the uploaded blobs, which live on the
filesystem and never in the database (ARC-010).
"""

from collections.abc import AsyncIterator
from sqlite3 import Connection as SQLiteConnection

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for every table in the application."""


def _apply_pragmas(connection: SQLiteConnection, _record: object) -> None:
    """Set the two pragmas SQLite does not default to (CQ-084).

    `foreign_keys=ON` because SQLite ignores foreign keys unless asked, which
    would make every FK in CQ-085 decorative. `journal_mode=WAL` because readers
    and writers otherwise block each other, which is the `database is locked`
    row in the DEP-025 failure table.

    WAL is persistent: it is a property of the database file, not of the
    connection, so setting it on every connect is idempotent.
    """
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def create_engine() -> AsyncEngine:
    """Build the async engine and attach the pragma listener.

    The listener goes on `sync_engine`: `connect` is emitted by the DBAPI
    underneath, and aiosqlite's connection is the synchronous one wrapped.
    """
    engine = create_async_engine(get_settings().database_url, future=True)
    event.listen(engine.sync_engine, "connect", _apply_pragmas)
    return engine


_engine: AsyncEngine = create_engine()

_session_factory = async_sessionmaker(
    _engine,
    class_=AsyncSession,
    # The service commits, then keeps using the entities it just wrote. With
    # expire_on_commit the attributes would be expired and reloaded lazily,
    # outside the repository — exactly what CQ-089 forbids.
    expire_on_commit=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield one session per request, and close it afterwards (CQ-083).

    The session is injected into the service and passed down to the repository.
    A repository never creates one, and never commits: the service owns the
    transaction boundary, which is what lets one upload write a document and
    move an application atomically (CQ-090, CQ-091).
    """
    async with _session_factory() as session:
        yield session


def background_session() -> AsyncSession:
    """A session for work that outlives the request that started it.

    `get_session` is a per-request dependency and its session is closed the
    moment the response is sent. A task scheduled to run *after* the commit —
    document classification, AI-018 — therefore cannot borrow it, and must own
    one it also closes. Same factory, same settings; only the lifetime differs.
    """
    return _session_factory()


async def create_all() -> None:
    """Create every table at startup. No Alembic (CQ-082).

    Migrations are a deliberate cut: one environment, one schema, no data to
    preserve. Adding them later is additive rather than a rewrite.
    """
    async with _engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
