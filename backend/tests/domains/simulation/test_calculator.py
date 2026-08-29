"""The Belgian rate convention, which is the one thing here that cannot be wrong.

Every figure is from 0-business-logic.md AC-002 and was computed, not estimated.
A change that moves one of them is a regression, not a refinement.
"""

from decimal import Decimal

import pytest

from app.core.errors import SimulationError
from app.domains.simulation.calculator import monthly_rate


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
