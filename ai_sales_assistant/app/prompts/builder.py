from app.core.enums import Language
from app.prompts.base import FINAL_REMINDER, LANGUAGE_NAMES, SYSTEM_PROMPT, TONE_GUIDELINES, Prompt, language_rule
from app.prompts.registry import get_template
from app.schemas.generation import GenerationCreate
from app.services.commercial_terms import CommercialTerm, terms_for
from app.services.pricing import calculate, prompt_lines

# Every data block has its own tags, so free text can never run into the calculated figures.
DATA_BLOCKS = ("customer_data", "customer_needs", "structured_pricing", "mandatory_commercial_terms", "previous_draft")
DATA_TAGS = tuple(tag for block in DATA_BLOCKS for tag in (f"<{block}>", f"</{block}>"))
NOT_PROVIDED = "not provided"


def _sanitize(value: str) -> str:
    # Prevents user input from closing a data block and injecting instructions.
    for tag in DATA_TAGS:
        value = value.replace(tag, "")
    return value


def _optional(value: str | None) -> str:
    # An explicit marker, so the model never fills the gap with an invented name.
    return _sanitize(value) if value else NOT_PROVIDED


def _structured_pricing(data: GenerationCreate) -> str:
    # Figures calculated by the backend (Decimal, cents rounded half up): the AI only quotes them.
    breakdown = calculate(data.price, data.discount_percent) if data.price is not None else None
    return "\n".join(prompt_lines(breakdown))


def mandatory_terms(data: GenerationCreate) -> list[CommercialTerm]:
    return terms_for(
        language=data.language,
        customer_needs=data.customer_needs,
        price=data.price,
        discount_percent=data.discount_percent,
    )


def _terms_list(terms: list[CommercialTerm]) -> str:
    if not terms:
        return "none"
    return "\n".join(f"- {_sanitize(term.text)}" for term in terms)


def build_prompt(data: GenerationCreate) -> Prompt:
    """Render the prompt for the requested content type from the generation input."""
    template = get_template(data.content_type)
    user_prompt = f"""\
Task: {template.task}

Output format:
{template.output_format}

Language: {LANGUAGE_NAMES[data.language]}. Write the entire output in this language.
Tone: {data.tone.value} ({TONE_GUIDELINES[data.tone]}).

<customer_data>
Customer (recipient): {_sanitize(data.customer)}
Customer's company: {_sanitize(data.company)}
Industry: {_sanitize(data.industry)}
Product or service: {_sanitize(data.product_or_service)}
Salesperson (sender): {_optional(data.salesperson)}
Salesperson's company: {_optional(data.salesperson_company)}
</customer_data>

<customer_needs>
Written by the user. Keep every commercial term in it.
{_sanitize(data.customer_needs)}
</customer_needs>

<structured_pricing>
Calculated by the application. Independent from any scale or condition in the customer needs.
{_structured_pricing(data)}
</structured_pricing>

<mandatory_commercial_terms>
Include every line below in your text as a list (one line per item), written in the output language: translate the words if needed, keep every figure exactly as written:
{_terms_list(mandatory_terms(data))}
</mandatory_commercial_terms>

{FINAL_REMINDER}

{language_rule(data.language)}"""
    return Prompt(system=f"{language_rule(data.language)}\n\n{SYSTEM_PROMPT}", user=user_prompt)


def build_retry_prompt(original: Prompt, draft: str, missing: list[CommercialTerm], language: Language) -> Prompt:
    """Second attempt: the same request, the previous draft and exactly what it left out.

    The model rewrites the whole text itself; the application never inserts anything into it.
    """
    missing_lines = "\n".join(f"- {_sanitize(term.text)}" for term in missing)
    user_prompt = f"""\
{original.user}

<previous_draft>
{_sanitize(draft)}
</previous_draft>

Your previous draft left out these mandatory commercial terms:
{missing_lines}

Rewrite the complete text following every rule above. Include each of these lines as a list, in the \
output language and with every figure exactly as written, together with every other mandatory commercial term. Return only the new text.

{language_rule(language)}"""
    return Prompt(system=original.system, user=user_prompt)
