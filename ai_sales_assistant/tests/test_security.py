from argon2 import PasswordHasher

from app.core import security
from app.core.security import (
    generate_token,
    hash_password,
    hash_token,
    password_needs_rehash,
    verify_password,
)


def test_password_is_hashed_with_argon2id_and_verifies() -> None:
    password_hash = hash_password("correct-horse-battery")

    assert password_hash.startswith("$argon2id$")
    assert "correct-horse-battery" not in password_hash
    assert verify_password("correct-horse-battery", password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_same_password_gets_different_hashes() -> None:
    # Random salt per hash.
    assert hash_password("same-password") != hash_password("same-password")


def test_verify_rejects_malformed_hashes() -> None:
    assert not verify_password("anything", "not-a-hash")
    assert not verify_password("anything", "")


def test_outdated_parameters_need_rehash(monkeypatch) -> None:
    old_hash = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash("pw-123456")
    monkeypatch.setattr(security, "_hasher", PasswordHasher(time_cost=2, memory_cost=16, parallelism=1))

    assert password_needs_rehash(old_hash)
    assert not password_needs_rehash(hash_password("pw-123456"))


def test_tokens_are_random_and_url_safe() -> None:
    tokens = {generate_token() for _ in range(50)}

    assert len(tokens) == 50
    for token in tokens:
        assert len(token) >= 43  # 32 random bytes, base64url
        assert set(token) <= set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")


def test_token_hash_is_deterministic_sha256_and_hides_the_token() -> None:
    token = generate_token()

    assert hash_token(token) == hash_token(token)
    assert len(hash_token(token)) == 64
    assert token not in hash_token(token)
