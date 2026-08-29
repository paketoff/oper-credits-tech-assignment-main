"""HTTP routes for auth; one service call per handler (CQ-017)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.domains.auth.dependencies import (
    SESSION_COOKIE,
    current_user,
    get_auth_service,
    rate_limit_auth,
)
from app.domains.auth.entities import User
from app.domains.auth.schemas import LoginRequest, SignupRequest, UserResponse
from app.domains.auth.security import TOKEN_LIFETIME
from app.domains.auth.service import AuthenticatedUser, AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _with_session_cookie(result: AuthenticatedUser, status_code: int) -> JSONResponse:
    """Render an auth result and attach the session cookie (AUTH-018).

    Response wiring, not logic: the handler still makes exactly one service call
    (CQ-017) and the service still holds no HTTP concept (ARC-005). The token
    goes in an httpOnly cookie and never into the body, so no code path can read
    it from JavaScript (AUTH-044).
    """
    response = JSONResponse(status_code=status_code, content=result.body.model_dump(mode="json"))
    response.set_cookie(
        key=SESSION_COOKIE,
        value=result.token,
        httponly=True,
        # AUTH-019: only ever false in development, where there is no TLS to
        # be secure over. force_https in fly.toml is what makes it true hold.
        secure=not get_settings().is_development,
        # AUTH-004: stops the cookie being sent on a cross-site state change,
        # which covers every such request in a single-origin application and is
        # why a CSRF token here would be ceremony (AUTH-005).
        samesite="lax",
        max_age=int(TOKEN_LIFETIME.total_seconds()),
        path="/",
    )
    return response


@router.post("/signup", dependencies=[Depends(rate_limit_auth)])
async def signup(
    payload: SignupRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> JSONResponse:
    """Register an account, claim a simulation, and log the borrower in."""
    return _with_session_cookie(await service.signup(session, payload), status.HTTP_201_CREATED)


@router.post("/login", dependencies=[Depends(rate_limit_auth)])
async def login(
    payload: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> JSONResponse:
    """Exchange credentials for a session."""
    return _with_session_cookie(await service.login(session, payload), status.HTTP_200_OK)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    """Clear the session cookie.

    Succeeds whether or not a session existed (AUTH-028), which is why it is on
    the public route list. There is no server-side denylist, so a stolen token
    stays valid until it expires — stated in the README rather than glossed
    over (AUTH-020).
    """
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=UserResponse)
def me(user: Annotated[User, Depends(current_user)]) -> User:
    """Return the current user.

    The frontend calls this on boot because it cannot read the httpOnly cookie
    itself (AUTH-029, AUTH-046).
    """
    return user
