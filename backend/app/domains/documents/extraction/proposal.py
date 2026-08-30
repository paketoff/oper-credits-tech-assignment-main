"""Pure: turn extracted fields into figures the borrower can confirm (T56).

A document says things; the affordability assessment reads two numbers. This is
the mapping between them, and it is deliberately the only place that knows it.

**Nothing here is authoritative.** Everything this produces is a *proposal*: it
pre-fills a form the borrower then confirms, and only what they confirm is ever
calculated on (`DOM-030`). That is what keeps a misread figure from reaching an
affordability band — it cannot, because a human sits between the two.

No IO, no framework beyond the schemas it maps from, so every conversion is
testable without a network (ARC-013's reasoning, applied to a mapping).
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.core.enums import DocumentType
from app.domains.documents.extraction.schemas import (
    AccountantStatementFields,
    ExistingLoanFields,
    PayslipFields,
    TaxAssessmentFields,
)

_CENT = Decimal("0.01")
_MONTHS_PER_YEAR = 12


@dataclass(frozen=True, slots=True)
class FinancialProposal:
    """What one document suggests for the borrower's financial profile.

    Both figures are optional and independent: a payslip proposes an income and
    says nothing about existing credit, and a loan statement the reverse.
    `source` names the document type in the borrower's words, so the
    reconciliation prompt can say *where* a number came from.
    """

    net_monthly_income: Decimal | None
    existing_credit_monthly: Decimal | None
    source: str

    def is_empty(self) -> bool:
        """True when the document proposed nothing worth showing."""
        return self.net_monthly_income is None and self.existing_credit_monthly is None


def _monthly_from_annual(annual: Decimal | None) -> Decimal | None:
    """Twelfth of an annual figure, to the cent.

    A tax assessment states a year; the assessment reads a month. Dividing here
    rather than at the point of use keeps the conversion in one place, and the
    borrower sees the monthly figure they are being asked to confirm rather than
    an annual one they would have to divide themselves.
    """
    if annual is None:
        return None
    return (annual / _MONTHS_PER_YEAR).quantize(_CENT, rounding=ROUND_HALF_UP)


def to_proposal(doc_type: DocumentType, fields: object) -> FinancialProposal | None:
    """Map one document's extracted fields onto the financial profile.

    Args:
        doc_type: What the borrower declared, which decides how to read the
            fields. Only reached when classification agreed (T57), so the two
            cannot disagree here.
        fields: The parsed schema instance for that type.

    Returns:
        The proposal, or None when this type contributes nothing to the
        assessment — a purchase agreement or an employer statement says useful
        things, but not the two numbers §21 reads.
    """
    if isinstance(fields, PayslipFields):
        return FinancialProposal(
            net_monthly_income=fields.net_monthly_pay,
            existing_credit_monthly=None,
            source="your payslip",
        )
    if isinstance(fields, TaxAssessmentFields):
        return FinancialProposal(
            net_monthly_income=_monthly_from_annual(fields.net_taxable_income),
            existing_credit_monthly=None,
            source="your tax assessment",
        )
    if isinstance(fields, AccountantStatementFields):
        return FinancialProposal(
            net_monthly_income=_monthly_from_annual(fields.net_annual_income),
            existing_credit_monthly=None,
            source="your accountant's statement",
        )
    if isinstance(fields, ExistingLoanFields):
        return FinancialProposal(
            net_monthly_income=None,
            existing_credit_monthly=fields.monthly_instalment,
            source="your existing loan statement",
        )
    # EMPLOYER_STATEMENT states a *gross* salary and PURCHASE_AGREEMENT a price;
    # neither is one of the two figures the assessment reads, and converting
    # gross to net would be inventing a tax model (SCP-011's cut, kept).
    return None
