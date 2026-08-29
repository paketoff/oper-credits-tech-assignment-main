"""Pure Belgian mortgage arithmetic: rate, annuity, schedule, costs, JKP.

No database, no IO, no framework imports, and entirely synchronous (CQ-048):
the maths is CPU-bound, and an `async def` around a few hundred `Decimal`
iterations would block the event loop for every other request.

This module is the one place in the codebase where being wrong is not
recoverable by good structure, so it is specified to the cent in
`0-business-logic.md` Part III and its acceptance criteria AC-001 – AC-008 are
the test suite rather than a suggestion.
"""

from decimal import Decimal

from app.core.errors import SimulationError

_MONTHS_PER_YEAR = 12
_ONE = Decimal(1)


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
