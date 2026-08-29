"""Queries against the users table."""

from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.auth.entities import User
from app.domains.auth.tables import UserRow


class UserRepository(Protocol):
    """Persistence for accounts."""

    async def create(self, session: AsyncSession, email: str, password_hash: str) -> User:
        """Insert an account, letting the unique index decide a race."""
        ...

    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
        """Find an account by address, or None."""
        ...

    async def get(self, session: AsyncSession, user_id: UUID) -> User | None:
        """Find an account by id, or None."""
        ...


def _to_entity(row: UserRow) -> User:
    """Map a row to the domain type."""
    return User(
        id=row.id,
        email=row.email,
        password_hash=row.password_hash,
        created_at=row.created_at,
    )


class SqlUserRepository:
    """The SQLite implementation of `UserRepository`."""

    async def create(self, session: AsyncSession, email: str, password_hash: str) -> User:
        """Insert an account.

        The flush is deliberate: it is what makes the unique index fire here
        rather than at commit, so the service can translate `IntegrityError`
        into EMAIL_ALREADY_REGISTERED while it still has context (CQ-092).
        """
        row = UserRow(email=email, password_hash=password_hash)
        session.add(row)
        await session.flush()
        return _to_entity(row)

    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
        """Find an account by address. The column collates case-insensitively."""
        statement = select(UserRow).where(UserRow.email == email)
        row = (await session.execute(statement)).scalar_one_or_none()
        return _to_entity(row) if row else None

    async def get(self, session: AsyncSession, user_id: UUID) -> User | None:
        """Find an account by id, for resolving a session token."""
        row = await session.get(UserRow, user_id)
        return _to_entity(row) if row else None
