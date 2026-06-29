from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class DocumentType(StrEnum):
    EMAIL = "EMAIL"
    PROPOSAL = "PROPOSAL"
    FOLLOW_UP = "FOLLOW_UP"
    WHATSAPP = "WHATSAPP"
    SUMMARY = "SUMMARY"


class Language(StrEnum):
    ES = "ES"
    EN = "EN"
    PT = "PT"


class Tone(StrEnum):
    PROFESSIONAL = "PROFESSIONAL"
    FORMAL = "FORMAL"
    FRIENDLY = "FRIENDLY"
    PERSUASIVE = "PERSUASIVE"
    CASUAL = "CASUAL"


class DocumentGenerationBase(BaseModel):
    client_name: str = Field(..., min_length=2, max_length=100)
    company: str = Field(..., min_length=2, max_length=100)
    sector: str = Field(..., min_length=2, max_length=80)
    product_service: str = Field(..., min_length=2, max_length=150)
    customer_need: str = Field(..., min_length=5)

    document_type: DocumentType
    language: Language
    tone: Tone


class DocumentGenerationCreate(DocumentGenerationBase):
    pass


class DocumentGenerationResponse(DocumentGenerationBase):
    id: int
    created_at: datetime
    prompt: str
    response: str
    model_name: str | None = None
    execution_time: float | None = None

    model_config = {
        "from_attributes": True
    }