"""The domain exception hierarchy and its stable codes.

A leaf module: exception classes and message text, importing nothing but the
standard library. That is what lets the pure modules raise a domain error
without breaking their import whitelist (ARC-013, ARC-045) — purity here means
no IO, no framework and no session, not the absence of a shared vocabulary.

**HTTP status is deliberately not in this file.** A code becomes a status in
exactly one place, `core/exception_handlers.py` (CQ-053), so that nothing below
the router layer has an opinion about HTTP.

MESSAGES is the single definition CQ-063 requires. A code that is not in it does
not exist, and it mirrors the registry in `7-validation.md` VAL-004 row for row.
"""


class DomainError(Exception):
    """A rule of the domain was violated.

    Carries a stable machine-readable code and a human message so that the
    frontend renders text it did not author (UX-023) and can place it beside the
    input it concerns (VAL-007).
    """

    def __init__(self, code: str, field: str | None = None, detail: str | None = None) -> None:
        """Raise a domain error by code.

        Args:
            code: A key of MESSAGES. Anything else is a programming error.
            field: The input this concerns, when it maps to exactly one.
            detail: Internal context for the log. Never rendered to a client,
                because a response must leak neither paths nor internals
                (CQ-062, VAL-030).
        """
        self.code = code
        self.field = field
        self.detail = detail
        self.message = MESSAGES[code]
        super().__init__(self.message)


class SimulationError(DomainError):
    """A simulation input or computation failed."""


class ApplicationError(DomainError):
    """An application could not be changed as asked."""


class DocumentError(DomainError):
    """An uploaded document was rejected."""


class AuthError(DomainError):
    """Authentication or registration failed."""


class NotFoundError(DomainError):
    """A resource does not exist, or belongs to someone else.

    The two cases are deliberately indistinguishable: a 403 would confirm that
    the resource exists (ERR-005, AUTH-035).
    """


class StorageError(DomainError):
    """The database or the blob store failed."""


MESSAGES: dict[str, str] = {
    "VALIDATION_ERROR": "Check the highlighted fields.",
    "LOAN_AMOUNT_NOT_POSITIVE": "Your own contribution must be less than the property price.",
    "TERM_OUT_OF_RANGE": "Term must be between 1 and 30 years.",
    "RATE_OUT_OF_RANGE": "Interest rate must be between 0% and 20%.",
    "PROPERTY_VALUE_OUT_OF_RANGE": "Property price must be between €10,000 and €10,000,000.",
    "JKP_COMPUTATION_FAILED": "Could not compute the effective annual rate.",
    "SIMULATION_NOT_FOUND": "Simulation not found.",
    "EMAIL_ALREADY_REGISTERED": "That email is already registered.",
    "INVALID_CREDENTIALS": "Email or password is incorrect.",
    "NOT_AUTHENTICATED": "Please sign in.",
    "TOO_MANY_ATTEMPTS": "Too many attempts. Try again in a few minutes.",
    "APPLICATION_NOT_FOUND": "Application not found.",
    "INVALID_STATE_TRANSITION": "This application cannot move to that state.",
    "APPLICATION_ALREADY_SUBMITTED": "This application has already been submitted.",
    "UNSUPPORTED_DOCUMENT_TYPE": "Only PDF, JPEG and PNG files are accepted.",
    "DOCUMENT_TOO_LARGE": "Files must be under 10 MB.",
    "DOCUMENT_EMPTY": "That file is empty.",
    "DOCUMENT_TYPE_NOT_REQUIRED": "That document is not part of this checklist.",
    "DOCUMENT_NOT_FOUND": "Document not found.",
    "UPLOAD_READ_FAILED": "Upload failed. Please try again.",
    "STORAGE_UNAVAILABLE": "Storage is temporarily unavailable.",
    "STORAGE_CORRUPT": "Stored data could not be read.",
}
