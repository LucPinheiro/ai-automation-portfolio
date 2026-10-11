# 0016. Mandatory commercial terms: prompt, verification and retry

- Status: Accepted
- Date: 2026-10-08

## Context

Commercial terms given by the user (structured price and discount, and prices, discounts, scales, quantities, dates or deadlines written in "Necesidades del cliente") must appear in the generated text, unchanged and complete. With llama3.2:3b they were dropped: a 5-tier discount scale became "discounts that grow with volume" and the structured price, saving and final price disappeared.

Causes found in the prompt: the calculated figures were appended right after the free text of the customer needs (after the user's own draft signature) with no separation; a rule said "never add other prices, discounts or conditions", which told the model to drop the scale; the email format only asked to "mention the final price and the saving" and had no place for a list; and every rule was a prohibition, none an obligation. A prompt alone cannot guarantee anything with a small model.

## Decision

Three layers. The application never edits the generated text.

**1. Prompt and pre-formatted data.** `app/services/commercial_terms.py` builds the list of mandatory terms: the structured pricing formatted for the output language by the backend ("Precio habitual: 15.000,00 €", "Descuento aplicado: 15 %", "Ahorro: 2.250,00 €", "Precio final: 12.750,00 €") and every line or sentence of the customer needs that contains a figure, verbatim (so each tier of a scale is its own line). The prompt has separate tagged blocks (`<customer_data>`, `<customer_needs>`, `<structured_pricing>`, `<mandatory_commercial_terms>`); the mandatory rules come first in the system prompt (preserve every term, include the structured values, complete scales, no summaries, no single tier, no changed figures, no invented relations, no invented values) and are repeated in the final reminder. Every output format has a place for the list. The structured pricing and the scale are declared independent: the model must not relate the structured 15 % to the 21–50 tier.

**2. Verification and one retry.** After generation, `find_missing` checks the text deterministically: figures are compared by value (15.000,00 = 15000.00 = €15,000.00; 15 % = 15%), each customer-needs term must appear with all its figures on one line of its own (a tier cannot be satisfied by scattered numbers or by another tier), and the structured values must appear outside those tier lines. If anything is missing, the model is called once more with its previous draft and the exact missing lines (`COMMERCIAL_TERMS_MAX_RETRIES`, default 1). The attempt that preserved more terms is kept; token usage and the guest AI-call counter include every call, and a guest without remaining calls gets no retry.

**3. Visible result.** `GenerationRead.missing_commercial_terms` is computed on every read from the stored input and text (no extra column). The UI shows a red warning listing the missing terms, with a "Regenerar" button, in the result and in "Ver". Strict mode (`COMMERCIAL_TERMS_STRICT=true`, off by default) rejects such a text with 502 `commercial_terms_missing` and stores nothing.

An optional live test (`tests/llm`, `RUN_LLM_TESTS=1`) runs the container example against the configured provider. With llama3.2:3b, all six cases (email and proposal × needs only / structured only / both) passed on the first attempt.

## Consequences

- Commercial terms can no longer disappear silently: either they are in the text, or the user sees exactly which are missing.
- The check is numeric: it cannot tell whether the model related two figures wrongly in prose (e.g. "15 % if you buy more than 50"). That is addressed by the prompt rule, not by the verifier.
- A retry doubles the latency of that generation; it only happens when terms are missing.
- Lines with figures that are not commercial (e.g. a phone number in the needs) are also treated as mandatory, which errs on the side of keeping data.

## Alternatives considered

- **Prompt only**: no guarantee with small models.
- **Inserting the missing lines into the text automatically**: rejected by the product owner; the text must come from the model.
- **Asking the model to verify itself**: unreliable for the same reason it omits the data.
