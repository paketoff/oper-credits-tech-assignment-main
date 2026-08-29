"""Ten attempts per five minutes, per IP, on the auth endpoints only. AUTH-040 - AUTH-042."""

import pytest

from app.core.errors import AuthError
from app.core.rate_limit import RateLimiter


def test_attempts_within_the_window_are_allowed():
    limiter = RateLimiter(max_attempts=10, window_seconds=300)

    for _ in range(10):
        limiter.check("203.0.113.7")


def test_the_eleventh_attempt_in_the_window_is_rejected():
    # VAL-020: "11 login attempts in 5 minutes" is a listed edge case.
    limiter = RateLimiter(max_attempts=10, window_seconds=300)
    for _ in range(10):
        limiter.check("203.0.113.7")

    with pytest.raises(AuthError) as exc:
        limiter.check("203.0.113.7")

    assert exc.value.code == "TOO_MANY_ATTEMPTS"


def test_the_window_slides(monkeypatch):
    # Sliding, not fixed: an attempt is forgotten once it is older than the
    # window, so a blocked caller recovers without the process restarting.
    clock = [1000.0]
    monkeypatch.setattr("app.core.rate_limit.time.monotonic", lambda: clock[0])
    limiter = RateLimiter(max_attempts=2, window_seconds=300)

    limiter.check("ip")
    limiter.check("ip")
    with pytest.raises(AuthError):
        limiter.check("ip")

    clock[0] += 301
    limiter.check("ip")


def test_keys_are_independent():
    # Per IP. One borrower failing to log in must not lock out another.
    limiter = RateLimiter(max_attempts=1, window_seconds=300)

    limiter.check("first")
    limiter.check("second")

    with pytest.raises(AuthError):
        limiter.check("first")


def test_a_successful_attempt_can_clear_the_key():
    limiter = RateLimiter(max_attempts=1, window_seconds=300)
    limiter.check("ip")

    limiter.reset("ip")

    limiter.check("ip")
