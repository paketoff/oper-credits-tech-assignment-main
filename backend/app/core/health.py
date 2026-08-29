"""Liveness and readiness probes, called like any service (DEP-015)."""

from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import LocalStorage


class LivenessResponse(BaseModel):
    """The answer to a liveness probe."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: str


class ReadinessResponse(BaseModel):
    """The answer to a readiness probe when both stores are usable."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: str


class NotReady(Exception):
    """A store the application depends on is unusable.

    Not a `DomainError`: `/ready` sits outside the `{code, message, field}`
    contract because it sits outside `/api`, and its reader is a health checker
    rather than a client (API-069). It gets its own handler, which answers
    `{"status": "unavailable"}` with 503.
    """


class HealthService:
    """Reports whether the process is alive, and whether its stores are usable.

    The two probes are deliberately different. Liveness touches nothing: a probe
    that fails while the database is merely busy makes the platform restart a
    machine that was working (DEP-036). Readiness touches both stores, because
    an instance that cannot reach them should not receive traffic.
    """

    def liveness(self) -> LivenessResponse:
        """Report that the process is running and serving."""
        return LivenessResponse(status="ok")

    async def readiness(self, session: AsyncSession, storage: LocalStorage) -> ReadinessResponse:
        """Check both stores and report readiness.

        The two checks cover the two stores ARC-010 keeps deliberately separate:
        `core.database` holds the rows and `core.storage` holds the blobs, and
        an instance with one of them missing serves broken requests rather than
        no requests.

        Args:
            session: A live database session.
            storage: The blob backend.

        Returns:
            Readiness, when both stores answer.

        Raises:
            NotReady: If either store is unusable. Rendered as 503 by the
                handler registered in `core/exception_handlers.py`, so this
                method holds no HTTP concept of its own (ARC-005).
        """
        try:
            await session.execute(text("SELECT 1"))
        except Exception as exc:
            raise NotReady("database unreachable") from exc
        if not storage.is_writable():
            raise NotReady("blob directory is not writable")
        return ReadinessResponse(status="ready")
