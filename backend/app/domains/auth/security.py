"""argon2id hashing and JWT encode/decode. No IO, no session.

Every choice here is one that gets asked about, so each carries its reason.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings
from app.core.errors import AuthError

_hasher = PasswordHasher()

_ALGORITHM = "HS256"
_ISSUER = "borrower-portal"
TOKEN_LIFETIME = timedelta(hours=24)

# AUTH-027. Computed once at import, against a throwaway string. Verifying a
# password for an email that does not exist has to cost the same as verifying a
# real one, or the response time answers "is this address registered?" for
# anyone who asks (AUTH-026).
_DUMMY_HASH = _hasher.hash("a-password-no-account-will-ever-have")


def hash_password(plain: str) -> str:
    """Hash a password with argon2id.

    Never sha256, never md5, never plaintext — not even with obviously fake
    test data. This is fintech and it is the first thing anyone looks at
    (AUTH-006, AUTH-007).
    """
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Check a password against its hash.

    Returns False on mismatch rather than raising, so callers do not have to
    distinguish a wrong password from an error (AUTH-009).

    `VerificationError` covers `VerifyMismatchError`, which is the ordinary
    wrong-password case; `InvalidHashError` covers a stored hash that is not
    one, which would otherwise escape as a 500.
    """
    try:
        return _hasher.verify(hashed, plain)
    except (VerificationError, InvalidHashError):
        return False


def verify_against_nobody(plain: str) -> None:
    """Burn the same work as a real verification, for an unknown email.

    The result is discarded on purpose: this exists for its timing, not its
    answer (AUTH-026).
    """
    verify_password(plain, _DUMMY_HASH)


def encode_token(user_id: UUID) -> str:
    """Issue a session token.

    The payload is a subject and nothing else — no email, no name, no role.
    A JWT payload is readable by anyone holding the token (AUTH-015).
    """
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": int(now.timestamp()),
            "exp": int((now + TOKEN_LIFETIME).timestamp()),
            "iss": _ISSUER,
        },
        get_settings().jwt_secret,
        algorithm=_ALGORITHM,
    )


def decode_token(token: str) -> UUID:
    """Read a user id out of a session token.

    Args:
        token: The raw cookie value.

    Returns:
        The subject.

    Raises:
        AuthError: NOT_AUTHENTICATED for anything wrong with the token —
            expired, tampered, malformed, or signed with another key. The
            client is told none of which, because the distinction is only
            useful to someone attacking it.
    """
    try:
        payload = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=[_ALGORITHM],
            issuer=_ISSUER,
        )
    except jwt.PyJWTError as exc:
        raise AuthError(code="NOT_AUTHENTICATED") from exc
    try:
        return UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise AuthError(code="NOT_AUTHENTICATED") from exc
