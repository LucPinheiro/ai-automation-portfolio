from sqlalchemy.orm import Session

from app.config import Settings
from app.database.session import is_database_available
from app.schemas.system import HealthResponse


def get_health_status(session: Session, settings: Settings) -> HealthResponse:
    database_ok = is_database_available(session)
    return HealthResponse(
        status="ok" if database_ok else "degraded",
        version=settings.app_version,
        database="ok" if database_ok else "unavailable",
    )
