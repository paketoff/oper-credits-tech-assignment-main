"""Affordability is a band, never a decision. SIM-022 - SIM-029, AC-009.

Tier 1 (T-P5): a pure function with a finite number of branches, so full
coverage is achievable and meaningful. The test that matters most is not any
single band — it is `test_assess_missing_income_returns_insufficient_data`,
because dividing by an unchecked income is the obvious bug in this module, and
`test_assess_takes_the_worse_of_the_two_measures`, because passing on income
share while failing on residual income is not a pass.
"""

from decimal import Decimal

import pytest

from app.domains.applications.affordability import assess, residual_floor
from app.domains.applications.entities import (
    AffordabilityBand,
    AffordabilityInput,
)

# AC-003's primary case, so the two acceptance criteria share a figure.
_PRIMARY_PAYMENT = Decimal("1414.52")


def _profile(
    income: Decimal | None = Decimal("4800.00"),
    existing_credit: Decimal | None = None,
    dependants: int = 0,
    adults: int = 1,
) -> AffordabilityInput:
    return AffordabilityInput(
        net_monthly_income=income,
        existing_credit_monthly=existing_credit,
        dependants=dependants,
        adults=adults,
    )


class TestResidualFloor:
    """SIM-024. Knowable from household composition alone, without income."""

    def test_residual_floor_single_adult_no_dependants_is_the_base(self) -> None:
        assert residual_floor(adults=1, dependants=0) == Decimal("1200.00")

    def test_residual_floor_second_adult_raises_it(self) -> None:
        assert residual_floor(adults=2, dependants=0) == Decimal("1600.00")

    def test_residual_floor_each_dependant_raises_it(self) -> None:
        assert residual_floor(adults=2, dependants=2) == Decimal("2200.00")

    def test_residual_floor_clamps_nonsensical_household_sizes(self) -> None:
        # Both are derived by the caller rather than typed by the borrower, so
        # clamping beats raising.
        assert residual_floor(adults=0, dependants=0) == Decimal("1200.00")
        assert residual_floor(adults=1, dependants=-3) == Decimal("1200.00")


class TestBands:
    """SIM-023 and SIM-024, one measure at a time."""

    @pytest.mark.parametrize(
        ("income", "expected"),
        [
            # 1414.52 / 4800 = 0.2947 -> comfortable on both measures
            (Decimal("4800.00"), AffordabilityBand.COMFORTABLE),
            # 1414.52 / 4000 = 0.3536 -> tight on DSTI, comfortable on residual
            (Decimal("4000.00"), AffordabilityBand.TIGHT),
            # 1414.52 / 3200 = 0.4420 -> outside on DSTI
            (Decimal("3200.00"), AffordabilityBand.OUTSIDE_TYPICAL_NORMS),
        ],
    )
    def test_assess_bands_the_income_share(
        self, income: Decimal, expected: AffordabilityBand
    ) -> None:
        assert assess(_profile(income=income), _PRIMARY_PAYMENT).band is expected

    def test_assess_residual_exactly_on_the_floor_is_tight_not_outside(self) -> None:
        # Income chosen so residual lands exactly on the 1200.00 floor: the
        # boundary belongs to the kinder band.
        result = assess(_profile(income=Decimal("2614.52")), _PRIMARY_PAYMENT)

        assert result.residual_income == Decimal("1200.00")
        assert result.residual_floor == Decimal("1200.00")

    def test_assess_residual_below_the_floor_is_outside_typical_norms(self) -> None:
        result = assess(_profile(income=Decimal("2500.00")), _PRIMARY_PAYMENT)

        assert result.residual_income == Decimal("1085.48")
        assert result.band is AffordabilityBand.OUTSIDE_TYPICAL_NORMS


class TestAssess:
    """The whole function, including the two cases it exists to get right."""

    def test_assess_takes_the_worse_of_the_two_measures(self) -> None:
        """SIM-026. A large income clears DSTI while dependants sink the residual."""
        # A big household on a good income: 1414.52 / 5614.52 = 0.2519, well
        # inside COMFORTABLE on income share. But two adults and eight
        # dependants put the floor at 1200 + 400 + 300*8 = 4000, comfortable
        # only from 4400, and the residual lands at 4200 -> TIGHT. The worse of
        # the two has to win, or a household with plenty of income and no money
        # left over reads as comfortable.
        result = assess(
            _profile(income=Decimal("5614.52"), dependants=8, adults=2),
            _PRIMARY_PAYMENT,
        )

        assert result.dsti == Decimal("0.2519")
        assert result.residual_floor == Decimal("4000.00")
        assert result.residual_income == Decimal("4200.00")
        assert result.band is AffordabilityBand.TIGHT

    def test_assess_missing_income_returns_insufficient_data(self) -> None:
        """SIM-027. Never a DivisionByZero, never a band the numbers cannot support."""
        result = assess(_profile(income=None), _PRIMARY_PAYMENT)

        assert result.band is AffordabilityBand.INSUFFICIENT_DATA
        assert result.dsti is None
        assert result.residual_income is None
        # Still answerable without income, and worth telling the borrower.
        assert result.residual_floor == Decimal("1200.00")
        assert result.monthly_obligations == _PRIMARY_PAYMENT

    def test_assess_non_positive_income_returns_insufficient_data(self) -> None:
        assert assess(_profile(income=Decimal("0.00")), _PRIMARY_PAYMENT).band is (
            AffordabilityBand.INSUFFICIENT_DATA
        )

    def test_assess_existing_credit_counts_towards_the_obligations(self) -> None:
        """SIM-022. The mortgage is not the only instalment the household pays."""
        result = assess(
            _profile(income=Decimal("4800.00"), existing_credit=Decimal("450.00")),
            _PRIMARY_PAYMENT,
        )

        assert result.monthly_obligations == Decimal("1864.52")
        assert result.dsti == Decimal("0.3884")
        assert result.band is AffordabilityBand.TIGHT

    def test_assess_absent_existing_credit_is_treated_as_zero(self) -> None:
        """SIM-027. "No existing credit" is the common case, not missing data."""
        with_none = assess(_profile(existing_credit=None), _PRIMARY_PAYMENT)
        with_zero = assess(_profile(existing_credit=Decimal("0.00")), _PRIMARY_PAYMENT)

        assert with_none == with_zero
        assert with_none.band is AffordabilityBand.COMFORTABLE

    def test_assess_never_reports_a_decision(self) -> None:
        """SIM-028. Four informational bands; no approve, no reject."""
        assert {band.value for band in AffordabilityBand} == {
            "COMFORTABLE",
            "TIGHT",
            "OUTSIDE_TYPICAL_NORMS",
            "INSUFFICIENT_DATA",
        }


class TestAcceptanceCriteria:
    """AC-009, to the cent."""

    def test_ac009_primary_case_on_a_modest_income_is_outside_norms(self) -> None:
        result = assess(_profile(income=Decimal("3200.00")), _PRIMARY_PAYMENT)

        assert result.monthly_obligations == Decimal("1414.52")
        assert result.dsti == Decimal("0.4420")
        assert result.residual_income == Decimal("1785.48")
        assert result.residual_floor == Decimal("1200.00")
        assert result.band is AffordabilityBand.OUTSIDE_TYPICAL_NORMS

    def test_ac009_the_same_household_on_a_higher_income_is_comfortable(self) -> None:
        result = assess(_profile(income=Decimal("4800.00")), _PRIMARY_PAYMENT)

        assert result.dsti == Decimal("0.2947")
        assert result.residual_income == Decimal("3385.48")
        assert result.band is AffordabilityBand.COMFORTABLE
