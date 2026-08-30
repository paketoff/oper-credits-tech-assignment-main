"""The sentence the borrower reads, composed server-side. AI-025, AI-026.

Composed here rather than in the client so the frontend renders a string and
never implements the decision table — change a threshold or a wording and no
client needs redeploying to agree with the server.
"""

import pytest

from app.domains.documents.classification import messages
from app.domains.documents.classification.entities import ClassifiedType


def test_a_likely_mismatch_names_both_types() -> None:
    composed = messages.compose(
        "LIKELY_MISMATCH", "BANK_STATEMENTS", ClassifiedType.PAYSLIPS
    )

    assert composed == "This looks like a bank statement, but it was uploaded as a payslip."


def test_a_possible_mismatch_is_hedged() -> None:
    composed = messages.compose("POSSIBLE_MISMATCH", "EPC", ClassifiedType.IDENTITY)

    assert composed is not None
    assert composed.startswith("This may be")


def test_unrecognised_asks_the_borrower_to_check_the_file() -> None:
    composed = messages.compose("UNRECOGNISED", "UNKNOWN", ClassifiedType.PAYSLIPS)

    assert composed is not None
    assert "could not recognise" in composed


@pytest.mark.parametrize(
    ("outcome", "detected"),
    [
        pytest.param(None, None, id="never_classified"),
        pytest.param("INCONCLUSIVE", "PAYSLIPS", id="not_confident_enough"),
        pytest.param("LIKELY_MISMATCH", None, id="outcome_without_a_detected_type"),
    ],
)
def test_silent_cases_compose_to_nothing(outcome: str | None, detected: str | None) -> None:
    """AI-021. Failed, skipped, unclassified and unconfident all render as nothing."""
    assert messages.compose(outcome, detected, ClassifiedType.PAYSLIPS) is None


def test_every_classified_type_has_a_label() -> None:
    """A missing label would raise while composing, inside a background task."""
    for member in ClassifiedType:
        assert messages.label_for(member)
