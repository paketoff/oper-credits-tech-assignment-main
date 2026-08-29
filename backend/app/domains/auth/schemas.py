"""Pydantic request and response models for the auth wire contract."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# AUTH-010. Minimum ten characters and nothing else. Composition rules reduce
# entropy in practice and annoy users; length is what matters.
_MIN_PASSWORD_LENGTH = 10


class SignupRequest(BaseModel):
    """Credentials, plus the simulation the borrower was just looking at."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    email: EmailStr
    password: str = Field(min_length=_MIN_PASSWORD_LENGTH)
    simulation_id: UUID | None = None


class LoginRequest(BaseModel):
    """Credentials."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """An account, as the frontend sees it.

    No `password_hash`. It is on the entity because `authenticate` compares
    against it, and it stops there (AUTH-011).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    email: str
    created_at: datetime


class SignupResponse(BaseModel):
    """The signup result.

    No `application_id`: signup claims a simulation and does not create an
    application. `2-architecture.md` §5.1 has the reasoning; the client calls
    `POST /api/applications` next.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    user: UserResponse
    claimed_simulation_id: UUID | None


class LoginResponse(BaseModel):
    """The login result."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    user: UserResponse
