from fastapi import FastAPI

from app.config.settings import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": f"{settings.app_name} API is running",
        "status": "ok",
    }