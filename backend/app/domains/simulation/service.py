"""Simulation flow: convert the wire schema, calculate, persist, assemble.

Holds no maths and no SQL. The arithmetic is `calculator.py`, the queries are
`repository.py`, and this module is the only place that knows the order.
"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, SimulationError
from app.domains.simulation import calculator
from app.domains.simulation.entities import Simulation, SimulationInput, SimulationResult
from app.domains.simulation.repository import SimulationRepository
from app.domains.simulation.schemas import (
    SimulationRequest,
    SimulationResponse,
    UpfrontCostsResponse,
)

# DOM-010 - DOM-014. Re-checked here rather than left to pydantic because
# VAL-008 gives each of these its own code, and a borrower is better served by
# "Term must be between 1 and 30 years" than by "Check the highlighted fields".
_MIN_PROPERTY_VALUE = Decimal("10000")
_MAX_PROPERTY_VALUE = Decimal("10000000")
_MIN_TERM_MONTHS = 12
_MAX_TERM_MONTHS = 360
_MAX_RATE = Decimal("0.20")


class SimulationService:
    """Creates and reads simulations."""

    def __init__(self, repository: SimulationRepository) -> None:
        """Take the repository as a protocol, never a concrete class (CQ-034)."""
        self._repository = repository

    async def create(self, session: AsyncSession, payload: SimulationRequest) -> SimulationResponse:
        """Validate, calculate, persist and assemble a simulation.

        Args:
            session: The request session. This method owns the transaction
                (CQ-091), so it is the one that commits.
            payload: The borrower's inputs, already shape-checked by pydantic.

        Returns:
            The full result, with every figure as a string.
        """
        request = self._to_entity(payload)
        result = calculator.simulate(request)
        stored = await self._repository.save(session, request)
        await session.commit()
        return self._to_response(stored, result)

    async def get(self, session: AsyncSession, simulation_id: UUID) -> SimulationResponse:
        """Read a simulation back and recompute its figures.

        Recomputed rather than stored, per DOM-001: a stored result can drift
        from what the rules say, and the calculation is cheap.

        Raises:
            NotFoundError: SIMULATION_NOT_FOUND.
        """
        stored = await self._repository.get(session, simulation_id)
        if stored is None:
            raise NotFoundError(code="SIMULATION_NOT_FOUND")
        return self._to_response(stored, calculator.simulate(stored.request))

    async def claim_for_user(
        self, session: AsyncSession, simulation_id: UUID, user_id: UUID
    ) -> UUID | None:
        """Attach an anonymous simulation to a user (ARC-017, DOM-025 - DOM-027).

        Returns:
            The claimed id, or None when there was nothing to claim. **Never
            raises**: a missing or already-owned simulation must not cost a
            registration (AUTH-031).
        """
        claimed = await self._repository.set_owner(session, simulation_id, user_id)
        return claimed.id if claimed else None

    def _to_entity(self, payload: SimulationRequest) -> SimulationInput:
        """Convert the wire schema into the entity the calculator takes (ARC-043)."""
        self._validate(payload)
        return SimulationInput(
            property_value=payload.property_value,
            own_contribution=payload.own_contribution,
            term_months=payload.term_months,
            annual_nominal_rate=payload.annual_nominal_rate,
            region=payload.region,
            is_first_home=payload.is_first_home,
        )

    def _validate(self, payload: SimulationRequest) -> None:
        """Apply the invariants that VAL-008 gives a named code to.

        Raises:
            SimulationError: The code for whichever bound was crossed.
        """
        if not _MIN_PROPERTY_VALUE <= payload.property_value <= _MAX_PROPERTY_VALUE:
            raise SimulationError(code="PROPERTY_VALUE_OUT_OF_RANGE", field="property_value")
        if not _MIN_TERM_MONTHS <= payload.term_months <= _MAX_TERM_MONTHS:
            raise SimulationError(code="TERM_OUT_OF_RANGE", field="term_months")
        if not 0 <= payload.annual_nominal_rate <= _MAX_RATE:
            raise SimulationError(code="RATE_OUT_OF_RANGE", field="annual_nominal_rate")

    def _to_response(self, stored: Simulation, result: SimulationResult) -> SimulationResponse:
        """Assemble the wire response from the stored row and the fresh figures."""
        return SimulationResponse(
            id=stored.id,
            loan_amount=result.loan_amount,
            quotiteit=result.quotiteit,
            above_supervisory_norm=result.above_supervisory_norm,
            monthly_payment=result.monthly_payment,
            total_paid=result.total_paid,
            total_interest=result.total_interest,
            nominal_rate=result.nominal_rate,
            jkp=result.jkp,
            upfront=UpfrontCostsResponse(
                registration_duty=result.upfront.registration_duty,
                notary_fee=result.upfront.notary_fee,
                mortgage_costs=result.upfront.mortgage_costs,
                dossier_fee=result.upfront.dossier_fee,
                valuation_fee=result.upfront.valuation_fee,
                total_costs=result.upfront.total_costs,
                own_contribution=result.upfront.own_contribution,
                total_cash_needed=result.upfront.total_cash_needed,
            ),
            created_at=stored.created_at,
        )
