"""The checklist is derived, not stored. DOC-005 - DOC-011.

This is the point of the whole feature: the required set genuinely differs by
borrower profile and property type, and a static list is a large part of why
Belgian mortgage files arrive incomplete.
"""

from datetime import date
from decimal import Decimal

from app.core.enums import DocumentType, Region
from app.domains.applications.checklist import mark_satisfied, required_documents
from app.domains.applications.entities import (
    ApplicationProfile,
    Borrower,
    EmploymentType,
    PropertyDetails,
    PropertyType,
)


def _borrower(
    employment: EmploymentType = EmploymentType.EMPLOYEE,
    has_existing_credit: bool = False,
) -> Borrower:
    return Borrower(
        full_name="Jan Test",
        date_of_birth=date(1990, 4, 12),
        employment_type=employment,
        monthly_net_income=Decimal("3200.00"),
        has_existing_credit=has_existing_credit,
    )


def _profile(
    employment: EmploymentType = EmploymentType.EMPLOYEE,
    property_type: PropertyType = PropertyType.EXISTING,
    has_existing_credit: bool = False,
) -> ApplicationProfile:
    return ApplicationProfile(
        borrowers=(_borrower(employment, has_existing_credit),),
        property_details=PropertyDetails(
            region=Region.FLANDERS,
            is_first_home=True,
            property_type=property_type,
            purchase_price=Decimal("300000.00"),
        ),
    )


def _types(profile: ApplicationProfile) -> set[DocumentType]:
    return {requirement.doc_type for requirement in required_documents(profile)}


def test_base_requirements_always_present():
    # DOC-006. True for every borrower, including EmploymentType.OTHER, which
    # adds nothing at all (DOC-011).
    for employment in EmploymentType:
        assert {
            DocumentType.IDENTITY,
            DocumentType.BANK_STATEMENTS,
            DocumentType.PURCHASE_AGREEMENT,
        } <= _types(_profile(employment=employment))

    assert _types(_profile(employment=EmploymentType.OTHER)) == {
        DocumentType.IDENTITY,
        DocumentType.BANK_STATEMENTS,
        DocumentType.PURCHASE_AGREEMENT,
        DocumentType.EPC,
    }


def test_employee_adds_payslips_and_employer_statement():
    types = _types(_profile(employment=EmploymentType.EMPLOYEE))

    assert DocumentType.PAYSLIPS in types
    assert DocumentType.EMPLOYER_STATEMENT in types


def test_self_employed_adds_tax_assessment_and_accountant_statement():
    types = _types(_profile(employment=EmploymentType.SELF_EMPLOYED))

    assert DocumentType.TAX_ASSESSMENT in types
    assert DocumentType.ACCOUNTANT_STATEMENT in types
    assert DocumentType.PAYSLIPS not in types


def test_existing_property_adds_epc():
    types = _types(_profile(property_type=PropertyType.EXISTING))

    assert DocumentType.EPC in types
    assert DocumentType.BUILDING_PERMIT not in types


def test_new_build_adds_permit_and_quote():
    types = _types(_profile(property_type=PropertyType.NEW_BUILD))

    assert DocumentType.BUILDING_PERMIT in types
    assert DocumentType.CONSTRUCTION_QUOTE in types
    assert DocumentType.EPC not in types


def test_existing_credit_adds_loan_statements():
    assert DocumentType.EXISTING_LOAN_STATEMENTS in _types(_profile(has_existing_credit=True))
    assert DocumentType.EXISTING_LOAN_STATEMENTS not in _types(_profile(has_existing_credit=False))


def test_requirement_satisfied_by_any_document_of_type():
    # DOC-008: satisfied per doc_type, not per file. Two payslips satisfy the
    # payslip row once, and the row stays satisfied while either remains.
    requirements = required_documents(_profile())
    uploaded = frozenset({DocumentType.IDENTITY, DocumentType.PAYSLIPS})

    marked = {r.doc_type: r.satisfied for r in mark_satisfied(requirements, uploaded)}

    assert marked[DocumentType.IDENTITY] is True
    assert marked[DocumentType.PAYSLIPS] is True
    assert marked[DocumentType.BANK_STATEMENTS] is False


def test_conditional_requirements_carry_a_reason():
    # API-046, UX-038. Base rows carry none: nothing conditional produced them.
    by_type = {r.doc_type: r for r in required_documents(_profile())}

    assert by_type[DocumentType.IDENTITY].reason is None
    assert by_type[DocumentType.PAYSLIPS].reason == "Required because you selected employed"
    assert by_type[DocumentType.EPC].reason == "Required for an existing property"


def test_changing_employment_type_changes_required_set():
    # SCP-022, and the reason the checklist is computed on read (API-047):
    # nothing has to be migrated when a borrower changes their answer.
    employee = _types(_profile(employment=EmploymentType.EMPLOYEE))
    self_employed = _types(_profile(employment=EmploymentType.SELF_EMPLOYED))

    assert employee != self_employed
