"""The whole calculation, end to end. AC-003, AC-005, AC-007.

These figures are the opening screen of the application as well as the test
suite: UX-010 prefills the simulator with exactly these inputs, so if one moves
the other moves with it.
"""

from decimal import Decimal

import pytest

from app.core.enums import Region
from app.core.errors import SimulationError
from app.domains.simulation.calculator import simulate
from app.domains.simulation.entities import SimulationInput


def _case(own_contribution: str = "30000", is_first_home: bool = True) -> SimulationInput:
    return SimulationInput(
        property_value=Decimal("300000"),
        own_contribution=Decimal(own_contribution),
        term_months=300,
        annual_nominal_rate=Decimal("0.04"),
        region=Region.FLANDERS,
        is_first_home=is_first_home,
    )


def test_simulate_primary_case_full_output():
    # AC-003, to the cent.
    result = simulate(_case())

    assert result.loan_amount == Decimal("270000.00")
    assert result.quotiteit == Decimal("0.9000")
    assert result.monthly_payment == Decimal("1414.52")
    assert result.total_paid == Decimal("424356.04")
    assert result.total_interest == Decimal("154356.04")
    assert result.upfront.total_cash_needed == Decimal("43175.00")
    assert round(result.jkp, 4) == Decimal("0.0414")


def test_simulate_first_home_flip_changes_cash_by_thirty_thousand():
    # AC-005: the same house and the same loan, EUR 30 000 apart in cash.
    first = simulate(_case(is_first_home=True))
    standard = simulate(_case(is_first_home=False))

    difference = standard.upfront.total_cash_needed - first.upfront.total_cash_needed
    assert difference == Decimal("30000.00")


def test_simulate_zero_own_contribution_flags_above_norm():
    # AC-007, VAL-020: valid, not an error. Quotiteit is 100% and the flag is
    # informational — Belgium has no statutory LTV cap (DOM-016).
    result = simulate(_case(own_contribution="0"))

    assert result.quotiteit == Decimal("1.0000")
    assert result.above_supervisory_norm is True


def test_simulate_quotiteit_exactly_ninety_is_not_flagged():
    # VAL-020: the flag is > 0.90, not >=. The primary case sits exactly on
    # the norm, which makes this the boundary worth pinning.
    result = simulate(_case())

    assert result.quotiteit == Decimal("0.9000")
    assert result.above_supervisory_norm is False


def test_simulate_own_contribution_equals_price_raises():
    # AC-007, DOM-012: the loan would be zero, so there is nothing to simulate.
    with pytest.raises(SimulationError) as exc:
        simulate(_case(own_contribution="300000"))

    assert exc.value.code == "LOAN_AMOUNT_NOT_POSITIVE"
    assert exc.value.field == "own_contribution"


def test_simulate_all_money_values_are_decimal():
    # DOM-003, SCP-024. float anywhere here loses cents, and the whole build is
    # judged on these numbers.
    result = simulate(_case())
    money = [
        result.loan_amount,
        result.monthly_payment,
        result.total_paid,
        result.total_interest,
        result.upfront.registration_duty,
        result.upfront.total_costs,
        result.upfront.total_cash_needed,
    ]

    assert all(isinstance(value, Decimal) for value in money)
    assert not any(isinstance(value, float) for value in money)
