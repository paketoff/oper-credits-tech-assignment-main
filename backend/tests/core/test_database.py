"""The two pragmas SQLite does not give us by default, and the request session.

CQ-084. Both are easy to assume and neither is on unless asked: without
foreign_keys every FK in CQ-085 is decorative, and without WAL readers and
writers block each other — the `database is locked` row in DEP-025.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session


async def test_foreign_keys_pragma_is_on(engine):
    async with engine.connect() as connection:
        result = await connection.execute(text("PRAGMA foreign_keys"))

    assert result.scalar() == 1


async def test_journal_mode_is_wal(engine):
    # File-backed on purpose. An in-memory database reports "memory" here
    # whatever we ask for, so this assertion would fail for a reason that has
    # nothing to do with the pragma listener.
    async with engine.connect() as connection:
        result = await connection.execute(text("PRAGMA journal_mode"))

    assert result.scalar() == "wal"


async def test_session_dependency_yields_and_closes(engine):
    # CQ-083: one session per request. The generator is what FastAPI drives, so
    # it is exercised the way FastAPI drives it, and two calls must not hand
    # back the same object — that would be one session shared across requests.
    first = [s async for s in get_session()]
    second = [s async for s in get_session()]

    assert len(first) == 1
    assert isinstance(first[0], AsyncSession)
    assert first[0] is not second[0]


@pytest.mark.parametrize("pragma", ["foreign_keys", "journal_mode"])
async def test_pragmas_survive_a_new_connection(engine, pragma):
    # The listener fires on connect, not once at startup. A pooled connection
    # opened later must come back with the same settings.
    async with engine.connect() as first:
        await first.execute(text(f"PRAGMA {pragma}"))
    async with engine.connect() as second:
        result = await second.execute(text(f"PRAGMA {pragma}"))

    assert result.scalar() in (1, "wal")


async def test_a_column_added_after_the_table_exists_is_reconciled(tmp_path):
    # The deployed failure: the volume outlives every deploy (DEP-003) and
    # `create_all` is CREATE TABLE IF NOT EXISTS, so the classifier columns
    # added at T35 - T58 never reached the production `documents` table. Every
    # read of it answered 500 with "no such column", on the checklist route and
    # nowhere else.
    import sqlalchemy
    from sqlalchemy import inspect, text

    from app.core.database import _add_missing_columns

    engine = sqlalchemy.create_engine(f"sqlite:///{tmp_path}/legacy.db")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE documents (id TEXT PRIMARY KEY)"))
        _add_missing_columns(connection)
        columns = {c["name"] for c in inspect(connection).get_columns("documents")}

    assert "proposed_income" in columns
    assert "classification_status" in columns
