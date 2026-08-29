"""Application factory: registers routers, handlers and middleware (ARC-014).

This is the only module that is allowed to know about every domain. At T02 it
knows about none of them: the skeleton exists to be deployed before any feature
work, so that the pipeline is proven while it is still cheap to fix
(5-deployment.md DEP-040).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import exception_handlers, telemetry
from app.core import logging as app_logging
from app.core.database import create_all, get_session
from app.core.dependencies import get_health_service, get_storage
from app.core.health import HealthService, LivenessResponse, ReadinessResponse
from app.core.limits import BodySizeLimitMiddleware
from app.core.storage import LocalStorage

# Imported for their side effect: a table is only in Base.metadata once its
# module has been imported, and create_all builds what the metadata knows.
# main.py is the only file allowed to know every domain (ARC-014).
from app.domains.applications import tables as _applications_tables  # noqa: F401
from app.domains.auth import tables as _auth_tables  # noqa: F401
from app.domains.documents import tables as _documents_tables  # noqa: F401
from app.domains.simulation import tables as _simulation_tables  # noqa: F401


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Create the schema on startup. No Alembic (CQ-082).

    Idempotent: `create_all` issues CREATE TABLE IF NOT EXISTS, so a restart
    against an existing volume leaves the data alone.
    """
    await create_all()
    yield


app = FastAPI(
    title="Borrower Portal",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Registered once, here, because this is the only module that knows the whole
# application (ARC-014). The handlers are what make CQ-053 true: a router never
# maps an error because there is exactly one place that can.
app_logging.configure()
exception_handlers.register(app)
app.add_middleware(BodySizeLimitMiddleware)
app.middleware("http")(app_logging.request_id_middleware)
telemetry.configure(app)


@app.get("/health", response_model=LivenessResponse)
def health(probe: Annotated[HealthService, Depends(get_health_service)]) -> LivenessResponse:
    """Liveness probe. Touches nothing (DEP-036)."""
    return probe.liveness()


@app.get("/ready", response_model=ReadinessResponse)
async def ready(
    probe: Annotated[HealthService, Depends(get_health_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
    storage: Annotated[LocalStorage, Depends(get_storage)],
) -> ReadinessResponse:
    """Readiness probe: database reachable and the blob directory writable."""
    return await probe.readiness(session, storage)
