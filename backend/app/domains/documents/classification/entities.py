"""Domain types for the optional classifier (AI-011, AI-012, AI-015).

Frozen dataclasses and enums, not the pydantic model that parses the API
response — that is `client.py`'s, and keeping the two apart is what lets
`evaluator.py` stay pure (ARC-013): it imports these and nothing else.

These live in the classification module rather than in `documents/entities.py`
because the whole feature has to be removable without the domain noticing
(AI-012, AI-020).
"""

from dataclasses import dataclass
from enum import StrEnum

from app.core.enums import DocumentType


class ClassifiedType(StrEnum):
    """What the model may answer: the eleven document types, plus `UNKNOWN`.

    **A separate enum, deliberately duplicating `DocumentType`'s members**
    (AI-012). Extending the domain enum with `UNKNOWN` would let it reach the
    checklist, which derives requirements from `DOC-006` and `DOC-007` — a
    requirement to upload an "unknown" is not a thing, and a stored document
    can never carry it either.

    The duplication is the point rather than an oversight, and
    `test_every_document_type_has_a_classified_counterpart` fails if the two
    ever drift apart.
    """

    IDENTITY = "IDENTITY"
    BANK_STATEMENTS = "BANK_STATEMENTS"
    PURCHASE_AGREEMENT = "PURCHASE_AGREEMENT"
    PAYSLIPS = "PAYSLIPS"
    EMPLOYER_STATEMENT = "EMPLOYER_STATEMENT"
    TAX_ASSESSMENT = "TAX_ASSESSMENT"
    ACCOUNTANT_STATEMENT = "ACCOUNTANT_STATEMENT"
    EXISTING_LOAN_STATEMENTS = "EXISTING_LOAN_STATEMENTS"
    EPC = "EPC"
    BUILDING_PERMIT = "BUILDING_PERMIT"
    CONSTRUCTION_QUOTE = "CONSTRUCTION_QUOTE"
    UNKNOWN = "UNKNOWN"


class ClassificationOutcome(StrEnum):
    """What the borrower is told, decided by code and never by the model (AI-015).

    `INCONCLUSIVE` and `UNRECOGNISED` are different states with different
    causes: the first is "we did not trust the answer", the second is "the
    answer was confidently *nothing recognisable*". Only the second is worth
    saying out loud.
    """

    CONFIRMED = "CONFIRMED"
    POSSIBLE_MISMATCH = "POSSIBLE_MISMATCH"
    LIKELY_MISMATCH = "LIKELY_MISMATCH"
    UNRECOGNISED = "UNRECOGNISED"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass(frozen=True, slots=True)
class ClassificationVerdict:
    """What the model thinks a document is. **Advisory only** (AI-003, AI-011).

    A domain dataclass rather than the pydantic model that parsed it: the
    boundary model belongs to `client.py`, and `evaluator.py` must be able to
    decide the outcome without importing a framework.

    `reason` is the model's own words, carried for a human reading a trace and
    **never shown to the borrower or written to a log** (AI-028) — composed
    copy is the frontend's, from the outcome.
    """

    doc_type: ClassifiedType
    confidence: float
    reason: str


def claimed_as_classified(claimed: DocumentType) -> ClassifiedType:
    """Read a declared document type as the model's vocabulary.

    Total by construction: every `DocumentType` member has a `ClassifiedType`
    counterpart with the same value, which is what the drift test guards.
    """
    return ClassifiedType(claimed.value)
