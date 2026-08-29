"""Auth flow: signup, authenticate, resolve a user from a token."""

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthError
from app.domains.auth import security
from app.domains.auth.entities import User
from app.domains.auth.repository import UserRepository
from app.domains.auth.schemas import (
    LoginRequest,
    LoginResponse,
    SignupRequest,
    SignupResponse,
    UserResponse,
)
from app.domains.simulation.service import SimulationService


class AuthenticatedUser:
    """A user plus the token that proves it, on its way to the router.

    The token is not on `UserResponse` because it must never be rendered into a
    body: it lives in an httpOnly cookie and no JavaScript ever reads it
    (AUTH-001, AUTH-044). This carries it the one hop from service to the
    router helper that sets the cookie.
    """

    def __init__(self, body: SignupResponse | LoginResponse, token: str) -> None:
        """Pair a wire body with its session token."""
        self.body = body
        self.token = token


class AuthService:
    """Accounts and sessions."""

    def __init__(self, repository: UserRepository, simulations: SimulationService) -> None:
        """Take the repository as a protocol, and the one foreign service.

        `simulations` is the cross-domain edge ARC-017, injected rather than
        imported at module level so the dependency is visible in the signature.
        """
        self._repository = repository
        self._simulations = simulations

    async def signup(self, session: AsyncSession, payload: SignupRequest) -> AuthenticatedUser:
        """Register an account, claim a simulation, and log the borrower in.

        Signing up logs the user in: making someone log in immediately after
        registering is friction with no security benefit (AUTH-024).

        Raises:
            AuthError: EMAIL_ALREADY_REGISTERED, from the unique index rather
                than only from the lookup — two simultaneous signups both pass
                the check and the constraint decides (AUTH-022, CQ-092).
        """
        email = _normalise(payload.email)
        if await self._repository.get_by_email(session, email) is not None:
            raise AuthError(code="EMAIL_ALREADY_REGISTERED", field="email")
        try:
            user = await self._repository.create(
                session, email, security.hash_password(payload.password)
            )
        except IntegrityError as exc:
            await session.rollback()
            raise AuthError(code="EMAIL_ALREADY_REGISTERED", field="email") from exc

        claimed = await self._claim(session, payload.simulation_id, user.id)
        await session.commit()
        return AuthenticatedUser(
            SignupResponse(user=_to_response(user), claimed_simulation_id=claimed),
            security.encode_token(user.id),
        )

    async def login(self, session: AsyncSession, payload: LoginRequest) -> AuthenticatedUser:
        """Verify credentials and issue a session."""
        user = await self.authenticate(session, payload.email, payload.password)
        return AuthenticatedUser(
            LoginResponse(user=_to_response(user)), security.encode_token(user.id)
        )

    async def authenticate(self, session: AsyncSession, email: str, password: str) -> User:
        """Verify credentials in constant-ish time.

        **Hashes on every attempt, including when no user exists.** Otherwise
        the response time reveals whether an address is registered, and login
        stops being the half of the trade-off where secrecy wins (AUTH-026,
        AUTH-043).

        Raises:
            AuthError: INVALID_CREDENTIALS, identical for an unknown email and
                a wrong password (AUTH-025).
        """
        user = await self._repository.get_by_email(session, _normalise(email))
        if user is None:
            security.verify_against_nobody(password)
            raise AuthError(code="INVALID_CREDENTIALS")
        if not security.verify_password(password, user.password_hash):
            raise AuthError(code="INVALID_CREDENTIALS")
        return user

    async def user_from_token(self, session: AsyncSession, token: str) -> User:
        """Resolve the user a session cookie names.

        Raises:
            AuthError: NOT_AUTHENTICATED if the token is bad or its subject no
                longer exists.
        """
        user = await self._repository.get(session, security.decode_token(token))
        if user is None:
            raise AuthError(code="NOT_AUTHENTICATED")
        return user

    async def _claim(
        self, session: AsyncSession, simulation_id: UUID | None, user_id: UUID
    ) -> UUID | None:
        """Attach the anonymous simulation, if there is one to attach.

        Never raises. A missing, unknown or already-owned simulation is ignored
        silently: losing a free calculation must not cost a registration
        (AUTH-031, UX-028).
        """
        if simulation_id is None:
            return None
        return await self._simulations.claim_for_user(session, simulation_id, user_id)


def _normalise(email: str) -> str:
    """Lowercase and trim, before both the lookup and the insert (AUTH-023)."""
    return email.strip().lower()


def _to_response(user: User) -> UserResponse:
    """Map the entity to the wire type, dropping the hash."""
    return UserResponse(id=user.id, email=user.email, created_at=user.created_at)
