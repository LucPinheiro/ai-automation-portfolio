from app.core.enums import ContentType
from app.prompts.base import PromptTemplate

TEMPLATE = PromptTemplate(
    content_type=ContentType.COMMERCIAL_EMAIL,
    task=(
        "Write a first-contact commercial email that introduces the product or service, "
        "connects it to the customer's needs and industry, and invites them to a short call or meeting."
    ),
    output_format=(
        "A first line starting with 'Subject:' followed by a one-line subject.\n"
        "A greeting addressed to the customer.\n"
        "Two to four short paragraphs.\n"
        "If there are mandatory commercial terms, after the first paragraph write one short sentence "
        "and then every mandatory line as a bullet list, complete and with every figure unchanged.\n"
        "One clear call to action, without proposing a specific date or time.\n"
        "A professional closing line, then the salesperson's name and company only if they are provided."
    ),
)
