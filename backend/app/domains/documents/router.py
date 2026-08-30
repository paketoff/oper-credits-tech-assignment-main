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

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.domains.applications.schemas import ApplicationListResponse
from app.domains.documents.dependencies import (
    DocumentContext,
    get_document_context,
    get_upload_context,
    get_upload_request,
)
from app.domains.documents.entities import Document
from app.domains.documents.schemas import (
    ChecklistResponse,
    DocumentDeleteResponse,
    DocumentResponse,
)
from app.domains.documents.service import UploadContext, UploadRequest

router = APIRouter(prefix="/applications", tags=["documents"])

_Context = Annotated[DocumentContext, Depends(get_document_context)]
_Upload = Annotated[UploadRequest, Depends(get_upload_request)]
_UploadContext = Annotated[UploadContext, Depends(get_upload_context)]


def _attachment(content: bytes, document: Document) -> Response:
    """Render stored bytes as a download (API-054).

    Response wiring, not logic — the same carve-out `auth/router.py` makes for
    the session cookie. The handler still makes exactly one service call
    (CQ-017), and the service still holds no HTTP concept of its own (ARC-005):
    it returns bytes and a row, and this decides what an HTTP download is.

    `Content-Disposition: attachment` is not decoration. The bytes are
    borrower-supplied, and rendering an uploaded file inline is how a stored
    HTML or SVG payload executes on the application's own origin.
    """
    return Response(
        content=content,
        media_type=document.content_type,
        headers={"Content-Disposition": f'attachment; filename="{document.filename}"'},
    )


@router.get("", response_model=ApplicationListResponse)
async def list_applications(context: _Context) -> ApplicationListResponse:
    """The borrower's own applications, and nobody else's (API-029, AUTH-034).

    In this router because the summary counts documents; see
    `DocumentService.list_applications`.
    """
    return await context.service.list_applications(context.session, context.user.id)


@router.get("/{application_id}/checklist", response_model=ChecklistResponse)
async def get_checklist(application_id: UUID, context: _Context) -> ChecklistResponse:
    """Read the derived checklist for one application (API-045)."""
    return await context.service.checklist(context.session, application_id, context.user.id)


@router.post("/{application_id}/documents", response_model=DocumentResponse, status_code=201)
async def upload_document(
    context: _Context, upload_context: _UploadContext, upload: _Upload
) -> DocumentResponse:
    """Upload one file against a checklist requirement (API-048)."""
    return await context.service.upload(context.session, upload_context, upload)


@router.get("/{application_id}/documents/{document_id}")
async def download_document(
    application_id: UUID, document_id: UUID, context: _Context
) -> Response:
    """Return a document's bytes as an attachment, never as a static file (API-054)."""
    return _attachment(
        *await context.service.download(
            context.session, application_id, context.user.id, document_id
        )
    )


@router.delete("/{application_id}/documents/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    application_id: UUID, document_id: UUID, context: _Context
) -> DocumentDeleteResponse:
    """Remove a document (API-055). Moving the application backwards is normal (API-056)."""
    return await context.service.delete(
        context.session, application_id, context.user.id, document_id
    )
