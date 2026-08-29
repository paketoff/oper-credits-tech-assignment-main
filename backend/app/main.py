"""Application factory: registers routers, handlers and middleware (ARC-014).

This is the only module that is allowed to know about every domain. At T02 it
knows about none of them: the skeleton exists to be deployed before any feature
work, so that the pipeline is proven while it is still cheap to fix
(5-deployment.md DEP-040).
"""

from typing import Annotated

from fastapi import Depends, FastAPI

from app.core.dependencies import get_health_service
from app.core.health import HealthService, LivenessResponse

app = FastAPI(
    title="Borrower Portal",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)


@app.get("/health", response_model=LivenessResponse)
def health(probe: Annotated[HealthService, Depends(get_health_service)]) -> LivenessResponse:
    """Liveness probe. Touches nothing (DEP-036)."""
    return probe.liveness()
