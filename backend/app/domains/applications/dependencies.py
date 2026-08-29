"""Dependency providers for the applications domain."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.domains.applications.repository import SqlApplicationRepository
from app.domains.applications.service import ApplicationService
from app.domains.auth.dependencies import current_user
from app.domains.auth.entities import User
from app.domains.simulation.dependencies import get_simulation_service


def get_application_service() -> ApplicationService:
    """Build the service with its repository and the one foreign service (ARC-047)."""
    return ApplicationService(SqlApplicationRepository(), get_simulation_service())


@dataclass(frozen=True, slots=True)
class ApplicationContext:
    """The three things every application route needs, bundled into one.

    Every protected handler here takes a path parameter, sometimes a body, and
    these three. Left as separate parameters, a route with both a path
    parameter and a body crosses CQ-038's four-parameter limit — this exists to
    keep the handler under that limit without loosening the rule.
    """

    session: AsyncSession
    service: ApplicationService
    user: User


def get_application_context(
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[ApplicationService, Depends(get_application_service)],
    user: Annotated[User, Depends(current_user)],
) -> ApplicationContext:
    """Assemble the bundle FastAPI injects into each route."""
    return ApplicationContext(session=session, service=service, user=user)
