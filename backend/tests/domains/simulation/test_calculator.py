"""The Belgian rate convention, which is the one thing here that cannot be wrong.

Every figure is from 0-business-logic.md AC-002 and was computed, not estimated.
A change that moves one of them is a regression, not a refinement.
"""

from decimal import Decimal

import pytest

from app.core.errors import SimulationError
from app.domains.simulation.calculator import (
    annuity,
    build_amortisation_schedule,
    monthly_rate,
)


def test_monthly_rate_uses_actuarial_conversion():
    # AC-002: 5.46% annual converts to 0.00443996 monthly, to 8 decimal places.
    rate = monthly_rate(Decimal("0.0546"))

    assert round(rate, 8) == Decimal("0.00443996")


def test_monthly_rate_roundtrips_to_annual():
    # SIM-003: (1 + i)**12 == 1 + I, within 1e-12.
    rate = monthly_rate(Decimal("0.0546"))

    assert abs((Decimal(1) + rate) ** 12 - Decimal("1.0546")) < Decimal("1e-12")


def test_monthly_rate_differs_from_naive_division():
    # SIM-002. A regression guard, not a formula check: it exists so nobody
    # "simplifies" this into the consumer-credit convention in six months.
    # The gap is small per month and EUR 12.62 per payment at AC-001's figures.
    annual = Decimal("0.0546")

    assert monthly_rate(annual) != annual / 12
    assert monthly_rate(annual) < annual / 12


def test_monthly_rate_zero_returns_zero():
    # SIM-005's precondition: a zero annual rate has a zero periodic rate, and
    # the annuity formula takes its separate branch rather than dividing by it.
    assert monthly_rate(Decimal("0")) == Decimal("0")


def test_monthly_rate_negative_raises():
    with pytest.raises(SimulationError) as exc:
        monthly_rate(Decimal("-0.01"))

    assert exc.value.code == "RATE_OUT_OF_RANGE"


def test_annuity_matches_kbc_published_example():
    # AC-001: KBC representative example, EUR 170 000 over 240 months at 5.46%.
    # The published figure is 1152.96; it derives from a rounded rate, which is
    # where the one-cent tolerance comes from.
    payment = annuity(Decimal("170000"), monthly_rate(Decimal("0.0546")), 240)

    assert abs(payment - Decimal("1152.96")) <= Decimal("0.02")


def test_annuity_zero_rate_returns_principal_over_term():
    # SIM-005: the formula divides by zero at I == 0, so this is a branch,
    # not a special case of the general one. AC-007: 120000 over 240 -> 500.00.
    assert annuity(Decimal("120000"), Decimal("0"), 240) == Decimal("500.00")


def test_annuity_naive_division_overstates_payment():
    # SIM-002 in money rather than in rates: dividing by twelve produces
    # 1165.57 against the correct 1152.95, EUR 12.62 a month too much.
    naive = annuity(Decimal("170000"), Decimal("0.0546") / 12, 240)
    actual = annuity(Decimal("170000"), monthly_rate(Decimal("0.0546")), 240)

    assert naive > actual
    assert round(naive - actual, 2) == Decimal("12.62")


def test_schedule_closes_at_exactly_zero():
    # AC-006. Not "close to zero": exactly 0.00.
    schedule = build_amortisation_schedule(Decimal("270000"), Decimal("0.04"), 300)

    assert schedule.entries[-1].balance == Decimal("0.00")


def test_schedule_principal_sums_to_loan_amount():
    # AC-006: every cent of capital is repaid, no more and no less.
    schedule = build_amortisation_schedule(Decimal("270000"), Decimal("0.04"), 300)

    assert sum(entry.principal for entry in schedule.entries) == Decimal("270000")


def test_schedule_final_instalment_absorbs_rounding():
    # SIM-009. The residue lands in the last instalment rather than being
    # spread or dropped, so total_paid is the sum of what is actually charged
    # and not 300 x 1414.52. AC-003 recorded 424355.98 until T07 — the
    # unrounded payment times the term, which no schedule produces.
    schedule = build_amortisation_schedule(Decimal("270000"), Decimal("0.04"), 300)
    last = schedule.entries[-1]

    assert last.interest + last.principal != schedule.monthly_payment
    assert schedule.total_paid == Decimal("424356.04")
