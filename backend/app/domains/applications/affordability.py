"""Pure: does this household's income support this loan (SIM-022 – SIM-029)?

No database, no IO, no framework imports, and entirely synchronous (CQ-048,
ARC-013) — the same shape as `checklist.py` and `state_machine.py` beside it.
The mortgage payment arrives as a `Decimal` argument rather than being
recomputed, which is what keeps this module free of any dependency on the
simulation domain.

**The output is a band, never a decision** (SIM-028). Nothing in the state
machine reads it and it can never move an application. This mirrors how an
above-norm quotiteit is treated (DOM-016: flagged, explained, never rejected),
and for the same reason: Oper is explicit that their own credit analyst applies
a written policy and is *not credit scoring*.

**The constants below are representative lender norms, not law** (SIM-029). The
~33% income share is an informal underwriting convention rather than a statutory
cap, and residual-income floors are bank-internal and vary between lenders. They
are named and gathered here — rather than inlined at their use — because they are
the entire tuning surface of this feature and the first thing a reviewer asks
about (SIM-025).
"""

from decimal import ROUND_HALF_UP, Decimal

from app.domains.applications.entities import (
    AffordabilityAssessment,
    AffordabilityBand,
    AffordabilityInput,
)

_CENT = Decimal("0.01")
_ZERO = Decimal("0.00")
# Four decimal places, matching how quotiteit is reported (DOM-015, API-005):
# both are ratios the borrower sees beside each other.
_RATIO = Decimal("0.0001")

# SIM-023. The share of net monthly income committed to credit.
_DSTI_COMFORTABLE_MAX = Decimal("0.33")
_DSTI_TIGHT_MAX = Decimal("0.40")

# SIM-024. What the household must keep after every credit obligation, and how
# its composition grows that floor.
_FLOOR_SINGLE_ADULT = Decimal("1200.00")
_FLOOR_PER_ADDITIONAL_ADULT = Decimal("400.00")
_FLOOR_PER_DEPENDANT = Decimal("300.00")
_RESIDUAL_COMFORTABLE_MULTIPLE = Decimal("1.10")

# SIM-026. Worst-wins ordering: clearing the income share while failing the
# residual floor is not a pass. Declared as a sequence because the bands are a
# StrEnum and carry no ordering of their own.
_SEVERITY: tuple[AffordabilityBand, ...] = (
    AffordabilityBand.COMFORTABLE,
    AffordabilityBand.TIGHT,
    AffordabilityBand.OUTSIDE_TYPICAL_NORMS,
)


def _cents(value: Decimal) -> Decimal:
    """Quantise to two decimal places, ROUND_HALF_UP (DOM-004)."""
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def residual_floor(adults: int, dependants: int) -> Decimal:
    """The monthly income a household must keep after credit (SIM-024).

    Public because it is meaningful on its own: a borrower with no income on
    file can still be told what they would need to clear.

    Args:
        adults: Borrowers on the application. Values below one are treated as
            one — a household with no adults is not a case, and clamping is
            kinder than raising on a field the caller derived rather than typed.
        dependants: People dependent on the household beyond the borrowers.

    Returns:
        The floor, quantised to the cent.
    """
    additional_adults = max(0, adults - 1)
    return _cents(
        _FLOOR_SINGLE_ADULT
        + _FLOOR_PER_ADDITIONAL_ADULT * additional_adults
        + _FLOOR_PER_DEPENDANT * max(0, dependants)
    )


def _dsti_band(dsti: Decimal) -> AffordabilityBand:
    """Band the income share alone (SIM-023)."""
    if dsti <= _DSTI_COMFORTABLE_MAX:
        return AffordabilityBand.COMFORTABLE
    if dsti <= _DSTI_TIGHT_MAX:
        return AffordabilityBand.TIGHT
    return AffordabilityBand.OUTSIDE_TYPICAL_NORMS


def _residual_band(residual: Decimal, floor: Decimal) -> AffordabilityBand:
    """Band the residual income alone (SIM-024)."""
    if residual >= floor * _RESIDUAL_COMFORTABLE_MULTIPLE:
        return AffordabilityBand.COMFORTABLE
    if residual >= floor:
        return AffordabilityBand.TIGHT
    return AffordabilityBand.OUTSIDE_TYPICAL_NORMS


def _worse(first: AffordabilityBand, second: AffordabilityBand) -> AffordabilityBand:
    """The less comfortable of two bands (SIM-026)."""
    return max(first, second, key=_SEVERITY.index)


def assess(profile: AffordabilityInput, monthly_payment: Decimal) -> AffordabilityAssessment:
    """Assess whether the household's income supports this loan.

    Args:
        profile: Confirmed figures only. A value read off a document is a
            proposal until the borrower confirms it and is never an input here
            (DOM-030) — which is what keeps this assessment defensible when the
            classifier is wrong.
        monthly_payment: The mortgage instalment (§15), passed in rather than
            recomputed so this module never imports the simulation domain.

    Returns:
        The band and the workings behind it. Never raises: a missing or
        non-positive income yields `INSUFFICIENT_DATA` rather than a
        `DivisionByZero`, because dividing by an unchecked income is the obvious
        bug here (SIM-027).
    """
    existing_credit = profile.existing_credit_monthly or _ZERO
    obligations = _cents(monthly_payment + existing_credit)
    floor = residual_floor(profile.adults, profile.dependants)
    income = profile.net_monthly_income

    # A ratio against a non-positive income is undefined, and a household with
    # no income is not a case a DSTI model can speak to at all. Saying so beats
    # returning a band the numbers do not support.
    if income is None or income <= _ZERO:
        return AffordabilityAssessment(
            band=AffordabilityBand.INSUFFICIENT_DATA,
            dsti=None,
            monthly_obligations=obligations,
            residual_income=None,
            residual_floor=floor,
        )

    dsti = (obligations / income).quantize(_RATIO, rounding=ROUND_HALF_UP)
    residual = _cents(income - obligations)
    return AffordabilityAssessment(
        band=_worse(_dsti_band(dsti), _residual_band(residual, floor)),
        dsti=dsti,
        monthly_obligations=obligations,
        residual_income=residual,
        residual_floor=floor,
    )
