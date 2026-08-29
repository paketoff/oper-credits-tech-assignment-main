"""Pure Belgian mortgage arithmetic: rate, annuity, schedule, costs, JKP.

No database, no IO, no framework imports, and entirely synchronous (CQ-048):
the maths is CPU-bound, and an `async def` around a few hundred `Decimal`
iterations would block the event loop for every other request.

This module is the one place in the codebase where being wrong is not
recoverable by good structure, so it is specified to the cent in
`0-business-logic.md` Part III and its acceptance criteria AC-001 – AC-008 are
the test suite rather than a suggestion.
"""

from decimal import ROUND_HALF_UP, Decimal, DivisionByZero, InvalidOperation, Overflow

from app.core.enums import Region
from app.core.errors import SimulationError
from app.domains.simulation.entities import (
    AmortisationSchedule,
    ScheduleEntry,
    SimulationInput,
    SimulationResult,
    UpfrontCosts,
)

_MONTHS_PER_YEAR = 12
_ONE = Decimal(1)
_CENT = Decimal("0.01")

# SIM-011. Standard rate, and the first-home rate where the region uses one.
# Brussels is absent on purpose: it applies an abattement, not a reduced rate,
# and modelling it as a rate would be the wrong mechanism (SIM-012).
_STANDARD_DUTY = {
    Region.FLANDERS: Decimal("0.12"),
    Region.WALLONIA: Decimal("0.125"),
    Region.BRUSSELS: Decimal("0.125"),
}
_FIRST_HOME_DUTY = {
    Region.FLANDERS: Decimal("0.02"),
    Region.WALLONIA: Decimal("0.03"),
}
_BRUSSELS_ABATTEMENT = Decimal("200000")

# SIM-010, SIM-014. The notary fee is a flat stand-in for a degressive tariff
# set by royal decree — a known simplification, flagged as SCP-016 rather than
# hidden.
_NOTARY_FEE = Decimal("3300.00")
_DOSSIER_FEE = Decimal("350.00")
_VALUATION_FEE = Decimal("285.00")
_MORTGAGE_COST_RATE = Decimal("0.012")

# SIM-018. Bisection bracket and tolerance for the JKP solve.
_JKP_LOW = Decimal("0.0001")
_JKP_HIGH = Decimal("0.30")
_JKP_TOLERANCE = Decimal("1e-10")

# DOM-015, API-006. Quotiteit is reported as a four-decimal fraction: 0.9000.
_RATIO = Decimal("0.0001")
# DOM-016. The Belgian supervisory norm. Strictly greater, never >=.
_SUPERVISORY_NORM = Decimal("0.90")


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


def registration_duty(property_value: Decimal, region: Region, is_first_home: bool) -> Decimal:
    """Compute the regional purchase tax (`registratierechten`).

    Two different mechanisms, not two different numbers. Flanders and Wallonia
    give a first-home buyer a **reduced rate**; Brussels instead grants an
    **abattement**, an allowance on the first slice of the price, and taxes the
    remainder at the standard rate (SIM-011, SIM-012).

    This is the single largest line in the upfront total. On a EUR 300 000 house
    in Flanders, first-home status is worth EUR 30 000 of cash the buyer must
    have on the day, and the tax cannot be financed (SIM-013, AC-005).

    Args:
        property_value: The purchase price.
        region: Which regional regime applies.
        is_first_home: Whether this is the buyer's only home
            (`enige eigen woning`).

    Returns:
        The duty, rounded to the cent. Never negative: below the Brussels
        threshold the taxable base is zero, not a refund.
    """
    if is_first_home and region is Region.BRUSSELS:
        taxable = max(Decimal("0"), property_value - _BRUSSELS_ABATTEMENT)
        return _to_cents(taxable * _STANDARD_DUTY[region])
    if is_first_home and region in _FIRST_HOME_DUTY:
        return _to_cents(property_value * _FIRST_HOME_DUTY[region])
    return _to_cents(property_value * _STANDARD_DUTY[region])


def compute_upfront_costs(request: SimulationInput, loan_amount: Decimal) -> UpfrontCosts:
    """Total up what the borrower must have in the bank on the day of signing.

    Purchase tax, the deed notary, the cost of registering the mortgage, and the
    lender's two fees — plus their own contribution, none of which is financed
    (SIM-010).

    Args:
        request: The borrower's inputs.
        loan_amount: The amount actually borrowed, which is what the mortgage
            registration cost scales with.

    Returns:
        Every component and the two totals, so the breakdown can be shown line
        by line (UX-020) rather than as a single unexplained figure.
    """
    duty = registration_duty(request.property_value, request.region, request.is_first_home)
    mortgage_costs = _to_cents(loan_amount * _MORTGAGE_COST_RATE)
    total_costs = duty + _NOTARY_FEE + mortgage_costs + _DOSSIER_FEE + _VALUATION_FEE

    return UpfrontCosts(
        registration_duty=duty,
        notary_fee=_NOTARY_FEE,
        mortgage_costs=mortgage_costs,
        dossier_fee=_DOSSIER_FEE,
        valuation_fee=_VALUATION_FEE,
        total_costs=total_costs,
        own_contribution=_to_cents(request.own_contribution),
        total_cash_needed=_to_cents(request.own_contribution) + total_costs,
    )


def _present_value(payment: Decimal, term_months: int, annual_rate: Decimal) -> Decimal:
    """Discount a level stream of instalments at an annual rate.

    Uses the same actuarial conversion as the rest of the module (SIM-018):
    the discount factor is the monthly rate implied by `annual_rate`, not that
    rate divided by twelve.

    There is no zero-rate branch here, unlike `annuity`. The only caller is the
    bisection, whose bracket starts at 0.0001 (SIM-018), so `rate` is never zero
    and a guard for it would be unreachable code rather than safety.
    """
    rate = monthly_rate(annual_rate)
    return payment * (_ONE - (_ONE + rate) ** -term_months) / rate


def compute_jkp(
    loan_amount: Decimal,
    monthly_payment: Decimal,
    term_months: int,
    fees: Decimal,
) -> Decimal:
    """Solve for the all-in annual cost (JKP/TAEG) by bisection.

    The rate that equates the present value of what the borrower receives to the
    present value of what they pay. What they receive is the loan **less the
    fees deducted from it** — the mortgage registration cost, the dossier fee
    and the valuation fee (SIM-016). Purchase tax and the deed notary fee are
    excluded: they are costs of buying a house, not costs of credit (SIM-017).

    Args:
        loan_amount: The nominal amount borrowed.
        monthly_payment: The instalment, already rounded to the cent.
        term_months: The term, in months.
        fees: The charges that legally belong in the JKP base.

    Returns:
        The effective annual rate. Always above the nominal rate, and in
        practice strictly above it: equality means the fees were never applied
        (SIM-019, AC-008).

    Raises:
        SimulationError: JKP_COMPUTATION_FAILED if there is no rate in the
            bracket that balances the two sides. `Decimal` raises errors that
            mean nothing to an API consumer, so they are translated here
            (CQ-054).
    """
    advance = loan_amount - fees
    if advance <= 0:
        raise SimulationError(code="JKP_COMPUTATION_FAILED")
    try:
        return _bisect_for_effective_rate(advance, monthly_payment, term_months)
    except (InvalidOperation, DivisionByZero, Overflow) as exc:
        raise SimulationError(code="JKP_COMPUTATION_FAILED") from exc


def _bisect_for_effective_rate(
    advance: Decimal,
    monthly_payment: Decimal,
    term_months: int,
) -> Decimal:
    """Halve the bracket until it is narrower than the tolerance (SIM-018).

    Present value falls as the rate rises, so the sign test is inverted
    relative to the usual formulation.
    """
    low, high = _JKP_LOW, _JKP_HIGH
    while high - low > _JKP_TOLERANCE:
        middle = (low + high) / 2
        if _present_value(monthly_payment, term_months, middle) > advance:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def simulate(request: SimulationInput) -> SimulationResult:
    """Run a full mortgage simulation.

    An orchestrator, per CQ-036 and CQ-037: every step below is a named function
    that is independently testable, and the body reads as a table of contents.

    Args:
        request: Validated borrower inputs.

    Returns:
        Payment figures, JKP, and the upfront cash breakdown.

    Raises:
        SimulationError: LOAN_AMOUNT_NOT_POSITIVE if the borrower would be
            putting in the whole price, leaving nothing to lend (DOM-012).
    """
    loan_amount = _to_cents(request.property_value - request.own_contribution)
    if loan_amount <= 0:
        raise SimulationError(code="LOAN_AMOUNT_NOT_POSITIVE", field="own_contribution")

    schedule = build_amortisation_schedule(
        loan_amount, request.annual_nominal_rate, request.term_months
    )
    upfront = compute_upfront_costs(request, loan_amount)
    jkp_fees = upfront.mortgage_costs + upfront.dossier_fee + upfront.valuation_fee
    jkp = compute_jkp(loan_amount, schedule.monthly_payment, request.term_months, jkp_fees)
    quotiteit = (loan_amount / request.property_value).quantize(_RATIO, rounding=ROUND_HALF_UP)

    return SimulationResult(
        loan_amount=loan_amount,
        quotiteit=quotiteit,
        above_supervisory_norm=quotiteit > _SUPERVISORY_NORM,
        monthly_payment=schedule.monthly_payment,
        total_paid=schedule.total_paid,
        total_interest=schedule.total_interest,
        nominal_rate=request.annual_nominal_rate,
        jkp=jkp,
        upfront=upfront,
        schedule=schedule,
    )
