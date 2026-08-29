"""Domain types for users."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class User:
    """An account.

    No real personal data lives in this system; the email is test data
    (DOM-020). The hash never leaves the auth domain — it is on the entity
    because `authenticate` compares against it, and it is absent from every
    schema in `schemas.py`.
    """

    id: UUID
    email: str
    password_hash: str
    created_at: datetime
