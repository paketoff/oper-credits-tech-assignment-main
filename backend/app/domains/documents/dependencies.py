"""Dependency providers for the documents domain."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import get_storage
from app.domains.applications.dependencies import get_application_service
from app.domains.auth.dependencies import current_user
from app.domains.auth.entities import User
from app.domains.documents.repository import SqlDocumentRepository
from app.domains.documents.service import DocumentService


def get_document_service() -> DocumentService:
    """Build the service with its repository, storage, and the foreign service (ARC-018)."""
    return DocumentService(SqlDocumentRepository(), get_application_service(), get_storage())


@dataclass(frozen=True, slots=True)
class DocumentContext:
    """The three things every document route needs, bundled into one.

    Same reasoning as `applications.dependencies.ApplicationContext`: a route
    with a path parameter and a body already has two of CQ-038's four slots
    spoken for, and the document routes need three collaborators besides.
    """

    session: AsyncSession
    service: DocumentService
    user: User


def get_document_context(
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[DocumentService, Depends(get_document_service)],
    user: Annotated[User, Depends(current_user)],
) -> DocumentContext:
    """Assemble the bundle FastAPI injects into each route."""
    return DocumentContext(session=session, service=service, user=user)
