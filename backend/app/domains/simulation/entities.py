"""Domain types the service and the calculator exchange (ARC-043).

Not the wire schemas. `SimulationRequest` and `SimulationResponse` are pydantic
models in `schemas.py` and they cross the wire; the types here cross the
service-to-calculator boundary. They are deliberately different types with
overlapping fields, because a pure module may not import a pydantic schema
(ARC-013) and the service is what converts between the two.

Frozen dataclasses rather than pydantic: these never face a client, so they need
no validation or serialisation, and CQ-024 asks for pydantic at the *boundary*.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.core.enums import Region


@dataclass(frozen=True, slots=True)
class ScheduleEntry:
    """One month of an amortisation schedule."""

    month: int
    interest: Decimal
    principal: Decimal
    balance: Decimal


@dataclass(frozen=True, slots=True)
class AmortisationSchedule:
    """A full repayment plan, computed but not rendered (SIM-008, SCP-013).

    `total_paid` is the sum of the instalments actually charged, which is not
    `monthly_payment * term_months`: the final instalment absorbs the rounding
    residue so the balance closes at exactly zero (SIM-009). On AC-003's figures
    the difference is two cents, and showing a total that does not match the
    schedule is how a simulator loses credibility.
    """

    monthly_payment: Decimal
    entries: tuple[ScheduleEntry, ...]
    total_interest: Decimal
    total_paid: Decimal


@dataclass(frozen=True, slots=True)
class SimulationInput:
    """What the borrower told us, on its way into the calculator.

    The service builds this from `SimulationRequest`. They carry the same fields
    and are deliberately different types: a pure module may not import a
    pydantic wire schema (ARC-013, ARC-043).
    """

    property_value: Decimal
    own_contribution: Decimal
    term_months: int
    annual_nominal_rate: Decimal
    region: Region
    is_first_home: bool


@dataclass(frozen=True, slots=True)
class UpfrontCosts:
    """The cash the borrower needs on the day of signing.

    The second of the two headline figures, and the one most simulators bury or
    omit. `registration_duty` is paid from savings and cannot be financed
    (SIM-013), which is why `total_cash_needed` and not `total_costs` is what
    the result panel leads with.
    """

    registration_duty: Decimal
    notary_fee: Decimal
    mortgage_costs: Decimal
    dossier_fee: Decimal
    valuation_fee: Decimal
    total_costs: Decimal
    own_contribution: Decimal
    total_cash_needed: Decimal


@dataclass(frozen=True, slots=True)
class SimulationResult:
    """Everything the calculator produces, on its way back to the service.

    `above_supervisory_norm` is a flag and never an error: the Belgian 90% norm
    is a supervisory expectation, not a statutory cap, and rejecting a loan for
    exceeding it would be wrong (DOM-016, ERR-006).

    The schedule is carried even though no screen renders it (SCP-013). It is
    what the totals are derived from, and dropping it here would mean
    recomputing it to show anything about the loan later.
    """

    loan_amount: Decimal
    quotiteit: Decimal
    above_supervisory_norm: bool
    monthly_payment: Decimal
    total_paid: Decimal
    total_interest: Decimal
    nominal_rate: Decimal
    jkp: Decimal
    upfront: UpfrontCosts
    schedule: AmortisationSchedule
