"""Liveness and readiness probes, called like any service (DEP-015)."""

from pydantic import BaseModel, ConfigDict


class LivenessResponse(BaseModel):
    """The answer to a liveness probe."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: str


class HealthService:
    """Reports whether the process is alive, and later whether its stores are usable.

    Liveness deliberately touches nothing. A probe that fails while the database
    is merely busy makes the platform restart a machine that was working, which
    is why DEP-036 separates it from readiness rather than folding both into one
    endpoint.

    Readiness arrives with `core/database.py` at T13; it is the half that is
    allowed to do IO.
    """

    def liveness(self) -> LivenessResponse:
        """Report that the process is running and serving."""
        return LivenessResponse(status="ok")
