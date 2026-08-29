"""current_user: the auth domain's second public surface (ARC-042).

It lives here and not in `core/dependencies.py` because `current_user` resolves
through `AuthService`, and `core` may not import a domain (ARC-012). The
exception is narrow by design: this module may read the request and delegate to
`auth.service`, and nothing else. It never touches a repository.
"""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errors import AuthError
from app.core.rate_limit import RateLimiter
from app.domains.auth.entities import User
from app.domains.auth.repository import SqlUserRepository
from app.domains.auth.service import AuthService
from app.domains.simulation.dependencies import get_simulation_service

SESSION_COOKIE = "session"

# AUTH-040. In-memory and per process: it resets on restart and does not span
# machines, both of which are fine for one machine and both are in the README
# (AUTH-041).
_auth_limiter = RateLimiter()


def get_auth_service() -> AuthService:
    """Build the auth service with its repository and the one foreign service."""
    return AuthService(SqlUserRepository(), get_simulation_service())


async def current_user(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    """Resolve the authenticated user from the session cookie.

    Every protected route takes this and passes `user.id` into its service.
    There is no global auth middleware on purpose: an explicit dependency makes
    it visible in each signature which routes are protected (AUTH-038).

    Raises:
        AuthError: NOT_AUTHENTICATED when there is no cookie, or the token in
            it is expired, tampered with or unknown.
    """
    token = request.cookies.get(SESSION_COOKIE)
    if token is None:
        raise AuthError(code="NOT_AUTHENTICATED")
    return await service.user_from_token(session, token)


def rate_limit_auth(request: Request) -> None:
    """Throttle the two auth endpoints, per IP (AUTH-040).

    Not applied to the simulator: it is anonymous, cheap, and the whole point is
    that people use it freely (AUTH-042).
    """
    client = request.client.host if request.client else "unknown"
    _auth_limiter.check(client)
