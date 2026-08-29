"""Accounts, sessions, and the two questions a reviewer always asks.

AUTH-018 - AUTH-038. Whether the cookie is httpOnly, and whether login tells an
attacker which addresses are registered.
"""

import time

import pytest

from app.core.config import get_settings
from app.domains.auth.dependencies import SESSION_COOKIE, _auth_limiter

_CREDENTIALS = {"email": "jan@example.com", "password": "hunter2hunter2"}


@pytest.fixture(autouse=True)
def _no_throttle():
    # The limiter is process-wide and would otherwise leak between tests.
    _auth_limiter._attempts.clear()


async def test_signup_sets_httponly_samesite_cookie(client, engine):
    response = await client.post("/api/auth/signup", json=_CREDENTIALS)

    assert response.status_code == 201
    cookie = response.headers["set-cookie"]
    assert "httponly" in cookie.lower()
    assert "samesite=lax" in cookie.lower()
    assert response.json()["user"]["email"] == "jan@example.com"


async def test_the_token_never_appears_in_the_body(client, engine):
    # AUTH-044: nothing reads it from JavaScript because nothing can.
    body = (await client.post("/api/auth/signup", json=_CREDENTIALS | {"email": "b@x.com"})).json()

    assert "token" not in body
    assert "password" not in str(body)
    assert "password_hash" not in str(body)


async def test_signup_duplicate_email_returns_409(client, engine):
    await client.post("/api/auth/signup", json=_CREDENTIALS | {"email": "dup@example.com"})

    response = await client.post(
        "/api/auth/signup", json=_CREDENTIALS | {"email": "dup@example.com"}
    )

    assert response.status_code == 409
    assert response.json()["code"] == "EMAIL_ALREADY_REGISTERED"


async def test_signup_normalises_the_email_before_checking(client, engine):
    # VAL-020: Test@Example.com when test@example.com exists.
    await client.post("/api/auth/signup", json=_CREDENTIALS | {"email": "case@example.com"})

    response = await client.post(
        "/api/auth/signup", json=_CREDENTIALS | {"email": "CASE@Example.com"}
    )

    assert response.status_code == 409


async def test_login_wrong_password_and_unknown_email_are_identical(client, engine):
    await client.post("/api/auth/signup", json=_CREDENTIALS | {"email": "same@example.com"})

    wrong = await client.post(
        "/api/auth/login", json={"email": "same@example.com", "password": "wrongwrongwrong"}
    )
    unknown = await client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": "wrongwrongwrong"}
    )

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


async def test_login_hashes_even_when_user_missing(client, engine):
    # AUTH-026. Timing, not correctness: if an unknown email returned early,
    # the response time would answer "is this address registered?".
    await client.post("/api/auth/signup", json=_CREDENTIALS | {"email": "timed@example.com"})

    start = time.perf_counter()
    await client.post(
        "/api/auth/login", json={"email": "nobody-here@example.com", "password": "hunter2hunter2"}
    )
    unknown_ms = (time.perf_counter() - start) * 1000

    start = time.perf_counter()
    await client.post(
        "/api/auth/login", json={"email": "timed@example.com", "password": "wrongwrongwrong"}
    )
    wrong_ms = (time.perf_counter() - start) * 1000

    # argon2 dominates both; an early return would make the unknown case an
    # order of magnitude faster rather than merely different.
    assert unknown_ms > wrong_ms / 4


async def test_me_without_cookie_returns_401(client, engine):
    response = await client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == "NOT_AUTHENTICATED"


async def test_me_returns_the_signed_in_user(client, engine):
    await client.post("/api/auth/signup", json=_CREDENTIALS | {"email": "me@example.com"})

    response = await client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


async def test_tampered_token_returns_401(client, engine):
    await client.post("/api/auth/signup", json=_CREDENTIALS | {"email": "tamper@example.com"})
    good = client.cookies[SESSION_COOKIE]

    client.cookies.set(SESSION_COOKIE, good[:-3] + "aaa")
    response = await client.get("/api/auth/me")

    assert response.status_code == 401


async def test_a_token_signed_with_another_key_is_rejected(client, engine, monkeypatch):
    import jwt

    forged = jwt.encode(
        {"sub": "x", "iss": "borrower-portal"},
        "a-different-secret-that-is-long-enough-32",
        algorithm="HS256",
    )
    client.cookies.set(SESSION_COOKIE, forged)

    assert (await client.get("/api/auth/me")).status_code == 401


async def test_logout_clears_the_cookie_and_succeeds_without_one(client, engine):
    # AUTH-028: 204 either way, which is why it is a public route (AUTH-039).
    response = await client.post("/api/auth/logout")

    assert response.status_code == 204


async def test_eleven_attempts_are_throttled(client, engine):
    # AUTH-040, VAL-020: 10 per 5 minutes, then 429.
    for _ in range(10):
        await client.post("/api/auth/login", json={"email": "x@y.com", "password": "whatever123"})

    response = await client.post(
        "/api/auth/login", json={"email": "x@y.com", "password": "whatever123"}
    )

    assert response.status_code == 429
    assert response.json()["code"] == "TOO_MANY_ATTEMPTS"


def test_startup_fails_without_jwt_secret(monkeypatch):
    # AUTH-017. A default secret in code is worse than no auth, because it
    # looks like auth — so the setting has no default and validation is what
    # stops a short one reaching a running process.
    from pydantic import ValidationError

    from app.core.config import Settings

    monkeypatch.setenv("JWT_SECRET", "too-short")
    with pytest.raises(ValidationError):
        Settings()

    monkeypatch.delenv("JWT_SECRET")
    with pytest.raises(ValidationError):
        Settings()


def test_the_configured_secret_is_long_enough(settings):
    assert len(settings.jwt_secret) >= 32
    assert get_settings() is settings
