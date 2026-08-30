"""Pydantic request and response models for the application wire contract."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import Region
from app.domains.applications.entities import (
    AffordabilityBand,
    ApplicationStatus,
    EmploymentType,
    PropertyType,
    Provenance,
)
from app.domains.simulation.schemas import Money, Rate


class BorrowerRequest(BaseModel):
    """One borrower, as sent by the wizard.

    No `id`: a PATCH replaces the collection wholesale (API-037), so the client
    never needs to name an existing row.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    full_name: str = Field(min_length=1, max_length=200)
    date_of_birth: date
    employment_type: EmploymentType
    monthly_net_income: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    has_existing_credit: bool = False


class BorrowerResponse(BaseModel):
    """One borrower, as returned. Carries an id because DOM-022 gives it one."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    full_name: str
    date_of_birth: date
    employment_type: EmploymentType
    monthly_net_income: Money | None
    has_existing_credit: bool


class PropertyRequest(BaseModel):
    """The property section, as sent by the wizard."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    region: Region
    is_first_home: bool
    property_type: PropertyType
    purchase_price: Decimal = Field(max_digits=12, decimal_places=2)


class PropertyResponse(BaseModel):
    """The property section, as returned.

    `property_type` is nullable on the wire, unlike the domain's
    `PropertyDetails.property_type`. A simulation-seeded draft has a region and
    a price before the borrower has said existing-vs-new-build (UX-027); the
    wizard's property step is what fills this in, and until then this is the
    honest shape of what is actually known.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    region: Region
    is_first_home: bool
    property_type: PropertyType | None
    purchase_price: Money


class ApplicationCreateRequest(BaseModel):
    """The body of `POST /api/applications` (API-032)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    simulation_id: UUID | None = None


class ApplicationPatchRequest(BaseModel):
    """A partial update (API-035).

    Every field defaults to a sentinel rather than `None`, so the service can
    tell "the borrower did not send this" from "the borrower sent an empty
    value" — API-036 validates only what is present. `status` is not a field
    here at all: it is not writable over PATCH (API-011, API-038), and pydantic
    rejects it as an extra key rather than silently accepting it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    borrowers: list[BorrowerRequest] | None = None
    property: PropertyRequest | None = None
    # A borrower who signed up without opening the calculator has an
    # application with no simulation on it, and therefore no instalment for the
    # affordability check to measure against (API-075). Attaching one had no
    # path: the link was made at creation and never again. Unlike `status`,
    # this is data the borrower owns — the service still resolves it through
    # `simulation.service` and refuses one that is not theirs (ARC-047).
    simulation_id: UUID | None = None


class ApplicationResponse(BaseModel):
    """The full application body (API-033)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    status: ApplicationStatus
    simulation_id: UUID | None
    borrowers: list[BorrowerResponse]
    property: PropertyResponse | None = Field(serialization_alias="property")
    submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ApplicationSummary(BaseModel):
    """One row of the summary list (API-029, API-030)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    status: ApplicationStatus
    property: PropertyResponse | None
    documents_required: int
    documents_satisfied: int
    created_at: datetime
    updated_at: datetime


class ApplicationListResponse(BaseModel):
    """Wrapped in `items` so pagination can be added later without breaking the shape (API-030)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    items: list[ApplicationSummary]


class FinancialsRequest(BaseModel):
    """The body of `PUT /api/applications/{id}/financials` (API-073).

    Values only. **Provenance is not accepted from the client** — the service
    records how each figure arrived, and every figure that arrives here was
    submitted by the borrower, whether they typed it or accepted a document's
    proposal into the form first (DOM-029, DOM-030). Letting the caller assert
    `DOCUMENT` would make the audit trail self-reported, which is the one thing
    an audit trail must not be.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    net_monthly_income: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )
    existing_credit_monthly: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )
    dependants: int = Field(default=0, ge=0, le=20)


class ConfirmedAmountResponse(BaseModel):
    """One confirmed figure and where it came from (DOM-029)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    amount: Money
    provenance: Provenance
    source_document_id: UUID | None
    confirmed_at: datetime


class AffordabilityResponse(BaseModel):
    """The assessment, with its workings (SIM-022 - SIM-028).

    `dsti` is a fraction with four decimals, serialised as a string exactly like
    `quotiteit` — the borrower sees the two beside each other, so they are
    formatted the same way (API-005).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    band: AffordabilityBand
    dsti: Rate | None
    monthly_obligations: Money
    residual_income: Money | None
    residual_floor: Money


class FinancialsResponse(BaseModel):
    """The confirmed profile plus the assessment derived from it (API-074).

    `assessment` is null when there is no linked simulation to measure against:
    the mortgage instalment is an input to the assessment (SIM-022), and
    inventing one would be worse than saying there is nothing to compare yet.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    net_monthly_income: ConfirmedAmountResponse | None
    existing_credit_monthly: ConfirmedAmountResponse | None
    dependants: int
    assessment: AffordabilityResponse | None
    updated_at: datetime | None
