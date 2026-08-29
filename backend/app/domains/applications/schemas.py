"""Pydantic request and response models for the application wire contract."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import Region
from app.domains.applications.entities import ApplicationStatus, EmploymentType, PropertyType
from app.domains.simulation.schemas import Money


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
