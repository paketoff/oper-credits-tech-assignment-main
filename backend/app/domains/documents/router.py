"""HTTP routes for documents; one service call per handler (CQ-017).

`GET /api/applications/{id}/checklist` lives here rather than in
`applications/router.py`. Only `documents` may query the documents table
(ARC-009), and the checklist reads one application's profile *and* its
documents — `applications` owning the route would need the arrow to point
both ways, which `2-architecture.md` §5.1 explains is the boundary this domain
split exists to avoid.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response

from app.core.enums import DocumentType
from app.domains.documents.dependencies import DocumentContext, get_document_context
from app.domains.documents.schemas import (
    ChecklistResponse,
    DocumentDeleteResponse,
    DocumentResponse,
)
from app.domains.documents.service import UploadRequest

router = APIRouter(prefix="/applications", tags=["documents"])

_Context = Annotated[DocumentContext, Depends(get_document_context)]


@router.get("/{application_id}/checklist", response_model=ChecklistResponse)
async def get_checklist(application_id: UUID, context: _Context) -> ChecklistResponse:
    """Read the derived checklist for one application (API-045)."""
    return await context.service.checklist(context.session, application_id, context.user.id)


@router.post("/{application_id}/documents", response_model=DocumentResponse, status_code=201)
async def upload_document(
    application_id: UUID,
    context: _Context,
    doc_type: Annotated[DocumentType, Form()],
    file: Annotated[UploadFile, File()],
) -> DocumentResponse:
    """Upload one file against a checklist requirement (API-048).

    The size limit is enforced earlier, by the body-size middleware, before
    this handler — or `UploadFile` itself — ever sees the bytes (VAL-024).
    """
    content = await file.read()
    upload = UploadRequest(
        doc_type=doc_type, filename=file.filename or "upload", content=content
    )
    return await context.service.upload(context.session, application_id, context.user.id, upload)


@router.get("/{application_id}/documents/{document_id}")
async def download_document(
    application_id: UUID, document_id: UUID, context: _Context
) -> Response:
    """Return a document's bytes as an attachment, never as a static file (API-054)."""
    content, document = await context.service.download(
        context.session, application_id, context.user.id, document_id
    )
    return Response(
        content=content,
        media_type=document.content_type,
        headers={"Content-Disposition": f'attachment; filename="{document.filename}"'},
    )


@router.delete("/{application_id}/documents/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    application_id: UUID, document_id: UUID, context: _Context
) -> DocumentDeleteResponse:
    """Remove a document (API-055). Moving the application backwards is normal (API-056)."""
    return await context.service.delete(
        context.session, application_id, context.user.id, document_id
    )
