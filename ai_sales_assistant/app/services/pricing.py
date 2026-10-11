"""Price and discount calculation: the single source of truth.

All money is handled as Decimal (never float) and rounded to cents with ROUND_HALF_UP,
the usual commercial rounding. A discount percentage keeps its meaning: 15 means 15 %.

    discount_amount = round(price * discount_percent / 100, 2)
    final_price     = price - discount_amount

The prompt, the API responses and the form preview all use `calculate`; the AI never computes
prices and the browser only formats what the backend returns.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
HUNDRED = Decimal(100)
MAX_PRICE = Decimal("99999999.99")
MAX_DISCOUNT_PERCENT = HUNDRED
CURRENCY = "EUR"


@dataclass(frozen=True)
class PriceBreakdown:
    original_price: Decimal
    discount_percent: Decimal | None
    discount_amount: Decimal
    final_price: Decimal


def money(value: Decimal) -> Decimal:
    """Round to cents, half up (26.845 -> 26.85, 9.998 -> 10.00)."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _require_decimal(name: str, value: object) -> Decimal:
    # Floats cannot represent most cent values exactly (0.1 + 0.2 != 0.3): refuse them outright.
    if not isinstance(value, Decimal) or not value.is_finite():
        raise TypeError(f"{name} must be a finite Decimal")
    return value


def calculate(price: Decimal, discount_percent: Decimal | None = None) -> PriceBreakdown:
    price = _require_decimal("price", price)
    if not Decimal(0) < price <= MAX_PRICE:
        raise ValueError(f"price must be greater than 0 and at most {MAX_PRICE}")
    original = money(price)

    if discount_percent is None:
        return PriceBreakdown(original, None, money(Decimal(0)), original)

    discount_percent = _require_decimal("discount_percent", discount_percent)
    if not Decimal(0) <= discount_percent <= MAX_DISCOUNT_PERCENT:
        raise ValueError("discount_percent must be between 0 and 100")
    amount = money(original * discount_percent / HUNDRED)
    return PriceBreakdown(original, discount_percent, amount, original - amount)


# --- Storage: exact integers on every database backend --------------------------------------
# SQLite has no real decimal type (NUMERIC is stored as a float), so the database keeps
# integer cents and integer basis points (hundredths of a percent).


def to_cents(price: Decimal) -> int:
    return int(money(price) * 100)


def from_cents(cents: int) -> Decimal:
    return (Decimal(cents) / 100).quantize(CENT)


def to_basis_points(percent: Decimal) -> int:
    return int(percent.quantize(CENT, rounding=ROUND_HALF_UP) * 100)


def from_basis_points(basis_points: int) -> Decimal:
    return (Decimal(basis_points) / 100).quantize(CENT)


# --- Text for the prompt ------------------------------------------------------------------------


def format_money(value: Decimal) -> str:
    return f"{money(value):.2f} {CURRENCY}"


def format_percent(value: Decimal) -> str:
    # 15.00 -> "15%", 12.50 -> "12.5%", 100 -> "100%" (no exponent notation).
    text = f"{value:f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return f"{text}%"


def prompt_lines(breakdown: PriceBreakdown | None) -> list[str]:
    if breakdown is None:
        return ["Pricing: not provided"]
    if breakdown.discount_percent is None:
        return [f"Price: {format_money(breakdown.original_price)}", "Discount: none"]
    return [
        f"Original price: {format_money(breakdown.original_price)}",
        f"Discount: {format_percent(breakdown.discount_percent)}",
        f"Discount amount: {format_money(breakdown.discount_amount)}",
        f"Final price: {format_money(breakdown.final_price)}",
    ]
