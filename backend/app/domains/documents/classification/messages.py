"""Pure: the sentence the borrower reads, composed server-side (AI-026).

**The frontend renders a string and never implements the decision table.** If
the thresholds or the copy change, they change here, and no client needs
redeploying to agree with the server about what a mismatch means.

`FAILED`, `SKIPPED`, `INCONCLUSIVE` and a document that was never classified
all compose to `None` — they render as nothing (AI-021). A failed
classification is our problem, and an unconfident one is not worth a sentence.
"""

from app.domains.documents.classification.entities import (
    ClassificationOutcome,
    ClassifiedType,
)

# Human labels for the model's vocabulary. Copy belonging to this feature, not
# the checklist's `label_en` — reaching into `applications` for it would cross a
# domain boundary for a string (ARC-011).
_LABELS: dict[ClassifiedType, str] = {
    ClassifiedType.IDENTITY: "identity document",
    ClassifiedType.BANK_STATEMENTS: "bank statement",
    ClassifiedType.PURCHASE_AGREEMENT: "purchase agreement",
    ClassifiedType.PAYSLIPS: "payslip",
    ClassifiedType.EMPLOYER_STATEMENT: "employer statement",
    ClassifiedType.TAX_ASSESSMENT: "tax assessment",
    ClassifiedType.ACCOUNTANT_STATEMENT: "accountant's statement",
    ClassifiedType.EXISTING_LOAN_STATEMENTS: "existing loan statement",
    ClassifiedType.EPC: "energy performance certificate",
    ClassifiedType.BUILDING_PERMIT: "building permit",
    ClassifiedType.CONSTRUCTION_QUOTE: "construction quote",
    ClassifiedType.UNKNOWN: "unrecognised document",
}


def label_for(doc_type: ClassifiedType) -> str:
    """The borrower-facing name of a document type."""
    return _LABELS[doc_type]


def compose(outcome: str | None, detected: str | None, claimed: ClassifiedType) -> str | None:
    """Compose what the borrower is told about one classified document.

    Args:
        outcome: The stored `ClassificationOutcome` value, or None if the
            document was never classified.
        detected: The stored `ClassifiedType` the model answered, or None.
        claimed: What the borrower declared on upload.

    Returns:
        One sentence, or None when there is nothing worth saying. `None`
        covers every silent case at once — never classified, skipped, failed,
        or classified without enough confidence to trust (AI-021).
    """
    if outcome is None or detected is None:
        return None
    try:
        parsed = ClassificationOutcome(outcome)
        actual = ClassifiedType(detected)
    except ValueError:  # pragma: no cover - a value only this module writes
        return None

    if parsed is ClassificationOutcome.CONFIRMED:
        return "This looks like the right document."
    if parsed is ClassificationOutcome.UNRECOGNISED:
        return "We could not recognise this document. Check it is the right file and readable."
    if parsed is ClassificationOutcome.POSSIBLE_MISMATCH:
        return f"This may be a {label_for(actual)} rather than a {label_for(claimed)}."
    if parsed is ClassificationOutcome.LIKELY_MISMATCH:
        return (
            f"This looks like a {label_for(actual)}, "
            f"but it was uploaded as a {label_for(claimed)}."
        )
    return None
