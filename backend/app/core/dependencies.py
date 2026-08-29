"""Shared FastAPI dependency providers.

Providers live here rather than beside their consumers so that a route handler
can stay one statement long (CQ-017): everything it needs arrives already
constructed.
"""

from app.core.config import get_settings
from app.core.health import HealthService
from app.core.storage import LocalStorage


def get_health_service() -> HealthService:
    """Provide the health service to a route handler."""
    return HealthService()


def get_storage() -> LocalStorage:
    """Provide the blob backend, rooted at DATA_DIR/blobs.

    Typed as the concrete class only here. Services take the `StorageBackend`
    protocol, so swapping this line is the whole cost of changing backend
    (CQ-034, CQ-035).
    """
    return LocalStorage(get_settings().blob_dir)
