from typing import Literal

from pydantic import BaseModel, Field


class RootResponse(BaseModel):
    name: str = Field(examples=["AI Sales Assistant"])
    version: str = Field(examples=["0.1.0"])
    docs_url: str = Field(examples=["/docs"])
    health_url: str = Field(examples=["/health"])


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"] = Field(description="Overall application status.")
    version: str = Field(examples=["0.1.0"])
    database: Literal["ok", "unavailable"] = Field(description="Database connectivity.")

    @property
    def is_healthy(self) -> bool:
        return self.status == "ok"
