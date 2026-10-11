from fastapi import APIRouter, Response, status

from app.api.dependencies import SessionDep, SettingsDep
from app.api.responses import error_responses
from app.schemas.system import HealthResponse, RootResponse
from app.services.health_service import get_health_status

router = APIRouter(tags=["System"])


@router.get(
    "/",
    response_model=RootResponse,
    summary="API information",
    description="Returns the application name, version and links to the documentation.",
    response_description="Application information",
    responses=error_responses(500),
)
def read_root(settings: SettingsDep) -> RootResponse:
    return RootResponse(
        name=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        health_url="/health",
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description=(
        "Reports application status and database connectivity. "
        "Returns 503 with `status: degraded` when the database is unreachable."
    ),
    response_description="Application and database are available",
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": HealthResponse,
            "description": "Database unavailable",
            "content": {
                "application/json": {"example": {"status": "degraded", "version": "0.1.0", "database": "unavailable"}}
            },
        },
        **error_responses(500),
    },
)
def health_check(session: SessionDep, settings: SettingsDep, response: Response) -> HealthResponse:
    health = get_health_status(session, settings)
    if not health.is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return health
