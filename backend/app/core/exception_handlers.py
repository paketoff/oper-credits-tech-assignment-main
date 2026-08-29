"""The single place a domain error becomes an HTTP status (CQ-053).

Nothing below the router layer has an opinion about HTTP. `core/errors.py` holds
the codes and their text; the status lives only here, so a router never maps an
error and a service never imports `fastapi.HTTPException`.

Every response, from every failure of an `/api` route, has the same three-key
shape (`API-013`, `VAL-006`). `/health` and `/ready` are outside it because they
are outside `/api` and their reader is a health checker rather than a client
(`API-069`).
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.errors import MESSAGES, DomainError

# 7-validation.md VAL-004, column two. 422 is the default for an input
# violation, not a blanket (VAL-005): the two computation failures are 500 and
# the four conflicts are 409, because a conflict with the resource's current
# state is not bad input.
STATUSES: dict[str, int] = {
    "VALIDATION_ERROR": 422,
    "LOAN_AMOUNT_NOT_POSITIVE": 422,
    "TERM_OUT_OF_RANGE": 422,
    "RATE_OUT_OF_RANGE": 422,
    "PROPERTY_VALUE_OUT_OF_RANGE": 422,
    "JKP_COMPUTATION_FAILED": 500,
    "SIMULATION_NOT_FOUND": 404,
    "EMAIL_ALREADY_REGISTERED": 409,
    "INVALID_CREDENTIALS": 401,
    "NOT_AUTHENTICATED": 401,
    "TOO_MANY_ATTEMPTS": 429,
    "APPLICATION_NOT_FOUND": 404,
    "INVALID_STATE_TRANSITION": 409,
    "APPLICATION_ALREADY_SUBMITTED": 409,
    "UNSUPPORTED_DOCUMENT_TYPE": 415,
    "DOCUMENT_TOO_LARGE": 413,
    "DOCUMENT_EMPTY": 422,
    "DOCUMENT_TYPE_NOT_REQUIRED": 422,
    "DOCUMENT_NOT_FOUND": 404,
    "UPLOAD_READ_FAILED": 500,
    "STORAGE_UNAVAILABLE": 503,
    "STORAGE_CORRUPT": 500,
}

_UNMAPPED_STATUS = 500


def error_body(code: str, field: str | None = None) -> dict[str, str | None]:
    """Render the one error shape the whole API uses (VAL-006).

    `detail` is deliberately not included. It exists for the log; a response
    leaks neither stack traces nor internal paths (CQ-062, VAL-030).
    """
    return {"code": code, "message": MESSAGES[code], "field": field}


async def handle_domain_error(_request: Request, exc: DomainError) -> JSONResponse:
    """Render a domain error at its registered status."""
    return JSONResponse(
        status_code=STATUSES.get(exc.code, _UNMAPPED_STATUS),
        content=error_body(exc.code, exc.field),
    )


async def handle_validation_error(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Normalise a pydantic failure into the same shape (API-015).

    A raw FastAPI `detail` array never reaches the client: it is a list of
    dicts with a different shape per error type, and the frontend would have to
    learn a second error format to place a message beside a field.
    """
    return JSONResponse(
        status_code=STATUSES["VALIDATION_ERROR"],
        content=error_body("VALIDATION_ERROR", _first_field(exc)),
    )


def _first_field(exc: RequestValidationError) -> str | None:
    """Name the first offending input, so the frontend can place the message."""
    for error in exc.errors():
        location = error.get("loc", ())
        if len(location) > 1:
            return str(location[-1])
    return None


def register(app: FastAPI) -> None:
    """Attach both handlers. Called once, from the app factory (CQ-019)."""
    app.add_exception_handler(DomainError, handle_domain_error)  # type: ignore[arg-type]  # starlette types the handler against Exception
    app.add_exception_handler(RequestValidationError, handle_validation_error)  # type: ignore[arg-type]  # same
