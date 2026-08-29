"""Application factory: registers routers, handlers and middleware (ARC-014).

This is the only module that is allowed to know about every domain. At T02 it
knows about none of them: the skeleton exists to be deployed before any feature
work, so that the pipeline is proven while it is still cheap to fix
(5-deployment.md DEP-040).
"""

from typing import Annotated

from fastapi import Depends, FastAPI

from app.core import exception_handlers
from app.core.dependencies import get_health_service
from app.core.health import HealthService, LivenessResponse
from app.core.limits import BodySizeLimitMiddleware

app = FastAPI(
    title="Borrower Portal",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# Registered once, here, because this is the only module that knows the whole
# application (ARC-014). The handlers are what make CQ-053 true: a router never
# maps an error because there is exactly one place that can.
exception_handlers.register(app)
app.add_middleware(BodySizeLimitMiddleware)


@app.get("/health", response_model=LivenessResponse)
def health(probe: Annotated[HealthService, Depends(get_health_service)]) -> LivenessResponse:
    """Liveness probe. Touches nothing (DEP-036)."""
    return probe.liveness()
