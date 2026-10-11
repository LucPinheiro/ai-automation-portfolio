from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import CurrentUserDep
from app.api.responses import error_responses
from app.schemas.pricing import DiscountPercent, Price, PricingRead
from app.services.pricing import calculate

router = APIRouter(prefix="/pricing", tags=["Pricing"])


@router.get(
    "/discount",
    response_model=PricingRead,
    summary="Calculate a discount",
    description=(
        "Calculates the discount amount and final price with the same backend logic used for "
        "generations (Decimal, cents rounded half up). The web form uses it for its live preview, "
        "so the browser never calculates prices. No AI call is made."
    ),
    response_description="Price breakdown",
    responses=error_responses(401, 422, 500),
)
def calculate_discount(
    _user: CurrentUserDep,
    price: Annotated[Price, Query()],
    discount_percent: Annotated[DiscountPercent | None, Query()] = None,
) -> PricingRead:
    return PricingRead.from_breakdown(calculate(price, discount_percent))
