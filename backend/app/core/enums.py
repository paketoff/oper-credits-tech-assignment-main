"""Value enums two domains share. Imports nothing (ARC-044).

Only genuinely shared types live here. `PropertyType`, `EmploymentType` and
`ApplicationStatus` each belong to one domain and stay in that domain's
`entities.py`.

The alternative — a copy of `DocumentType` in `applications/` and another in
`documents/` — fails the first time one of them gains a member: the checklist
and the upload validator would then disagree about what satisfies a
requirement, which is the one thing DOC-008 cannot survive.
"""

from enum import StrEnum


class Region(StrEnum):
    """A Belgian region. Drives purchase tax and nothing else (DOM-007).

    Priced by `simulation/calculator.py`, stored by `applications/`.
    """

    FLANDERS = "FLANDERS"
    WALLONIA = "WALLONIA"
    BRUSSELS = "BRUSSELS"


class DocumentType(StrEnum):
    """A supporting document a borrower may be asked for.

    Eleven members, from DOC-006 (the three always required) and DOC-007 (the
    conditional ones). `UNKNOWN` is deliberately absent: it is a classifier
    output, never a checklist requirement and never a stored `doc_type`
    (AI-012).

    Derived into requirements by `applications/checklist.py`, validated against
    on upload by `documents/`.
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
