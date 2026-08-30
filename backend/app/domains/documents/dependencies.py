"""Dependency providers for the documents domain."""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import BackgroundTasks, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.core.dependencies import get_storage
from app.core.enums import DocumentType
from app.domains.applications.dependencies import get_application_service
from app.domains.auth.dependencies import current_user
from app.domains.auth.entities import User
from app.domains.documents.classification.client import ClassificationClient
from app.domains.documents.classification.pipeline import ClassificationPipeline
from app.domains.documents.repository import SqlDocumentRepository
from app.domains.documents.service import DocumentService, UploadContext, UploadRequest


def _get_classifier() -> ClassificationPipeline | None:
    """Build the classifier, or None when the feature is off (AI-004, AI-024).

    Returning None rather than a disabled object is the point: with the flag
    off no client is constructed and `ANTHROPIC_API_KEY` is never read, so a
    revoked or absent key cannot degrade anything.
    """
    settings = get_settings()
    if not settings.ai_classification_enabled or not settings.anthropic_api_key:
        return None
    return ClassificationPipeline(
        ClassificationClient(settings.anthropic_api_key), SqlDocumentRepository()
    )


def get_document_service() -> DocumentService:
    """Build the service with its repository, storage, and the foreign service (ARC-018)."""
    return DocumentService(
        SqlDocumentRepository(), get_application_service(), get_storage(), _get_classifier()
    )


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
    background_tasks: BackgroundTasks


def get_document_context(
    background_tasks: BackgroundTasks,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[DocumentService, Depends(get_document_service)],
    user: Annotated[User, Depends(current_user)],
) -> DocumentContext:
    """Assemble the bundle FastAPI injects into each route."""
    return DocumentContext(
        session=session, service=service, user=user, background_tasks=background_tasks
    )


def get_upload_context(
    application_id: UUID,
    context: Annotated[DocumentContext, Depends(get_document_context)],
) -> UploadContext:
    """Bind the application in the path to the user and task queue of the request.

    Assembled here rather than in the handler: `CQ-018` forbids building an
    object field by field inside a route, and this is the "authorisation and
    input" column of `CQ-019`'s table — who is uploading, to what.
    """
    return UploadContext(
        application_id=application_id,
        user_id=context.user.id,
        background_tasks=context.background_tasks,
    )


async def get_upload_request(
    doc_type: Annotated[DocumentType, Form()],
    file: Annotated[UploadFile, File()],
) -> UploadRequest:
    """Read the multipart body into the service's own input type.

    `UploadFile` is a framework object and `UploadRequest` is the domain's;
    turning one into the other is input handling, which `CQ-019` puts in a
    dependency. Doing it in the handler cost that route three statements where
    the rule allows one.

    The size limit is enforced earlier still, by the body-size middleware,
    before this — or `UploadFile` itself — ever sees the bytes (`VAL-024`).
    """
    return UploadRequest(
        doc_type=doc_type,
        filename=file.filename or "upload",
        content=await file.read(),
    )
