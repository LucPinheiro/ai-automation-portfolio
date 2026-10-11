import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# Argon2id with the library's defaults (RFC 9106 low-memory profile), as recommended by OWASP.
_hasher = PasswordHasher()

# Verified against when an email is unknown, so login takes the same time either way.
_DUMMY_PASSWORD_HASH = _hasher.hash("timing-equaliser-not-a-real-password")

TOKEN_BYTES = 32


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    """True when the hash was made with older Argon2 parameters and should be upgraded."""
    return _hasher.check_needs_rehash(password_hash)


def burn_password_check(password: str) -> None:
    """Spend the same work as a real check, for unknown accounts (prevents user enumeration by timing)."""
    verify_password(password, _DUMMY_PASSWORD_HASH)


def generate_token() -> str:
    """A URL-safe random token with 256 bits of entropy (session ids, password reset links)."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    # Tokens are random and high-entropy, so a fast hash is enough: only the hash is stored,
    # and a leaked database cannot be used to hijack sessions or reset passwords.
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
