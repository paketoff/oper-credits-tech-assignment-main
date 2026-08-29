"""What the borrower needs in the bank on the day, which is the number they came for.

The tax matrix is AC-004 and the regional rates are SIM-011. The Brussels rows
are a different mechanism from the other two, not a different number.
"""

from decimal import Decimal

import pytest

from app.core.enums import Region
from app.domains.simulation.calculator import compute_upfront_costs, registration_duty
from app.domains.simulation.entities import SimulationInput


@pytest.mark.parametrize(
    ("region", "is_first_home", "expected"),
    [
        (Region.FLANDERS, True, Decimal("6000.00")),
        (Region.FLANDERS, False, Decimal("36000.00")),
        (Region.WALLONIA, True, Decimal("9000.00")),
        (Region.WALLONIA, False, Decimal("37500.00")),
        (Region.BRUSSELS, True, Decimal("12500.00")),
        (Region.BRUSSELS, False, Decimal("37500.00")),
    ],
)
def test_registration_duty_regional_matrix(region, is_first_home, expected):
    # AC-004, all six rows, on a EUR 300 000 property.
    assert registration_duty(Decimal("300000"), region, is_first_home) == expected


def test_brussels_abattement_never_returns_negative():
    # SIM-012: an allowance on the first slice, not a reduced rate. Below the
    # threshold the taxable base is max(0, price - 200 000), never a negative
    # number that would turn a tax into a refund.
    duty = registration_duty(Decimal("150000"), Region.BRUSSELS, True)

    assert duty >= Decimal("0")


def test_brussels_below_abattement_returns_zero():
    # VAL-020: exactly zero at and below the threshold, not a rounding artefact.
    assert registration_duty(Decimal("150000"), Region.BRUSSELS, True) == Decimal("0.00")
    assert registration_duty(Decimal("200000"), Region.BRUSSELS, True) == Decimal("0.00")


def _primary_case() -> SimulationInput:
    return SimulationInput(
        property_value=Decimal("300000"),
        own_contribution=Decimal("30000"),
        term_months=300,
        annual_nominal_rate=Decimal("0.04"),
        region=Region.FLANDERS,
        is_first_home=True,
    )


def test_upfront_total_is_sum_of_components():
    # SIM-010. AC-003: 6000 + 3300 + 3240 + 350 + 285 = 13175.00.
    costs = compute_upfront_costs(_primary_case(), Decimal("270000"))

    assert costs.total_costs == (
        costs.registration_duty
        + costs.notary_fee
        + costs.mortgage_costs
        + costs.dossier_fee
        + costs.valuation_fee
    )
    assert costs.total_costs == Decimal("13175.00")


def test_total_cash_needed_includes_own_contribution():
    # SIM-013: the tax is paid from savings and cannot be financed, so the
    # headline figure is contribution + costs. AC-003: 30000 + 13175 = 43175.
    costs = compute_upfront_costs(_primary_case(), Decimal("270000"))

    assert costs.total_cash_needed == Decimal("43175.00")
    assert costs.total_cash_needed == costs.own_contribution + costs.total_costs
