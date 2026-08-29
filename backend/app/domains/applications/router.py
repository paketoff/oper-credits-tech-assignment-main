"""HTTP routes for applications; one service call per handler (CQ-017)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.domains.applications.dependencies import ApplicationContext, get_application_context
from app.domains.applications.schemas import (
    ApplicationCreateRequest,
    ApplicationListResponse,
    ApplicationPatchRequest,
    ApplicationResponse,
)

router = APIRouter(prefix="/applications", tags=["applications"])

_Context = Annotated[ApplicationContext, Depends(get_application_context)]


@router.get("", response_model=ApplicationListResponse)
async def list_applications(context: _Context) -> ApplicationListResponse:
    """The borrower's own applications, and nobody else's (API-029, AUTH-034)."""
    return await context.service.list_for_user(context.session, context.user.id, {})


@router.post("", response_model=ApplicationResponse, status_code=201)
async def create_application(
    payload: ApplicationCreateRequest, context: _Context
) -> ApplicationResponse:
    """Create a draft, seeded from a simulation when one is given (API-032)."""
    return await context.service.create(context.session, context.user.id, payload)


@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(application_id: UUID, context: _Context) -> ApplicationResponse:
    """Fetch one application. 404, not 403, for someone else's (API-034, AUTH-035)."""
    return await context.service.get(context.session, application_id, context.user.id)


@router.patch("/{application_id}", response_model=ApplicationResponse)
async def patch_application(
    application_id: UUID, payload: ApplicationPatchRequest, context: _Context
) -> ApplicationResponse:
    """Apply a partial update from a wizard step (API-035)."""
    return await context.service.patch(context.session, application_id, context.user.id, payload)


@router.post("/{application_id}/submit", response_model=ApplicationResponse)
async def submit_application(application_id: UUID, context: _Context) -> ApplicationResponse:
    """Validate and transition DRAFT -> DOCUMENTS_PENDING (API-041, APP-001)."""
    return await context.service.submit(context.session, application_id, context.user.id)
