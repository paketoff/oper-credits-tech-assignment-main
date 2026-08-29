"""SQLAlchemy definition of the users table."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserRow(Base):
    """One account.

    **The unique index on `email` is what makes signup correct**, not the lookup
    that precedes it. Two simultaneous signups with the same address both pass
    the check; the constraint decides which one wins, and the loser's
    `IntegrityError` becomes EMAIL_ALREADY_REGISTERED (CQ-092, AUTH-022).

    SQLite compares text case-sensitively by default, so the column is declared
    `COLLATE NOCASE` — DOM-019 requires the email to be unique
    case-insensitively, and normalising in Python alone would leave the database
    willing to store `Test@` beside `test@`.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320, collation="NOCASE"), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
