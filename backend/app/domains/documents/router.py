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
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.domains.auth.dependencies import current_user
from app.domains.auth.entities import User
from app.domains.documents.dependencies import get_document_service
from app.domains.documents.schemas import ChecklistResponse
from app.domains.documents.service import DocumentService

router = APIRouter(prefix="/applications", tags=["documents"])


@router.get("/{application_id}/checklist", response_model=ChecklistResponse)
async def get_checklist(
    application_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[DocumentService, Depends(get_document_service)],
    user: Annotated[User, Depends(current_user)],
) -> ChecklistResponse:
    """Read the derived checklist for one application (API-045)."""
    return await service.checklist(session, application_id, user.id)
