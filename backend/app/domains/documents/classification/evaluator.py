"""Pure: what a classification verdict means for the borrower (AI-014 – AI-017).

**This module is where the outcome is decided, and the model has no vote.** It
takes a verdict and what the borrower declared, and returns one of five
outcomes. No IO, no API client, no session (ARC-013, CQ-048), so every row of
the decision table is testable without touching the network.

That separation is the entire architectural argument of the feature. A model
that calls a payslip a tax assessment cannot corrupt anything, because it has
no authority over anything: the outcome never changes `Document.doc_type`,
never satisfies or unsatisfies a requirement, and never moves an application
(AI-017). The worst case it can produce is an unhelpful hint.
"""

from app.core.enums import DocumentType
from app.domains.documents.classification.entities import (
    ClassificationOutcome,
    ClassificationVerdict,
    ClassifiedType,
    claimed_as_classified,
)

# AI-016. Both thresholds are named constants, never literals at the point of
# use: they are the entire tuning surface of this feature and the first thing
# a reviewer asks about.
#
# CONFIDENCE_FLOOR — below this the verdict is not trusted at all, and the
# borrower is told nothing. Silence beats a bad guess (AI-015).
CONFIDENCE_FLOOR = 0.60

# HIGH_CONFIDENCE — at or above this a disagreement is stated plainly rather
# than hedged. Below it, a mismatch is raised as a possibility.
HIGH_CONFIDENCE = 0.85


def evaluate(verdict: ClassificationVerdict, claimed: DocumentType) -> ClassificationOutcome:
    """Decide what to tell the borrower about a classified document.

    The model's verdict is advisory. This function owns the outcome, so a wrong
    or low-confidence verdict can never change application state (AI-003).

    Args:
        verdict: What the model answered, already parsed and range-checked.
        claimed: The requirement the borrower uploaded this file against. The
            borrower is the authority here — a mismatch is reported as a
            question, never acted on (AI-006).

    Returns:
        One of the five outcomes of AI-015's decision table.
    """
    if verdict.confidence < CONFIDENCE_FLOOR:
        return ClassificationOutcome.INCONCLUSIVE
    if verdict.doc_type is ClassifiedType.UNKNOWN:
        return ClassificationOutcome.UNRECOGNISED
    if verdict.doc_type is claimed_as_classified(claimed):
        return ClassificationOutcome.CONFIRMED
    if verdict.confidence < HIGH_CONFIDENCE:
        return ClassificationOutcome.POSSIBLE_MISMATCH
    return ClassificationOutcome.LIKELY_MISMATCH
