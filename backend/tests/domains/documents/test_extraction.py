"""Extraction schemas and the mapping onto the financial profile. T56, T57.

The mapping is where a document stops being a document and becomes two numbers
the assessment can read. Everything it produces is a *proposal*: the borrower
confirms it before anything is calculated on it (DOM-030), which is what stops a
misread figure from ever reaching an affordability band.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.core.enums import DocumentType
from app.domains.documents.extraction.proposal import to_proposal
from app.domains.documents.extraction.schemas import (
    EXTRACTION_SCHEMAS,
    AccountantStatementFields,
    EmployerStatementFields,
    ExistingLoanFields,
    PayslipFields,
    PurchaseAgreementFields,
    TaxAssessmentFields,
    schema_for,
)


def test_identity_and_bank_statements_are_deliberately_not_extracted() -> None:
    """A national register number and an account number are a different commitment.

    Declining to read them is a decision, not an omission — and it is a stronger
    position on a walkthrough than extracting them because we could.
    """
    assert schema_for(DocumentType.IDENTITY) is None
    assert schema_for(DocumentType.BANK_STATEMENTS) is None


def test_only_the_money_bearing_types_have_schemas() -> None:
    assert set(EXTRACTION_SCHEMAS) == {
        DocumentType.PAYSLIPS,
        DocumentType.TAX_ASSESSMENT,
        DocumentType.ACCOUNTANT_STATEMENT,
        DocumentType.EMPLOYER_STATEMENT,
        DocumentType.EXISTING_LOAN_STATEMENTS,
        DocumentType.PURCHASE_AGREEMENT,
    }


def test_every_schema_generates_a_json_schema_for_the_prompt() -> None:
    """T56. The prompt is generated from the model, so the two cannot drift."""
    for schema in EXTRACTION_SCHEMAS.values():
        generated = schema.model_json_schema()
        assert generated["properties"]


def test_every_field_is_optional_so_a_partial_read_is_not_an_error() -> None:
    """A model that cannot find the net pay should omit it, not invent it."""
    for schema in EXTRACTION_SCHEMAS.values():
        assert schema.model_validate({})


def test_a_payslip_proposes_its_net_pay_as_monthly_income() -> None:
    proposal = to_proposal(
        DocumentType.PAYSLIPS,
        PayslipFields(net_monthly_pay=Decimal("3200.00"), period="2026-03", employer_name="Acme"),
    )

    assert proposal is not None
    assert proposal.net_monthly_income == Decimal("3200.00")
    assert proposal.existing_credit_monthly is None
    assert proposal.source == "your payslip"


@pytest.mark.parametrize(
    ("doc_type", "fields", "expected"),
    [
        pytest.param(
            DocumentType.TAX_ASSESSMENT,
            TaxAssessmentFields(assessment_year=2025, net_taxable_income=Decimal("48000.00")),
            Decimal("4000.00"),
            id="tax_assessment",
        ),
        pytest.param(
            DocumentType.ACCOUNTANT_STATEMENT,
            AccountantStatementFields(year=2025, net_annual_income=Decimal("50000.00")),
            Decimal("4166.67"),
            id="accountant_statement_rounds_to_the_cent",
        ),
    ],
)
def test_an_annual_figure_is_proposed_as_a_monthly_one(
    doc_type: DocumentType, fields: object, expected: Decimal
) -> None:
    """The document states a year; the assessment reads a month (SIM-023)."""
    proposal = to_proposal(doc_type, fields)

    assert proposal is not None
    assert proposal.net_monthly_income == expected


def test_a_loan_statement_proposes_an_instalment_not_an_income() -> None:
    proposal = to_proposal(
        DocumentType.EXISTING_LOAN_STATEMENTS,
        ExistingLoanFields(
            outstanding_balance=Decimal("12000.00"), monthly_instalment=Decimal("250.00")
        ),
    )

    assert proposal is not None
    assert proposal.net_monthly_income is None
    assert proposal.existing_credit_monthly == Decimal("250.00")


@pytest.mark.parametrize(
    ("doc_type", "fields"),
    [
        pytest.param(
            DocumentType.EMPLOYER_STATEMENT,
            EmployerStatementFields(
                contract_type="permanent",
                start_date=date(2020, 1, 6),
                gross_annual_salary=Decimal("60000.00"),
            ),
            id="gross_is_not_net",
        ),
        pytest.param(
            DocumentType.PURCHASE_AGREEMENT,
            PurchaseAgreementFields(
                purchase_price=Decimal("300000.00"), deed_date=date(2026, 6, 1)
            ),
            id="a_price_is_not_a_monthly_figure",
        ),
    ],
)
def test_types_that_say_nothing_the_assessment_reads_propose_nothing(
    doc_type: DocumentType, fields: object
) -> None:
    """Converting gross to net would be inventing a tax model — SCP-011's cut, kept."""
    assert to_proposal(doc_type, fields) is None


def test_a_document_that_read_nothing_proposes_an_empty_proposal() -> None:
    proposal = to_proposal(DocumentType.PAYSLIPS, PayslipFields())

    assert proposal is not None
    assert proposal.is_empty()
