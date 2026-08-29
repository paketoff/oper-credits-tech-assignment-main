"""HTTP routes for simulations; one service call per handler (CQ-017)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.domains.simulation.dependencies import get_simulation_service
from app.domains.simulation.schemas import SimulationRequest, SimulationResponse
from app.domains.simulation.service import SimulationService

router = APIRouter(prefix="/simulations", tags=["simulations"])


@router.post("", response_model=SimulationResponse, status_code=201)
async def create_simulation(
    payload: SimulationRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[SimulationService, Depends(get_simulation_service)],
) -> SimulationResponse:
    """Create an anonymous mortgage simulation.

    Public, and POST rather than GET: an anonymous simulation has to be
    claimable at signup, so it needs an identity and has to exist (API-012).
    """
    return await service.create(session, payload)


@router.get("/{simulation_id}", response_model=SimulationResponse)
async def get_simulation(
    simulation_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[SimulationService, Depends(get_simulation_service)],
) -> SimulationResponse:
    """Read a simulation back.

    Public: the id is an unguessable UUID4 and the payload carries no personal
    data (API-021).
    """
    return await service.get(session, simulation_id)
