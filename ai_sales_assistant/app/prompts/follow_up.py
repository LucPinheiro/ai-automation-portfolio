from app.core.enums import ContentType
from app.prompts.base import PromptTemplate

TEMPLATE = PromptTemplate(
    content_type=ContentType.FOLLOW_UP,
    task=(
        "Write a follow-up email for a customer who has already been contacted about the product "
        "or service. Briefly recall the value for their needs and propose a concrete next step."
    ),
    output_format=(
        "A first line starting with 'Subject:' followed by a one-line subject.\n"
        "A greeting addressed to the customer.\n"
        "One or two short paragraphs, shorter than a first-contact email.\n"
        "If there are mandatory commercial terms, after the first paragraph write one short sentence "
        "and then every mandatory line as a bullet list, complete and with every figure unchanged.\n"
        "One clear call to action, without proposing a specific date or time.\n"
        "A professional closing line, then the salesperson's name and company only if they are provided."
    ),
)
