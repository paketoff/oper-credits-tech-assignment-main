"""Shared FastAPI dependency providers.

Providers live here rather than beside their consumers so that a route handler
can stay one statement long (CQ-017): everything it needs arrives already
constructed.
"""

from app.core.health import HealthService


def get_health_service() -> HealthService:
    """Provide the health service to a route handler."""
    return HealthService()
