"""The all-in annual cost the lender must disclose beside the nominal rate.

AC-008. A JKP equal to the nominal rate means the fees were never applied, and
that is a bug rather than a very cheap loan.
"""

from decimal import Decimal

import pytest

from app.core.errors import SimulationError
from app.domains.simulation.calculator import compute_jkp

_LOAN = Decimal("270000")
_PAYMENT = Decimal("1414.52")
_TERM = 300
# SIM-016: mortgage registration + dossier + valuation. 3240 + 350 + 285.
_FEES = Decimal("3875.00")


def test_jkp_exceeds_nominal_rate():
    # SIM-019, AC-008: strictly greater, always. Equality is the bug signature.
    jkp = compute_jkp(_LOAN, _PAYMENT, _TERM, _FEES)

    assert jkp > Decimal("0.04")


def test_jkp_primary_case_matches_expected():
    # AC-008: approximately 0.0414 on the primary case.
    jkp = compute_jkp(_LOAN, _PAYMENT, _TERM, _FEES)

    assert round(jkp, 4) == Decimal("0.0414")


def test_jkp_excludes_registration_duty_and_purchase_notary():
    # SIM-017. Purchase tax and the deed notary are costs of buying a house,
    # not costs of credit, so including them would inflate the disclosed rate.
    # On the primary case they are 6000 + 3300 — an order of magnitude above
    # the fees that do belong, so their absence is unmistakable.
    correct = compute_jkp(_LOAN, _PAYMENT, _TERM, _FEES)
    if_wrongly_included = compute_jkp(
        _LOAN, _PAYMENT, _TERM, _FEES + Decimal("6000") + Decimal("3300")
    )

    assert if_wrongly_included > correct
    assert round(correct, 4) == Decimal("0.0414")


def test_jkp_with_zero_fees_equals_nominal_rate():
    # With nothing to amortise beyond the interest, the all-in cost collapses
    # onto the nominal rate. It does not land exactly on it because the
    # instalment is rounded to the cent (SIM-006), so this is a tolerance.
    jkp = compute_jkp(_LOAN, _PAYMENT, _TERM, Decimal("0"))

    assert abs(jkp - Decimal("0.04")) < Decimal("0.0001")


def test_jkp_computation_failure_raises_domain_error():
    # CQ-054: a Decimal failure means nothing to an API consumer, so it is
    # translated. Fees at or above the advance leave nothing to solve for.
    with pytest.raises(SimulationError) as exc:
        compute_jkp(_LOAN, _PAYMENT, _TERM, _LOAN)

    assert exc.value.code == "JKP_COMPUTATION_FAILED"


def test_jkp_translates_a_decimal_failure(monkeypatch):
    # CQ-054 requires the bisection to be wrapped so that a Decimal error
    # becomes a domain code. The inputs that reach this function are already
    # range-checked (DOM-013), so the branch cannot be reached with real
    # arguments — it is forced here rather than left as the one untested path
    # in a Tier 1 module.
    from decimal import InvalidOperation

    from app.domains.simulation import calculator

    def _explode(*_args: object) -> Decimal:
        raise InvalidOperation

    monkeypatch.setattr(calculator, "_bisect_for_effective_rate", _explode)

    with pytest.raises(SimulationError) as exc:
        compute_jkp(_LOAN, _PAYMENT, _TERM, _FEES)

    assert exc.value.code == "JKP_COMPUTATION_FAILED"
    assert isinstance(exc.value.__cause__, InvalidOperation)
