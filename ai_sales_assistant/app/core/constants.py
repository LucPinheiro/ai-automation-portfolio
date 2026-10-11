# Field length limits shared by the ORM columns and the request schemas.
CUSTOMER_MAX_LENGTH = 150
COMPANY_MAX_LENGTH = 150
INDUSTRY_MAX_LENGTH = 100
PRODUCT_OR_SERVICE_MAX_LENGTH = 200
CUSTOMER_NEEDS_MAX_LENGTH = 2000
SALESPERSON_MAX_LENGTH = 150
SALESPERSON_COMPANY_MAX_LENGTH = 150

# Pagination for list endpoints.
DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 100

# Users and passwords (NIST SP 800-63B: length matters, composition rules do not).
USER_NAME_MAX_LENGTH = 100
EMAIL_MAX_LENGTH = 254
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 30
# Lowercase letters, digits, dot, underscore and hyphen; no "@", so a login identifier with "@" is an email.
USERNAME_PATTERN = r"^[a-z0-9._-]+$"
GUEST_NAME = "Invitado"
