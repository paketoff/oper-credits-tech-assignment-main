"""Pure: the allowed lifecycle transitions and their single validator (APP-009).

One function owns the allowed edges. An invalid transition raises rather than
silently setting a field, which is what stops a status from being written by
anything that happens to hold the row — and it is why `status` is not a writable
field on the API either (API-011, API-038).
"""

from app.core.errors import ApplicationError
from app.domains.applications.entities import ApplicationStatus

# APP-006, APP-007: nothing leaves these two.
_TERMINAL = frozenset({ApplicationStatus.OFFER_ISSUED, ApplicationStatus.WITHDRAWN})

# APP-001 - APP-007. The WITHDRAWN edges are added below rather than written out
# seven times, because APP-007 states them as a rule about every non-terminal
# state and repeating it by hand is how one gets missed.
ALLOWED_TRANSITIONS: dict[ApplicationStatus, frozenset[ApplicationStatus]] = {
    ApplicationStatus.DRAFT: frozenset({ApplicationStatus.SUBMITTED}),
    ApplicationStatus.SUBMITTED: frozenset({ApplicationStatus.DOCUMENTS_PENDING}),
    ApplicationStatus.DOCUMENTS_PENDING: frozenset({ApplicationStatus.DOCUMENTS_COMPLETE}),
    ApplicationStatus.DOCUMENTS_COMPLETE: frozenset(
        # APP-004 first: a document is removed or rejected and the file moves
        # backwards. This is the loop that matters in production (APP-008).
        {ApplicationStatus.DOCUMENTS_PENDING, ApplicationStatus.UNDER_REVIEW}
    ),
    ApplicationStatus.UNDER_REVIEW: frozenset({ApplicationStatus.OFFER_ISSUED}),
    ApplicationStatus.OFFER_ISSUED: frozenset(),
    ApplicationStatus.WITHDRAWN: frozenset(),
}
ALLOWED_TRANSITIONS = {
    state: targets | ({ApplicationStatus.WITHDRAWN} if state not in _TERMINAL else frozenset())
    for state, targets in ALLOWED_TRANSITIONS.items()
}


def assert_transition(current: ApplicationStatus, target: ApplicationStatus) -> None:
    """Check that an application may move from one state to another.

    Args:
        current: The state the application is in.
        target: The state it is being asked to move to.

    Raises:
        ApplicationError: INVALID_STATE_TRANSITION, which maps to 409 rather
            than 422 — this is a conflict with the resource's current state,
            not bad input (VAL-005).
    """
    if target not in ALLOWED_TRANSITIONS[current]:
        raise ApplicationError(code="INVALID_STATE_TRANSITION")
