"""The classifier's decision table. AI-014 - AI-017, AI-033, AI-034.

Tier 1 (T-P5): pure, finite, no network.

`test_below_confidence_floor_returns_inconclusive_despite_sharp_mismatch` is the
one worth pointing at on a walkthrough. It is the test that proves *code* owns
the outcome and the model does not: the model is maximally wrong — a passport
called a construction quote — and the answer is still "say nothing", because
the confidence was too low to trust. Nothing about the model's opinion reaches
the borrower or the application.
"""

import pytest

from app.core.enums import DocumentType
from app.domains.documents.classification import evaluator
from app.domains.documents.classification.entities import (
    ClassificationOutcome,
    ClassificationVerdict,
    ClassifiedType,
)


def _verdict(doc_type: ClassifiedType, confidence: float) -> ClassificationVerdict:
    return ClassificationVerdict(doc_type=doc_type, confidence=confidence, reason="because")


def test_below_confidence_floor_returns_inconclusive_despite_sharp_mismatch() -> None:
    """AI-033. The model owns no outcome, however wrong or however sure it is."""
    verdict = _verdict(ClassifiedType.CONSTRUCTION_QUOTE, 0.59)

    outcome = evaluator.evaluate(verdict, DocumentType.IDENTITY)

    assert outcome is ClassificationOutcome.INCONCLUSIVE


def test_matching_type_above_floor_returns_confirmed() -> None:
    outcome = evaluator.evaluate(_verdict(ClassifiedType.PAYSLIPS, 0.61), DocumentType.PAYSLIPS)

    assert outcome is ClassificationOutcome.CONFIRMED


def test_unknown_above_floor_returns_unrecognised() -> None:
    """A confident "this is nothing I recognise" is worth saying; a doubtful one is not."""
    outcome = evaluator.evaluate(_verdict(ClassifiedType.UNKNOWN, 0.90), DocumentType.PAYSLIPS)

    assert outcome is ClassificationOutcome.UNRECOGNISED


def test_mismatch_medium_confidence_returns_possible_mismatch() -> None:
    outcome = evaluator.evaluate(
        _verdict(ClassifiedType.BANK_STATEMENTS, 0.70), DocumentType.PAYSLIPS
    )

    assert outcome is ClassificationOutcome.POSSIBLE_MISMATCH


def test_mismatch_high_confidence_returns_likely_mismatch() -> None:
    outcome = evaluator.evaluate(
        _verdict(ClassifiedType.BANK_STATEMENTS, 0.92), DocumentType.PAYSLIPS
    )

    assert outcome is ClassificationOutcome.LIKELY_MISMATCH


@pytest.mark.parametrize(
    ("doc_type", "confidence", "claimed", "expected"),
    [
        # AI-034: every row of the table, and both sides of both thresholds.
        (ClassifiedType.PAYSLIPS, 0.0, DocumentType.PAYSLIPS, ClassificationOutcome.INCONCLUSIVE),
        (ClassifiedType.UNKNOWN, 0.59, DocumentType.EPC, ClassificationOutcome.INCONCLUSIVE),
        # Exactly on the floor is trusted: the boundary belongs to the answer.
        (ClassifiedType.EPC, 0.60, DocumentType.EPC, ClassificationOutcome.CONFIRMED),
        (ClassifiedType.UNKNOWN, 0.60, DocumentType.EPC, ClassificationOutcome.UNRECOGNISED),
        (
            ClassifiedType.EPC,
            0.60,
            DocumentType.IDENTITY,
            ClassificationOutcome.POSSIBLE_MISMATCH,
        ),
        # Exactly on the high threshold is stated plainly, not hedged.
        (
            ClassifiedType.EPC,
            0.85,
            DocumentType.IDENTITY,
            ClassificationOutcome.LIKELY_MISMATCH,
        ),
        (
            ClassifiedType.EPC,
            0.84,
            DocumentType.IDENTITY,
            ClassificationOutcome.POSSIBLE_MISMATCH,
        ),
        (ClassifiedType.EPC, 1.0, DocumentType.EPC, ClassificationOutcome.CONFIRMED),
    ],
)
def test_decision_table_is_covered_end_to_end(
    doc_type: ClassifiedType,
    confidence: float,
    claimed: DocumentType,
    expected: ClassificationOutcome,
) -> None:
    assert evaluator.evaluate(_verdict(doc_type, confidence), claimed) is expected


def test_thresholds_are_module_constants_not_literals() -> None:
    """AI-016. The tuning surface has to be findable and changeable in one place."""
    assert evaluator.CONFIDENCE_FLOOR == 0.60
    assert evaluator.HIGH_CONFIDENCE == 0.85
    assert evaluator.CONFIDENCE_FLOOR < evaluator.HIGH_CONFIDENCE


def test_every_document_type_has_a_classified_counterpart() -> None:
    """AI-012. The two enums are deliberately separate, and must not drift apart.

    `ClassifiedType` duplicates `DocumentType` on purpose so that `UNKNOWN`
    can never reach the checklist. That duplication is only safe while it stays
    in step, and this is what notices when it does not.
    """
    assert {member.value for member in ClassifiedType} == {
        member.value for member in DocumentType
    } | {"UNKNOWN"}


def test_unknown_is_not_a_document_type() -> None:
    """AI-012. The domain enum is never extended; a stored doc_type cannot be UNKNOWN."""
    assert "UNKNOWN" not in {member.value for member in DocumentType}
