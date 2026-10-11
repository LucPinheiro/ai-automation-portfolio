from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, ValidationInfo, computed_field, field_validator
from pydantic_core import PydanticCustomError

from app.core.constants import (
    EMAIL_MAX_LENGTH,
    COMPANY_MAX_LENGTH,
    CUSTOMER_MAX_LENGTH,
    CUSTOMER_NEEDS_MAX_LENGTH,
    INDUSTRY_MAX_LENGTH,
    PRODUCT_OR_SERVICE_MAX_LENGTH,
    SALESPERSON_COMPANY_MAX_LENGTH,
    SALESPERSON_MAX_LENGTH,
)
from app.core.enums import ContentType, Language, Tone
from app.schemas.pricing import DiscountPercent, Price, PricingRead
from app.services.commercial_terms import find_missing, terms_for
from app.services.pricing import calculate

GENERATION_READ_EXAMPLE = {
    "id": 1,
    "content_type": "commercial_email",
    "generated_content": (
        "Subject: Real-time fleet visibility for Logística Norte\n\n"
        "Dear María,\n\nI understand that reducing fuel costs and tracking deliveries in real time "
        "are priorities for Logística Norte...\n\nBest regards,\n\nCarlos Vila\nFleetSoft S.L."
    ),
    "language": "es",
    "tone": "professional",
    "customer": "María López",
    "customer_email": "maria@logisticanorte.es",
    "company": "Logística Norte S.L.",
    "industry": "Logistics",
    "product_or_service": "Fleet management software",
    "customer_needs": "Reduce fuel costs and track deliveries in real time.",
    "price": "179.00",
    "discount_percent": "15.00",
    "pricing": {
        "original_price": "179.00",
        "discount_percent": "15.00",
        "discount_amount": "26.85",
        "final_price": "152.15",
        "currency": "EUR",
    },
    "missing_commercial_terms": [],
    "salesperson": "Carlos Vila",
    "salesperson_company": "FleetSoft S.L.",
    "ai_provider": "openai",
    "ai_model": "gpt-4o-mini-2024-07-18",
    "created_at": "2026-10-07T12:00:00Z",
}


CustomerEmail = Annotated[EmailStr, Field(max_length=EMAIL_MAX_LENGTH)]


class GenerationCreate(BaseModel):
    """Input data used to generate commercial content."""

    # Whitespace is stripped before length checks, so "   " is rejected as empty.
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    content_type: ContentType = Field(
        description="Type of content to generate.", examples=[ContentType.COMMERCIAL_EMAIL]
    )
    customer: str = Field(
        min_length=1,
        max_length=CUSTOMER_MAX_LENGTH,
        description="Customer: the contact person the content is addressed to or about (the recipient).",
        examples=["María López"],
    )
    company: str = Field(
        min_length=1,
        max_length=COMPANY_MAX_LENGTH,
        description="The customer's company (where the recipient works).",
        examples=["Logística Norte S.L."],
    )
    industry: str = Field(
        min_length=1,
        max_length=INDUSTRY_MAX_LENGTH,
        description="Customer's industry or sector.",
        examples=["Logistics"],
    )
    product_or_service: str = Field(
        min_length=1,
        max_length=PRODUCT_OR_SERVICE_MAX_LENGTH,
        description="Product or service being offered.",
        examples=["Fleet management software"],
    )
    customer_email: CustomerEmail | None = Field(
        default=None,
        description=(
            "Optional email of the customer. Only used to pre-fill the recipient when the result is "
            "sent by email from the web page; it is never sent to the AI provider."
        ),
        examples=["maria@logisticanorte.es"],
    )
    customer_needs: str = Field(
        min_length=1,
        max_length=CUSTOMER_NEEDS_MAX_LENGTH,
        description="Customer needs or pain points the content should address.",
        examples=["Reduce fuel costs and track deliveries in real time."],
    )
    # Optional pricing: the backend calculates the discount amount and final price (app.services.pricing).
    price: Price | None = Field(
        default=None,
        description="Optional original price in EUR (at most 2 decimals).",
        examples=["179.00"],
    )
    discount_percent: DiscountPercent | None = Field(
        default=None,
        description="Optional discount from 0 to 100 (15 means 15 %). Requires a price.",
        examples=["15"],
    )
    salesperson: str | None = Field(
        default=None,
        max_length=SALESPERSON_MAX_LENGTH,
        description="Salesperson sending the communication (the sender). Optional: no name is invented when empty.",
        examples=["Carlos Vila"],
    )
    salesperson_company: str | None = Field(
        default=None,
        max_length=SALESPERSON_COMPANY_MAX_LENGTH,
        description="The salesperson's company, which offers the product or service. Optional.",
        examples=["FleetSoft S.L."],
    )
    language: Language = Field(description="Output language (ISO 639-1).", examples=[Language.SPANISH])
    tone: Tone = Field(description="Tone of voice.", examples=[Tone.PROFESSIONAL])

    @field_validator("price", "discount_percent", "customer_email", mode="before")
    @classmethod
    def _empty_number_is_not_provided(cls, value: object) -> object:
        # An empty form input means "no price" / "no discount" / "no email".
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("discount_percent")
    @classmethod
    def _discount_needs_a_price(cls, value: Decimal | None, info: ValidationInfo) -> Decimal | None:
        # Only when the price itself was valid but missing (an invalid price is already reported).
        if value is not None and "price" in info.data and info.data["price"] is None:
            raise PydanticCustomError("discount_requires_price", "A discount needs a price.")
        return value

    @field_validator("salesperson", "salesperson_company", mode="after")
    @classmethod
    def _blank_is_not_provided(cls, value: str | None) -> str | None:
        # Whitespace is already stripped by the model config, so "" means "not provided".
        return value or None


class GenerationRead(BaseModel):
    """A stored generation as returned by the API."""

    model_config = ConfigDict(from_attributes=True, json_schema_extra={"examples": [GENERATION_READ_EXAMPLE]})

    id: int
    content_type: ContentType
    generated_content: str = Field(description="Content generated by the AI.")
    language: Language
    tone: Tone
    customer: str
    customer_email: str | None = None
    company: str
    industry: str
    product_or_service: str
    customer_needs: str
    price: Decimal | None = None
    discount_percent: Decimal | None = None
    salesperson: str | None = None
    salesperson_company: str | None = None
    ai_provider: str = Field(description="AI provider that generated the content.")
    ai_model: str = Field(description="Exact model version reported by the provider.")
    created_at: datetime = Field(description="Creation date (UTC).")

    @computed_field(description="Price breakdown calculated by the backend; null without a price.")
    @property
    def pricing(self) -> PricingRead | None:
        if self.price is None:
            return None
        return PricingRead.from_breakdown(calculate(self.price, self.discount_percent))

    @computed_field(
        description=(
            "Mandatory commercial terms (structured pricing and figures written in the customer needs) "
            "that the generated text does not contain. Empty when everything is there."
        )
    )
    @property
    def missing_commercial_terms(self) -> list[str]:
        terms = terms_for(
            language=self.language,
            customer_needs=self.customer_needs,
            price=self.price,
            discount_percent=self.discount_percent,
        )
        return [term.text for term in find_missing(terms, self.generated_content)]


class GenerationList(BaseModel):
    """A page of stored generations, newest first."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"items": [GENERATION_READ_EXAMPLE], "total": 1, "limit": 20, "offset": 0}]}
    )

    items: list[GenerationRead]
    total: int = Field(description="Total number of generations matching the filter.")
    limit: int
    offset: int
