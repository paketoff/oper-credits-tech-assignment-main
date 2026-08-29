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
