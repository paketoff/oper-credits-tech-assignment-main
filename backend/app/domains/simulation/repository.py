"""Queries against the simulations table; the ORM boundary (CQ-088).

A `SimulationRow` never leaves this module. Entities go in, entities come out,
and nothing above here can accidentally trigger a lazy load against a session
that has already closed (CQ-089).

Nothing here commits. The service owns the transaction boundary, which is what
lets a signup claim a simulation and insert a user atomically (CQ-091).
"""

from datetime import UTC
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import Region
from app.domains.simulation.entities import Simulation, SimulationInput
from app.domains.simulation.tables import SimulationRow


class SimulationRepository(Protocol):
    """Persistence for simulations."""

    async def save(self, session: AsyncSession, request: SimulationInput) -> Simulation:
        """Persist a simulation and return it with its generated id."""
        ...

    async def get(self, session: AsyncSession, simulation_id: UUID) -> Simulation | None:
        """Fetch a simulation by id, or None."""
        ...

    async def set_owner(
        self, session: AsyncSession, simulation_id: UUID, user_id: UUID
    ) -> Simulation | None:
        """Attach an unowned simulation to a user, or return None."""
        ...


def _to_entity(row: SimulationRow) -> Simulation:
    """Map a row to the domain type. The only place this conversion happens."""
    return Simulation(
        id=row.id,
        user_id=row.user_id,
        request=SimulationInput(
            property_value=row.property_value,
            own_contribution=row.own_contribution,
            term_months=row.term_months,
            annual_nominal_rate=row.annual_nominal_rate,
            region=Region(row.region),
            is_first_home=row.is_first_home,
        ),
        created_at=row.created_at.replace(tzinfo=row.created_at.tzinfo or UTC),
    )


class SqlSimulationRepository:
    """The SQLite implementation of `SimulationRepository`."""

    async def save(self, session: AsyncSession, request: SimulationInput) -> Simulation:
        """Insert a simulation and return it with its generated id."""
        row = SimulationRow(
            property_value=request.property_value,
            own_contribution=request.own_contribution,
            term_months=request.term_months,
            annual_nominal_rate=request.annual_nominal_rate,
            region=request.region.value,
            is_first_home=request.is_first_home,
        )
        session.add(row)
        await session.flush()
        return _to_entity(row)

    async def get(self, session: AsyncSession, simulation_id: UUID) -> Simulation | None:
        """Fetch one simulation, or None."""
        row = await session.get(SimulationRow, simulation_id)
        return _to_entity(row) if row else None

    async def set_owner(
        self, session: AsyncSession, simulation_id: UUID, user_id: UUID
    ) -> Simulation | None:
        """Attach an unowned simulation to a user.

        The `user_id IS NULL` clause is in the WHERE, not in a preceding check:
        an owned simulation is never reassigned (DOM-027), and putting the
        condition in the query means two concurrent claims cannot both win.
        """
        statement = select(SimulationRow).where(
            SimulationRow.id == simulation_id,
            SimulationRow.user_id.is_(None),
        )
        row = (await session.execute(statement)).scalar_one_or_none()
        if row is None:
            return None
        row.user_id = user_id
        await session.flush()
        return _to_entity(row)
