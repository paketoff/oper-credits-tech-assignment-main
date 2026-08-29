"""Structured JSON logging with a request id and redaction by default (DEP-031).

Fly collects stdout, so there is no shipping step in production (DEP-029).

**Redaction is the reason this module is not three lines.** In mortgage
origination the payload *is* the sensitive data, and telemetry is where it
leaks: an amount, an income figure, an email, a name or an original filename
must never reach a log line, a span attribute or a metric label (DEP-035).
"""

import logging
import sys
import uuid
from collections.abc import Awaitable, Callable, MutableMapping

import structlog
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"

# DEP-031. Exact keys first, then substrings: `monthly_net_income` and
# `property_value` must go the same way `income` and `value` do, and listing
# every field name that ever holds money is how one gets missed.
_REDACTED_KEYS = frozenset(
    {
        "password",
        "token",
        "secret",
        "api_key",
        "authorization",
        "email",
        "full_name",
        "filename",
    }
)
_REDACTED_SUBSTRINGS = ("amount", "income", "value")
_REDACTED = "[redacted]"


def _is_sensitive(key: str) -> bool:
    """Whether a field name may not carry its value into a log."""
    lowered = key.lower()
    if lowered in _REDACTED_KEYS:
        return True
    return any(fragment in lowered for fragment in _REDACTED_SUBSTRINGS)


def redact(
    _logger: object,
    _name: str,
    event_dict: MutableMapping[str, object],
) -> MutableMapping[str, object]:
    """Replace sensitive values, keeping their keys.

    The key survives on purpose: a line that shows `email: [redacted]` still
    tells you the field was there, which is what makes a log useful for
    debugging a flow without exposing what flowed through it.
    """
    for key in list(event_dict):
        if _is_sensitive(key):
            event_dict[key] = _REDACTED
    return event_dict


def configure() -> None:
    """Set up structlog to emit one JSON object per line on stdout."""
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            redact,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


async def request_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Give every request an id, bind it to the logs, and return it (DEP-030).

    An inbound `X-Request-ID` is honoured so a trace survives a proxy; otherwise
    one is generated. It comes back on the response so a reported problem can be
    traced to the request that caused it, which is the whole point.
    """
    request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    response = await call_next(request)
    response.headers[REQUEST_ID_HEADER] = request_id
    return response
