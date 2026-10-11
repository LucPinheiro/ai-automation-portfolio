from app.core.enums import ContentType
from app.prompts.base import PromptTemplate

TEMPLATE = PromptTemplate(
    content_type=ContentType.CUSTOMER_SUMMARY,
    task=(
        "Write an internal summary of the customer for the sales team (not addressed to the customer), "
        "highlighting the opportunity for the product or service."
    ),
    output_format=(
        "Use these sections with headings:\n"
        "- Customer profile\n"
        "- Key needs\n"
        "- Fit with our product or service\n"
        "- Recommended next actions\n"
        "When the customer data does not cover a point, say briefly that it was not provided "
        "instead of guessing it.\n"
        "In Fit with our product or service, list every mandatory commercial line, complete and with every figure unchanged.\n"
        "If the salesperson is provided, name them as the account owner in Recommended next actions. "
        "This is internal: no greeting and no signature."
    ),
)
