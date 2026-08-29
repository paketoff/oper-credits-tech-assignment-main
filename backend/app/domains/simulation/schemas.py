"""Pydantic request and response models for the simulation wire contract.

**Money and rates cross as strings, never numbers** (API-004, API-005, CQ-014).
`0.1 + 0.2` in JavaScript is the whole reason: a JSON number is a float on the
other side, and this build is judged on cents.

Pydantic renders `Decimal` as a string in JSON mode already, but not at a fixed
width — `Decimal("0.04")` would go out as `"0.04"` where API-005 requires
`"0.0400"`. The serialisers below fix the width, so the frontend never has to
normalise what it was given.
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

from app.core.enums import Region


def _as_money(value: Decimal) -> str:
    """Render an amount with two decimals (API-004)."""
    return f"{value:.2f}"


def _as_rate(value: Decimal) -> str:
    """Render a rate or ratio as a four-decimal fraction (API-005, API-006)."""
    return f"{value:.4f}"


Money = Annotated[Decimal, PlainSerializer(_as_money, return_type=str)]
Rate = Annotated[Decimal, PlainSerializer(_as_rate, return_type=str)]


class SimulationRequest(BaseModel):
    """Inputs for a mortgage simulation.

    The bounds here are pydantic's job — shape and range (VAL-001). The *codes*
    a violation produces are the domain's, so the service re-checks the ranges
    that VAL-008 gives a named code to: a borrower who sets their contribution
    equal to the price should be told exactly that, not "check the highlighted
    fields".
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    property_value: Decimal = Field(max_digits=12, decimal_places=2)
    own_contribution: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    term_months: int
    annual_nominal_rate: Decimal = Field(max_digits=6, decimal_places=4)
    region: Region
    is_first_home: bool


class UpfrontCostsResponse(BaseModel):
    """The cash breakdown, line by line, so it can be shown as a table (UX-020)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    registration_duty: Money
    notary_fee: Money
    mortgage_costs: Money
    dossier_fee: Money
    valuation_fee: Money
    total_costs: Money
    own_contribution: Money
    total_cash_needed: Money


class SimulationResponse(BaseModel):
    """What the borrower gets back. Figures are AC-003 to the cent (API-019)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    loan_amount: Money
    quotiteit: Rate
    above_supervisory_norm: bool
    monthly_payment: Money
    total_paid: Money
    total_interest: Money
    nominal_rate: Rate
    jkp: Rate
    upfront: UpfrontCostsResponse
    created_at: datetime
