"""Dependency providers for the simulation domain."""

from app.domains.simulation.repository import SqlSimulationRepository
from app.domains.simulation.service import SimulationService


def get_simulation_service() -> SimulationService:
    """Build the service with its repository.

    The concrete repository is named here and nowhere else; the service holds
    it as a protocol (CQ-034, CQ-035).
    """
    return SimulationService(SqlSimulationRepository())
