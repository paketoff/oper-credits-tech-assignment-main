"""One schema per extractable document type (T56).

**The pydantic model is the single source of truth.** The JSON schema handed to
the model is generated from it with `model_json_schema()`, so the prompt and the
type cannot drift: adding a field changes both at once, and `mypy --strict`
checks every use of it. A YAML description of the same thing would have to be
interpreted at runtime as `dict[str, Any]`, which `CQ-021` forbids outright.

**Six types, not eleven.** These are the ones carrying numbers the affordability
assessment reads (`0-business-logic.md` §21). `IDENTITY` and `BANK_STATEMENTS`
are deliberately absent: a national register number and an account number are a
materially different GDPR commitment, and declining to extract them is a
stronger position than extracting them because we could. `EPC`,
`BUILDING_PERMIT` and `CONSTRUCTION_QUOTE` carry nothing any calculation uses.

Every field is optional. A model that cannot find the net pay on a payslip
should say so by omitting it, not by inventing one — and a missing field is a
proposal with less in it, never an error.
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import DocumentType

# Money constraints repeated at each field rather than unpacked from a dict:
# `**kwargs` defeats mypy's overload resolution on `Field`, and losing strict
# typing on the money fields to save four lines is a bad trade (CQ-086).


class PayslipFields(BaseModel):
    """A `loonfiche` / `fiche de paie`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    net_monthly_pay: Decimal | None = Field(
        default=None,
        description="Net pay actually transferred this month, in EUR",
        max_digits=12,
        decimal_places=2,
        ge=0,
    )
    period: str | None = Field(
        default=None, max_length=32, description="The month this slip covers, e.g. 2026-03"
    )
    employer_name: str | None = Field(default=None, max_length=200)


class TaxAssessmentFields(BaseModel):
    """An `aanslagbiljet` / `avertissement-extrait de rôle`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    assessment_year: int | None = Field(default=None, ge=1990, le=2100)
    net_taxable_income: Decimal | None = Field(
        default=None, description="Net taxable income for the year, in EUR",
        max_digits=12,
        decimal_places=2,
        ge=0,
    )


class AccountantStatementFields(BaseModel):
    """A statement of income prepared by an accountant."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    year: int | None = Field(default=None, ge=1990, le=2100)
    net_annual_income: Decimal | None = Field(
        default=None, description="Net annual income for the year, in EUR",
        max_digits=12,
        decimal_places=2,
        ge=0,
    )


class EmployerStatementFields(BaseModel):
    """A `werkgeversattest` or employment contract."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_type: str | None = Field(
        default=None, max_length=64, description="Permanent, fixed-term, interim, or similar"
    )
    start_date: date | None = None
    gross_annual_salary: Decimal | None = Field(
        default=None, description="Gross annual salary, in EUR",
        max_digits=12,
        decimal_places=2,
        ge=0,
    )


class ExistingLoanFields(BaseModel):
    """A statement for a credit the borrower already has."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    outstanding_balance: Decimal | None = Field(
        default=None, description="Remaining balance, in EUR",
        max_digits=12,
        decimal_places=2,
        ge=0,
    )
    monthly_instalment: Decimal | None = Field(
        default=None, description="Monthly repayment, in EUR",
        max_digits=12,
        decimal_places=2,
        ge=0,
    )


class PurchaseAgreementFields(BaseModel):
    """A `compromis` / `verkoopovereenkomst`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    purchase_price: Decimal | None = Field(
        default=None, description="Agreed purchase price, in EUR",
        max_digits=12,
        decimal_places=2,
        ge=0,
    )
    deed_date: date | None = None


EXTRACTION_SCHEMAS: dict[DocumentType, type[BaseModel]] = {
    DocumentType.PAYSLIPS: PayslipFields,
    DocumentType.TAX_ASSESSMENT: TaxAssessmentFields,
    DocumentType.ACCOUNTANT_STATEMENT: AccountantStatementFields,
    DocumentType.EMPLOYER_STATEMENT: EmployerStatementFields,
    DocumentType.EXISTING_LOAN_STATEMENTS: ExistingLoanFields,
    DocumentType.PURCHASE_AGREEMENT: PurchaseAgreementFields,
}


def schema_for(doc_type: DocumentType) -> type[BaseModel] | None:
    """The extraction schema for a declared type, or None if nothing is extracted."""
    return EXTRACTION_SCHEMAS.get(doc_type)
