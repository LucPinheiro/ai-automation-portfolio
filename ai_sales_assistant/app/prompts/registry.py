from types import MappingProxyType

from app.core.enums import ContentType
from app.prompts import commercial_email, customer_summary, follow_up, sales_proposal, whatsapp
from app.prompts.base import PromptTemplate

PROMPT_TEMPLATES: MappingProxyType[ContentType, PromptTemplate] = MappingProxyType(
    {
        module.TEMPLATE.content_type: module.TEMPLATE
        for module in (commercial_email, sales_proposal, follow_up, whatsapp, customer_summary)
    }
)


def get_template(content_type: ContentType) -> PromptTemplate:
    return PROMPT_TEMPLATES[content_type]
