"""Domain types for applications, borrowers and the property.

Frozen dataclasses and enums. Not the wire schemas, which are pydantic and live
in `schemas.py` (ARC-040).
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

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

    `borrowers` is a table of its own (DOM-022), so each row carries an id;
    `8-api.md` §6 returns it. A default factory means a test can build one
    without naming it, the way T12's checklist tests already did before this
    field existed.

    `monthly_net_income` is what the borrower typed into the wizard, and the
    affordability assessment deliberately does **not** read it (DOM-023,
    superseded at T53): this collection is replaced wholesale on every PATCH
    (API-037) and carries no provenance. The figure that is assessed lives on
    `FinancialProfile`, where it is confirmed and provenanced (DOM-029).
    """

    full_name: str
    date_of_birth: date
    employment_type: EmploymentType
    monthly_net_income: Decimal | None
    has_existing_credit: bool
    id: UUID = field(default_factory=uuid4)


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
class PropertySeed:
    """What a simulation can prefill about the property, before it is complete.

    A simulation never asks existing-vs-new-build, so `property_type` is not
    here. Kept as a distinct type from `PropertyDetails` rather than making
    that dataclass's field optional: `PropertyDetails.property_type` stays
    required, which is what lets `ApplicationProfile` — and therefore the
    checklist — depend on it being there without a None-check at every use
    (API-032, ARC-047, UX-027).
    """

    region: Region
    is_first_home: bool
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


class Provenance(StrEnum):
    """Where a confirmed financial figure came from (DOM-029).

    An underwriter needs to know whether a number was typed by the borrower or
    read off a document, and it is the audit trail `9-ai-classification.md`
    AI-003 argues for. `DOCUMENT` never means "the model said so" — it means the
    borrower was shown what the model read and confirmed it (DOM-030).
    """

    MANUAL = "MANUAL"
    DOCUMENT = "DOCUMENT"


@dataclass(frozen=True, slots=True)
class ConfirmedAmount:
    """A money figure together with where it came from.

    Provenance travels with the value rather than sitting beside it, so a
    caller cannot read the number and forget to ask how it got there.
    """

    amount: Decimal
    provenance: Provenance
    source_document_id: UUID | None
    confirmed_at: datetime


@dataclass(frozen=True, slots=True)
class FinancialProfile:
    """The confirmed figures an affordability assessment reads (DOM-029).

    One row per application, deliberately **not** columns on `Borrower`:
    `8-api.md` API-037 replaces the borrower collection wholesale on every
    PATCH, so anything stored there is destroyed the next time the borrower
    edits the wizard.

    `dependants` carries no provenance because no document states it — it is
    always something the borrower tells us.
    """

    application_id: UUID
    net_monthly_income: ConfirmedAmount | None
    existing_credit_monthly: ConfirmedAmount | None
    dependants: int
    updated_at: datetime


class AffordabilityBand(StrEnum):
    """How comfortably the household carries this loan (SIM-028).

    A band, never a decision. Nothing in the state machine reads it and it can
    never move an application: a verdict would be credit scoring, which is the
    thing `9-ai-classification.md` AI-003 argues the whole design against.

    `INSUFFICIENT_DATA` is a first-class member rather than a `None` return, so
    every caller renders one of four states instead of branching on optionality
    (SIM-027).
    """

    COMFORTABLE = "COMFORTABLE"
    TIGHT = "TIGHT"
    OUTSIDE_TYPICAL_NORMS = "OUTSIDE_TYPICAL_NORMS"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True, slots=True)
class AffordabilityInput:
    """The part of an application the affordability assessment is a function of.

    Deliberately narrower than the stored financial profile, for the same reason
    `ApplicationProfile` is narrower than `Application`: passing the whole row
    would let an unrelated field quietly become an input. Provenance in
    particular is absent on purpose — where a number came from is a storage and
    audit concern (DOM-029), never an input to the arithmetic.

    `adults` is the number of borrowers on the application (DOM-021), so a joint
    application raises the residual floor without a second field to fill in.
    """

    net_monthly_income: Decimal | None
    existing_credit_monthly: Decimal | None
    dependants: int
    adults: int


@dataclass(frozen=True, slots=True)
class AffordabilityAssessment:
    """The result of §21.2, carrying its own workings.

    `dsti` and `residual_income` are null exactly when the band is
    `INSUFFICIENT_DATA` (SIM-027). `residual_floor` is always present: it is a
    function of household composition alone, so it is knowable even when income
    is not, and the borrower can be told what they would need to clear.
    """

    band: AffordabilityBand
    dsti: Decimal | None
    monthly_obligations: Decimal
    residual_income: Decimal | None
    residual_floor: Decimal


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
    property_seed: PropertySeed | None
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
