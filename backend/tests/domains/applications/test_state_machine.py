"""Allowed lifecycle edges, and the one that looks like an error but is not.

APP-001 - APP-009. The cycle is deliberately not linear: an application moves
back from complete to pending every time a document is removed, and in
production that loop is the first-time-right problem the product exists to fix.
"""

import pytest

from app.core.errors import ApplicationError
from app.domains.applications.entities import ApplicationStatus
from app.domains.applications.state_machine import ALLOWED_TRANSITIONS, assert_transition

_ALL_EDGES = [
    (current, target)
    for current in ApplicationStatus
    for target in ApplicationStatus
]
_ALLOWED = [(c, t) for c, targets in ALLOWED_TRANSITIONS.items() for t in targets]
_DISALLOWED = [edge for edge in _ALL_EDGES if edge not in _ALLOWED]


@pytest.mark.parametrize(("current", "target"), _ALLOWED)
def test_every_allowed_transition_passes(current, target):
    # The assertion is that it does not raise; assert_transition returns None.
    assert_transition(current, target)


@pytest.mark.parametrize(("current", "target"), _DISALLOWED)
def test_every_disallowed_transition_raises(current, target):
    with pytest.raises(ApplicationError) as exc:
        assert_transition(current, target)

    assert exc.value.code == "INVALID_STATE_TRANSITION"


def test_documents_complete_can_return_to_pending():
    # APP-004, APP-008. A real edge, not an error path.
    assert_transition(ApplicationStatus.DOCUMENTS_COMPLETE, ApplicationStatus.DOCUMENTS_PENDING)


def test_submitted_cannot_return_to_draft():
    # Submission is the point of no return for editing (API-040).
    with pytest.raises(ApplicationError):
        assert_transition(ApplicationStatus.SUBMITTED, ApplicationStatus.DRAFT)


def test_withdrawn_is_terminal():
    # APP-007 allows any non-terminal state into WITHDRAWN, and nothing out.
    for target in ApplicationStatus:
        with pytest.raises(ApplicationError):
            assert_transition(ApplicationStatus.WITHDRAWN, target)
