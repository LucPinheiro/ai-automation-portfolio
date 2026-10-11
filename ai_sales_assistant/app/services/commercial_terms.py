"""Mandatory commercial terms: what the generated text must contain, and whether it does.

Two sources, kept independent of each other:
- Structured pricing (price / discount fields), calculated by app.services.pricing and formatted
  here for the output language: "Precio habitual: 15.000,00 €".
- Commercial data written by the user in the customer needs: every line or sentence with a
  figure (prices, percentages, quantities, ranges, dates, deadlines...) is extracted verbatim, so a
  discount scale keeps every tier.

The AI receives the list and must include every line in the output language: it may translate the
words, never the figures. After generation, `find_missing` checks the figures of each term
deterministically, not its wording; the application never edits the text itself.
"""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Literal

from app.core.enums import Language
from app.services.pricing import CENT, PriceBreakdown, calculate, money

Source = Literal["structured_pricing", "customer_needs"]


@dataclass(frozen=True)
class CommercialTerm:
    """A line the generated text must contain, and the figures that identify it."""

    text: str
    source: Source
    figures: tuple[str, ...]


# --- Figures ----------------------------------------------------------------------------------------

_DATE = r"\d{1,2}/\d{1,2}/\d{2,4}"
_GROUPED = r"\d{1,3}(?:[.,   ]\d{3})+(?:[.,]\d{1,2})?"
_PLAIN = r"\d+(?:[.,]\d+)?"
FIGURE = re.compile(rf"(?<![\w/])(?:{_DATE}|{_GROUPED}|{_PLAIN})(?![\w/])")


def _number_key(token: str) -> str | None:
    """Canonical value of a number written in Spanish or English style ("15.000,00" == "15000.00")."""
    text = re.sub(r"[   ]", "", token)
    if "." in text and "," in text:
        decimal_mark = "," if text.rfind(",") > text.rfind(".") else "."
        text = text.replace("." if decimal_mark == "," else ",", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", "") if re.fullmatch(r"\d{1,3}(,\d{3})+", text) else text.replace(",", ".")
    elif "." in text and re.fullmatch(r"\d{1,3}(\.\d{3})+", text):
        text = text.replace(".", "")
    try:
        return str(Decimal(text).quantize(CENT))
    except InvalidOperation:
        return None


def figures_in(text: str) -> list[str]:
    """Every figure in a text, as comparable keys (numbers by value, dates literally)."""
    keys = []
    for match in FIGURE.finditer(text):
        token = match.group(0)
        key = f"date:{token}" if "/" in token else _number_key(token)
        if key is not None:
            keys.append(key)
    return keys


# --- Structured pricing, formatted for the output language ----------------------------------------

_LABELS: dict[Language, dict[str, str]] = {
    Language.SPANISH: {"price": "Precio", "original": "Precio habitual", "discount": "Descuento aplicado",
                       "saving": "Ahorro", "final": "Precio final"},
    Language.ENGLISH: {"price": "Price", "original": "Regular price", "discount": "Discount applied",
                       "saving": "Saving", "final": "Final price"},
    Language.PORTUGUESE: {"price": "Preço", "original": "Preço habitual", "discount": "Desconto aplicado",
                          "saving": "Poupança", "final": "Preço final"},
    Language.FRENCH: {"price": "Prix", "original": "Prix habituel", "discount": "Remise appliquée",
                      "saving": "Économie", "final": "Prix final"},
}


def _group(integer: str, separator: str) -> str:
    groups = []
    while len(integer) > 3:
        groups.insert(0, integer[-3:])
        integer = integer[:-3]
    return separator.join([integer, *groups])


def format_amount(value: Decimal, language: Language) -> str:
    """15000 -> "15.000,00 €" (es, pt), "15 000,00 €" (fr), "€15,000.00" (en)."""
    integer, cents = f"{money(value):.2f}".split(".")
    if language is Language.ENGLISH:
        return f"€{_group(integer, ',')}.{cents}"
    separator = " " if language is Language.FRENCH else "."
    return f"{_group(integer, separator)},{cents} €"


def format_percent(value: Decimal, language: Language) -> str:
    """15 -> "15 %" (es, fr) or "15%" (en, pt); 12.5 -> "12,5 %" (es)."""
    text = f"{value:f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if language is not Language.ENGLISH:
        text = text.replace(".", ",")
    return f"{text} %" if language in (Language.SPANISH, Language.FRENCH) else f"{text}%"


def structured_terms(breakdown: PriceBreakdown | None, language: Language) -> list[CommercialTerm]:
    if breakdown is None:
        return []
    labels = _LABELS[language]

    def term(label: str, value: str) -> CommercialTerm:
        text = f"{labels[label]}: {value}"
        return CommercialTerm(text=text, source="structured_pricing", figures=tuple(figures_in(value)))

    if breakdown.discount_percent is None:
        return [term("price", format_amount(breakdown.original_price, language))]
    return [
        term("original", format_amount(breakdown.original_price, language)),
        term("discount", format_percent(breakdown.discount_percent, language)),
        term("saving", format_amount(breakdown.discount_amount, language)),
        term("final", format_amount(breakdown.final_price, language)),
    ]


# --- Commercial data written in the customer needs -------------------------------------------------

_BULLET = re.compile(r"^\s*(?:[-*•·–]|\d{1,2}[.)](?=\s))\s*")
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¿¡])")


def needs_terms(customer_needs: str) -> list[CommercialTerm]:
    """Every line (or sentence) of the customer needs that contains a figure, verbatim and in order."""
    terms: list[CommercialTerm] = []
    seen: set[str] = set()
    for line in customer_needs.splitlines():
        line = _BULLET.sub("", line).strip()
        for sentence in _SENTENCE_BREAK.split(line):
            sentence = sentence.strip()
            figures = figures_in(sentence)
            if figures and sentence not in seen:
                seen.add(sentence)
                terms.append(CommercialTerm(text=sentence, source="customer_needs", figures=tuple(figures)))
    return terms


def terms_for(
    *, language: Language, customer_needs: str, price: Decimal | None, discount_percent: Decimal | None
) -> list[CommercialTerm]:
    """All mandatory terms of a generation: structured pricing first, then the customer needs."""
    breakdown = calculate(price, discount_percent) if price is not None else None
    return structured_terms(breakdown, language) + needs_terms(customer_needs)


# --- Verification -----------------------------------------------------------------------------------


def _contains(line_figures: list[str], required: tuple[str, ...]) -> bool:
    available = list(line_figures)
    for figure in required:
        if figure not in available:
            return False
        available.remove(figure)
    return True


def find_missing(terms: list[CommercialTerm], text: str) -> list[CommercialTerm]:
    """Terms whose figures do not appear together in one line of the text.

    Each customer-needs term (e.g. one tier of a scale) needs its own line, so the structured
    15 % can never be "found" in the 21-50 tier line, nor one tier stand in for another.
    Structured pricing lines may share a line with each other ("12.750,00 € (ahorro 2.250,00 €)").
    """
    lines = [figures_in(line) for line in text.splitlines()]
    used: set[int] = set()
    missing: list[CommercialTerm] = []

    needs = sorted((t for t in terms if t.source == "customer_needs"), key=lambda t: -len(t.figures))
    for term in needs:
        match = next((i for i, figs in enumerate(lines) if i not in used and _contains(figs, term.figures)), None)
        if match is None:
            missing.append(term)
        else:
            used.add(match)

    for term in (t for t in terms if t.source == "structured_pricing"):
        if not any(i not in used and _contains(figs, term.figures) for i, figs in enumerate(lines)):
            missing.append(term)

    # Report in the original order of the terms.
    order = {id(term): index for index, term in enumerate(terms)}
    return sorted(missing, key=lambda term: order[id(term)])
