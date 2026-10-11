"""Discount calculation: Decimal, cents rounded half up, 15 means 15 %."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.services import pricing
from app.services.pricing import (
    calculate,
    format_percent,
    from_basis_points,
    from_cents,
    prompt_lines,
    to_basis_points,
    to_cents,
)

D = Decimal
PREVIEW = "/api/v1/pricing/discount"


# --- calculate -------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("price", "percent", "amount", "final"),
    [
        ("179", "15", "26.85", "152.15"),
        ("100", "10", "10.00", "90.00"),
        ("49.99", "20", "10.00", "39.99"),  # 9.998 is rounded to 10.00 before subtracting
        ("179", "0", "0.00", "179.00"),
        ("179", "100", "179.00", "0.00"),
        ("19.95", "7.5", "1.50", "18.45"),  # decimal price and decimal percent: 1.49625 -> 1.50
        ("0.01", "50", "0.01", "0.00"),  # 0.005 -> 0.01 (half up)
        ("12.50", "12.5", "1.56", "10.94"),  # 1.5625 -> 1.56
    ],
)
def test_discount_examples(price: str, percent: str, amount: str, final: str) -> None:
    breakdown = calculate(D(price), D(percent))

    assert breakdown.original_price == D(price).quantize(D("0.01"))
    assert breakdown.discount_amount == D(amount)
    assert breakdown.final_price == D(final)
    assert breakdown.original_price - breakdown.discount_amount == breakdown.final_price


def test_amounts_always_have_two_decimals() -> None:
    breakdown = calculate(D("100"), D("10"))

    assert str(breakdown.original_price) == "100.00"
    assert str(breakdown.discount_amount) == "10.00"
    assert str(breakdown.final_price) == "90.00"


def test_percentage_keeps_its_meaning() -> None:
    # 15 means 15 %, never 0.15 %.
    assert calculate(D("200"), D("15")).discount_amount == D("30.00")
    assert calculate(D("200"), D("0.15")).discount_amount == D("0.30")


def test_rounding_is_half_up_not_bankers() -> None:
    # 0.125 -> 0.13 with ROUND_HALF_UP (bankers' rounding would give 0.12).
    assert calculate(D("1.25"), D("10")).discount_amount == D("0.13")


def test_price_without_discount() -> None:
    breakdown = calculate(D("179"))

    assert (breakdown.discount_percent, breakdown.discount_amount, breakdown.final_price) == (None, D("0.00"), D("179.00"))


@pytest.mark.parametrize(("price", "percent"), [("-1", "10"), ("0", "10"), ("100", "-5"), ("100", "100.01"), ("100", "150")])
def test_out_of_range_values_are_rejected(price: str, percent: str) -> None:
    with pytest.raises(ValueError):
        calculate(D(price), D(percent))


@pytest.mark.parametrize("value", [179.0, 179, "179", D("NaN"), D("Infinity")])
def test_only_finite_decimals_are_accepted(value: object) -> None:
    # Floats cannot represent most cent values exactly: never accepted.
    with pytest.raises(TypeError):
        calculate(value)  # type: ignore[arg-type]


def test_no_float_arithmetic_in_the_module() -> None:
    source = pricing.__loader__.get_source(pricing.__name__)  # type: ignore[union-attr]

    assert "float(" not in source


# --- Storage conversions ---------------------------------------------------------------------------


@pytest.mark.parametrize(("price", "cents"), [("179", 17900), ("49.99", 4999), ("0.01", 1), ("99999999.99", 9999999999)])
def test_cents_round_trip(price: str, cents: int) -> None:
    assert to_cents(D(price)) == cents
    assert from_cents(cents) == D(price).quantize(D("0.01"))


@pytest.mark.parametrize(("percent", "basis_points"), [("15", 1500), ("12.5", 1250), ("0", 0), ("100", 10000)])
def test_basis_points_round_trip(percent: str, basis_points: int) -> None:
    assert to_basis_points(D(percent)) == basis_points
    assert from_basis_points(basis_points) == D(percent).quantize(D("0.01"))


# --- Prompt text --------------------------------------------------------------------------------------


def test_prompt_lines_with_discount() -> None:
    assert prompt_lines(calculate(D("179"), D("15"))) == [
        "Original price: 179.00 EUR",
        "Discount: 15%",
        "Discount amount: 26.85 EUR",
        "Final price: 152.15 EUR",
    ]


def test_prompt_lines_without_discount_or_price() -> None:
    assert prompt_lines(calculate(D("49.99"))) == ["Price: 49.99 EUR", "Discount: none"]
    assert prompt_lines(None) == ["Pricing: not provided"]


@pytest.mark.parametrize(("value", "text"), [("15.00", "15%"), ("12.50", "12.5%"), ("100.00", "100%"), ("0", "0%"), ("7.25", "7.25%")])
def test_format_percent(value: str, text: str) -> None:
    assert format_percent(D(value)) == text


# --- Preview endpoint (used by the form) -----------------------------------------------------------


def test_preview_returns_the_backend_breakdown_as_exact_strings(client: TestClient) -> None:
    response = client.get(PREVIEW, params={"price": "179", "discount_percent": "15"})

    assert response.status_code == 200
    assert response.json() == {
        "original_price": "179.00",
        "discount_percent": "15",
        "discount_amount": "26.85",
        "final_price": "152.15",
        "currency": "EUR",
    }


def test_preview_with_decimal_price(client: TestClient) -> None:
    body = client.get(PREVIEW, params={"price": "49.99", "discount_percent": "20"}).json()

    assert (body["discount_amount"], body["final_price"]) == ("10.00", "39.99")


def test_preview_requires_a_session(anon_client: TestClient) -> None:
    assert anon_client.get(PREVIEW, params={"price": "179", "discount_percent": "15"}).status_code == 401


def test_preview_works_for_guests(anon_client: TestClient) -> None:
    anon_client.post("/api/v1/auth/guest")

    assert anon_client.get(PREVIEW, params={"price": "100", "discount_percent": "10"}).json()["final_price"] == "90.00"


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"price": "-1", "discount_percent": "10"}, "price"),
        ({"price": "0", "discount_percent": "10"}, "price"),
        ({"price": "179.999", "discount_percent": "10"}, "price"),
        ({"price": "abc", "discount_percent": "10"}, "price"),
        ({"price": "100", "discount_percent": "101"}, "discount_percent"),
        ({"price": "100", "discount_percent": "-1"}, "discount_percent"),
        ({"discount_percent": "10"}, "price"),
    ],
)
def test_preview_rejects_invalid_values(client: TestClient, params: dict, field: str) -> None:
    response = client.get(PREVIEW, params=params)

    assert response.status_code == 422
    # Query-string fields are reported with their location, as everywhere in the API.
    assert response.json()["error"]["details"][0]["field"] == f"query.{field}"
