"""Pure Belgian mortgage arithmetic: rate, annuity, schedule, costs, JKP.

No database, no IO, no framework imports, and entirely synchronous (CQ-048):
the maths is CPU-bound, and an `async def` around a few hundred `Decimal`
iterations would block the event loop for every other request.

This module is the one place in the codebase where being wrong is not
recoverable by good structure, so it is specified to the cent in
`0-business-logic.md` Part III and its acceptance criteria AC-001 – AC-008 are
the test suite rather than a suggestion.
"""

from decimal import ROUND_HALF_UP, Decimal

from app.core.errors import SimulationError
from app.domains.simulation.entities import AmortisationSchedule, ScheduleEntry

_MONTHS_PER_YEAR = 12
_ONE = Decimal(1)
_CENT = Decimal("0.01")


def _to_cents(value: Decimal) -> Decimal:
    """Quantise to two decimal places, half up (DOM-004)."""
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def monthly_rate(annual_rate: Decimal) -> Decimal:
    """Convert a Belgian annual mortgage rate to its monthly periodic rate.

    Belgian mortgage credit derives the annual rate from the periodic rate
    **actuarially**, anchored in art. I.9, 44° of the Wetboek van Economisch
    Recht: `(1 + i) ** 12 == 1 + I`. Dividing by twelve is the *consumer* credit
    convention. It is what almost every online calculator uses and it is wrong
    here — on AC-001's figures it overstates the payment by EUR 12.62 a month,
    which is the difference between output a Belgian lender recognises and
    output they do not (SIM-001, SIM-002).

    The result is deliberately not rounded. Banks quote the periodic rate at six
    decimal places, but the schedule has to reconcile to the cent, so the value
    is carried at full precision and rounded only for display (DOM-006).

    Args:
        annual_rate: Nominal annual rate as a fraction, e.g. Decimal("0.04").

    Returns:
        The monthly periodic rate, unrounded.

    Raises:
        SimulationError: RATE_OUT_OF_RANGE if the rate is negative.
    """
    if annual_rate < 0:
        raise SimulationError(code="RATE_OUT_OF_RANGE", field="annual_nominal_rate")
    if annual_rate == 0:
        return Decimal(0)
    return (_ONE + annual_rate) ** (_ONE / _MONTHS_PER_YEAR) - _ONE


def annuity(principal: Decimal, periodic_rate: Decimal, term_months: int) -> Decimal:
    """Compute the constant monthly instalment of an annuity loan.

    `vaste maandlast`: M = K * i / (1 - (1 + i) ** -n), where i is the *periodic*
    rate from `monthly_rate` and not the annual one (SIM-004).

    The parameter is named `periodic_rate` rather than `monthly_rate` because the
    latter is the function directly above it; a parameter shadowing it inside
    this module would read as a bug.

    Args:
        principal: The loan amount K.
        periodic_rate: The monthly rate i, unrounded.
        term_months: The term n, in months.

    Returns:
        The instalment, rounded to the cent. Rounding here rather than at
        display time is deliberate: the schedule and the totals are built from
        the rounded payment so that the figures shown to the borrower add up
        (SIM-006).
    """
    if periodic_rate == 0:
        return _to_cents(principal / term_months)
    discount = _ONE - (_ONE + periodic_rate) ** -term_months
    return _to_cents(principal * periodic_rate / discount)


def build_amortisation_schedule(
    principal: Decimal,
    annual_rate: Decimal,
    term_months: int,
) -> AmortisationSchedule:
    """Build the full repayment plan, month by month.

    Each month charges interest on the outstanding balance and puts the rest of
    the instalment against capital (SIM-008). The final month is different: it
    repays whatever balance is left rather than the nominal instalment, which is
    what makes the closing balance exactly 0.00 instead of a few cents either
    side (SIM-009, AC-006).

    Args:
        principal: The loan amount.
        annual_rate: The nominal annual rate, as a fraction.
        term_months: The term, in months.

    Returns:
        The schedule, its instalment, and the totals actually charged.
    """
    rate = monthly_rate(annual_rate)
    payment = annuity(principal, rate, term_months)

    entries: list[ScheduleEntry] = []
    balance = _to_cents(principal)
    total_interest = Decimal("0.00")
    total_paid = Decimal("0.00")

    for month in range(1, term_months + 1):
        interest = _to_cents(balance * rate)
        capital = balance if month == term_months else payment - interest
        balance -= capital
        total_interest += interest
        total_paid += interest + capital
        entries.append(ScheduleEntry(month, interest, capital, balance))

    return AmortisationSchedule(
        monthly_payment=payment,
        entries=tuple(entries),
        total_interest=total_interest,
        total_paid=total_paid,
    )
