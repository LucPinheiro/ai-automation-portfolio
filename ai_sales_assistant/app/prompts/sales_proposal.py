from app.core.enums import ContentType
from app.prompts.base import PromptTemplate

TEMPLATE = PromptTemplate(
    content_type=ContentType.SALES_PROPOSAL,
    task=(
        "Write a structured sales proposal that shows how the product or service solves the "
        "customer's needs, in the context of their company and industry."
    ),
    output_format=(
        "Use these sections with headings:\n"
        "1. Context and customer needs\n"
        "2. Proposed solution\n"
        "3. Expected benefits\n"
        "4. Next steps\n"
        "In Expected benefits, describe qualitative benefits linked to the customer's needs, using "
        "prudent wording such as 'can help'; do not quantify them unless the figure is in the customer data.\n"
        "In Proposed solution, add a list of commercial terms with every mandatory line, "
        "complete and with every figure unchanged (every tier of any scale, and the structured pricing if provided).\n"
        "Do not invent timelines; keep any deadline written in the customer needs.\n"
        "In Next steps, name the salesperson as the contact person if provided.\n"
        "End with a professional closing, then the salesperson's name and company only if they are provided."
    ),
)
