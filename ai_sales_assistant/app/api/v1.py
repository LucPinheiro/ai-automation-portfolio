from fastapi import APIRouter

from app.routers import auth, generations, pricing

API_V1_PREFIX = "/api/v1"

api_v1_router = APIRouter(prefix=API_V1_PREFIX)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(generations.router)
api_v1_router.include_router(pricing.router)
