"""Pure: derives the required document set from an application (DOC-005).

**The required set is a function, not a list.** An employee needs payslips; a
self-employed borrower needs tax assessments and an accountant's statement; an
existing home needs an energy certificate and a new build needs a permit and
quotes. A static checklist is a design error rather than a simplification, and
it is a large part of why Belgian mortgage files arrive incomplete.
"""

from app.core.enums import DocumentType
from app.domains.applications.entities import (
    ApplicationProfile,
    Borrower,
    DocumentRequirement,
    EmploymentType,
    PropertyType,
)

_LABELS: dict[DocumentType, tuple[str, str]] = {
    DocumentType.IDENTITY: ("Identity document", "identiteitskaart"),
    DocumentType.BANK_STATEMENTS: ("Bank statements", "rekeninguittreksels"),
    DocumentType.PURCHASE_AGREEMENT: ("Purchase agreement", "compromis"),
    DocumentType.PAYSLIPS: ("Recent payslips", "loonfiches"),
    DocumentType.EMPLOYER_STATEMENT: ("Employer statement", "werkgeversattest"),
    DocumentType.TAX_ASSESSMENT: ("Tax assessment", "aanslagbiljet"),
    DocumentType.ACCOUNTANT_STATEMENT: ("Accountant's statement", "boekhoudersattest"),
    DocumentType.EXISTING_LOAN_STATEMENTS: ("Existing loan statements", "kredietoverzichten"),
    DocumentType.EPC: ("Energy performance certificate", "energieprestatiecertificaat"),
    DocumentType.BUILDING_PERMIT: ("Building permit", "bouwvergunning"),
    DocumentType.CONSTRUCTION_QUOTE: ("Construction quote", "bestek"),
}

# DOC-006. Always required, whoever is borrowing and whatever they are buying.
_BASE = (
    DocumentType.IDENTITY,
    DocumentType.BANK_STATEMENTS,
    DocumentType.PURCHASE_AGREEMENT,
)

_EMPLOYMENT_RULES: dict[EmploymentType, tuple[tuple[DocumentType, ...], str]] = {
    EmploymentType.EMPLOYEE: (
        (DocumentType.PAYSLIPS, DocumentType.EMPLOYER_STATEMENT),
        "Required because you selected employed",
    ),
    EmploymentType.SELF_EMPLOYED: (
        (DocumentType.TAX_ASSESSMENT, DocumentType.ACCOUNTANT_STATEMENT),
        "Required because you selected self-employed",
    ),
    # EmploymentType.OTHER is absent on purpose, not by oversight (DOC-011).
}

_PROPERTY_RULES: dict[PropertyType, tuple[tuple[DocumentType, ...], str]] = {
    PropertyType.EXISTING: (
        (DocumentType.EPC,),
        "Required for an existing property",
    ),
    PropertyType.NEW_BUILD: (
        (DocumentType.BUILDING_PERMIT, DocumentType.CONSTRUCTION_QUOTE),
        "Required for a new build",
    ),
}

_EXISTING_CREDIT_REASON = "Required because you have an existing credit"


def _requirement(doc_type: DocumentType, reason: str | None) -> DocumentRequirement:
    """Build one row, looking its labels up once."""
    label_en, label_nl = _LABELS[doc_type]
    return DocumentRequirement(
        doc_type=doc_type,
        label_en=label_en,
        label_nl=label_nl,
        required=True,
        reason=reason,
    )


def _employment_requirements(borrowers: tuple[Borrower, ...]) -> list[DocumentRequirement]:
    """Collect what the borrowers' employment types add, without duplicating."""
    seen: dict[DocumentType, str] = {}
    for borrower in borrowers:
        rule = _EMPLOYMENT_RULES.get(borrower.employment_type)
        if rule is None:
            continue
        doc_types, reason = rule
        for doc_type in doc_types:
            seen.setdefault(doc_type, reason)
    return [_requirement(doc_type, reason) for doc_type, reason in seen.items()]


def required_documents(application: ApplicationProfile) -> list[DocumentRequirement]:
    """Derive the document checklist for one application.

    Args:
        application: The borrowers and the property. Nothing else is an input,
            which is what makes this testable and what makes the checklist
            change the moment an answer changes (SCP-022).

    Returns:
        The required rows, base first, in a stable order so the list does not
        reshuffle under the borrower between two reads.
    """
    requirements = [_requirement(doc_type, None) for doc_type in _BASE]
    requirements.extend(_employment_requirements(application.borrowers))

    if any(borrower.has_existing_credit for borrower in application.borrowers):
        requirements.append(
            _requirement(DocumentType.EXISTING_LOAN_STATEMENTS, _EXISTING_CREDIT_REASON)
        )

    doc_types, reason = _PROPERTY_RULES[application.property_details.property_type]
    requirements.extend(_requirement(doc_type, reason) for doc_type in doc_types)
    return requirements


def mark_satisfied(
    requirements: list[DocumentRequirement],
    uploaded: frozenset[DocumentType],
) -> list[DocumentRequirement]:
    """Mark which requirements the uploaded documents already cover.

    A requirement is satisfied by **at least one** document of its type, not by
    one document per requirement: two payslips satisfy the payslip row once, and
    removing one of them leaves it satisfied (DOC-008).

    Args:
        requirements: The derived checklist.
        uploaded: The distinct `doc_type` values attached to the application.

    Returns:
        The same rows with `satisfied` filled in. A new list: the requirements
        are frozen, and mutating an input is how bugs hide (CQ-026).
    """
    return [
        DocumentRequirement(
            doc_type=requirement.doc_type,
            label_en=requirement.label_en,
            label_nl=requirement.label_nl,
            required=requirement.required,
            reason=requirement.reason,
            satisfied=requirement.doc_type in uploaded,
        )
        for requirement in requirements
    ]
