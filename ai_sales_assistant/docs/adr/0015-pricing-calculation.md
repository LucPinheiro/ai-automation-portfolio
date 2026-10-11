# 0015. Discount calculation in the backend

- Status: Accepted
- Date: 2026-10-08

## Context

Generations can quote a price and a discount. Language models make arithmetic and rounding mistakes and tend to invent figures, and floating point cannot represent most cent values exactly. Prices must therefore be calculated by the application, once, and the model must only quote the result.

## Decision

**Single source of truth: `app/services/pricing.py`.** `calculate(price, discount_percent)` works only with `Decimal` (floats are rejected) and rounds to cents with `ROUND_HALF_UP`:

- `discount_amount = round(price × discount_percent / 100, 2)`
- `final_price = price − discount_amount`

A percentage keeps its meaning (15 means 15 %). Examples: 179 € with 15 % → 26.85 € and 152.15 €; 49.99 € with 20 % → 9.998 is rounded to 10.00 → 39.99 €.

Three consumers, none with its own arithmetic:
1. **Prompt**: the data block carries the calculated figures (`Original price: 179.00 EUR`, `Discount: 15%`, `Discount amount: 26.85 EUR`, `Final price: 152.15 EUR`, or `Pricing: not provided`). The system prompt tells the model to quote them exactly, never recalculate or round them, and never add other prices or discounts.
2. **API responses**: `GenerationRead.pricing` is a computed field. Amounts are serialized as strings (`"152.15"`) so JSON never loses precision.
3. **Form preview**: `GET /api/v1/pricing/discount` (requires a session, no AI call). The browser only converts the Spanish decimal comma before sending and formats the backend's values for display.

**Validation** (`GenerationCreate`, same for create and edit): both fields optional; price > 0, at most 2 decimals, up to 99,999,999.99; discount 0–100 with up to 2 decimals; a discount without a price is rejected (422 `discount_requires_price`). Invalid values never reach the AI.

**Storage** (migration `0005`): only the input is stored, as exact integers, because SQLite has no real decimal type: `price_cents` (17900) and `discount_basis_points` (1500 = 15.00 %). The model exposes them as `Decimal` properties. CHECK constraints enforce a positive price, a discount between 0 and 10000 basis points, and no discount without a price. The discount amount and final price are derived, not stored.

## Consequences

- Ollama and OpenAI receive identical, already-correct figures; the model can still phrase them in the output language's format (152,15 €).
- Changing the rounding rule is a one-line change in one module, and stored data stays valid (only inputs are stored).
- The form preview needs a round trip to the server (debounced); acceptable for a local or same-site app.

## Alternatives considered

- **Letting the model calculate**: unreliable arithmetic and rounding.
- **Calculating in JavaScript for the preview**: a second implementation that could drift from the backend.
- **`Numeric` columns**: stored as floating point by SQLite.
- **Storing the final price**: derived data that could become inconsistent with its inputs.
