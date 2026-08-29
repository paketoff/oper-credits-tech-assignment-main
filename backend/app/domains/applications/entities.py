"""Domain types for applications, borrowers and the property.

Frozen dataclasses and enums. Not the wire schemas, which are pydantic and live
in `schemas.py` (ARC-040).
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from app.core.enums import DocumentType, Region


class ApplicationStatus(StrEnum):
    """Where an application sits in its lifecycle (0-business-logic.md §12).

    Single-domain, so it lives here rather than in `core/enums.py` (ARC-044).

    `UNDER_REVIEW` collapses three distinct real-world gates — property
    valuation, CKP credit-register consultation, and credit assessment. Named as
    one state with this comment rather than silently omitted (APP-010, SCP-018).
    """

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    DOCUMENTS_PENDING = "DOCUMENTS_PENDING"
    DOCUMENTS_COMPLETE = "DOCUMENTS_COMPLETE"
    UNDER_REVIEW = "UNDER_REVIEW"
    OFFER_ISSUED = "OFFER_ISSUED"
    WITHDRAWN = "WITHDRAWN"


class EmploymentType(StrEnum):
    """How a borrower earns. Drives most of the conditional checklist (DOC-007).

    `OTHER` is the honest bucket for a borrower who is neither employed nor
    self-employed — a pensioner, a student, someone between jobs. It adds no
    requirement, deliberately: there is no single document set that fits all of
    them, so a credit analyst asks by hand (DOC-011).
    """

    EMPLOYEE = "EMPLOYEE"
    SELF_EMPLOYED = "SELF_EMPLOYED"
    OTHER = "OTHER"


class PropertyType(StrEnum):
    """Existing home or new build. Changes which property documents apply."""

    EXISTING = "EXISTING"
    NEW_BUILD = "NEW_BUILD"


@dataclass(frozen=True, slots=True)
class Borrower:
    """One person on the application.

    Income is captured but not used for a decision: affordability is a
    deliberate cut (DOM-023, SCP-011).
    """

    full_name: str
    date_of_birth: date
    employment_type: EmploymentType
    monthly_net_income: Decimal | None
    has_existing_credit: bool


@dataclass(frozen=True, slots=True)
class PropertyDetails:
    """The house being bought.

    `is_first_home` sits here and not on a borrower on purpose: if any
    co-borrower has previously held a mortgage the status is lost for all of
    them, and modelling it per borrower would encode the rule incorrectly
    (DOM-024).
    """

    region: Region
    is_first_home: bool
    property_type: PropertyType
    purchase_price: Decimal


@dataclass(frozen=True, slots=True)
class ApplicationProfile:
    """The part of an application the checklist is a function of.

    Deliberately narrower than the stored application: the checklist depends on
    who is borrowing and what they are buying, and on nothing else. Passing the
    whole row would let an unrelated field quietly become an input.
    """

    borrowers: tuple[Borrower, ...]
    property_details: PropertyDetails


@dataclass(frozen=True, slots=True)
class DocumentRequirement:
    """One row of the derived checklist.

    `reason` is populated only for conditional rows (API-046). It is what stops
    the list feeling arbitrary and what shows the checklist is derived rather
    than fixed — the product point of the whole build (UX-038).
    """

    doc_type: DocumentType
    label_en: str
    label_nl: str
    required: bool
    reason: str | None
    satisfied: bool = False


@dataclass(frozen=True, slots=True)
class Application:
    """A borrower's mortgage file.

    `borrowers` is a collection from the start even though the UI fills one.
    Most Belgian mortgages are joint, and adding the second is then a form
    problem rather than a migration (DOM-021, SCP-010).

    `status` is a stored column, not a derived value: transitions are written in
    the same transaction as the change that caused them (CQ-087). It is also not
    writable over the wire — moving state is an action, never a PATCH on a field
    (API-011, API-038).
    """

    id: UUID
    user_id: UUID
    simulation_id: UUID | None
    status: ApplicationStatus
    borrowers: tuple[Borrower, ...]
    property_details: PropertyDetails | None
    submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def profile(self) -> ApplicationProfile:
        """Narrow this to what the checklist is a function of (DOC-005).

        Raises:
            ValueError: If the property section has not been filled yet. A
                checklist cannot be derived from an application that does not
                yet say what is being bought.
        """
        if self.property_details is None:
            raise ValueError("an application without property details has no checklist")
        return ApplicationProfile(borrowers=self.borrowers, property_details=self.property_details)
