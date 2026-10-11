from enum import StrEnum


class ContentType(StrEnum):
    COMMERCIAL_EMAIL = "commercial_email"
    SALES_PROPOSAL = "sales_proposal"
    FOLLOW_UP = "follow_up"
    WHATSAPP = "whatsapp"
    CUSTOMER_SUMMARY = "customer_summary"


class Language(StrEnum):
    SPANISH = "es"
    ENGLISH = "en"
    PORTUGUESE = "pt"
    FRENCH = "fr"


class Tone(StrEnum):
    PROFESSIONAL = "professional"
    FORMAL = "formal"
    FRIENDLY = "friendly"
    PERSUASIVE = "persuasive"
    CONCISE = "concise"
