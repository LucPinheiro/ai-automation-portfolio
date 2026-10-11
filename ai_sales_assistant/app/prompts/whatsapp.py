from app.core.enums import ContentType
from app.prompts.base import PromptTemplate

TEMPLATE = PromptTemplate(
    content_type=ContentType.WHATSAPP,
    task=(
        "Write a short WhatsApp message to the customer about the product or service, "
        "related to their needs, that invites a reply."
    ),
    output_format=(
        "Short plain text (around 600 characters) in 1-3 short paragraphs. "
        "If there are mandatory commercial terms, put every line on its own line, with every figure unchanged, even if "
        "the message gets longer: never drop a term to keep it short. "
        "No subject line, no bold or headings. At most one emoji, only if it suits the tone. "
        "If the salesperson is provided, end with their first name; otherwise add no signature. "
        "No figures that are not in the customer data."
    ),
)
