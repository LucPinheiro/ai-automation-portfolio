from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.services.pricing import MAX_DISCOUNT_PERCENT, MAX_PRICE, PriceBreakdown

# Input types shared by the generation schema and the preview endpoint. Decimal end to end:
# JSON numbers and strings are parsed straight into Decimal, never through float arithmetic.
Price = Annotated[
    Decimal,
    Field(
        gt=0,
        le=MAX_PRICE,
        max_digits=10,
        decimal_places=2,
        description="Original price in EUR, with at most 2 decimals (e.g. 179 or 49.99).",
        examples=["179.00"],
    ),
]
DiscountPercent = Annotated[
    Decimal,
    Field(
        ge=0,
        le=MAX_DISCOUNT_PERCENT,
        max_digits=5,
        decimal_places=2,
        description="Discount percentage from 0 to 100: 15 means 15 % (not 0.15).",
        examples=["15"],
    ),
]


class PricingRead(BaseModel):
    """Price breakdown calculated by the backend (Decimal, rounded to cents half up).

    Amounts are serialized as strings ("152.15") so no precision is lost in JSON.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "original_price": "179.00",
                    "discount_percent": "15.00",
                    "discount_amount": "26.85",
                    "final_price": "152.15",
                    "currency": "EUR",
                }
            ]
        }
    )

    original_price: Decimal
    discount_percent: Decimal | None = Field(description="None when there is no discount.")
    discount_amount: Decimal
    final_price: Decimal
    currency: str = "EUR"

    @classmethod
    def from_breakdown(cls, breakdown: PriceBreakdown) -> "PricingRead":
        return cls(
            original_price=breakdown.original_price,
            discount_percent=breakdown.discount_percent,
            discount_amount=breakdown.discount_amount,
            final_price=breakdown.final_price,
        )
