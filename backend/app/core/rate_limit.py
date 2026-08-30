"""Generic per-IP attempt limiter. Knows no domain (AUTH-040, ARC-012).

Applied to the two auth endpoints and nothing else. Not to the simulator: it is
anonymous, cheap, and the whole point is that people use it freely (AUTH-042).

In-memory, so it resets on restart and does not work across machines. Both are
fine for one machine and both are stated in the README rather than discovered
(AUTH-041).
"""

import time
from collections import defaultdict, deque

from app.core.errors import AuthError

_MAX_ATTEMPTS = 10
_WINDOW_SECONDS = 300.0


class RateLimiter:
    """Counts attempts per key inside a sliding window.

    Swept on write rather than on a timer: there is no background task to own,
    and a key nobody touches costs nothing to leave behind until they do.
    """

    def __init__(
        self,
        max_attempts: int = _MAX_ATTEMPTS,
        window_seconds: float = _WINDOW_SECONDS,
    ) -> None:
        """Configure the window.

        Args:
            max_attempts: Attempts allowed inside the window.
            window_seconds: How long an attempt is remembered.
        """
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._attempts: defaultdict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        """Record an attempt for this key, and reject once the window is full.

        Args:
            key: Usually a client IP.

        Raises:
            AuthError: TOO_MANY_ATTEMPTS, which maps to 429.
        """
        now = time.monotonic()
        recent = self._attempts[key]
        while recent and now - recent[0] > self._window_seconds:
            recent.popleft()
        if len(recent) >= self._max_attempts:
            raise AuthError(code="TOO_MANY_ATTEMPTS")
        recent.append(now)

    def reset(self, key: str) -> None:
        """Forget a key.

        Nothing in `app/` calls this: `AUTH-040` counts *attempts*, and a
        successful login is an attempt like any other — clearing the window on
        success would let an attacker reset their own budget with one valid
        credential. It exists so a test can arrange a window without waiting
        five minutes for one to expire.
        """
        self._attempts.pop(key, None)
