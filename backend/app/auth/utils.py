"""Password hashing helpers — Argon2ID via pwdlib (NFR-004)."""

from pwdlib import PasswordHash

_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a plaintext password with Argon2ID."""
    return _hasher.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against its stored hash."""
    return _hasher.verify(plain, hashed)
